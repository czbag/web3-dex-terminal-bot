from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, List

from enums.network import NetworkStatus


@dataclass
class TokenMeta:
    name: str
    ticker: str
    decimals: int
    supply: int


@dataclass
class PoolInfo:
    fee: int
    pool: str
    sqrt_price: int
    liquidity_raw: int
    amount_token: Decimal
    amount_weth: Decimal
    price_token: Decimal
    tvl: Decimal

    def to_dict(self) -> dict:
        return {
            "fee": self.fee,
            "sqrt_price": self.sqrt_price,
            "liquidity_raw": self.liquidity_raw,
            "amount_token": self.amount_token,
            "amount_weth": self.amount_weth,
            "price_token": self.price_token,
            "tvl": self.tvl,
        }


@dataclass
class TokenSnapshot:
    network: str
    token: str
    weth: str
    meta: TokenMeta
    pools: List[PoolInfo]
    best: Optional[PoolInfo]
    market_cap: Optional[Decimal]

    def to_dict(self) -> dict:
        return {
            "network": self.network,
            "token": self.token,
            "weth": self.weth,
            "meta": {
                "name": self.meta.name,
                "ticker": self.meta.ticker,
                "decimals": self.meta.decimals,
                "supply": self.meta.supply,
            },
            "pools": self.pools,
            "best": self.best,
            "market_cap": self.market_cap,
        }


@dataclass
class NetworkWithStatus:
    network_id: int
    chain_id: int
    is_active: bool
    
    settings_id: int | None
    is_enabled: bool | None
    
    status: NetworkStatus


@dataclass
class WalletData:
    private_key: bytes
    address: str
    mnemonic: str | None = None


@dataclass
class NetworkConfig:
    chain_id: int
    name: str
    display_name: str
    symbol: str
    explorer: str
    rpc_url: str
    weth_address: str
    multicall3_address: str
    swap_router_address: str
    pool_deployer: str
