from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Row

from dialogs.chains_menu.handlers import chains_status
from dialogs.settings_menu.handlers import settings_menu
from dialogs.wallets_menu.handlers import wallets_menu
from states.dialog_states import StartSG

start_dialog = Dialog(
    Window(
        Const("👋 <b>Hello!</b>"),
        Button(text=Const("🔗 Chains"), id="chains", on_click=chains_status),
        Row(
            Button(text=Const("👛 Wallets"), id="wallets", on_click=wallets_menu),
            Button(text=Const("⚙️ Settings"), id="settings", on_click=settings_menu),
        ),
        state=StartSG.start,
    ),
)
