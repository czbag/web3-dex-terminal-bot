from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import asc, desc, outerjoin, select
from sqlalchemy.orm import selectinload, joinedload
from db import Chain, UserChainSettings, user
from db.repositories.base import BaseRepository
from enums.chain import ChainStatus
from db.repositories.models import ChainWithStatus


class ChainRepository(BaseRepository[Chain]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Chain)

    async def get_all(
        self,
        is_active: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[Chain]:
        return await super()._query_all({"is_active": is_active}, order_by, ascending)

    async def get_by_chain_id(self, chain_id: int) -> Chain | None:
        query = select(Chain).where(Chain.chain_id == chain_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_active(self) -> Sequence[Chain]:
        return await self.get_all(is_active=True)

    async def get_inactive(self) -> Sequence[Chain]:
        return await self.get_all(is_active=False)

    async def count(self, is_active: bool | None = None) -> int:
        return await super().count("is_active", is_active)
    
    async def update_status(self, chain_id: int, is_active: bool) -> Chain | None:
        chain = await super().get_by_id(chain_id)
        if not chain:
            return None
        
        chain.is_active = is_active
        await self.session.flush()
        return chain


class UserChainRepository(BaseRepository[UserChainSettings]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserChainSettings)

    async def create_default_settings_for_user(self, user_id: int) -> list[UserChainSettings]:
        chain_repo = ChainRepository(self.session)
        all_chains = await chain_repo.get_all()

        settings_list = [
            UserChainSettings(
                user_id=user_id,
                chain_id=chain.id
            ) for chain in all_chains
        ]

        if settings_list:
            self.session.add_all(settings_list)
            await self.session.flush()

        return settings_list

    async def get_all(
        self,
        user_id: int | None = None,
        is_enabled: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[UserChainSettings]:
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if is_enabled:
            filters["is_enabled"] = is_enabled
        return await super()._query_all(filters, order_by, ascending)

    async def get_all_with_chain(
        self,
        user_id: int | None = None,
        is_enabled: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[UserChainSettings]:
        query = select(UserChainSettings).options(
            selectinload(UserChainSettings.chain)
        )

        if user_id is not None:
            query = query.where(UserChainSettings.user_id == user_id)

        if is_enabled is not None:
            query = query.where(UserChainSettings.is_enabled == is_enabled)

        order_col = getattr(UserChainSettings, order_by, UserChainSettings.id)
        query = query.order_by(asc(order_col) if ascending else desc(order_col))

        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_id_with_chain(self, id: int) -> UserChainSettings | None:
        query = (
            select(UserChainSettings).options(
                joinedload(UserChainSettings.chain)
            ).where(
                UserChainSettings.id == id
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_chain_id_and_user_id(self, user_id: int, chain_id: int) -> UserChainSettings | None:
        query = select(UserChainSettings).where(
            UserChainSettings.user_id == user_id,
            UserChainSettings.chain_id == chain_id
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_enabled(self) -> Sequence[UserChainSettings]:
        return await self.get_all(is_enabled=True)
    
    async def get_disabled(self) -> Sequence[UserChainSettings]:
        return await self.get_all(is_enabled=False)
    
    async def count(self, is_enabled: bool | None = None) -> int:
        return await super().count("is_enabled", is_enabled)
    
    async def get_chains_with_status(
        self,
        user_id: int,
        order_by: str = "id"
    ) -> list[ChainWithStatus]:
        query = (
            select(
                Chain.id.label("chain_id"),
                Chain.chain_id.label("evm_chain_id"),
                Chain.is_active.label("chain_is_active"),
                UserChainSettings.id.label("settings_id"),
                UserChainSettings.is_enabled.label("user_is_enabled"),
            ).select_from(
                outerjoin(
                    Chain,
                    UserChainSettings,
                    (Chain.id == UserChainSettings.chain_id)
                    & (UserChainSettings.user_id == user_id),
                )
            ).order_by(getattr(Chain, order_by, Chain.id))
        )

        rows = (await self.session.execute(query)).mappings().all()

        chains_dto = []
        for row in rows:
            if not row["chain_is_active"]:
                status = ChainStatus.MAINTENANCE
            elif row["user_is_enabled"] is False:
                status = ChainStatus.INACTIVE
            else:
                status = ChainStatus.ACTIVE
        
            chains_dto.append(
                ChainWithStatus(
                    chain_id=row["chain_id"],
                    evm_chain_id=row["evm_chain_id"],
                    is_active=row["chain_is_active"],
                    settings_id=row["settings_id"],
                    is_enabled=row["user_is_enabled"],
                    status=status,
                )
            )
        return chains_dto
    
    async def update_status(
        self, 
        user_id: int, 
        chain_id: int, 
        is_enabled: bool
    ) -> UserChainSettings | None:
        settings = await self.get_by_chain_id_and_user_id(user_id, chain_id)

        if not settings:
            return None
        
        settings.is_enabled = is_enabled
        await self.session.flush()
        return settings
    
    async def update_auto_approve_status(
        self, 
        user_id: int, 
        chain_id: int, 
        auto_approve: bool
    ) -> UserChainSettings | None:
        query = select(UserChainSettings).where(
            UserChainSettings.user_id == user_id,
            UserChainSettings.chain_id == chain_id
        )

        result = await self.session.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            return None
        
        settings.auto_approve = auto_approve
        await self.session.flush()
        return settings
