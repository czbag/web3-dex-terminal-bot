import asyncio
from dataclasses import dataclass
from decimal import Decimal
import time
from typing import Any

from web3 import AsyncWeb3, Web3
from web3.types import TxParams
from eth_abi.abi import encode as encode_abi

from chains.dto import ChainConfig
from clients.evm.base import BaseWeb3Client
from clients.evm.dex.dto import TokenSnapshot
from clients.evm.dto import TraceResult
from clients.evm.scanner import BestPool, ScanResult


@dataclass
class SwapSimulation:
    amount_in: Decimal
    amount_out: Decimal
    price_impact: Decimal
    slippage: Decimal
    success: bool = True
    error: str | None = None


@dataclass
class Hop:
    dex_type: int # 0 = UNISWAP_V2, 1 = UNISWAP_V3_SINGLE, 2 = AERODROME_V2
    token_in: str
    token_out: str
    min_amount_out: Decimal
    deadline: int
    dex_data: bytes


@dataclass
class SwapRoute:
    token_in: str
    token_out: str
    amount_in: Decimal
    min_final_amount_out: Decimal
    hops: list[Hop]


class HopBuilder:
    @staticmethod
    def _build_v2_hop(
        token_in: str,
        token_out: str,
        min_amount_out: Decimal,
        deadline: int
    ) -> Hop:
        path = [token_in, token_out]
        dex_data = encode_abi(["address[]"], [path])
        
        return Hop(
            dex_type=0,
            token_in=token_in,
            token_out=token_out,
            min_amount_out=min_amount_out,
            deadline=deadline,
            dex_data=dex_data
        )
    
    @staticmethod
    def _build_v3_hop(
        token_in: str,
        token_out: str,
        min_amount_out: Decimal,
        fee: int,
        sqrt_price: int = 0
    ) -> Hop:
        dex_data = encode_abi(["uint24", "uint160"], [fee, sqrt_price])
        
        return Hop(
            dex_type=1,
            token_in=token_in,
            token_out=token_out,
            min_amount_out=min_amount_out,
            deadline=0,
            dex_data=dex_data
        )
    
    @staticmethod
    def _build_aerodrome_hop(
        token_in: str,
        token_out: str,
        min_amount_out: Decimal,
        deadline: int,
        is_stable: bool
    ) -> Hop:
        factory = AsyncWeb3.to_checksum_address("0x420DD381b31aEf6683db6B902084cB0FFECe40Da")
        routes = [(token_in, token_out, is_stable, factory)]
        dex_data = encode_abi(["(address,address,bool,address)[]"], [routes])
        
        return Hop(
            dex_type=2,
            token_in=token_in,
            token_out=token_out,
            min_amount_out=min_amount_out,
            deadline=deadline,
            dex_data=dex_data
        )
    
    def build_hop(
        self,
        pool: BestPool,
        token_in: str,
        token_out: str,
        min_amount_out: Decimal,
        deadline: int
    ) -> Hop:
        dex = f"{pool.dex}_{pool.version}"

        if dex == "uniswap_v2":
            return self._build_v2_hop(token_in, token_out, min_amount_out, deadline)
        elif dex == "uniswap_v3":
            return self._build_v3_hop(token_in, token_out, min_amount_out, pool.pool.fee)
        else:
            return self._build_aerodrome_hop(
                token_in, token_out, min_amount_out, deadline, pool.pool.is_stable
            )
        

class RouteBuilder:
    ETH_ADDRESS = "0x0000000000000000000000000000000000000000"

    def __init__(self, chain_config):
        self.chain = chain_config
        self.weth = chain_config.weth_address
    
    def build_direct(
        self,
        pool: BestPool,
        token: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int,
        hop_builder: HopBuilder,
        is_buy: bool
    ) -> SwapRoute:
        token_in = self.weth if is_buy else token
        token_out = token if is_buy else self.weth

        hop = hop_builder.build_hop(
            pool=pool,
            token_in=token_in,
            token_out=token_out,
            min_amount_out=min_amount_out,
            deadline=deadline
        )

        return SwapRoute(
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            min_final_amount_out=Decimal("0"),
            hops=[hop]
        )
    
    def build_multihop(
        self,
        eth_stable_pool: BestPool,
        stable_token_pool: BestPool,
        token: str,
        amount_in: Decimal,
        min_amount_out: Decimal,
        deadline: int,
        hop_builder: HopBuilder,
        is_buy: bool
    ) -> SwapRoute:
        token_in = self.weth if is_buy else token
        token_out = token if is_buy else self.weth
        stable = stable_token_pool.stable_address
        pool_hop1 = eth_stable_pool if is_buy else stable_token_pool
        pool_hop2 = stable_token_pool if is_buy else eth_stable_pool

        hop1 = hop_builder.build_hop(
            pool=pool_hop1,
            token_in=token_in,
            token_out=stable,
            min_amount_out=min_amount_out,
            deadline=deadline
        )
        
        hop2 = hop_builder.build_hop(
            pool=pool_hop2,
            token_in=stable,
            token_out=token_out,
            min_amount_out=min_amount_out,
            deadline=deadline
        )

        return SwapRoute(
            token_in=token_in,
            token_out=token_out,
            amount_in=amount_in,
            min_final_amount_out=min_amount_out,
            hops=[hop1, hop2]
        )
        


class SwapClient(BaseWeb3Client):
    ROUTER_ADDRESS = {
        "ethereum": "0x251388dbe11cfc6739222d03912e8d8bede1b4e2",
        "base": "0xA69418B7924d556f3ed8fc59f09710cCB58da538",
    }

    ROUTER_V2_ABI = [
        {
            "inputs": [
                {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
                {"internalType": "address[]", "name": "path", "type": "address[]"},
            ],
            "name": "getAmountsOut",
            "outputs": [
                {"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}
            ],
            "stateMutability": "view",
            "type": "function",
        }
    ]

    ROUTER_ABI = [
        {
            "name": "executeRoute",
            "type": "function",
            "stateMutability": "payable",
            "inputs": [
                {
                    "name": "tokenIn",
                    "type": "address",
                },
                {
                    "name": "tokenOut",
                    "type": "address",
                },
                {
                    "name": "amountIn",
                    "type": "uint256",
                },
                {
                    "name": "minFinalAmountOut",
                    "type": "uint256",
                },
                {
                    "name": "hops",
                    "type": "tuple[]",
                    "components": [
                        {"name": "dexType", "type": "uint8"},
                        {"name": "tokenIn", "type": "address"},
                        {"name": "tokenOut", "type": "address"},
                        {"name": "minAmountOut", "type": "uint256"},
                        {"name": "deadline", "type": "uint256"},
                        {"name": "dexData", "type": "bytes"},
                    ],
                },
            ],
            "outputs": [
                {
                    "name": "finalAmountOut",
                    "type": "uint256",
                }
            ],
        }
    ]

    ETH_ADDRESS = "0x0000000000000000000000000000000000000000"
    
    def __init__(self, chain_config):
        super().__init__(chain_config)
        self.route_builder = RouteBuilder(chain_config)
        self.hop_builder = HopBuilder()


    @staticmethod
    def _human_amount(raw: int, decimals: int) -> Decimal:
        return Decimal(raw) / (Decimal(10) ** decimals)

    @staticmethod
    def _raw_amount(human: Decimal, decimals: int) -> int:
        return int(human * (Decimal(10) ** decimals))

    @staticmethod
    def _calculate_price_impact(
        amount_in: int,
        amount_out: int,
        price_wei: int,
        token_decimals: int,
        is_buy: bool = True,
    ) -> Decimal:
        price_wei_dec = Decimal(price_wei)

        if price_wei_dec == 0 or amount_in == 0:
            return Decimal(0)

        if is_buy:
            expected_out_raw = (
                Decimal(amount_in) * (Decimal(10) ** token_decimals) / price_wei_dec
            )
        else:
            expected_out_raw = (
                Decimal(amount_in) * price_wei_dec / (Decimal(10) ** token_decimals)
            )

        if expected_out_raw == 0:
            return Decimal(0)

        price_impact = abs((expected_out_raw - Decimal(amount_out)) / expected_out_raw) * Decimal(100)
        return price_impact.quantize(Decimal("0.01"))

    @staticmethod
    def _calculate_min_amount_out(amount_out: Decimal, slippage: Decimal) -> Decimal:
        slippage_multiplier = Decimal(1) - (slippage / Decimal(100))
        min_amount = amount_out * slippage_multiplier
        return min_amount
    
    
    @staticmethod
    def _calculate_slippage(
        amount_in: Decimal, 
        amount_out: Decimal, 
        price_token_wei: Decimal, 
        token_decimals: int,
        is_buy: bool
    ) -> Decimal:
        dec = Decimal(10) ** token_decimals

        if is_buy:
            real_price = (amount_in * dec) / amount_out
        else:
            real_price = (amount_out * dec) / amount_in

        slippage = (real_price - price_token_wei) / price_token_wei * Decimal(100)
        return slippage.quantize(Decimal("0.01"))
    
    def _get_contract(self):
        address = self.ROUTER_ADDRESS[self.chain_config.name]
        return self.w3.eth.contract(
            AsyncWeb3.to_checksum_address(address),
            abi=self.ROUTER_ABI
        )
    
    @staticmethod
    def _convert_hops_to_tuples(hops: list[Hop]) -> list[tuple]:
        return [
            (
                hop.dex_type,
                AsyncWeb3.to_checksum_address(hop.token_in),
                AsyncWeb3.to_checksum_address(hop.token_out),
                int(hop.min_amount_out),
                hop.deadline,
                hop.dex_data
            )
            for hop in hops
        ]
    
    def _parse_amount_out(self, trace_response: dict) -> Decimal | None:        
        result = trace_response["result"]
        
        if "output" in result and result["output"] != "0x":
            output = result["output"]
            if output.startswith("0x"):
                amount_out = Decimal(int(output, 16))
                return amount_out
        
        return None
    
    async def build_route(
        self,
        scan_result: ScanResult,
        amount_in: Decimal,
        is_buy: bool = True
    ) -> SwapRoute:
        token = scan_result.token_meta.address
        route_type = scan_result.route_type
        deadline = int(time.time()) + 3600 

        if route_type == "direct":
            pool = scan_result.best_eth_token_pool
            route = self.route_builder.build_direct(
                pool=pool,
                token=token,
                amount_in=amount_in,
                min_amount_out=Decimal("0"),
                deadline=deadline,
                hop_builder=self.hop_builder,
                is_buy=is_buy
            )
        else:
            route = self.route_builder.build_multihop(
                eth_stable_pool=scan_result.best_eth_stable_pool,
                stable_token_pool=scan_result.best_stable_token_pool,
                token=token,
                amount_in=amount_in,
                min_amount_out=Decimal("0"),
                deadline=deadline,
                hop_builder=self.hop_builder,
                is_buy=is_buy
            )
        
        return route
    
    async def _simulate_swap_trace(
        self,
        scan_result: ScanResult,
        wallet_address: str,
        amount_in: int,
        is_buy: bool = True
    ) -> SwapSimulation:
        route = await self.build_route(scan_result, amount_in, is_buy)

        token_in = self.ETH_ADDRESS if is_buy else scan_result.token_meta.address
        token_out = scan_result.token_meta.address if is_buy else self.ETH_ADDRESS

        price_token = scan_result.token_price_raw
        
        contract = self._get_contract()

        hops_tuples = self._convert_hops_to_tuples(route.hops)

        func = contract.functions.executeRoute(
            token_in,
            token_out,
            amount_in,
            0,
            hops_tuples
        )

        tx = {
            'to': contract.address,
            'from': wallet_address,
            'data': func._encode_transaction_data(),
        }

        if is_buy:
            tx['value'] = hex(amount_in)

        try:
            raw_result = await self.trace_call(tx)
            trace_result = self._parse_trace_result(raw_result)

            if not trace_result.success:
                return SwapSimulation(
                    amount_in=Decimal(0),
                    amount_out=Decimal(0),
                    price_impact=Decimal(0),
                    slippage=Decimal(0),
                    success=False,
                    error=trace_result.error_message
                )
            
            amount_out = self._parse_amount_out(trace_result.raw_trace)
            price_impact = self._calculate_price_impact(
                amount_in, amount_out, price_token, scan_result.token_meta.decimals, is_buy
            )
            slippage = self._calculate_slippage(
                Decimal(str(amount_in)),
                Decimal(str(amount_out)),
                price_token,
                scan_result.token_meta.decimals,
                is_buy
            )

            return SwapSimulation(
                amount_in=Decimal(str(amount_in)),
                amount_out=Decimal(str(amount_out)),
                price_impact=price_impact,
                slippage=slippage
            )
        except Exception as e:
            return SwapSimulation(
                amount_in=Decimal(0),
                amount_out=Decimal(0),
                price_impact=Decimal(0),
                slippage=Decimal(0),
                success=False,
                error=str(e)
            )
        
    async def simulate_swap(
        self,
        scan_result: ScanResult,
        wallet_address: str,
        amount_in: int,
        is_buy: bool = True
    ) -> SwapSimulation:
        token_address = scan_result.token_meta.address

        allowance, simulation = await asyncio.gather(
            self.check_allowance(token_address, wallet_address),
            self._simulate_swap_trace(
                scan_result,
                wallet_address,
                amount_in,
                is_buy
            )
        )
        if not is_buy and allowance == 0 and not simulation.success:
            simulation.error = "Allowance is 0, need make approve"

        return simulation
    
    async def make_swap(
        self,
        scan_result: ScanResult,
        wallet_address: str,
        amount_in: Decimal,
        amount_out: Decimal,
        slippage: Decimal,
        max_gas_price: float,
        max_gas_limit: int,
        gas_delta: float,
        is_buy: bool = True
    ):
        token_in = self.ETH_ADDRESS if is_buy else scan_result.token_meta.address
        token_out = scan_result.token_meta.address if is_buy else self.ETH_ADDRESS
        min_amount_out = self._calculate_min_amount_out(amount_out, slippage)

        route = await self.build_route(scan_result, amount_in, is_buy)
        
        nonce, (max_priority_fee, max_fee) = await asyncio.gather(
            self.w3.eth.get_transaction_count(
                AsyncWeb3.to_checksum_address(wallet_address)
            ),
            self.get_gas_fees()
        )

        contract = self._get_contract()

        hops_tuples = self._convert_hops_to_tuples(route.hops)

        func = contract.functions.executeRoute(
            token_in,
            token_out,
            int(amount_in),
            int(min_amount_out),
            hops_tuples
        )

        tx_params = {
            "from": wallet_address,
            "nonce": nonce,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

        if is_buy:
            tx_params["value"] = int(amount_in)

        estimate_gas = await func.estimate_gas(tx_params)
        tx_params = self._build_tx_params(
            tx_params, 
            estimate_gas,
            max_gas_price,
            max_gas_limit,
            gas_delta
        )

        tx = await func.build_transaction(tx_params)
        return tx

    async def check_allowance(
        self,
        token_address: str,
        wallet_address: str,
    ) -> int:
        spender_address = self.ROUTER_ADDRESS[self.chain_config.name]
        token_contract = self._get_erc20_contract(token_address)

        allowance = await token_contract.functions.allowance(
            AsyncWeb3.to_checksum_address(wallet_address),
            AsyncWeb3.to_checksum_address(spender_address)
        ).call()

        return allowance
    
    async def approve(
        self,
        address: str,
        token_address: str,
        max_gas_price: float,
        max_gas_limit: int,
        gas_delta: float,
        amount: int = 2 ** 256 - 1,
    ):
        spender_address = self.ROUTER_ADDRESS[self.chain_config.name]

        token_contract = self._get_erc20_contract(token_address)

        nonce, (max_priority_fee, max_fee) = await asyncio.gather(
            self.w3.eth.get_transaction_count(address),
            self.get_gas_fees()
        )

        tx_params = {
            "from": address,
            "nonce": nonce,
            "maxFeePerGas": max_fee,
            "maxPriorityFeePerGas": max_priority_fee,
        }

        estimate_gas = await token_contract.functions.approve(
            AsyncWeb3.to_checksum_address(spender_address),
            amount
        ).estimate_gas(tx_params)
        
        tx_params = self._build_tx_params(
            tx_params, 
            estimate_gas,
            max_gas_price,
            max_gas_limit,
            gas_delta
        )

        tx = await token_contract.functions.approve(
            AsyncWeb3.to_checksum_address(spender_address),
            amount
        ).build_transaction(tx_params)

        return tx
    
    async def revoke(
        self,
        address: str,
        token_address: str,
        max_gas_price: float,
        max_gas_limit: int,
        gas_delta: float,
    ):
        return await self.approve(
            address=address,
            token_address=token_address,
            max_gas_price=max_gas_price,
            max_gas_limit=max_gas_limit,
            gas_delta=gas_delta,
            amount=0,
        )
