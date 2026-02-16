from aiogram.types import User as AIOUser
from aiogram_dialog import DialogManager

from db.repositories.chain import UserChainRepository
from chains import registery


async def get_chains(
    dialog_manager: DialogManager, event_from_user: AIOUser, **kwargs
):
    session = kwargs.get("session")

    user_id = dialog_manager.start_data.get("user_id")

    user_networks_repo = UserChainRepository(session)

    all_user_networks = await user_networks_repo.get_chains_with_status(user_id)

    chains = [
        {
            "settings_id": i.settings_id,
            "name": registery.get(i.evm_chain_id).display_name,
            "status": i.status.emoji, 
            "status_value": i.status.label
        } for i in all_user_networks
    ]

    return {"chains": chains}
