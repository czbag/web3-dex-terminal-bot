from aiogram.types import User as AIOUser
from aiogram_dialog import DialogManager

from clients.evm.wallet import WalletClient
from db.repositories.chain import ChainRepository
from db.repositories.wallet import WalletRepository
from chains import registery


async def wallets_by_chain(
    dialog_manager: DialogManager, event_from_user: AIOUser, **kwargs
):
    session = kwargs.get("session")

    user_id = dialog_manager.dialog_data.get("user_id")
    chain_id = dialog_manager.dialog_data.get("chain_id")

    wallet_repo = WalletRepository(session)
    network_repo = ChainRepository(session)

    all_user_wallets = await wallet_repo.get_all(user_id, int(chain_id))
    chain = await network_repo.get_by_id(int(chain_id))

    chain_config = registery.get(chain.chain_id)

    addresses = [w.address for w in all_user_wallets]

    async with WalletClient(chain_config) as wallet:
        balances = await wallet.get_native_balances(addresses)

    wallets = [
        *[
            {
                "id": i.id, 
                "name": i.name, 
                "address": i.address,
                "symbol": registery.get(chain.chain_id).symbol,
                "explorer": registery.get(chain.chain_id).explorer + "address/",
                "balance": balances.get(i.address, float(0))
            }
            for i in all_user_wallets
        ]
    ]

    wallets_exist = len(wallets) > 0

    if wallets_exist:
        dialog_manager.dialog_data.update({"wallets": len(wallets)})

    return {
        "wallets": wallets, 
        "name": registery.get(chain.chain_id).display_name, 
        "wallets_exist": wallets_exist,
        "not_wallets_exist": not wallets_exist
    }
