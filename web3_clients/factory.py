from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from models.dtos import NetworkConfig
from web3_clients.dex.uniswap import UniswapV3Client
from web3_clients.router import SwapRouterClient
from web3_clients.token import TokenService
from web3_clients.wallet import WalletClient


class Web3ClientFactory:
    def __init__(self, network_config: NetworkConfig):
        self.network_config = network_config
        self._w3 = AsyncWeb3(AsyncHTTPProvider(network_config.rpc_url))

    def create_uniswap_client(self) -> UniswapV3Client:
        return UniswapV3Client(self.network_config, self._w3)

    def create_token_service(self) -> TokenService:
        return TokenService(self.network_config, self._w3)

    def create_wallet_client(self, private_key: str | None = None) -> WalletClient:
        return WalletClient(self.network_config, self._w3, private_key)

    def create_router_client(self) -> SwapRouterClient:
        return SwapRouterClient(self.network_config, self._w3)
