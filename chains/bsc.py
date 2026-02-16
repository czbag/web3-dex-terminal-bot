from chains.dto import ChainConfig, StableConfig


bsc = ChainConfig(
    chain_id=56,
    name="bsc",
    display_name="BSC",
    symbol="BNB",
    explorer="https://bscscna.com/",
    rpc_url="https://bsc.rpc.blxrbdn.com",
    weth_address="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    swap_router_address="",
    pool_deployer="0227628f3F023bb0B980b67D528571c95c6DaC1c",
    quoter_address="0x78D78E420Da98ad378D7799bE8f4AF69033EB077",
    available_dex=["uniswap_v2", "uniswap_v3"],
    stables=[
        StableConfig("USDT", "0x55d398326f99059fF775485246999027B3197955", 18),
    ]
)
