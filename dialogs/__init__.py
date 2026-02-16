from dialogs.user_menu.dialogs import start_dialog
from dialogs.chains_menu.dialogs import chains_dialog
from dialogs.wallets_menu.dialogs import wallets_dialog
from dialogs.settings_menu.dialogs import settings_dialog, settings_chain_dialog



def include_dialogs():
    dialogs = [
        start_dialog,
        chains_dialog,
        wallets_dialog,
        settings_dialog, 
        settings_chain_dialog,
    ]

    return dialogs
