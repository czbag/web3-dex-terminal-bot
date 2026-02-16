from models.dtos import NetworkConfig


ethereum = NetworkConfig(
    chain_id=1,
    name="ethereum",
    display_name="Ethereum",
    symbol="ETH",
    explorer="https://etherscan.io/",
    rpc_url="https://rpc.ankr.com/eth",
    weth_address="0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
    multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    swap_router_address="0x569592221c3cA78253353fB33930F3869B611199",
    pool_deployer="0227628f3F023bb0B980b67D528571c95c6DaC1c"
)

sepolia = NetworkConfig(
    chain_id=11155111,
    name="ethereum-sepolia",
    display_name="Sepolia",
    symbol="ETH",
    explorer="https://sepolia.etherscan.io/",
    rpc_url="https://0xrpc.io/sep",
    weth_address="0xfff9976782d46cc05630d1f6ebab18b2324d6b14",
    multicall3_address="0xcA11bde05977b3631167028862bE2a173976CA11",
    swap_router_address="0x569592221c3cA78253353fB33930F3869B611199",
    pool_deployer="0227628f3F023bb0B980b67D528571c95c6DaC1c"
)
