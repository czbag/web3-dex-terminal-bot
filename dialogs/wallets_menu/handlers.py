import logging

from aiogram import types
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.input import ManagedTextInput
from aiogram_dialog.widgets.kbd import Button
from db.repositories.user import UserRepository
from db.repositories.wallet import WalletRepository
from services.wallet import WalletService
from states.dialog_states import WalletsSG
# from utils.enums import UserStatus

module_logger = logging.getLogger(__name__)


async def wallets_menu(
    callback: types.CallbackQuery, button: Button, dialog_manager: DialogManager
):
    session = dialog_manager.middleware_data["session"]

    user_repo = UserRepository(session)
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    await dialog_manager.start(state=WalletsSG.start, data={"user_id": user.id})


async def go_to_wallets(
    callback: types.CallbackQuery, button: Button, dialog_manager: DialogManager
):
    await dialog_manager.switch_to(WalletsSG.info)


async def add_wallet(
    callback: types.CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
):
    data = dialog_manager.dialog_data

    if data.get("wallets", 0) < 5:
        dialog_manager.dialog_data.update({"add_wallet_method": button.widget_id})

        await dialog_manager.switch_to(state=WalletsSG.wallet_name)
    else:
        await callback.answer(
            "⚠️ You have reached the maximum numbers of wallets!",
            show_alert=True
        )


async def correct_wallet_name(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    wallet_name: str
) -> None:
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data

    if data["add_wallet_method"] == "import_wallet":
        dialog_manager.dialog_data.update({"wallet_name": wallet_name})
        await dialog_manager.switch_to(state=WalletsSG.private_key)
        return
    
    try:
        wallet_repo = WalletRepository(session)

        generated_wallet = await WalletService.create_wallet()

        new_wallet = await wallet_repo.create_wallet(
            int(data["chain_id"]),
            data["user_id"],
            generated_wallet.address,
            generated_wallet.private_key,
            wallet_name
        )
        
        await session.commit()

        cipher = WalletService.get_cipher()

        await message.answer(
            "✅ Generated new wallet:\n\n" +
            f"<b>Address:</b> <code>{new_wallet.address}</code>\n"+
            f"<b>PK:</b> <code>{new_wallet.decrypt_private_key(cipher)}</code>\n"+
            f"<b>Mnemonic</b> <code>{generated_wallet.mnemonic}</code>"
        )
    except Exception as e:
        print(e)
        await session.rollback()
        await message.answer(text="Error")

    await dialog_manager.switch_to(state=WalletsSG.info)


async def error_wallet_name(
    message: types.Message, 
    widget: ManagedTextInput, 
    dialog_manager: DialogManager, 
    error: ValueError
):
    await message.answer(
        text='❌ This is not a valid wallet name. Name must be alphanumeric, 10 letters max.'
    )


async def correct_private_key(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    private_key: str
) -> None:
    session = dialog_manager.middleware_data["session"]
    data = dialog_manager.dialog_data

    try:
        wallet_repo = WalletRepository(session)

        imported_wallet = await WalletService.import_wallet(
            session,
            private_key,
            int(data["chain_id"])
        )

        await wallet_repo.create_wallet(
            int(data["chain_id"]),
            data["user_id"],
            imported_wallet.address,
            imported_wallet.private_key,
            data["wallet_name"]
        )
        
        await session.commit()

        await message.answer(
            f"✅ Added new wallet ({data['wallet_name']})"
        )
    except Exception as e:
        print(e)
        await session.rollback()
        await message.answer(text="Error")

    await dialog_manager.switch_to(state=WalletsSG.info)


async def error_private_key(
    message: types.Message,
    widget: ManagedTextInput,
    dialog_manager: DialogManager,
    error: ValueError
):
    await message.answer(
        text='❌ This is not a valid private key or mnemonic phrase. ' \
        'Private keys are 64-character hex strings.'
    )
