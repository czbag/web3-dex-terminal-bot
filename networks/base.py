from models.dtos import NetworkConfig


base = NetworkConfig(
    chain_id=8453,
    name="base",
    display_name="Base",
    symbol="ETH",
    explorer="https://basescan.org/",
    rpc_url="https://base-public.nodies.app",
    weth_address="0x4200000000000000000000000000000000000006",
    multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    swap_router_address="",
    pool_deployer="33128a8fC17869897dcE68Ed026d694621f6FDfD"
)
