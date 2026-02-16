from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Group, Select, Row
from aiogram_dialog.widgets.text import Const, Format, Multi, List
from aiogram_dialog.widgets.input import TextInput

from dialogs.getters import get_chains
from dialogs.handlers import choose_network, go_to_main_menu
from dialogs.wallets_menu.filters import private_key_check, wallet_name_check
from dialogs.wallets_menu.getters import wallets_by_chain
from dialogs.wallets_menu.handlers import (
    correct_private_key,
    correct_wallet_name,
    error_private_key,
    error_wallet_name,
    add_wallet,
    go_to_wallets,
    wallets_menu,
)
from states.dialog_states import WalletsSG

wallets_dialog = Dialog(
    Window(
        Const("👛 <b>Wallets</b>"),
        Group(
            Select(
                Format("{item[1]}"),
                id="choose_chain_wallets",
                item_id_getter=lambda x: x[0],
                items="chains",
                on_click=choose_network,
            ),
            width=3,
        ),
        Button(text=Const("◀️ Return"), id="go_main_menu", on_click=go_to_main_menu),
        state=WalletsSG.start,
        getter=get_chains,
    ),
    Window(
        Const(
            "ℹ️ Wallet not found. Please import or generate.", when="not_wallets_exist"
        ),
        Multi(
            Format("🔗 <b>{name}</b>\n"),
            List(
                field=Format(
                    "<a href='{item[explorer]}{item[address]}'>{item[name]}</a>: "
                    "<code>{item[address]}</code>\n🏦 <b>{item[balance]} {item[symbol]}</b>\n"
                ),
                items="wallets",
            ),
            sep="\n",
            when="wallets_exist",
        ),
        Row(
            Button(
                text=Const("Import Wallet"), id="import_wallet", on_click=add_wallet
            ),
            Button(
                text=Const("Generate Wallet"), id="generate_wallet", on_click=add_wallet
            ),
        ),
        Button(text=Format("◀️ Return"), id="go_to_wallet", on_click=wallets_menu),
        state=WalletsSG.info,
        getter=wallets_by_chain,
        disable_web_page_preview=True,
    ),
    Window(
        Format(
            "ℹ️ What would you like to name this wallet? 10 letters max, only numbers and letters."
        ),
        TextInput(
            id="wallet_name",
            type_factory=wallet_name_check,
            on_success=correct_wallet_name,
            on_error=error_wallet_name,
        ),
        Button(text=Format("❌ Close"), id="go_to_wallets", on_click=go_to_wallets),
        state=WalletsSG.wallet_name,
    ),
    Window(
        Format("ℹ️ What's the private key of this wallet?"),
        TextInput(
            id="private_key",
            type_factory=private_key_check,
            on_success=correct_private_key,
            on_error=error_private_key,
        ),
        Button(text=Format("❌ Close"), id="go_to_wallets", on_click=go_to_wallets),
        state=WalletsSG.private_key,
    ),
)
