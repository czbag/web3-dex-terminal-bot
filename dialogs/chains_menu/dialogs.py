from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Group, Select, Url, Row
from aiogram_dialog.widgets.text import Const, Format

from dialogs.chains_menu.getters import get_chains
from dialogs.chains_menu.handlers import change_chain_status
from dialogs.handlers import go_to_main_menu
from states.dialog_states import ChainSG

chains_dialog = Dialog(
    Window(
        Const("🔗 <b>Chains</b>"),
        Group(
            Select(
                Format("{item[name]} {item[status]}"),
                id="choose_chain",
                item_id_getter=lambda x: f"{x['settings_id']}:{x['status_value']}",
                items='chains',
                on_click=change_chain_status
            ),
            width=2
        ),
        Button(text=Const("❌ Close"), id="go_to_main_menu", on_click=go_to_main_menu),
        state=ChainSG.start,
        getter=get_chains,
    )
)
