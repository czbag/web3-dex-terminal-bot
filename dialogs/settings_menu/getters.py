from aiogram.types import User as AIOUser
from aiogram_dialog import DialogManager

from db.repositories.chain import UserChainRepository
from chains import registery
from utils.utils import smart_round


async def get_chain_settings(
    dialog_manager: DialogManager, event_from_user: AIOUser, **kwargs
):
    session = kwargs.get("session")

    chain_id = dialog_manager.start_data.get("chain_id")

    user_chains_repo = UserChainRepository(session)

    chain_settings = await user_chains_repo.get_by_id_with_chain(int(chain_id))

    data = dialog_manager.dialog_data

    data.update(
        {   
            "chain_id": chain_settings.id,
            "name": registery.get(chain_settings.chain.chain_id).display_name,
            "buy_slippage": smart_round(float(chain_settings.buy_slippage)),
            "sell_slippage": smart_round(float(chain_settings.sell_slippage)),
            "buy_price_impact": smart_round(float(chain_settings.buy_price_impact)),
            "sell_price_impact": smart_round(float(chain_settings.sell_price_impact)),
            "buy_gas_delta": smart_round(float(chain_settings.buy_gas_delta)),
            "sell_gas_delta": smart_round(float(chain_settings.sell_gas_delta)),
            "approve_gas_delta": smart_round(float(chain_settings.approve_gas_delta)),
            "auto_approve": chain_settings.auto_approve,
            "not_auto_approve": not chain_settings.auto_approve,
            "max_gas_price": chain_settings.max_gas_price,
            "max_gas_limit": chain_settings.max_gas_limit,
        }
    )

    return data
