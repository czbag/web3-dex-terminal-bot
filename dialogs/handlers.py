import logging
import time

from aiogram import types, Bot
from aiogram.enums import ContentType
from aiogram_dialog import DialogManager, StartMode, BgManagerFactory, ShowMode
from aiogram_dialog.api.entities import MediaAttachment, MediaId
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button, Select
from sqlalchemy import select

from db.repositories.chain import UserChainRepository
from db.repositories.user import UserRepository
from states.dialog_states import StartSG, WalletsSG, ChainSettingsSG


async def go_to_main_menu(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    await dialog_manager.start(
        state=StartSG.start,
        mode=StartMode.RESET_STACK
    )


async def done_dialog(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    await dialog_manager.done()


async def choose_network(
    callback: types.CallbackQuery,
    widget: Select,
    dialog_manager: DialogManager,
    item_id: str,
):
    start_data = dialog_manager.start_data

    data = {"chain_id": item_id, "user_id": start_data["user_id"]}

    if widget.widget_id == "choose_chain_settings":
        await dialog_manager.start(state=ChainSettingsSG.start, data=data)
    else:
        dialog_manager.dialog_data.update(data)
        await dialog_manager.switch_to(state=WalletsSG.info)
