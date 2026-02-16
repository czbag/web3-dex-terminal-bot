from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import asc, desc, outerjoin, select
from sqlalchemy.orm import selectinload, joinedload
from db import Network, UserNetworkSettings
from db.repositories.base import BaseRepository
from enums.network import NetworkStatus
from models.dtos import NetworkWithStatus


class NetworkRepository(BaseRepository[Network]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Network)

    async def get_all(
        self,
        is_active: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[Network]:
        return await super()._query_all({"is_active": is_active}, order_by, ascending)

    async def get_active(self) -> Sequence[Network]:
        return await self.get_all(is_active=True)

    async def get_inactive(self) -> Sequence[Network]:
        return await self.get_all(is_active=False)

    async def count(self, is_active: bool | None = None) -> int:
        return await super().count("is_active", is_active)
    
    async def update_status(self, network_id: int, is_active: bool) -> Network | None:
        network = await super().get_by_id(network_id)
        if not network:
            return None
        
        network.is_active = is_active
        await self.session.flush()
        return network


class UserNetworkRepository(BaseRepository[UserNetworkSettings]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, UserNetworkSettings)

    async def create_default_settings_for_user(self, user_id: int) -> list[UserNetworkSettings]:
        network_repo = NetworkRepository(self.session)
        all_networks = await network_repo.get_all()

        settings_list = [
            UserNetworkSettings(
                user_id=user_id,
                network_id=network.id
            ) for network in all_networks
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
    ) -> Sequence[UserNetworkSettings]:
        filters = {}
        if user_id:
            filters["user_id"] = user_id
        if is_enabled:
            filters["is_enabled"] = is_enabled
        return await super()._query_all(filters, order_by, ascending)

    async def get_all_with_network(
        self,
        user_id: int | None = None,
        is_enabled: bool | None = None,
        order_by: str = "id",
        ascending: bool = True,
    ) -> Sequence[UserNetworkSettings]:
        query = select(UserNetworkSettings).options(
            selectinload(UserNetworkSettings.network)
        )

        if user_id is not None:
            query = query.where(UserNetworkSettings.user_id == user_id)

        if is_enabled is not None:
            query = query.where(UserNetworkSettings.is_enabled == is_enabled)

        order_col = getattr(UserNetworkSettings, order_by, UserNetworkSettings.id)
        query = query.order_by(asc(order_col) if ascending else desc(order_col))

        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_by_id_with_network(self, id: int) -> UserNetworkSettings | None:
        query = (
            select(UserNetworkSettings).options(
                joinedload(UserNetworkSettings.network)
            ).where(
                UserNetworkSettings.id == id
            )
        )

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_enabled(self) -> Sequence[UserNetworkSettings]:
        return await self.get_all(is_enabled=True)
    
    async def get_disabled(self) -> Sequence[UserNetworkSettings]:
        return await self.get_all(is_enabled=False)
    
    async def count(self, is_enabled: bool | None = None) -> int:
        return await super().count("is_enabled", is_enabled)
    
    async def get_networks_with_status(
        self,
        user_id: int,
        order_by: str = "id"
    ) -> list[NetworkWithStatus]:
        query = (
            select(
                Network.id.label("network_id"),
                Network.chain_id,
                Network.is_active,
                UserNetworkSettings.id.label("settings_id"),
                UserNetworkSettings.is_enabled
            ).select_from(
                outerjoin(
                    Network,
                    UserNetworkSettings,
                    (Network.id == UserNetworkSettings.network_id) &
                    (UserNetworkSettings.user_id == user_id)
                )
            ).order_by(getattr(Network, order_by, Network.id))
        )

        result = await self.session.execute(query)
        rows = result.all()

        networks_dto = []
        for row in rows:
            if not row.is_active:
                status = NetworkStatus.MAINTENANCE
            elif row.is_enabled is False:
                status = NetworkStatus.INACTIVE
            else:
                status = NetworkStatus.ACTIVE
        
            networks_dto.append(
                NetworkWithStatus(
                    network_id=row.network_id,
                    chain_id=row.chain_id,
                    is_active=row.is_active,
                    settings_id=row.settings_id,
                    is_enabled=row.is_enabled,
                    status=status
                )
            )
        return networks_dto
    
    async def update_status(
        self, 
        user_id: int, 
        network_id: int, 
        is_enabled: bool
    ) -> UserNetworkSettings | None:
        query = select(UserNetworkSettings).where(
            UserNetworkSettings.user_id == user_id,
            UserNetworkSettings.network_id == network_id
        )

        result = await self.session.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            return None
        
        settings.is_enabled = is_enabled
        await self.session.flush()
        return settings
    
    async def update_auto_approve_status(
        self, 
        user_id: int, 
        network_id: int, 
        auto_approve: bool
    ) -> UserNetworkSettings | None:
        query = select(UserNetworkSettings).where(
            UserNetworkSettings.user_id == user_id,
            UserNetworkSettings.network_id == network_id
        )

        result = await self.session.execute(query)
        settings = result.scalar_one_or_none()

        if not settings:
            return None
        
        settings.auto_approve = auto_approve
        await self.session.flush()
        return settings
