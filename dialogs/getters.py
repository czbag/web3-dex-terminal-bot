from aiogram.types import User as AIOUser
from aiogram_dialog import DialogManager

from db.repositories.user import UserRepository
from db.repositories.chain import UserChainRepository
from chains import registery


async def get_chains(dialog_manager: DialogManager, event_from_user: AIOUser, **kwargs):
    session = kwargs.get("session")

    user_id = dialog_manager.start_data.get("user_id")

    user_chains_repo = UserChainRepository(session)

    all_user_chains = await user_chains_repo.get_all_with_chain(user_id)

    chains = [
        *[
            (
                i.id,
                registery.get(i.chain.chain_id).display_name,
            )
            for i in all_user_chains
        ]
    ]

    return {"chains": chains}


async def get_start_data(
    dialog_manager: DialogManager, event_from_user: AIOUser, **kwargs
):
    data = dialog_manager.start_data
    return data
