from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any
from web3 import AsyncWeb3
from web3.providers import AsyncHTTPProvider
from chains.dto import ChainConfig
from clients.evm.dto import TokenMeta, TraceResult


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
        {
            "inputs": [
                {"name": "owner", "type": "address"},
                {"name": "spender", "type": "address"},
            ],
            "name": "allowance",
            "outputs": [{"name": "", "type": "uint256"}],
            "stateMutability": "view",
            "type": "function",
        },
        {
            "inputs": [
                {"name": "spender", "type": "address"},
                {"name": "amount", "type": "uint256"},
            ],
            "name": "approve",
            "outputs": [{"name": "", "type": "bool"}],
            "stateMutability": "nonpayable",
            "type": "function",
        },
    ]

    def __init__(self, chain_config: ChainConfig):
        self.chain_config = chain_config
        self._w3: AsyncWeb3 | None = None

    async def __aenter__(self):
        if self._w3 is None:
            self._w3 = AsyncWeb3(AsyncHTTPProvider(self.chain_config.rpc_url))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._w3 is not None:
            await self._w3.provider.disconnect()

            self._w3 = None

    @property
    def w3(self) -> AsyncWeb3:
        return self._w3

    @staticmethod
    def _create_call(target: str, calldata: bytes, allow_failure: bool = True) -> tuple:
        return (target, allow_failure, calldata)
    
    @staticmethod
    def _build_tx_params(
        tx_params: dict[str, Any],
        estimate_gas: int,
        max_gas_price: float,
        max_gas_limit: int,
        gas_delta: float,
    ) -> dict[str, Any]:
        gas_limit = int(estimate_gas * 1.2)

        if gas_limit > max_gas_limit:
            gas_limit = max_gas_limit

        tx_params["gas"] = gas_limit

        max_gas_price_wei = AsyncWeb3.to_wei(max_gas_price, "gwei")
        gas_delta_wei = AsyncWeb3.to_wei(gas_delta, "gwei")

        cur_max_fee = int(tx_params["maxFeePerGas"])
        cur_tip = int(tx_params["maxPriorityFeePerGas"])

        new_max_fee = cur_max_fee + gas_delta_wei
        new_tip = cur_tip + gas_delta_wei

        if new_max_fee > max_gas_price_wei:
            new_max_fee = max_gas_price_wei

        if new_tip > new_max_fee:
            new_tip = new_max_fee

        tx_params["maxFeePerGas"] = new_max_fee
        tx_params["maxPriorityFeePerGas"] = new_tip

        return tx_params

    async def trace_call(self, tx: dict):
        trace_result = await self.w3.provider.make_request(
            "debug_traceCall",
            [tx, "latest", {"tracer": "callTracer"}],
        )
        return trace_result

    def _parse_trace_result(self, trace_response: dict) -> TraceResult:
        if "error" in trace_response:
            error_data = trace_response["error"]
            return TraceResult(
                success=False,
                error_message=error_data.get("message", "Unknown RPC error"),
                raw_trace=trace_response,
            )

        if "result" in trace_response:
            result = trace_response["result"]

            if "error" in result:
                return TraceResult(
                    success=False,
                    error_message=result["error"],
                    gas_used=int(result.get("gasUsed", "0x0"), 16),
                    raw_trace=trace_response,
                )

            return TraceResult(
                success=True,
                gas_used=int(result.get("gasUsed", "0x0"), 16),
                raw_trace=trace_response,
            )

        return TraceResult(
            success=False,
            error_message="Unexpected trace response format",
            raw_trace=trace_response,
        )

    def _get_multicall_contract(self):
        return self.w3.eth.contract(
            AsyncWeb3.to_checksum_address(self.chain_config.multicall3_address),
            abi=self.MULTICALL3_ABI,
        )

    def _get_erc20_contract(self, token_address: str):
        return self.w3.eth.contract(
            AsyncWeb3.to_checksum_address(token_address), abi=self.ERC20_ABI
        )


    async def get_gas_fees(self) -> tuple[int, int]:
        latest_block = await self.w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)

        max_priority_fee = await self.w3.eth.max_priority_fee

        max_fee = base_fee + max_priority_fee

        return max_priority_fee, max_fee


class BaseDexClient(BaseWeb3Client, ABC):
    def __init__(self, chain_config: ChainConfig):
        super().__init__(chain_config)

    @abstractmethod
    async def get_pool_address(self, token_a: str, token_b: str, **kwargs):
        pass

    @abstractmethod
    async def get_snapshot(self, token_address: str, token_meta: TokenMeta, **kwargs):
        pass
