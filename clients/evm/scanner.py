
import asyncio
from decimal import Decimal
from typing import Any, Literal
from sqlalchemy.orm import sessionmaker
from chains.dto import ChainConfig
from clients.evm.dex.dto import PoolInfoBase, TokenSnapshot
from clients.evm.dex.uniswap import AerodromeV2Client, UniswapV2Client, UniswapV3Client
from clients.evm.dto import TokenMeta
from clients.evm.token import TokenService


from dataclasses import dataclass

from clients.evm.wallet import WalletClient

@dataclass
class ChainWithToken:
    chain_config: ChainConfig
    token_meta: TokenMeta

@dataclass
class WalletItem:
    wallet_name: str
    address: str

@dataclass
class ChainBalances:
    wallets: list[WalletItem]
    native_total: int | float
    token_total: int | float


@dataclass
class BestPool:
    chain: ChainConfig
    category: Literal['eth_token', 'eth_stable', 'stable_token']
    dex: str
    version: str
    pool: PoolInfoBase
    tvl: Decimal
    stable_symbol: str | None = None
    stable_address: str | None = None


@dataclass
class ScanResult:
    route_type: Literal["direct", "multihop"] | None
    chains_found: list[ChainWithToken]
    market_cap: Decimal
    best_eth_token_pool: BestPool | None
    best_eth_stable_pool: BestPool | None
    best_stable_token_pool: BestPool | None
    token_meta: TokenMeta | None
    wallet_balances: list[ChainBalances]
    token_price: Decimal
    token_price_raw: Decimal


class LiquidityScanner:
    DEX_CLIENTS = {
        "uniswap_v2": UniswapV2Client,
        "uniswap_v3": UniswapV3Client,
        "aerodrome_v2": AerodromeV2Client
    }

    def __init__(self, chain_configs: list[ChainConfig], session_factory: sessionmaker):
        self.chain_configs = chain_configs
        self.session_factory = session_factory

    async def scan_token(self, token_address: str, wallets: dict[str, list[str]], price: Decimal) -> ScanResult:
        if not self.chain_configs:
            return ScanResult(
                route_type=None,
                chains_found=[],
                market_cap=Decimal(0),
                best_eth_token_pool=None,
                best_eth_stable_pool=None,
                best_stable_token_pool=None,
                token_meta=None,
                wallet_balances=[],
                token_price=Decimal("0"),
                token_price_raw=Decimal("0")
            )
        
        chains_with_token = await self._fetch_chains_with_token(token_address)

        if not chains_with_token:
            return ScanResult(
                route_type=None,
                chains_found=[],
                market_cap=Decimal(0),
                best_eth_token_pool=None,
                best_eth_stable_pool=None,
                best_stable_token_pool=None,
                token_meta=None,
                wallet_balances=[],
                token_price=Decimal("0"),
                token_price_raw=Decimal("0")
            )
        
        snapshots_task = self._fetch_all_snapshots(chains_with_token, token_address)
        balances_task = self._fetch_wallet_balances(
            chains_with_token,
            token_address,
            wallets
        )

        all_snapshots, wallet_balances = await asyncio.gather(
            snapshots_task,
            balances_task
        )

        if not all_snapshots:
            return ScanResult(
                route_type=None,
                chains_found=[],
                market_cap=Decimal(0),
                best_eth_token_pool=None,
                best_eth_stable_pool=None,
                best_stable_token_pool=None,
                token_meta=None,
                wallet_balances=[],
                token_price=Decimal("0"),
                token_price_raw=Decimal("0")
            )
        
        return self._build_scan_result(
            all_snapshots, 
            chains_with_token,
            wallet_balances,
            price
        )

    async def _fetch_wallet_balances(
        self, 
        chains: list[ChainWithToken], 
        token_address: str,
        wallets: dict[str, list[str]]
    ) -> dict:
        tasks = []

        for chain in chains:
            chain_id = chain.chain_config.chain_id

            items = wallets.get(str(chain_id), [])

            if not items:
                continue

            addresses = [w["address"] for w in items if w.get("address")]

            if not addresses:
                continue

            task = self._get_balances_for_chain(
                chain.chain_config,
                token_address,
                addresses
            )

            tasks.append((chain_id, task))

        results = await asyncio.gather(
            *[task for _, task in tasks],
            return_exceptions=True
        )

        balances = {}
        for (chain_id, _), result in zip(tasks, results):
            if isinstance(result, Exception):
                continue

            native_map: dict[str, Any] = result.get("native_balance", {}) if isinstance(result, dict) else {}
            token_map: dict[str, Any]  = result.get("token_balance",  {}) if isinstance(result, dict) else {}

            items = wallets.get(str(chain_id), [])
            wallet_rows: list[dict[str, Any]] = []
            native_total = 0
            token_total  = 0

            for w in items:
                addr = w["address"]
                row = {
                    "wallet_name": w["wallet_name"],
                    "id": w["id"],
                    "address": addr,
                    "native_balance": native_map.get(addr, 0),
                    "token_balance": token_map.get(addr, 0),
                }
                wallet_rows.append(row)
                nv = row["native_balance"]
                tv = row["token_balance"]
                native_total += nv if isinstance(nv, (int, float)) else 0
                token_total  += tv if isinstance(tv, (int, float)) else 0

            balances[chain_id] = {"wallets": wallet_rows}
        return balances
    
    async def _get_balances_for_chain(
        self,
        chain_config: ChainConfig,
        token_address: str,
        addresses: list[str]
    ):
        async with WalletClient(chain_config) as wallet:
            native_balances, token_balances = await asyncio.gather(
                wallet.get_native_balances(addresses),
                wallet.get_token_balances(token_address, addresses),
                return_exceptions=True
            )
            
            return {
                "native_balance": native_balances if isinstance(native_balances, dict) else {},
                "token_balance": token_balances if isinstance(token_balances, dict) else {}
            }

    async def _fetch_chains_with_token(
        self,
        token_address: str
    ) -> list[ChainWithToken]:
        tasks = [
            self._check_token_in_chain(
                chain_config,
                token_address
            ) for chain_config in self.chain_configs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        chains_with_token = [
            result for result in results if isinstance(result, ChainWithToken)
        ]
        return chains_with_token

    async def _check_token_in_chain(
        self,
        chain_config: ChainConfig,
        token_address: str
    ) -> ChainWithToken | None:
        async with self.session_factory() as session:
            async with TokenService(chain_config) as token_service:
                token_meta = await token_service.get_token_meta(
                    session,
                    token_address,
                    chain_config.chain_id
                )

                if token_meta:
                    return ChainWithToken(
                        chain_config=chain_config, 
                        token_meta=token_meta
                    )
                return None
            
    async def _fetch_all_snapshots(
        self,
        chains_with_token: list[ChainWithToken],
        token_address: str
    ) -> list[TokenSnapshot]:
        tasks = []

        for chain in chains_with_token:
            chain_config = chain.chain_config

            chain_dex = chain_config.available_dex

            for dex in chain_dex:
                if dex not in self.DEX_CLIENTS:
                    continue

                task = self._fetch_snapshot_from_dex(
                    chain,
                    token_address,
                    dex,
                )

                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        snapshots = [result for result in results if isinstance(result, TokenSnapshot)]

        return snapshots
    
    async def _fetch_snapshot_from_dex(
        self,
        chain: ChainWithToken,
        token_address: str,
        dex: str
    ) -> TokenSnapshot | None:
        dex_client = self.DEX_CLIENTS[dex]

        async with dex_client(chain.chain_config) as client:
            snapshot = await client.get_snapshot(
                token_address,
                chain.token_meta
            )

            if snapshot:
                return snapshot
            return None
    
    @staticmethod
    def _get_best_pools(snapshots: list[TokenSnapshot]) -> dict[str, BestPool | None]:
        best = {
            'eth_token': None,
            'eth_stable': None,
            'stable_token': None
        }
        
        for s in snapshots:
            if s.eth_token_pool:
                tvl = s.eth_token_pool.tvl
                if not best['eth_token'] or tvl > best['eth_token'].tvl:
                    best['eth_token'] = BestPool(
                        chain=s.chain,
                        category='eth_token',
                        dex=s.dex,
                        version=s.version,
                        pool=s.eth_token_pool,
                        tvl=tvl
                    )
            
            eth_stable = s.eth_stable_pools
            if eth_stable and eth_stable.get('pool'):
                pool = eth_stable['pool']
                tvl = pool.tvl

                if not best['eth_stable'] or tvl > best['eth_stable'].tvl:
                    best['eth_stable'] = BestPool(
                        chain=s.chain,
                        category='eth_stable',
                        dex=s.dex,
                        version=s.version,
                        pool=pool,
                        tvl=tvl,
                        stable_symbol=eth_stable.get('stable'),
                        stable_address=eth_stable.get('address'),
                    )
            
            stable_token = s.stable_token_pools
            if stable_token and stable_token.get('pool'):
                pool = stable_token['pool']
                tvl = pool.tvl

                if not best['stable_token'] or tvl > best['stable_token'].tvl:
                    best['stable_token'] = BestPool(
                        chain=s.chain,
                        category='stable_token',
                        dex=s.dex,
                        version=s.version,
                        pool=pool,
                        tvl=tvl,
                        stable_symbol=stable_token.get('stable'),
                        stable_address=stable_token.get('address'),
                    )
        
        return best
        
    def _build_scan_result(
        self,
        all_snapshots: list[TokenSnapshot],
        chains_found: list[ChainWithToken],
        wallet_balances: dict[str, dict[str, dict[str, Decimal]]],
        price: Decimal
    ) -> ScanResult:
        best_pools = self._get_best_pools(all_snapshots)

        eth_token_tvl = best_pools['eth_token'].tvl
        stable_token_tvl = best_pools['stable_token'].tvl if best_pools['stable_token'] else Decimal(0)

        route_type = "multihop" if stable_token_tvl > eth_token_tvl * price else "direct"
        
        token_meta = all_snapshots[0].meta

        supply = Decimal(token_meta.supply) / (10 ** token_meta.decimals)
        
        if route_type == "multihop" and best_pools['stable_token']:
            token_price_usd = best_pools['stable_token'].pool.price
            token_price_eth = token_price_usd / price
            token_price_eth_raw = token_price_eth * (10 ** token_meta.decimals)
            market_cap = token_price_usd * supply
        elif route_type == "direct" and best_pools['eth_token']:
            token_price_eth = best_pools['eth_token'].pool.price
            token_price_eth_raw = best_pools['eth_token'].pool.price_raw * (10 ** token_meta.decimals)
            token_price_usd = token_price_eth * price
            market_cap = token_price_usd * supply

        return ScanResult(
            route_type=route_type,
            best_eth_token_pool=best_pools['eth_token'],
            best_eth_stable_pool=best_pools['eth_stable'],
            best_stable_token_pool=best_pools['stable_token'],
            chains_found=chains_found,
            token_meta=token_meta,
            wallet_balances=wallet_balances,
            market_cap=market_cap,
            token_price=token_price_eth,
            token_price_raw=token_price_eth_raw
        )
