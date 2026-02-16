from eth_abi.abi import decode as abi_decode
from web3 import AsyncWeb3
from sqlalchemy.ext.asyncio import AsyncSession
from clients.evm.base import BaseWeb3Client
from clients.evm.dto import TokenMeta
from db.repositories.chain import ChainRepository
from db.repositories.token import TokenRepository


class TokenService(BaseWeb3Client):
    async def _fetch_token_meta(self, token_address: str) -> TokenMeta | None:
        token = AsyncWeb3.to_checksum_address(token_address)
        contract = self._get_erc20_contract(token)
        multicall = self._get_multicall_contract()

        calls = [
            self._create_call(
                token, contract.functions.name()._encode_transaction_data()
            ),
            self._create_call(
                token, contract.functions.symbol()._encode_transaction_data()
            ),
            self._create_call(
                token, contract.functions.decimals()._encode_transaction_data()
            ),
            self._create_call(
                token, contract.functions.totalSupply()._encode_transaction_data()
            ),
        ]

        results = await multicall.functions.aggregate3(calls).call()

        if all(success and data for success, data in results):
            name, name_bytes = results[0]
            symbol, symbol_bytes = results[1]
            decimals, decimals_bytes = results[2]
            supply, supply_bytes = results[3]

            name = abi_decode(["string"], name_bytes)[0]
            symbol = abi_decode(["string"], symbol_bytes)[0]
            decimals = abi_decode(["uint8"], decimals_bytes)[0]
            supply = abi_decode(["uint256"], supply_bytes)[0]

            return TokenMeta(
                address=token_address,
                name=name, 
                ticker=symbol, 
                decimals=decimals, 
                supply=supply
            )
        return None
    
    async def get_token_meta(
        self, 
        session: AsyncSession, 
        token_address: str,
        chain_id: int
    ) -> TokenMeta | None:
        token_repo = TokenRepository(session)
        token = await token_repo.get_by_address(token_address, chain_id)

        if token:
            return TokenMeta(
                address=token.address,
                name=token.name,
                ticker=token.ticker,
                decimals=token.decimals,
                supply=token.total_supply * (10 ** token.decimals)
            )
        
        token_meta = await self._fetch_token_meta(token_address)

        if token_meta is not None:
            chain_repo = ChainRepository(session)
            chain = await chain_repo.get_by_chain_id(chain_id)
            
            if not chain:
                return None
            
            await token_repo.create_token(
                chain.id, 
                token_address, 
                token_meta.name, 
                token_meta.ticker, 
                token_meta.decimals, 
                token_meta.supply // (10 ** token_meta.decimals)
            )

            await session.commit()

            return token_meta
        
        return None
    
    async def get_balance(self, token_address: str, wallet_address: str) -> int:
        token = AsyncWeb3.to_checksum_address(token_address)
        wallet = AsyncWeb3.to_checksum_address(wallet_address)

        contract = self._get_erc20_contract(token)

        multicall = self._get_multicall_contract()

        calls = [
            self._create_call(
                token,
                contract.functions.balanceOf(wallet)._encode_transaction_data()
            )
        ]

        results = await multicall.functions.aggregate3(calls).call()
        _, data = results[0]

        if _ and data:
            balance = int(abi_decode(["uint256"], data)[0])
            return balance
        
        return 0
