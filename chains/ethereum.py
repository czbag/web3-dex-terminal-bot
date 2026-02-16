from chains.dto import ChainConfig, StableConfig


ethereum = ChainConfig(
    chain_id=1,
    name="ethereum",
    display_name="Ethereum",
    symbol="ETH",
    explorer="https://etherscan.io/",
    rpc_url="https://eth.drpc.org",
    weth_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    swap_router_address="0x68b3465833fb72A70ecDF485E0e4C7bD8665Fc45",
    pool_deployer="1F98431c8aD98523631AE4a59f267346ea31F984",
    quoter_address="0x61fFE014bA17989E743c5F6cB21bF9697530B21e",
    available_dex=["uniswap_v2", "uniswap_v3"],
    stables=[
        StableConfig("USDC", "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", 6),
        StableConfig("USDT", "0xdAC17F958D2ee523a2206206994597C13D831ec7", 6),
    ]
)

# sepolia = ChainConfig(
#     chain_id=11155111,
#     name="ethereum-sepolia",
#     display_name="Sepolia",
#     symbol="ETH",
#     explorer="https://sepolia.etherscan.io/",
#     rpc_url="https://0xrpc.io/sep",
#     weth_address="0xfff9976782d46cc05630d1f6ebab18b2324d6b14",
#     multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
#     swap_router_address="0x569592221c3cA78253353fB33930F3869B611199",
#     pool_deployer="0227628f3F023bb0B980b67D528571c95c6DaC1c",
#     quoter_address="0xEd1f6473345F45b75F8179591dd5bA1888cf2FB3",
#     available_dex=["uniswap_v2", "uniswap_v3"],
# )
