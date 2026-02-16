import logging

from aiogram import types
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from db.repositories.chain import UserChainRepository
from db.repositories.user import UserRepository
from states.dialog_states import ChainSG

module_logger = logging.getLogger(__name__)


async def chains_status(
    call: types.CallbackQuery, button: Button, dialog_manager: DialogManager
):
    session = dialog_manager.middleware_data["session"]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(call.from_user.id)

    await dialog_manager.start(
        state=ChainSG.start,
        data={"user_id": user.id}
    )


async def change_chain_status(
    call: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
    item_id: str,
):
    session = dialog_manager.middleware_data["session"]
    user_id = dialog_manager.start_data.get("user_id")

    chain_id = item_id.split(":")[0]
    status = item_id.split(":")[-1]

    user_networks_repo = UserChainRepository(session)

    if status == "active":
        await user_networks_repo.update_status(user_id, int(chain_id), False)
        await session.commit()
    elif status == "inactive":
        await user_networks_repo.update_status(user_id, int(chain_id), True)
        await session.commit()
    else:
        await call.answer("🛠 Network under maintenance", show_alert=True)
    


