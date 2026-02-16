from aiogram import Router

from filters.chat_type import ChatTypeFilter
from . import start
from . import address


def setup_routers() -> Router:
    router = Router()
    router.message.filter(ChatTypeFilter(["private"]))
    router.include_router(start.router)
    router.include_router(address.router)

    return router
