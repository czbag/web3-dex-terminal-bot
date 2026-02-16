import asyncio
from decimal import Decimal
from eth_account import Account
from eth_abi.abi import decode as abi_decode
from eth_typing import HexStr
from web3 import AsyncWeb3
from models.dtos import NetworkConfig
from web3_clients.base import BaseWeb3Client


class WalletClient(BaseWeb3Client):
    def __init__(
        self,
        network_config: NetworkConfig,
        w3: AsyncWeb3 | None = None,
        private_key: str | None = None,
    ):
        super().__init__(network_config, w3)
        self._account = None

        if private_key:
            self._account = Account.from_key(private_key)

    @property
    def address(self) -> str | None:
        return self._account.address if self._account else None
    
    async def get_code(self, address: str | None = None) -> bool:
        addr = address or self.address
        try:
            code = await self.w3.eth.get_code(
                AsyncWeb3.to_checksum_address(addr)
            )
            return len(code) > 0
        except Exception:
            return False

    async def get_native_balance(self, address: str | None = None) -> Decimal:
        addr = address or self.address
        if not addr:
            raise ValueError("Address not provided and no account set")

        balance_wei = await self.w3.eth.get_balance(AsyncWeb3.to_checksum_address(addr))

        return Decimal(balance_wei) / Decimal(10**18)

    async def get_native_balances(self, addresses: list[str]) -> dict[str, Decimal]:
        if not addresses:
            return {}

        balances = {}

        tasks = [
            self.w3.eth.get_balance(AsyncWeb3.to_checksum_address(address))
            for address in addresses
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for address, result in zip(addresses, results):
            if isinstance(result, Exception):
                balances[address] = Decimal(0)
            else:
                balances[address] = Decimal(result) / Decimal(10**18)

        return balances

    async def get_token_balance(
        self, token_address: str, address: str | None = None
    ) -> Decimal:
        addr = address or self.address
        if not addr:
            raise ValueError("Address not provided and no account set")

        token = AsyncWeb3.to_checksum_address(token_address)
        wallet = AsyncWeb3.to_checksum_address(addr)

        contract = self._get_erc20_contract(token)
        multicall = self._get_multicall_contract()

        calls = [
            self._create_call(
                token,
                contract.functions.balanceOf(wallet)._encode_transaction_data()
            ),
            self._create_call(
                token,
                contract.functions.decimals()._encode_transaction_data()
            ),
        ]

        results = await multicall.functions.aggregate3(calls).call()

        balance, balance_data = results[0]
        decimals, decimals_data = results[1]

        if not (balance and decimals):
            return Decimal(0)
        
        balance_raw = int(abi_decode(["uint256"], balance_data)[0])
        decimals_raw = int(abi_decode(["uint8"], decimals_data)[0])

        return Decimal(balance_raw) / Decimal(10 ** decimals_raw)
    
    async def get_token_balances(
        self, token_address: str, addresses: list[str]
    ) -> dict[str, Decimal]:
        if not addresses:
            return {}
        
        token = AsyncWeb3.to_checksum_address(token_address)
        contract = self._get_erc20_contract(token)

        multicall = self._get_multicall_contract()

        decimals_call = self._create_call(
            token,
            contract.functions.decimals()._encode_transaction_data()
        )

        balance_calls = [
            self._create_call(
                token,
                contract.functions.balanceOf(
                    AsyncWeb3.to_checksum_address(addr)
                )._encode_transaction_data()
            ) for addr in addresses
        ]

        all_calls = [decimals_call] + balance_calls

        results = await multicall.functions.aggregate3(all_calls).call()

        decimals, decimals_data = results[0]
        if not decimals:
            return {addr: Decimal(0) for addr in addresses}

        decimals_raw = int(abi_decode(["uint8"], decimals_data)[0])
        divisor = Decimal(10 ** decimals_raw)

        balances = {}

        for i, addr in enumerate(addresses, start=1):
            success, data = results[i]
            if success and data:
                balance_raw = int(abi_decode(["uint256"], data)[0])
                balances[addr] = Decimal(balance_raw) / divisor
            else:
                balances[addr] = Decimal(0)

        return balances
    
    def sign_transaction(self, tx_params: dict) -> HexStr:
        signed_tx = self.w3.eth.account.sign_transaction(
            tx_params,
            self._account.key
        )
        
        return signed_tx.raw_transaction.hex()
    
    async def send_transaction(self, signed_tx: HexStr) -> HexStr:
        tx_hash = await self.w3.eth.send_raw_transaction(signed_tx)
        return tx_hash.hex()
    
    async def wait_for_transaction(
        self,
        tx_hash: HexStr,
        timeout: int = 120,
        poll_latency: float = 0.5
    ) -> dict:
        receipt = await self.w3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=timeout,
            poll_latency=poll_latency
        )
        return dict(receipt)
    
    async def execute_transaction(
        self,
        tx_params: dict,
        wait: bool = True,
        timeout: int = 120
    ) -> tuple[str, dict | None]:
        signed_tx = self.sign_transaction(tx_params)
        tx_hash = await self.send_transaction(signed_tx)
        
        receipt = None
        if wait:
            receipt = await self.wait_for_transaction(tx_hash, timeout=timeout)
        
        return tx_hash, receipt
