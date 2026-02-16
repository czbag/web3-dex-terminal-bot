from decimal import Decimal, getcontext

from web3 import AsyncWeb3
from eth_abi.abi import encode, decode as abi_decode
from sqlalchemy.ext.asyncio import AsyncSession

from models.dtos import PoolInfo, TokenMeta, TokenSnapshot, NetworkConfig
from web3_clients.token import TokenService

from eth_utils.crypto import keccak

from web3_clients.base import BaseWeb3Client


class UniswapV3Client(BaseWeb3Client):
    FACTORY_ADDRESS = "0x33128a8fC17869897dcE68Ed026d694621f6FDfD"
    FEE_TIERS = [500, 3000, 10000]

    FACTORY_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "tokenA", "type": "address"},
                {"internalType": "address", "name": "tokenB", "type": "address"},
                {"internalType": "uint24", "name": "fee", "type": "uint24"},
            ],
            "name": "getPool",
            "outputs": [{"internalType": "address", "name": "pool", "type": "address"}],
            "stateMutability": "view",
            "type": "function",
        }
    ]

    POOL_ABI = [
        {
            "inputs": [],
            "name": "slot0",
            "outputs": [
                {"internalType": "uint160", "name": "sqrtPriceX96", "type": "uint160"},
                {"internalType": "int24", "name": "tick", "type": "int24"},
                {
                    "internalType": "uint16",
                    "name": "observationIndex",
                    "type": "uint16",
                },
                {
                    "internalType": "uint16",
                    "name": "observationCardinality",
                    "type": "uint16",
                },
                {
                    "internalType": "uint16",
                    "name": "observationCardinalityNext",
                    "type": "uint16",
                },
                {"internalType": "uint8", "name": "feeProtocol", "type": "uint8"},
                {"internalType": "bool", "name": "unlocked", "type": "bool"},
            ],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "liquidity",
            "outputs": [{"internalType": "uint128", "name": "", "type": "uint128"}],
            "stateMutility": "view",
            "type": "function",
        },
    ]

    POOL_INIT_CODE_HASH = (
        "e34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54"
    )
    
    def __init__(self, network_config: NetworkConfig, w3: AsyncWeb3 | None = None):
        super().__init__(network_config, w3)
        self.token_service = TokenService(network_config, self.w3)

    @staticmethod
    def _human_amount(raw: int, decimals: int) -> Decimal:
        return Decimal(raw) / (Decimal(10) ** decimals)

    @staticmethod
    def _calculate_price(sqrt_price: int, dec0: int, dec1: int) -> Decimal:
        getcontext().prec = 50
        q96 = Decimal(2) ** 96
        price = (Decimal(sqrt_price) / q96) ** 2
        return price * (Decimal(10) ** (dec0 - dec1))
    
    @staticmethod
    def _sort_tokens(token_a: str, token_b: str) -> tuple[str, str]:
        return (token_a, token_b) if token_a.lower() < token_b.lower() else (token_b, token_a)

    async def get_token_snapshot(
        self, 
        token_address: str, 
        token_meta: TokenMeta
    ) -> TokenSnapshot | None:
        token = AsyncWeb3.to_checksum_address(token_address)
        weth = AsyncWeb3.to_checksum_address(self.network_config.weth_address)

        token_a, token_b = self._sort_tokens(token, weth)

        pools = self._fetch_pool_addresses(token_a, token_b)

        pools_infos = await self._fetch_pool_data(
            token, weth, pools, token_meta.decimals, token_a < token_b
        )

        if len(pools_infos) == 0:
            return None

        best_pool = max(pools_infos, key=lambda p: p.tvl) if pools_infos else None

        market_cap = None
        if best_pool:
            market_cap = (
                Decimal(token_meta.supply) / (Decimal(10) ** token_meta.decimals)
            ) * best_pool.price_token

        return TokenSnapshot(
            network=self.network_config.name,
            token=token,
            weth=weth,
            meta=token_meta,
            pools=pools_infos,
            best=best_pool,
            market_cap=market_cap,
        )

    def _fetch_pool_addresses(
        self, token_a: str, token_b: str
    ) -> list[tuple[int, str]]:
        pools = []
        for fee in self.FEE_TIERS:
            salt = keccak(encode(["address", "address", "uint24"], [token_a, token_b, fee]))
            packed = (
                b"\xff"
                + bytes.fromhex(self.network_config.pool_deployer)
                + salt
                + bytes.fromhex(self.POOL_INIT_CODE_HASH)
            )
            pools.append((fee, AsyncWeb3.to_checksum_address(keccak(packed)[12:])))

        return pools

    async def _fetch_pool_data(
        self,
        token: str,
        weth: str,
        pools: list[tuple[int, str]],
        token_decimals: int,
        token_is_token_a: bool,
    ) -> list[PoolInfo]:
        if not pools:
            return []
        
        contract = self._get_erc20_contract(token)
        weth_contract = self._get_erc20_contract(weth)

        multicall = self._get_multicall_contract()

        calls = []
        for _, pool in pools:
            pool_contract = self.w3.eth.contract(
                AsyncWeb3.to_checksum_address(pool), 
                abi=self.POOL_ABI
            )
            calls.extend([
                self._create_call(pool, pool_contract.functions.slot0()._encode_transaction_data()),
                self._create_call(pool, pool_contract.functions.liquidity()._encode_transaction_data()),
                self._create_call(token, contract.functions.balanceOf(pool)._encode_transaction_data()),
                self._create_call(weth, weth_contract.functions.balanceOf(pool)._encode_transaction_data()),
            ])

        results = await multicall.functions.aggregate3(calls).call()

        pool_infos = []

        for _, (fee, pool) in enumerate(pools):
            offset = _ * 4
            slot, slot_bytes = results[offset]
            liq, liq_bytes = results[offset + 1]
            bt, bt_bytes = results[offset + 2]
            bw, bw_bytes = results[offset + 3]

            if not all([
                slot and slot_bytes and len(slot_bytes) > 0,
                bt and bt_bytes,
                bw and bw_bytes
            ]):
                continue

            sqrt_price_x96, *_ = abi_decode(
                ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"],
                slot_bytes
            )

            liquidity_raw = (
                int.from_bytes(liq_bytes[-32:], "big") if liq and liq_bytes else 0
            )

            balance_token_raw = int(abi_decode(["uint256"], bt_bytes)[0])
            balance_weth_raw = int(abi_decode(["uint256"], bw_bytes)[0])

            amount_token = self._human_amount(balance_token_raw, token_decimals)
            amount_weth = self._human_amount(balance_weth_raw, 18)

            if token_is_token_a:
                price_token = self._calculate_price(
                    sqrt_price_x96,
                    token_decimals,
                    18
                )
            else:
                price_token_per_weth = self._calculate_price(
                    sqrt_price_x96, 
                    18, 
                    token_decimals
                )

                price_token = (
                    (Decimal(1) / price_token_per_weth)
                    if price_token_per_weth != 0 else Decimal(0)
                )

            tvl = amount_token * price_token + amount_weth

            pool_infos.append(
                PoolInfo(
                    fee=fee,
                    pool=pool,
                    sqrt_price=int(sqrt_price_x96),
                    liquidity_raw=int(liquidity_raw),
                    amount_token=amount_token,
                    amount_weth=amount_weth,
                    price_token=price_token,
                    tvl=tvl
                )
            )

        return pool_infos
