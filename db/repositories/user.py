from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db import User
from db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def create_user(
        self,
        user_id: int,
        first_name: str,
        last_name: str,
        username: str,
    ) -> User:
        user = User(
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            username=username
        )

        self.session.add(user)
        await self.session.flush()

        return user
    
    async def get_by_telegram_id(self, user_id: int) -> User | None:
        query = select(User).where(User.user_id == user_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_or_create_user(
        self,
        user_id: int,
        first_name: str,
        last_name: str,
        username: str,
    ) -> tuple[User, bool]:
        user = await self.get_by_telegram_id(user_id)

        if user:
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True

            if updated:
                await self.session.flush()
            
            return user, False
        
        new_user = await self.create_user(user_id, first_name, last_name, username)
        return new_user, True

    async def get_all(
        self,
        is_active: bool | None = None,
        is_premium: bool | None = None,
        is_blocked: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[User]:
        filters = {}
        if is_active:
            filters["is_active"] = is_active
        if is_premium:
            filters["is_premium"] = is_premium
        if is_blocked:
            filters["is_blocked"] = is_blocked

        return await super()._query_all(filters, order_by, ascending)

    async def get_active(self) -> Sequence[User]:
        return await self.get_all(is_active=True)

    async def get_inactive(self) -> Sequence[User]:
        return await self.get_all(is_active=False)

    async def get_premium(self) -> Sequence[User]:
        return await self.get_all(is_premium=True)

    async def get_blocked(self) -> Sequence[User]:
        return await self.get_all(is_blocked=True)

    async def count(self, is_active: bool | None = None) -> int:
        return await super().count("is_active", is_active)

