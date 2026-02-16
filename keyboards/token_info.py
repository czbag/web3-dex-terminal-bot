from decimal import Decimal
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types



def token_info_kb(wallets: list, idx: int, is_multi: bool = True, is_buy: bool = True):
    builder = InlineKeyboardBuilder()

    active_wallets = [w for w in wallets if w["is_active"] is True]
    wallets_with_balance = [w for w in wallets if Decimal(w["token_balance"]) > 0]
    emoji = "🟩" if is_buy else "🟥"

    builder.row(
        types.InlineKeyboardButton(text="🔄 Update", callback_data="update_token_info"),
    )
    if not is_multi:
        if not is_buy and len(wallets_with_balance) == 0:
            builder.row(
                types.InlineKeyboardButton(text="🔴 Multi", callback_data="multi"),
            )
        else:
            builder.row(
                types.InlineKeyboardButton(text=f"💳 {wallets[idx]['name']} 🔄", callback_data="next_wallet"),
                types.InlineKeyboardButton(text="🔴 Multi", callback_data="multi"),
            )
    else:
        builder.row(types.InlineKeyboardButton(text="🟢 Multi", callback_data="multi"))
        if is_buy:
            builder.row(
                *[
                    types.InlineKeyboardButton(
                        text=f"{'🟢' if w['is_active'] else '🔴'} {w['name']}", 
                        callback_data=f"change_active_status:{w['id']}"
                    )
                    for w in wallets
                ],
                width=3
            )
        #elif not is_buy and len(wallets_with_balance) > 0:
        else:
            builder.row(
                *[
                    types.InlineKeyboardButton(
                        text=f"{'🟢' if w['is_active'] else '🔴'} {w['name']}", 
                        callback_data=f"change_active_status:{w['id']}"
                    )
                    for w in wallets_with_balance
                ],
                width=3
            )
        builder.row(
            types.InlineKeyboardButton(text="Turn All On", callback_data="turn_all:on"),
            types.InlineKeyboardButton(text="Turn All Off", callback_data="turn_all:off"),
        )
    builder.row(
        types.InlineKeyboardButton(text="Approve", callback_data="make_approve"),
        types.InlineKeyboardButton(text=f"↔️ Go to {'Sell' if is_buy else 'Buy'}", callback_data="go_to_buy_or_sell"),
        types.InlineKeyboardButton(text="Revoke", callback_data="make_revoke"),
    )
    if len(active_wallets) == 0:
        builder.row(
            types.InlineKeyboardButton(text="⚠️ No Wallets Selected ⚠️", callback_data="-")
        )
    elif not is_buy and len(wallets_with_balance) == 0:
        builder.row(
            types.InlineKeyboardButton(text="⚠️ No Balance Detected ⚠️", callback_data="-")
        )
    else:
        if is_buy:
            builder.row(
                *[
                    types.InlineKeyboardButton(text=f"{i} ETH", callback_data=f"buy_token:{i}")
                    for i in [0.01, 0.05, 0.1, 0.2, 0.5, 1]
                ],
                types.InlineKeyboardButton(text="Buy X ETH", callback_data="buy_token_custom"),
                width=3
            )
        else:
            builder.row(
                types.InlineKeyboardButton(text=f"25%", callback_data=f"sell_token:0.25"),
                types.InlineKeyboardButton(text=f"50%", callback_data=f"sell_token:0.50"),
                types.InlineKeyboardButton(text=f"75%", callback_data=f"sell_token:0.75"),
                types.InlineKeyboardButton(text=f"100%", callback_data=f"sell_token:1"),
                width=4
            )
    builder.row(
        types.InlineKeyboardButton(text=f"{emoji} Slippage |", callback_data="slippage"),
        types.InlineKeyboardButton(text=f"{emoji} Gas | Gwei", callback_data="gas"),
    )
    return builder
