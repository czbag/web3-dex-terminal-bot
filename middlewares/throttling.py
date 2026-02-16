import time
from collections import defaultdict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit=1.0, key_prefix='antiflood_'):
        super().__init__()
        self.rate_limit = rate_limit
        self.prefix = key_prefix
        self.cache = defaultdict(float)

    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        else:
            return await handler(event, data)

        current_time = time.time()

        key = f"{self.prefix}{user_id}"

        delta = current_time - self.cache[key]
        if delta < self.rate_limit:
            await event.answer("Пожалуйста, не отправляйте сообщения слишком часто.")
            return False
        else:
            self.cache[key] = current_time
            return await handler(event, data)
