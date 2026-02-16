from chains.dto import ChainConfig, StableConfig


base = ChainConfig(
    chain_id=8453,
    name="base",
    display_name="Base",
    symbol="ETH",
    explorer="https://basescan.org/",
    rpc_url="https://base.drpc.org",
    weth_address="0x4200000000000000000000000000000000000006",
    multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    swap_router_address="",
    pool_deployer="33128a8fC17869897dcE68Ed026d694621f6FDfD",
    quoter_address="0x3d4e44Eb1374240CE5F1B871ab261CD16335B76a",
    available_dex=["uniswap_v2", "uniswap_v3", "aerodrome_v2"],
    stables=[
        StableConfig("USDC", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", 6),
    ]
)
