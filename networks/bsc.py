from models.dtos import NetworkConfig


bsc = NetworkConfig(
    chain_id=56,
    name="bsc",
    display_name="BSC",
    symbol="BNB",
    explorer="https://bscscna.com/",
    rpc_url="https://bsc.rpc.blxrbdn.com",
    weth_address="0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c",
    multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    swap_router_address="",
    pool_deployer="0227628f3F023bb0B980b67D528571c95c6DaC1c"
)
