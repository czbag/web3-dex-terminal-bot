from aiogram import types
from aiogram.filters import BaseFilter
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings


class AdminFilter(BaseFilter):
    async def __call__(self, message: types.Message, session: AsyncSession) -> bool:
        if message.from_user.id in settings.ADMINS:
            return True
        else:
            return False
