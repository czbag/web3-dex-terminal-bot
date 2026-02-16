import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram import types
from aiogram_dialog import DialogManager, StartMode
from sqlalchemy.ext.asyncio import AsyncSession

from db.repositories.chain import UserChainRepository
from db.repositories.user import UserRepository
from states.dialog_states import StartSG

router = Router()
module_logger = logging.getLogger(__name__)


async def create_user(session: AsyncSession, user):
    user_repo = UserRepository(session)

    user, created = await user_repo.get_or_create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )

    if created:
        module_logger.info(f"Create new user -> {user.user_id}")

        user_networks_repo = UserChainRepository(session)
        await user_networks_repo.create_default_settings_for_user(user.id)

    await session.commit()
    return user

@router.message(CommandStart(deep_link=False, magic=F.args.is_(None)))
async def start(msg: types.Message, session: AsyncSession, dialog_manager: DialogManager) -> None:
    try:
        module_logger.info(f"User {msg.from_user.id} started the bot")
        
        await create_user(session, msg.from_user)

        await dialog_manager.start(
            state=StartSG.start,
            mode=StartMode.RESET_STACK
        )
    except Exception as e:
        module_logger.error(f"Error in start handler: {e}")
        await msg.answer("😔 Error. Try again later.")
