from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.text import Const
from aiogram_dialog.widgets.kbd import Button, Group, Select, Url, Row
from aiogram_dialog.widgets.text import Const, Format
from aiogram_dialog.widgets.input import TextInput

from dialogs.getters import get_chains
from dialogs.handlers import choose_network, go_to_main_menu
from dialogs.settings_menu.filters import (
    gas_delta_check,
    gas_limit_check,
    gas_price_check,
    price_impact_check,
    slippage_check,
)
from dialogs.settings_menu.getters import get_chain_settings
from dialogs.settings_menu.handlers import (
    change_action_settings,
    change_auto_approve_status,
    change_gas_delta,
    change_max_gas_limit,
    change_max_gas_price,
    change_price_impact,
    change_slippage,
    correct_gas_delta,
    correct_gas_limit,
    correct_gas_price,
    correct_price_impact,
    correct_slippage,
    error_gas_delta,
    error_gas_limit,
    error_gas_price,
    error_price_impact,
    error_slippage,
    go_to_settings,
    settings_menu,
)
from states.dialog_states import SettingsSG, ChainSettingsSG

settings_dialog = Dialog(
    Window(
        Const("⚙️ <b>Settings</b>"),
        Group(
            Select(
                Format("{item[1]}"),
                id="choose_chain_settings",
                item_id_getter=lambda x: x[0],
                items="chains",
                on_click=choose_network,
            ),
            width=3,
        ),
        Button(text=Const("◀️ Return"), id="go_main_menu", on_click=go_to_main_menu),
        state=SettingsSG.start,
        getter=get_chains,
    )
)

settings_chain_dialog = Dialog(
    Window(
        Format("🔗 <b>{name}</b>"),
        Row(
            Button(
                text=Const("⚙️ Buy"), id="buy_settings", on_click=change_action_settings
            ),
            Button(
                text=Const("⚙️ Sell"),
                id="sell_settings",
                on_click=change_action_settings,
            ),
            Button(
                text=Const("⚙️ Approve"),
                id="approve_settings",
                on_click=change_action_settings,
            ),
        ),
        Button(
            text=Format("Max Gas Price | {max_gas_price} Gwei"),
            id="change_gas_price",
            on_click=change_max_gas_price,
        ),
        Button(
            text=Format("Max Gas Limit | {max_gas_limit}"),
            id="change_gas_limit",
            on_click=change_max_gas_limit,
        ),
        Button(text=Format("◀️ Return"), id="go_settings_menu", on_click=settings_menu),
        state=ChainSettingsSG.start,
        getter=get_chain_settings,
    ),
    Window(
        Const(
            text="Reply to this message with your desired maximum gas price (in gwei).\n"
        ),
        Const(text="min 5, max 1,000,000"),
        TextInput(
            id="gas_price",
            type_factory=gas_price_check,
            on_success=correct_gas_price,
            on_error=error_gas_price,
        ),
        state=ChainSettingsSG.gas_price,
    ),
    Window(
        Const(text="Reply to this message with your desired maximum gas limit.\n"),
        Const(text="min 1,000,000, max 30,000,000"),
        TextInput(
            id="gas_limit",
            type_factory=gas_limit_check,
            on_success=correct_gas_limit,
            on_error=error_gas_limit,
        ),
        state=ChainSettingsSG.gas_limit,
    ),
    Window(
        Format("🔗 <b>{name}</b>\n"),
        Const("Customize the settings of your <b>buys</b>."),
        Button(
            text=Format("Price Impact | {buy_price_impact}%"),
            id="buy_price_impact",
            on_click=change_price_impact,
        ),
        Button(
            text=Format("Gas Delta | {buy_gas_delta} Gwei"),
            id="buy_gas_delta",
            on_click=change_gas_delta,
        ),
        Button(
            text=Format("Slippage | {buy_slippage}%"),
            id="buy_slippage",
            on_click=change_slippage,
        ),
        Button(text=Format("◀️ Return"), id="go_to_settings", on_click=go_to_settings),
        state=ChainSettingsSG.buy,
        getter=get_chain_settings,
    ),
    Window(
        Format("🔗 <b>{name}</b>\n"),
        Const("Customize the settings of your <b>sells</b>."),
        Button(
            text=Format("Price Impact | {sell_price_impact}%"),
            id="sell_price_impact",
            on_click=change_price_impact,
        ),
        Button(
            text=Format("Gas Delta | {sell_gas_delta} Gwei"),
            id="sell_gas_delta",
            on_click=change_gas_delta,
        ),
        Button(
            text=Format("Slippage | {sell_slippage}"),
            id="sell_slippage",
            on_click=change_slippage,
        ),
        Button(text=Format("◀️ Return"), id="go_to_settings", on_click=go_to_settings),
        state=ChainSettingsSG.sell,
        getter=get_chain_settings,
    ),
    Window(
        Format("🔗 <b>{name}</b>\n"),
        Const("Customize the settings of your <b>approves</b>."),
        Button(
            text=Format("Gas Delta | {approve_gas_delta} Gwei"),
            id="approve_gas_delta",
            on_click=change_gas_delta,
        ),
        Button(
            text=Format("🟢 Auto Approve"),
            id="auto_approve",
            on_click=change_auto_approve_status,
            when="auto_approve",
        ),
        Button(
            text=Format("🔴 Auto Approve"),
            id="auto_approve",
            on_click=change_auto_approve_status,
            when="not_auto_approve",
        ),
        Button(text=Format("◀️ Return"), id="go_to_settings", on_click=go_to_settings),
        state=ChainSettingsSG.approve,
        getter=get_chain_settings,
    ),
    Window(
        Const(text="Reply to this message with your desired price-impact percentage. \n"),
        Const(text="min 0.1%, max 100%"),
        TextInput(
            id="price_impact",
            type_factory=price_impact_check,
            on_success=correct_price_impact,
            on_error=error_price_impact,
        ),
        state=ChainSettingsSG.price_impact,
    ),
    Window(
        Const(text="Reply to this message with your desired slippage percentage. \n"),
        Const(text="min 0.1%, max 1000%"),
        TextInput(
            id="slippage",
            type_factory=slippage_check,
            on_success=correct_slippage,
            on_error=error_slippage,
        ),
        state=ChainSettingsSG.slippage,
    ),
    Window(
        Const(
            text="Reply to this message with your desired delta buy gas price (in gwei).\n"
        ),
        Const(text="This is a delta value. Example:"),
        Const(text="AVG gas price = 5 gwei"),
        Const(text="Delta gas price = 3 gwei"),
        Const(text="Transaction gas price = 5 + 3 = 8 gwei"),
        TextInput(
            id="gas_delta",
            type_factory=gas_delta_check,
            on_success=correct_gas_delta,
            on_error=error_gas_delta,
        ),
        state=ChainSettingsSG.gas_delta,
    ),
)
