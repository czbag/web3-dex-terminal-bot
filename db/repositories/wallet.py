from collections.abc import Sequence
from sqlalchemy import select, asc, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from db import Wallet
from db.repositories.base import BaseRepository


class WalletRepository(BaseRepository[Wallet]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Wallet)

    async def create_wallet(
        self,
        chain_id: int,
        user_id: int,
        address: str,
        private_key: bytes,
        name: str | None = None,
    ) -> Wallet:
        wallet = Wallet(
            user_id=user_id,
            chain_id=chain_id,
            address=address,
            encrypted_private_key=private_key,
            name=name
        )

        self.session.add(wallet)
        await self.session.flush()

        return wallet

    async def get_all(
        self,
        user_id: int | None = None,
        chain_id: int | None = None,
        is_active: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[Wallet]:
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if chain_id:
            filters["chain_id"] = chain_id
        if is_active:
            filters["is_active"] = is_active

        return await super()._query_all(filters, order_by, ascending)
    
    async def get_all_with_chain(
        self,
        user_id: int | None = None,
        chain_id: int | None = None,
        is_active: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[Wallet]:
        query = select(Wallet).options(
            selectinload(Wallet.chain)
        )

        if user_id is not None:
            query = query.where(Wallet.user_id == user_id)

        if chain_id is not None:
            query = query.where(Wallet.chain_id == chain_id)

        if is_active is not None:
            query = query.where(Wallet.is_active == is_active)

        order_col = getattr(Wallet, order_by, Wallet.id)
        query = query.order_by(asc(order_col) if ascending else desc(order_col))

        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_address(self, address: str, chain_id: int) -> Wallet | None:
        query = select(Wallet).where(Wallet.address == address)
        query = query.where(Wallet.chain_id == chain_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_name(self, name: str, user_id: int, chain_id: int) -> Wallet | None:
        query = select(Wallet).where(Wallet.name == name)
        query = query.where(Wallet.chain_id == chain_id)
        query = query.where(Wallet.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_active(self) -> Sequence[Wallet]:
        return await self.get_all(is_active=True)

    async def get_inactive(self) -> Sequence[Wallet]:
        return await self.get_all(is_active=False)

    async def count(self, is_active: bool | None = None) -> int:
        return await super().count("is_active", is_active)
