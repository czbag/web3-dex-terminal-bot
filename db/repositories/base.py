from typing import Any, TypeVar, Generic, Type
from collections.abc import Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, asc
from db import Base


ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def _query_all(
        self,
        filters: dict[str, Any] | None = None,
        order_by: str = "id",
        ascending: bool = True
    ) -> Sequence[ModelType]:
        query = select(self.model)

        if filters:
            for field, value in filters.items():
                if value is not None:
                    column = getattr(self.model, field)
                    query = query.where(column == value)

        order_column = getattr(self.model, order_by, self.model.id)
        query = query.order_by(asc(order_column)) if ascending else desc(order_column)

        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def count(
        self,
        filtered_field: str | None = None,
        filtered_value: bool | None = None,
    ) -> int:
        query = select(func.count()).select_from(self.model)

        if filtered_field and filtered_value is not None:
            filtered_column = getattr(self.model, filtered_field)
            query = query.where(filtered_column == filtered_value)

        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_by_id(self, id: int) -> ModelType | None:
        query = select(self.model).where(self.model.id == id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        

