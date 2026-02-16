from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db import Token
from db.chain import Chain
from db.repositories.base import BaseRepository


class TokenRepository(BaseRepository[Token]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Token)

    async def create_token(
        self,
        chain_id: int,
        address: str,
        name: str,
        ticker: str,
        decimals: int,
        supply: int
    ) -> Token:
        token = Token(
            chain_id=chain_id,
            address=address,
            name=name,
            ticker=ticker,
            decimals=decimals,
            total_supply=supply
        )

        self.session.add(token)
        await self.session.flush()

        return token

    async def get_all(
        self,
        chain_id: int | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[Token]:
        filters = {}
        if chain_id:
            filters["chain_id"] = chain_id

        return await super()._query_all(filters, order_by, ascending)
    
    async def get_by_address(self, address: str, chain_id: int) -> Token | None:
        query = (
            select(Token)
            .join(Chain, Token.chain_id == Chain.id)
            .where(
                Token.address == address,
                Chain.chain_id == chain_id
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def count(self) -> int:
        return await super().count()

