from dataclasses import dataclass
from decimal import Decimal, getcontext
from typing import Literal
from web3 import AsyncWeb3
from chains.dto import StableConfig
from clients.evm.base import BaseDexClient
from eth_utils.crypto import keccak
from eth_abi.abi import encode as abi_encode, decode as abi_decode
from eth_abi.packed import encode_packed

from clients.evm.dex.dto import PairPools, PoolInfoV2, PoolInfoV3, PoolInfoAerodromeV2, RouteInfo, TokenPair, TokenSnapshot
from clients.evm.dto import TokenMeta


class UniswapV3Client(BaseDexClient):
    FEE_TIERS = [100, 500, 3000, 10000]

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
                {"internalType": "uint16", "name": "observationIndex", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinality", "type": "uint16"},
                {"internalType": "uint16", "name": "observationCardinalityNext", "type": "uint16"},
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

    POOL_INIT_CODE_HASH = "e34f199b19b2b4f47f68442619d555527d244f78a3297ea89325f843f87b8b54"
    
    @staticmethod
    def _human_amount(raw: int, decimals: int) -> Decimal:
        return Decimal(raw) / (Decimal(10) ** decimals)

    @staticmethod
    def _calculate_price(sqrt_price: int, dec0: int, dec1: int) -> tuple[Decimal, Decimal]:
        getcontext().prec = 60
        q192 = Decimal(2) ** 192
        sqrt_p = Decimal(sqrt_price)
        price_raw = (sqrt_p * sqrt_p) / q192
        price = price_raw * (Decimal(10) ** (Decimal(dec0) - Decimal(dec1)))
        return price_raw, price

    @staticmethod
    def _sort_tokens(token_x: str, token_y: str) -> tuple[str, str, bool]:
        return (token_x, token_y, True) if token_x.lower() < token_y.lower() else (token_y, token_x, False)

    def get_pool_address(self, token_a: str, token_b: str, fee: int) -> str:
        salt = keccak(abi_encode(["address", "address", "uint24"], [token_a, token_b, fee]))
        packed = b"\xff" + bytes.fromhex(self.chain_config.pool_deployer) + salt + bytes.fromhex(self.POOL_INIT_CODE_HASH)
        return AsyncWeb3.to_checksum_address(keccak(packed)[12:])
    
    async def _compute_pool_addresses(
        self,
        pool_keys: list[tuple[str, str, int]]
    ) -> dict[tuple[str, str, int], str]:
        return {
            key: self.get_pool_address(key[0], key[1], key[2])
            for key in pool_keys
        }
    
    def _build_multicall_requests(
        self, 
        pool_addresses: dict[tuple[str, str, int], str]
    ) -> list:
        calls = []
        
        for (token_a, token_b, _), pool_addr in pool_addresses.items():
            pool_contract = self.w3.eth.contract(
                AsyncWeb3.to_checksum_address(pool_addr), 
                abi=self.POOL_ABI
            )
            contract_a = self._get_erc20_contract(token_a)
            contract_b = self._get_erc20_contract(token_b)
            
            calls.extend([
                self._create_call(pool_addr, pool_contract.functions.slot0()._encode_transaction_data()),
                self._create_call(pool_addr, pool_contract.functions.liquidity()._encode_transaction_data()),
                self._create_call(token_a, contract_a.functions.balanceOf(pool_addr)._encode_transaction_data()),
                self._create_call(token_b, contract_b.functions.balanceOf(pool_addr)._encode_transaction_data()),
            ])
        
        return calls
    
    async def _fetch_all_pools_data(
        self,
        pairs: list[TokenPair],
    ) -> dict[tuple[str, str, int], list[tuple[bool, bytes]]]:
        pool_addresses = await self._compute_pool_addresses([
            (pair.token_a, pair.token_b, fee)
            for pair in pairs
            for fee in self.FEE_TIERS
        ])

        multicall = self._get_multicall_contract()
        calls = self._build_multicall_requests(pool_addresses)
        results = await multicall.functions.aggregate3(calls).call()

        return {
            key: results[i * 4:(i + 1) * 4]
            for i, key in enumerate(pool_addresses.keys())
        }

    def _create_token_pair(
        self, 
        token_x: str, 
        token_y: str,
        decimals_x: int,
        decimals_y: int,
        target_is_y: bool = True
    ) -> TokenPair:
        token_a, token_b, not_swapped = self._sort_tokens(token_x, token_y)

        if not_swapped:
            return TokenPair(token_a, token_b, decimals_x, decimals_y, not target_is_y)
        else:
            return TokenPair(token_a, token_b, decimals_y, decimals_x, target_is_y)

    def _build_pairs_map(
        self, 
        weth: str, 
        token: str, 
        token_decimals: int
    ) -> dict[str, TokenPair]:
        pairs = {"eth_token": self._create_token_pair(weth, token, 18, token_decimals)}
        
        for stable in self.chain_config.stables:
            stable_addr = AsyncWeb3.to_checksum_address(stable.contract)
            stable_lower = stable.symbol.lower()
            
            pairs[f"eth_{stable_lower}"] = self._create_token_pair(
                weth, stable_addr, 18, stable.decimals
            )
            pairs[f"{stable_lower}_token"] = self._create_token_pair(
                stable_addr, token, stable.decimals, token_decimals,
            )

        return pairs
    
    def _parse_pool_chunk(
        self,
        chunk: list[tuple[bool, bytes]],
        fee: int,
        pool_address: str,
        pair: TokenPair,
    ) -> PoolInfoV3 | None:
        slot, slot_bytes = chunk[0]
        liq, liq_bytes = chunk[1]
        ba, ba_bytes = chunk[2]
        bb, bb_bytes = chunk[3]

        if not all([slot, slot_bytes, len(slot_bytes) > 0, ba, ba_bytes, bb, bb_bytes]):
            return None
        
        sqrt_price_x96, *_ = abi_decode(
            ["uint160", "int24", "uint16", "uint16", "uint16", "uint8", "bool"],
            slot_bytes
        )
        
        liquidity_raw = int.from_bytes(liq_bytes[-32:], "big") if liq and liq_bytes else 0
        balance_a_raw = int(abi_decode(["uint256"], ba_bytes)[0])
        balance_b_raw = int(abi_decode(["uint256"], bb_bytes)[0])
        
        if liquidity_raw == 0:
            return None

        token_price_raw, token_price = self._calculate_price(
            sqrt_price_x96, 
            pair.token_a_decimals, 
            pair.token_b_decimals
        )

        if not pair.is_target_token_a:
            token_price_raw = (Decimal(1) / token_price_raw).quantize(Decimal("1e-18"))
            token_price = Decimal(1) / token_price
        
        amount_a = self._human_amount(balance_a_raw, pair.token_a_decimals)
        amount_b = self._human_amount(balance_b_raw, pair.token_b_decimals)

        if pair.is_target_token_a:
            target_amount = amount_a
            base_amount   = amount_b
        else:
            target_amount = amount_b
            base_amount   = amount_a

        tvl = base_amount + target_amount * token_price

        return PoolInfoV3(
            pool=pool_address,
            price_raw=token_price_raw,
            price=token_price,
            tvl=tvl,
            fee=fee,
            sqrt_price=int(sqrt_price_x96),
            liquidity_raw=int(liquidity_raw),
            amount_a=amount_a,
            amount_b=amount_b,
        )
    
    async def _parse_pools_for_pair(
        self,
        pair: TokenPair,
        pool_data: dict[tuple[str, str, int], list[tuple[bool, bytes]]]
    ) -> list[PoolInfoV3]:
        pools = []
        
        for fee in self.FEE_TIERS:
            chunk = pool_data.get((pair.token_a, pair.token_b, fee))
            if not chunk:
                continue
            
            pool_addr = self.get_pool_address(pair.token_a, pair.token_b, fee)
            pool_info = self._parse_pool_chunk(chunk, fee, pool_addr, pair)
            
            if pool_info:
                pools.append(pool_info)
        
        return pools

    async def get_all_pairs(
        self,
        token_address: str,
        token_meta: TokenMeta,
    ) -> dict[str, PairPools]:
        token = AsyncWeb3.to_checksum_address(token_address)
        weth = AsyncWeb3.to_checksum_address(self.chain_config.weth_address)

        pairs_map = self._build_pairs_map(weth, token, token_meta.decimals)

        pool_data = await self._fetch_all_pools_data(list(pairs_map.values()))

        result = {}
        for pair_name, pair in pairs_map.items():
            pools = await self._parse_pools_for_pair(pair, pool_data)
            best_pool = max(pools, key=lambda p: p.tvl) if pools else None
            
            result[pair_name] = PairPools(
                pair_name=pair_name,
                pair=pair,
                pools=pools,
                best_pool=best_pool
            )
        
        return result
    
    def _extract_best_pools_by_category(
        self,
        all_pairs: dict[str, PairPools]
    ) -> tuple[dict[str, PoolInfoV3], dict[str, PoolInfoV3]]:
        best_eth_stable = {}
        best_stable_token = {}
        
        for stable in self.chain_config.stables:
            stable_lower = stable.symbol.lower()
            
            eth_stable_pair = all_pairs.get(f"eth_{stable_lower}")
            if eth_stable_pair and eth_stable_pair.best_pool:
                best_eth_stable["stable"] = stable.symbol
                best_eth_stable["address"] = stable.contract
                best_eth_stable["pool"] = eth_stable_pair.best_pool
            
            stable_token_pair = all_pairs.get(f"{stable_lower}_token")
            if stable_token_pair and stable_token_pair.best_pool:
                best_stable_token["stable"] = stable.symbol
                best_stable_token["address"] = stable.contract
                best_stable_token["pool"] = stable_token_pair.best_pool
        
        return best_eth_stable, best_stable_token

    async def get_snapshot(
        self, 
        token_address: str, 
        token_meta: TokenMeta
    ) -> TokenSnapshot | None:
        weth = AsyncWeb3.to_checksum_address(self.chain_config.weth_address)
        token = AsyncWeb3.to_checksum_address(token_address)

        all_pairs = await self.get_all_pairs(token_address, token_meta)

        eth_token_pair = all_pairs.get("eth_token")
        if not eth_token_pair or not eth_token_pair.best_pool:
            return None
        
        best_eth_stable, best_stable_token = self._extract_best_pools_by_category(all_pairs)

        return TokenSnapshot(
            dex="uniswap",
            version="v3",
            chain=self.chain_config,
            token=token,
            weth=weth,
            meta=token_meta,
            eth_token_pool=eth_token_pair.best_pool,
            eth_stable_pools=best_eth_stable,
            stable_token_pools=best_stable_token,
        )
        

class UniswapV2Client(BaseDexClient):
    FACTORY_ABI = [
        {
            "constant": True,
            "inputs": [
                { "internalType": "address", "name": "", "type": "address" },
                { "internalType": "address", "name": "", "type": "address" }
            ],
            "name": "getPair",
            "outputs": [
                { "internalType": "address", "name": "", "type": "address" }
            ],
            "payable": False,
            "stateMutability": "view",
            "type": "function"
        }
    ]

    POOL_ABI = [
        {
            "constant": True,
            "inputs": [],
            "name": "getReserves",
            "outputs": [
            { "internalType": "uint112", "name": "_reserve0", "type": "uint112" },
            { "internalType": "uint112", "name": "_reserve1", "type": "uint112" },
            { "internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32" }
            ],
            "payable": False,
            "stateMutability": "view",
            "type": "function"
        }
    ]

    POOL_INIT_CODE_HASH = (
        "96e8ac4277198ff8b6f785478aa9a39f403cb768dd02cbee326c3e7da348845f"
    )

    FACTORY_ADDRESS = {
        "ethereum-sepolia": "F62c03E08ada871A0bEb309762E260a7a6a880E6",
        "base": "8909Dc15e40173Ff4699343b6eB8132c65e18eC6",
        "ethereum": "5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
    }

    
    @staticmethod
    def _human_amount(raw: int, decimals: int) -> Decimal:
        return Decimal(raw) / (Decimal(10) ** decimals)

    @staticmethod
    def _sort_tokens(token_x: str, token_y: str) -> tuple[str, str, bool]:
        return (token_x, token_y, True) if token_x.lower() < token_y.lower() else (token_y, token_x, False)

    def get_pool_address(self, token_a: str, token_b: str) -> str:
        salt = keccak(encode_packed(["address", "address"], [token_a, token_b]))
        packed = (
            b"\xff"
            + bytes.fromhex(self.FACTORY_ADDRESS[self.chain_config.name])
            + salt
            + bytes.fromhex(self.POOL_INIT_CODE_HASH)
        )

        return AsyncWeb3.to_checksum_address(keccak(packed)[12:])
    
    def _compute_pool_addresses(
        self,
        pool_keys: list[tuple[str, str]]
    ) -> dict[tuple[str, str], str]:
        return {
            key: self.get_pool_address(key[0], key[1])
            for key in pool_keys
        }
    
    def _build_multicall_requests(
        self, 
        pool_addresses: dict[tuple[str, str], str]
    ) -> list:
        calls = []
        
        for pool_addr in pool_addresses:
            contract = self.w3.eth.contract(
                AsyncWeb3.to_checksum_address(pool_addresses[pool_addr]),
                abi=self.POOL_ABI
            )
            
            calls.extend([
                self._create_call(pool_addresses[pool_addr], contract.functions.getReserves()._encode_transaction_data()),
            ])
        
        return calls
    
    async def _fetch_all_pools_data(
        self,
        pairs: list[TokenPair],
    ):
        pool_addresses = self._compute_pool_addresses([
            (pair.token_a, pair.token_b)
            for pair in pairs
        ])
        
        multicall = self._get_multicall_contract()
        calls = self._build_multicall_requests(pool_addresses)
        results = await multicall.functions.aggregate3(calls).call()

        return {
            key: results[i]
            for i, key in enumerate(pool_addresses.keys())
        }
    
    def _create_token_pair(
        self, 
        token_x: str, 
        token_y: str,
        decimals_x: int,
        decimals_y: int,
        target_is_y: bool = True
    ) -> TokenPair:
        token_a, token_b, not_swapped = self._sort_tokens(token_x, token_y)

        if not_swapped:
            return TokenPair(token_a, token_b, decimals_x, decimals_y, not target_is_y)
        else:
            return TokenPair(token_a, token_b, decimals_y, decimals_x, target_is_y)

    def _build_pairs_map(
        self, 
        weth: str, 
        token: str, 
        token_decimals: int
    ) -> dict[str, TokenPair]:
        pairs = {"eth_token": self._create_token_pair(weth, token, 18, token_decimals)}
        
        for stable in self.chain_config.stables:
            stable_addr = AsyncWeb3.to_checksum_address(stable.contract)
            stable_lower = stable.symbol.lower()
            
            pairs[f"eth_{stable_lower}"] = self._create_token_pair(
                weth, stable_addr, 18, stable.decimals
            )
            pairs[f"{stable_lower}_token"] = self._create_token_pair(
                stable_addr, token, stable.decimals, token_decimals,
            )

        return pairs
    
    def _parse_pool_chunk(
        self,
        chunk: tuple[bool, bytes],
        pool_address: str,
        pair: TokenPair,
    ) -> PoolInfoV2 | None:
        success, data = chunk
        
        if not success or not data or len(data) < 96:
            return None
        
        try:
            reserve0, reserve1, _ = abi_decode(
                ["uint112", "uint112", "uint32"],
                data
            )
        except Exception:
            return None
        
        if reserve0 == 0 or reserve1 == 0:
            return None
        
        amount_a = self._human_amount(reserve0, pair.token_a_decimals)
        amount_b = self._human_amount(reserve1, pair.token_b_decimals)
        
        price_raw = Decimal(reserve1) / Decimal(reserve0) if reserve0 != 0 else Decimal(0)
        
        price = amount_b / amount_a if amount_a != 0 else Decimal(0)
        
        if not pair.is_target_token_a:
            price_raw = Decimal(1) / price_raw if price_raw != 0 else Decimal(0)
            price = Decimal(1) / price if price != 0 else Decimal(0)
        
        if pair.is_target_token_a:
            base_amount = amount_b
        else:
            base_amount = amount_a
        
        tvl = base_amount * 2
        
        return PoolInfoV2(
            pool=pool_address,
            price_raw=price_raw,
            price=price,
            tvl=tvl,
            reserve0=int(reserve0),
            reserve1=int(reserve1),
        )
    
    async def _parse_pools_for_pair(
        self,
        pair: TokenPair,
        pool_data: dict[tuple[str, str], tuple[bool, bytes]]
    ) -> list[PoolInfoV2]:
        chunk = pool_data.get((pair.token_a, pair.token_b))
        if not chunk:
            return []
        
        pool_addr = self.get_pool_address(pair.token_a, pair.token_b)
        pool_info = self._parse_pool_chunk(chunk, pool_addr, pair)
        
        # V2 возвращает список с одним пулом (или пустой)
        return [pool_info] if pool_info else []
    
    async def get_all_pairs(
        self,
        token_address: str,
        token_meta: TokenMeta,
    ) -> dict[str, PairPools]:
        token = AsyncWeb3.to_checksum_address(token_address)
        weth = AsyncWeb3.to_checksum_address(self.chain_config.weth_address)

        pairs_map = self._build_pairs_map(weth, token, token_meta.decimals)

        pool_data = await self._fetch_all_pools_data(list(pairs_map.values()))

        result = {}
        for pair_name, pair in pairs_map.items():
            pools = await self._parse_pools_for_pair(pair, pool_data)
            best_pool = max(pools, key=lambda p: p.tvl) if pools else None
            
            result[pair_name] = PairPools(
                pair_name=pair_name,
                pair=pair,
                pools=pools,
                best_pool=best_pool
            )
        
        return result
    
    def _extract_best_pools_by_category(
        self,
        all_pairs: dict[str, PairPools]
    ) -> tuple[dict[str, PoolInfoV2], dict[str, PoolInfoV2]]:
        best_eth_stable = {}
        best_stable_token = {}
        
        for stable in self.chain_config.stables:
            stable_lower = stable.symbol.lower()
            
            eth_stable_pair = all_pairs.get(f"eth_{stable_lower}")
            if eth_stable_pair and eth_stable_pair.best_pool:
                best_eth_stable[stable.symbol] = eth_stable_pair.best_pool
            
            stable_token_pair = all_pairs.get(f"{stable_lower}_token")
            if stable_token_pair and stable_token_pair.best_pool:
                best_stable_token[stable.symbol] = stable_token_pair.best_pool
        
        return best_eth_stable, best_stable_token
    
    async def get_snapshot(self, token_address: str, token_meta: TokenMeta) -> TokenSnapshot | None:
        token = AsyncWeb3.to_checksum_address(token_address)
        weth = AsyncWeb3.to_checksum_address(self.chain_config.weth_address)

        all_pairs = await self.get_all_pairs(token_address, token_meta)

        eth_token_pair = all_pairs.get("eth_token")
        if not eth_token_pair or not eth_token_pair.best_pool:
            return None
        
        best_eth_stable, best_stable_token = self._extract_best_pools_by_category(all_pairs)

        return TokenSnapshot(
            dex="uniswap",
            version="v2",
            chain=self.chain_config,
            token=token,
            weth=weth,
            meta=token_meta,
            eth_token_pool=eth_token_pair.best_pool,
            eth_stable_pools=best_eth_stable,
            stable_token_pools=best_stable_token,
        )

        

class AerodromeV2Client(BaseDexClient):
    FACTORY_ADDRESS = "0x420DD381b31aEf6683db6B902084cB0FFECe40Da"

    POOL_ABI = [
        {
            "constant": True,
            "inputs": [],
            "name": "getReserves",
            "outputs": [
            { "internalType": "uint112", "name": "_reserve0", "type": "uint112" },
            { "internalType": "uint112", "name": "_reserve1", "type": "uint112" },
            { "internalType": "uint32", "name": "_blockTimestampLast", "type": "uint32" }
            ],
            "payable": False,
            "stateMutability": "view",
            "type": "function"
        }
    ]

    POOL_INIT_CODE_HASH = (
        "3d602d80600a3d3981f3363d3d373d3d3d36" +
        "3d73A4e46b4f701c62e14DF11B48dCe76A7d" +
        "793CD6d75af43d82803e903d91602b57fd5bf3"
    )

    @staticmethod
    def _human_amount(raw: int, decimals: int) -> Decimal:
        return Decimal(raw) / (Decimal(10) ** decimals)

    @staticmethod
    def _sort_tokens(token_x: str, token_y: str) -> tuple[str, str, bool]:
        return (token_x, token_y, True) if token_x.lower() < token_y.lower() else (token_y, token_x, False)

    def get_pool_address(self, token_a: str, token_b: str, is_stable: bool) -> str:
        salt = keccak(
            encode_packed(
                ["address", "address", "bool"], 
                [token_a, token_b, is_stable]
            )
        )
        packed = (
            b"\xff"
            + bytes.fromhex(self.FACTORY_ADDRESS[2:])
            + salt
            + keccak(bytes.fromhex(self.POOL_INIT_CODE_HASH))
        )

        return AsyncWeb3.to_checksum_address(keccak(packed)[12:])
    
    def _compute_pool_addresses(
        self,
        pool_keys: list[tuple[str, str, bool]]
    ) -> dict[tuple[str, str, bool], str]:
        return {
            key: self.get_pool_address(key[0], key[1], key[2])
            for key in pool_keys
        }
    
    def _build_multicall_requests(
        self, 
        pool_addresses: dict[tuple[str, str, bool], str]
    ) -> list:
        calls = []
        
        for pool_addr in pool_addresses:
            contract = self.w3.eth.contract(
                AsyncWeb3.to_checksum_address(pool_addresses[pool_addr]),
                abi=self.POOL_ABI
            )
            
            calls.extend([
                self._create_call(pool_addresses[pool_addr], contract.functions.getReserves()._encode_transaction_data()),
            ])
        
        return calls
    
    async def _fetch_all_pools_data(
        self,
        pairs: list[TokenPair],
    ):
        pool_addresses = self._compute_pool_addresses([
            (pair.token_a, pair.token_b, is_stable)
            for pair in pairs
            for is_stable in [True, False]
        ])
        
        multicall = self._get_multicall_contract()
        calls = self._build_multicall_requests(pool_addresses)
        results = await multicall.functions.aggregate3(calls).call()

        return {
            key: results[i]
            for i, key in enumerate(pool_addresses.keys())
        }
    
    def _create_token_pair(
        self, 
        token_x: str, 
        token_y: str,
        decimals_x: int,
        decimals_y: int,
        target_is_y: bool = True
    ) -> TokenPair:
        token_a, token_b, not_swapped = self._sort_tokens(token_x, token_y)

        if not_swapped:
            return TokenPair(token_a, token_b, decimals_x, decimals_y, not target_is_y)
        else:
            return TokenPair(token_a, token_b, decimals_y, decimals_x, target_is_y)
        
    def _build_pairs_map(
        self, 
        weth: str, 
        token: str, 
        token_decimals: int
    ) -> dict[str, TokenPair]:
        pairs = {"eth_token": self._create_token_pair(weth, token, 18, token_decimals)}
        
        for stable in self.chain_config.stables:
            stable_addr = AsyncWeb3.to_checksum_address(stable.contract)
            stable_lower = stable.symbol.lower()
            
            pairs[f"eth_{stable_lower}"] = self._create_token_pair(
                weth, stable_addr, 18, stable.decimals
            )
            pairs[f"{stable_lower}_token"] = self._create_token_pair(
                stable_addr, token, stable.decimals, token_decimals,
            )

        return pairs
    
    def _parse_pool_chunk(
        self,
        chunk: tuple[bool, bytes],
        is_stable: bool,
        pool_address: str,
        pair: TokenPair,
    ) -> PoolInfoAerodromeV2 | None:
        success, data = chunk
        
        if not success or not data or len(data) < 96:
            return None
        
        try:
            reserve0, reserve1, _ = abi_decode(
                ["uint112", "uint112", "uint32"],
                data
            )
        except Exception:
            return None
        
        if reserve0 == 0 or reserve1 == 0:
            return None
        
        amount_a = self._human_amount(reserve0, pair.token_a_decimals)
        amount_b = self._human_amount(reserve1, pair.token_b_decimals)
        
        price_raw = Decimal(reserve1) / Decimal(reserve0) if reserve0 != 0 else Decimal(0)
        
        price = amount_b / amount_a if amount_a != 0 else Decimal(0)
        
        if not pair.is_target_token_a:
            price_raw = Decimal(1) / price_raw if price_raw != 0 else Decimal(0)
            price = Decimal(1) / price if price != 0 else Decimal(0)
        
        if pair.is_target_token_a:
            base_amount = amount_b
        else:
            base_amount = amount_a
        
        tvl = base_amount * 2
        
        return PoolInfoAerodromeV2(
            pool=pool_address,
            price_raw=price_raw,
            price=price,
            tvl=tvl,
            reserve0=int(reserve0),
            reserve1=int(reserve1),
            is_stable=is_stable
        )
    
    async def _parse_pools_for_pair(
        self,
        pair: TokenPair,
        pool_data: dict[tuple[str, str, bool], tuple[bool, bytes]]
    ) -> list[PoolInfoAerodromeV2]:
        pools = []

        for is_stable in [True, False]:
            chunk = pool_data.get((pair.token_a, pair.token_b, is_stable))
            if not chunk:
                return []
        
            pool_addr = self.get_pool_address(pair.token_a, pair.token_b, is_stable)
            pool_info = self._parse_pool_chunk(chunk, is_stable, pool_addr, pair)

            if pool_info:
                pools.append(pool_info)
                
        return pools
    
    async def get_all_pairs(
        self,
        token_address: str,
        token_meta: TokenMeta,
    ) -> dict[str, PairPools]:
        token = AsyncWeb3.to_checksum_address(token_address)
        weth = AsyncWeb3.to_checksum_address(self.chain_config.weth_address)

        pairs_map = self._build_pairs_map(weth, token, token_meta.decimals)
        pool_data = await self._fetch_all_pools_data(list(pairs_map.values()))

        result = {}
        for pair_name, pair in pairs_map.items():
            pools = await self._parse_pools_for_pair(pair, pool_data)
            best_pool = max(pools, key=lambda p: p.tvl) if pools else None
            
            result[pair_name] = PairPools(
                pair_name=pair_name,
                pair=pair,
                pools=pools,
                best_pool=best_pool
            )
        
        return result
    
    def _extract_best_pools_by_category(
        self,
        all_pairs: dict[str, PairPools]
    ) -> tuple[dict[str, PoolInfoV2], dict[str, PoolInfoV2]]:
        best_eth_stable = {}
        best_stable_token = {}
        
        for stable in self.chain_config.stables:
            stable_lower = stable.symbol.lower()
            
            eth_stable_pair = all_pairs.get(f"eth_{stable_lower}")
            if eth_stable_pair and eth_stable_pair.best_pool:
                best_eth_stable[stable.symbol] = eth_stable_pair.best_pool
            
            stable_token_pair = all_pairs.get(f"{stable_lower}_token")
            if stable_token_pair and stable_token_pair.best_pool:
                best_stable_token[stable.symbol] = stable_token_pair.best_pool
        
        return best_eth_stable, best_stable_token
    
    async def get_snapshot(self, token_address: str, token_meta: TokenMeta) -> TokenSnapshot | None:
        token = AsyncWeb3.to_checksum_address(token_address)
        weth = AsyncWeb3.to_checksum_address(self.chain_config.weth_address)

        all_pairs = await self.get_all_pairs(token_address, token_meta)
        
        eth_token_pair = all_pairs.get("eth_token")
        if not eth_token_pair or not eth_token_pair.best_pool:
            return None
        
        best_eth_stable, best_stable_token = self._extract_best_pools_by_category(all_pairs)

        return TokenSnapshot(
            dex="aerodrome",
            version="v2",
            chain=self.chain_config,
            token=token,
            weth=weth,
            meta=token_meta,
            eth_token_pool=eth_token_pair.best_pool,
            eth_stable_pools=best_eth_stable,
            stable_token_pools=best_stable_token,
        )
