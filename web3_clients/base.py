from abc import ABC
from decimal import Decimal
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from models.dtos import NetworkConfig


class BaseWeb3Client(ABC):
    MULTICALL3_ABI = [
        {
            "inputs": [
                {
                    "components": [
                        {
                            "internalType": "address",
                            "name": "target",
                            "type": "address",
                        },
                        {
                            "internalType": "bool",
                            "name": "allowFailure",
                            "type": "bool",
                        },
                        {"internalType": "bytes", "name": "callData", "type": "bytes"},
                    ],
                    "internalType": "struct Multicall3.Call3[]",
                    "name": "calls",
                    "type": "tuple[]",
                }
            ],
            "name": "aggregate3",
            "outputs": [
                {
                    "components": [
                        {"internalType": "bool", "name": "success", "type": "bool"},
                        {
                            "internalType": "bytes",
                            "name": "returnData",
                            "type": "bytes",
                        },
                    ],
                    "internalType": "struct Multicall3.Result[]",
                    "name": "returnData",
                    "type": "tuple[]",
                }
            ],
            "stateMutability": "payable",
            "type": "function",
        }
    ]

    ERC20_ABI = [
        {
            "inputs": [],
            "name": "name",
            "outputs": [{"name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "symbol",
            "outputs": [{"name": "", "type": "string"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "decimals",
            "outputs": [{"name": "", "type": "uint8"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [],
            "name": "totalSupply",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [{"name": "owner", "type": "address"}],
            "name": "balanceOf",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
    ]

    def __init__(self, network_config: NetworkConfig, w3: AsyncWeb3 | None = None):
        self.network_config = network_config
        self._w3 = w3 or AsyncWeb3(AsyncHTTPProvider(network_config.rpc_url))

    @property
    def w3(self) -> AsyncWeb3:
        return self._w3
    
    @staticmethod
    def _create_call(target: str, calldata: bytes, allow_failure: bool = True) -> tuple:
        return (target, allow_failure, calldata)
    
    def _get_multicall_contract(self):
        return self.w3.eth.contract(
            AsyncWeb3.to_checksum_address(self.network_config.multicall3_address),
            abi=self.MULTICALL3_ABI
        )
    
    def _get_erc20_contract(self, token_address: str):
        return self.w3.eth.contract(
            AsyncWeb3.to_checksum_address(token_address),
            abi=self.ERC20_ABI
        )
    
    async def get_gas_fees(self) -> tuple[int, int]:
        latest_block = await self.w3.eth.get_block('latest')
        base_fee = latest_block.get('baseFeePerGas', 0)
        
        max_priority_fee = await self.w3.eth.max_priority_fee
        
        max_fee = base_fee + max_priority_fee
        
        return max_priority_fee, max_fee

