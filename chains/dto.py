from dataclasses import dataclass

@dataclass
class StableConfig:
    symbol: str
    contract: str
    decimals: int

@dataclass
class ChainConfig:
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
    quoter_address: str
    available_dex: list[str]
    stables: list[StableConfig]
