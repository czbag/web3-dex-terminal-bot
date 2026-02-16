from aiogram.fsm.state import StatesGroup, State


class TokenInfo(StatesGroup):
    info = State()
    amount = State()
