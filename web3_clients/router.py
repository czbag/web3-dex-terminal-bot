import asyncio
from decimal import Decimal
from eth_account import Account
from eth_abi.abi import decode as abi_decode
from web3 import AsyncWeb3
from web3.types import TxParams
from models.dtos import NetworkConfig
from web3_clients.base import BaseWeb3Client


class SwapRouterClient(BaseWeb3Client):
    ROUTER_ABI = [
        {
            "inputs": [],
            "name": "feePercent",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "",
                    "type": "uint256"
                }
            ],
            "stateMutability": "view",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "tokenOut",
                    "type": "address"
                },
                {
                    "internalType": "uint24",
                    "name": "fee",
                    "type": "uint24"
                },
                {
                    "internalType": "uint256",
                    "name": "amountOutMinimum",
                    "type": "uint256"
                },
                {
                    "internalType": "uint160",
                    "name": "sqrtPriceLimitX96",
                    "type": "uint160"
                }
            ],
            "name": "swapETHForToken",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "amountOut",
                    "type": "uint256"
                }
            ],
            "stateMutability": "payable",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "tokenIn",
                    "type": "address"
                },
                {
                    "internalType": "uint256",
                    "name": "amountIn",
                    "type": "uint256"
                },
                {
                    "internalType": "uint24",
                    "name": "fee",
                    "type": "uint24"
                },
                {
                    "internalType": "uint256",
                    "name": "amountOutMinimum",
                    "type": "uint256"
                },
                {
                    "internalType": "uint160",
                    "name": "sqrtPriceLimitX96",
                    "type": "uint160"
                }
            ],
            "name": "swapTokenForETH",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "amountOut",
                    "type": "uint256"
                }
            ],
            "stateMutability": "nonpayable",
            "type": "function"
        },
        {
            "inputs": [
                {
                    "internalType": "address",
                    "name": "tokenIn",
                    "type": "address"
                },
                {
                    "internalType": "address",
                    "name": "tokenOut",
                    "type": "address"
                },
                {
                    "internalType": "uint256",
                    "name": "amountIn",
                    "type": "uint256"
                },
                {
                    "internalType": "uint24",
                    "name": "fee",
                    "type": "uint24"
                },
                {
                    "internalType": "uint256",
                    "name": "amountOutMinimum",
                    "type": "uint256"
                },
                {
                    "internalType": "uint160",
                    "name": "sqrtPriceLimitX96",
                    "type": "uint160"
                }
            ],
            "name": "swapTokenForToken",
            "outputs": [
                {
                    "internalType": "uint256",
                    "name": "amountOut",
                    "type": "uint256"
                }
            ],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]
    
    MAX_UINT256 = 2**256 - 1
    
    def __init__(self, network_config: NetworkConfig, w3: AsyncWeb3 | None = None):
        super().__init__(network_config, w3)
        self.router_address = AsyncWeb3.to_checksum_address(network_config.swap_router_address)

        self.contract = self.w3.eth.contract(
            self.router_address,
            abi=self.ROUTER_ABI
        )

    async def get_fee_percent(self) -> int:
        return await self.contract.functions.feePercent().call()
    
    async def check_allowance(
        self,
        token_address: str,
        owner_address: str,
        spender_address: str | None = None
    ) -> int:
        ...
    
    async def build_approve(
        self,
        token_address: str,
        amount: int | None = None,
        spender_address: str | None = None,
        max_gas_price_gwei: Decimal | None = None
    ) -> TxParams:
        ...
    
    async def needs_approval(
        self,
        token_address: str,
        owner_address: str,
        amount: int,
        spender_address: str | None = None
    ) -> bool:
        ...
    
    @staticmethod
    def calculate_amount_out_minimum(
        amount_in: int,
        price: Decimal,
        decimals_in: int,
        decimals_out: int,
        slippage_percent: Decimal,
        fee_percent: int
    ) -> int:
        amount_after_fee = amount_in - (amount_in * fee_percent) // 10000
        amount_in_human = Decimal(amount_after_fee) / Decimal(10 ** decimals_in)
        expected_amount_out_human = amount_in_human / price
        slippage_multiplier = Decimal('1') - (slippage_percent / Decimal('100'))
        min_amount_out_human = expected_amount_out_human * slippage_multiplier
        min_amount_out = int(min_amount_out_human * Decimal(10 ** decimals_out))
        return min_amount_out
    
    async def build_swap_eth_for_token(
        self,
        wallet_address: str,
        token_out: str,
        amount_eth: int,
        fee_tier: int,
        price: Decimal,
        slippage_percent: Decimal,
        current_sqrt_price: int,
        token_decimals: int,
        max_gas_price_gwei: Decimal | None = None
    ) -> TxParams:
        token_out_checksum = AsyncWeb3.to_checksum_address(token_out)
        weth_address = self.network_config.weth_address
        chain_id = self.network_config.chain_id
        fee_percent_task = self.get_fee_percent()
        gas_fees_task = self.get_gas_fees()
        get_nonce = self.get_nonce(wallet_address)

        fee_percent, nonce, (max_priority_fee, calculated_max_fee) = await asyncio.gather(
            fee_percent_task,
            get_nonce,
            gas_fees_task
        )
        
        amount_out_minimum = self.calculate_amount_out_minimum(
            amount_eth,
            price,
            18,  # ETH decimals
            token_decimals,
            slippage_percent,
            fee_percent
        )
        
        if max_gas_price_gwei is not None:
            max_gas_price_wei = int(max_gas_price_gwei * Decimal(10**9))
            final_max_fee = min(calculated_max_fee, max_gas_price_wei)
        else:
            final_max_fee = calculated_max_fee

        tx_params = {
            'from': wallet_address,
            'value': amount_eth,
            'nonce': nonce,
            'chainId': chain_id,
            'maxPriorityFeePerGas': max_priority_fee,
            'maxFeePerGas': final_max_fee,
        }

        tx = await self.contract.functions.swapETHForToken(
            token_out_checksum,
            fee_tier,
            amount_out_minimum,
            0
        ).build_transaction(tx_params)
        
        return tx

    async def estimate_swap_gas(
        self,
        tx_params: TxParams,
        from_address: str
    ) -> int:
        tx_params['from'] = AsyncWeb3.to_checksum_address(from_address)
        estimated_gas = await self.w3.eth.estimate_gas(tx_params)
        return estimated_gas
    
    async def get_nonce(self, address: str) -> int:
        addr = address
        
        nonce = await self.w3.eth.get_transaction_count(
            AsyncWeb3.to_checksum_address(addr)
        )
        return nonce
    
    async def validate_swap(self):
        ...
