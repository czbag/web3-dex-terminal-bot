from aiogram.fsm.state import StatesGroup, State


class StartSG(StatesGroup):
    start = State()


class ChainSG(StatesGroup):
    start = State()


class SettingsSG(StatesGroup):
    start = State()


class WalletsSG(StatesGroup):
    start = State()
    info = State()
    wallet_name = State()
    private_key = State()


class ChainSettingsSG(StatesGroup):
    start = State()
    gas_price = State()
    gas_limit = State()
    buy = State()
    sell = State()
    approve = State()
    slippage = State()
    gas_delta = State()
    price_impact = State()


class TokenSG(StatesGroup):
    start = State()
    buy_token = State()
