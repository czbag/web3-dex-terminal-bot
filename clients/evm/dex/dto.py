from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from chains.dto import ChainConfig
from clients.evm.dto import TokenMeta


@dataclass
class PoolInfoBase:
    pool: str
    price_raw: Decimal
    price: Decimal
    tvl: Decimal


@dataclass
class PoolInfoV2(PoolInfoBase):
    reserve0: int
    reserve1: int


@dataclass
class PoolInfoV3(PoolInfoBase):
    fee: int
    sqrt_price: int
    liquidity_raw: int
    amount_a: Decimal
    amount_b: Decimal


@dataclass
class PoolInfoAerodromeV2(PoolInfoV2):
    is_stable: bool


@dataclass
class TokenPair:
    token_a: str
    token_b: str
    token_a_decimals: int
    token_b_decimals: int
    is_target_token_a: bool


@dataclass
class PairPools:
    pair_name: str
    pair: TokenPair
    pools: list[PoolInfoBase]
    best_pool: PoolInfoBase | None


@dataclass
class RouteInfo:
    route_type: Literal["direct", "multi_hop"]
    pools: list[PoolInfoBase]
    effective_tvl: Decimal
    effective_price: Decimal
    total_fee_bps: int
    intermediate_token: str | None = None


@dataclass
class TokenSnapshot:
    dex: str
    version: str
    
    chain: ChainConfig
    token: str
    weth: str
    meta: TokenMeta

    # best direct pool: eth-token
    eth_token_pool: PoolInfoBase | None

    # best eth-stable pools: eth-usdt, eth-usdc
    eth_stable_pools: dict[str, PoolInfoBase]

    # best stable-token pools: usdt-token, usdc-token
    stable_token_pools: dict[str, PoolInfoBase]

    market_cap: Decimal | None = None
