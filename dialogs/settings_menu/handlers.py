import logging

from aiogram import types
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button
from db.repositories.chain import UserChainRepository
from db.repositories.user import UserRepository
from states.dialog_states import SettingsSG, ChainSettingsSG

module_logger = logging.getLogger(__name__)


async def settings_menu(
    callback: types.CallbackQuery, button: Button, dialog_manager: DialogManager
):
    session = dialog_manager.middleware_data["session"]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    await dialog_manager.start(state=SettingsSG.start, data={"user_id": user.id})


async def go_to_settings(
    callback: types.CallbackQuery, button: Button, dialog_manager: DialogManager
):
    await dialog_manager.switch_to(ChainSettingsSG.start)


async def change_max_gas_price(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    await dialog_manager.switch_to(state=ChainSettingsSG.gas_price)


async def correct_gas_price(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    gas_price: int,
) -> None:
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data

    try:
        user_networks_repo = UserChainRepository(session)

        chain = await user_networks_repo.get_by_id(int(data["chain_id"]))
        chain.max_gas_price = gas_price

        await session.commit()
    except Exception:
        await session.rollback()
        await message.answer(text="Error")

    await dialog_manager.switch_to(state=ChainSettingsSG.start)


async def error_gas_price(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
):
    await message.answer(
        text="❌ You must use a valid number greater than 5 and less than "
        "1,000,000. Please try again."
    )


async def change_max_gas_limit(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    await dialog_manager.switch_to(state=ChainSettingsSG.gas_limit)


async def correct_gas_limit(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    gas_limit: int,
) -> None:
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data

    try:
        user_networks_repo = UserChainRepository(session)

        chain = await user_networks_repo.get_by_id(int(data["chain_id"]))
        chain.max_gas_limit = gas_limit

        await session.commit()
    except Exception:
        await session.rollback()
        await message.answer(text="Error")

    await dialog_manager.switch_to(state=ChainSettingsSG.start)


async def error_gas_limit(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
):
    await message.answer(
        text="❌ You must use a valid number greater than 1,000,000 and less than "
        "30,000,000. Please try again."
    )


async def change_action_settings(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    if button.widget_id == "buy_settings":
        await dialog_manager.switch_to(state=ChainSettingsSG.buy)
    elif button.widget_id == "sell_settings":
        await dialog_manager.switch_to(state=ChainSettingsSG.sell)
    else:
        await dialog_manager.switch_to(state=ChainSettingsSG.approve)


async def change_slippage(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    if button.widget_id == "buy_slippage":
        dialog_manager.dialog_data.update({"slippage": "buy"})
    else:
        dialog_manager.dialog_data.update({"slippage": "sell"})

    await dialog_manager.switch_to(state=ChainSettingsSG.slippage)


async def correct_slippage(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    slippage: float,
) -> None:
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data

    try:
        user_networks_repo = UserChainRepository(session)

        chain = await user_networks_repo.get_by_id(int(data["chain_id"]))

        if data["slippage"] == "buy":
            chain.buy_slippage = float(slippage)
            await session.commit()
            await dialog_manager.switch_to(state=ChainSettingsSG.buy)
        else:
            chain.sell_slippage = float(slippage)
            await session.commit()
            await dialog_manager.switch_to(state=ChainSettingsSG.sell)

    except Exception:
        await session.rollback()
        await message.answer(text="Error")


async def error_slippage(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
):
    await message.answer(
        text="❌ You must use a valid number between 0.1% and 1000% inclusive. Please try again."
    )


async def change_gas_delta(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    if button.widget_id == "buy_gas_delta":
        dialog_manager.dialog_data.update({"gas_delta": "buy"})
    elif button.widget_id == "sell_gas_delta":
        dialog_manager.dialog_data.update({"gas_delta": "sell"})
    else:
        dialog_manager.dialog_data.update({"gas_delta": "approve"})

    await dialog_manager.switch_to(state=ChainSettingsSG.gas_delta)


async def correct_gas_delta(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    slippage: float,
) -> None:
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data

    try:
        user_networks_repo = UserChainRepository(session)

        chain = await user_networks_repo.get_by_id(int(data["chain_id"]))

        if data["gas_delta"] == "buy":
            chain.buy_gas_delta = float(slippage)
            await session.commit()
            await dialog_manager.switch_to(state=ChainSettingsSG.buy)
        elif data["gas_delta"] == "sell":
            chain.sell_gas_delta = float(slippage)
            await session.commit()
            await dialog_manager.switch_to(state=ChainSettingsSG.sell)
        else:
            chain.approve_gas_delta = float(slippage)
            await session.commit()
            await dialog_manager.switch_to(state=ChainSettingsSG.approve)

    except Exception as e:
        print(e)
        await session.rollback()
        await message.answer(text="Error")


async def error_gas_delta(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
):
    await message.answer(
        text="❌ You must use a valid number greater than 1.5 and less than 1000000. Please try again."
    )


async def change_price_impact(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    if button.widget_id == "buy_price_impact":
        dialog_manager.dialog_data.update({"price_impact": "buy"})
    else:
        dialog_manager.dialog_data.update({"price_impact": "sell"})

    await dialog_manager.switch_to(state=ChainSettingsSG.price_impact)


async def correct_price_impact(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    slippage: float,
) -> None:
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data

    try:
        user_networks_repo = UserChainRepository(session)

        chain = await user_networks_repo.get_by_id(int(data["chain_id"]))

        if data["price_impact"] == "buy":
            chain.buy_price_impact = float(slippage)
            await session.commit()
            await dialog_manager.switch_to(state=ChainSettingsSG.buy)
        else:
            chain.sell_price_impact = float(slippage)
            await session.commit()
            await dialog_manager.switch_to(state=ChainSettingsSG.sell)

    except Exception as e:
        print(e)
        await session.rollback()
        await message.answer(text="Error")


async def error_price_impact(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError,
):
    await message.answer(
        text="❌ You must use a valid number greater than 1.5 and less than 1000000. Please try again."
    )


async def change_auto_approve_status(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data
    user_id = dialog_manager.start_data.get("user_id")

    user_networks_repo = UserChainRepository(session)

    await user_networks_repo.update_auto_approve_status(
        user_id, 
        int(data["chain_id"]), 
        data["not_auto_approve"]
    )
    await session.commit()
