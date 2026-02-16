from datetime import datetime
from decimal import Decimal
import logging
import re

from aiogram import Router, F
from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram_dialog import DialogManager, StartMode
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from chains import registery
from clients.evm.scanner import LiquidityScanner, ScanResult
from clients.evm.swap import SwapClient
from clients.evm.wallet import WalletClient
from db.repositories.chain import ChainRepository, UserChainRepository
from db.repositories.user import UserRepository
from db.repositories.wallet import WalletRepository
from dialogs.token_menu.handlers import format_number
from enums.chain import ChainStatus
from filters.address import AddressFilter
from keyboards.token_info import token_info_kb
from services.wallet import WalletService
from states.dialog_states import TokenSG
from states.fsm_states import TokenInfo
from utils.utils import convert_price, format_amount

router = Router()

module_logger = logging.getLogger(__name__)


@router.message(F.text.regexp(r"^(0x)?[0-9a-fA-F]{40}$"), AddressFilter())
async def check_address(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
    address: str,
) -> None:
    await state.clear()

    user_repo = UserRepository(session)
    user_chains_repo = UserChainRepository(session)
    wallet_repo = WalletRepository(session)

    user = await user_repo.get_by_telegram_id(message.from_user.id)
    all_user_networks = await user_chains_repo.get_chains_with_status(user.id)
    scan_chains = [registery.get(i.evm_chain_id) for i in all_user_networks if i.status is ChainStatus.ACTIVE]
    
    scanner = LiquidityScanner(
        scan_chains,
        session_factory
    )

    wallets = await wallet_repo.get_all_with_chain(user.id)

    all_user_wallets = {}
    for wallet in wallets:
        chain_id = str(wallet.chain.chain_id)

        if chain_id not in all_user_wallets:
            all_user_wallets[chain_id] = []

        all_user_wallets[chain_id].append({
            "id": wallet.id,
            "wallet_name": wallet.name,
            "address": wallet.address
        })

    price = await redis.get("eth:usd")

    data = await scanner.scan_token(address, all_user_wallets, Decimal(price))
    print(data)
    if not data:
        await message.answer(
            "💳 <b>Wallet address</b>\n\n" +
            f"<code>{message.text}</code>"
        )
        return

    best_chain = data.best_eth_token_pool.chain \
                if data.route_type == "direct" else \
                data.best_stable_token_pool.chain

    await state.set_state(TokenInfo.info)
    await state.update_data(
        {
            "token_address": address,
            "name": data.token_meta.name,
            "ticker": data.token_meta.ticker,
            "chain_id": best_chain.chain_id,
            "_user_id": user.id,
            "is_multi": False,
            "is_buy": True
        }
    )

    await token_info(message, state, redis, data, address)

async def get_token_analysis(
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
    user_id: int,
    chain_id: int,
    token_address: str
) -> ScanResult:
    user_repo = UserRepository(session)
    chains_repo = ChainRepository(session)
    wallet_repo = WalletRepository(session)

    user = await user_repo.get_by_id(user_id)
    chain = await chains_repo.get_by_chain_id(chain_id)

    wallets = await wallet_repo.get_all_with_chain(user.id, chain.id)

    price = await redis.get("eth:usd")

    all_user_wallets = {}
    for wallet in wallets:
        if str(chain_id) not in all_user_wallets:
            all_user_wallets[str(chain_id)] = []

        all_user_wallets[str(chain_id)].append({
            "id": wallet.id,
            "wallet_name": wallet.name,
            "address": wallet.address
        })

    scanner = LiquidityScanner(
        [registery.get(chain_id)],
        session_factory
    )

    data = await scanner.scan_token(token_address, all_user_wallets, Decimal(price))
    return data

async def token_info(
    message: types.Message,
    state: FSMContext, 
    redis: Redis, 
    data: ScanResult, 
    token_address: str
):
    token_meta = data.token_meta
    is_direct = True if data.route_type == "direct" else False
    best_pool = data.best_eth_token_pool if is_direct else data.best_stable_token_pool
    chain = best_pool.chain

    price = await redis.get("eth:usd")
    token_price = convert_price(data.token_price, Decimal(price))
    market_cap = convert_price(data.market_cap, Decimal("1"))
    tvl = convert_price(best_pool.tvl, Decimal(price)) if is_direct else convert_price(best_pool.tvl, Decimal("1"))

    refresh_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    wallets = data.wallet_balances[chain.chain_id]["wallets"]

    await state.update_data(
        wallets=[
            {
                "id": i["id"],
                "name": i["wallet_name"],
                "native_balance": str(i["native_balance"]),
                "token_balance": str(i["token_balance"]),
                "is_active": True if _ == 0 else False
            } for _, i in enumerate(wallets)
        ],
    )
    state_data = await state.get_data()

    current_wallet_idx = state_data.get("idx", 0)

    balances_text = "".join(
        [
            f"\n{w['wallet_name']} | {format_amount(w['token_balance'])} | {format_amount(w['native_balance'])}" for w in wallets
        ]
    )

    kb = token_info_kb(state_data["wallets"], current_wallet_idx, state_data.get("is_multi", False), state_data["is_buy"])

    await message.answer(
        f"🪙 <b><a href='{chain.explorer}address/{token_address}'>{token_meta.name}</a></b> " +
        f"(<code>{token_meta.ticker}</code>) | {best_pool.version.title()} " +
        f"<a href='{chain.explorer}address/{best_pool.pool.pool}'>Pool</a> | {chain.name}\n\n" +
        f"📝 <code>{token_address}</code>\n\n" +
        # "⛽️ BASE | <b>0.009 GWEI  Ξ $0.0₇32</b>\n\n" +
        f"💵 Price: <b>${token_price}</b>\n" +
        f"🧢 MC: <b>${market_cap}</b>\n" +
        f"💧 TVL: <b>${tvl}</b>\n\n" +
        f"🕓 Refresh | <b>{refresh_time} (UTC+0)</b>\n\n" +
        "<blockquote expandable>💰 <b>Balance • Click to Expand</b>\n" +
        f"<code>Wallet | {token_meta.ticker} | {chain.symbol}" +
        balances_text +
        "</code></blockquote>",
        reply_markup=kb.as_markup(),
        disable_web_page_preview=True
    )


async def refresh_data(
    user_id: int,
    chain_id: int,
    token_address: str,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis
):
    scan_data = await get_token_analysis(
        session, 
        session_factory,
        redis,
        user_id,
        chain_id,
        token_address
    )

    return scan_data


@router.callback_query(F.data == "update_token_info", TokenInfo.info)
async def update_token_info(
    callback: types.CallbackQuery, 
    state: FSMContext,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
):
    data = await state.get_data()

    user_id = data["_user_id"]
    chain_id = data["chain_id"]
    token_address = data["token_address"]
    is_buy = data["is_buy"]

    scan_data = await refresh_data(
        user_id, chain_id, token_address, session, session_factory, redis
    )

    if not scan_data:
        await callback.answer("❗️ Update token data is error!", True)
        return
    
    await state.update_data({"idx": 0, "is_multi": False, "is_buy": is_buy})
    
    await callback.message.delete()
    return await token_info(callback.message, state, redis, scan_data, token_address)


@router.callback_query(F.data == "next_wallet", TokenInfo.info)
async def next_wallet(
    callback: types.CallbackQuery, 
    state: FSMContext,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
):
    data = await state.get_data()
    user_id = data["_user_id"]
    chain_id = data["chain_id"]
    token_address = data["token_address"]
    wallets = data["wallets"]
    is_buy = data["is_buy"]
    current_idx = data.get("idx", 0)

    if is_buy:
        current_idx = (current_idx + 1) % len(wallets)
    else:
        current_idx = (current_idx + 1) % len([w for w in wallets if Decimal(w["token_balance"]) > 0])

    await state.update_data(idx=current_idx)

    scan_data = await refresh_data(
        user_id, chain_id, token_address, session, session_factory, redis
    )

    if not scan_data:
        await callback.answer("❗️ Update token data is error!", True)
        return
    
    await callback.message.delete()
    return await token_info(callback.message, state, redis, scan_data, token_address)


@router.callback_query(F.data == "multi", TokenInfo.info)
async def toggle_multi(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    is_multi = data.get("is_multi", False)
    is_buy = data["is_buy"]
    current_idx = data.get("idx", 0)

    new_is_multi = not is_multi

    await state.update_data(is_multi=new_is_multi)

    kb = token_info_kb(data["wallets"], current_idx, new_is_multi, is_buy)

    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


@router.callback_query(F.data == "go_to_buy_or_sell", TokenInfo.info)
async def toggle_buy_sell(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    is_buy = data["is_buy"]

    new_is_buy = not is_buy

    if not new_is_buy:
        await state.update_data({"idx": 0, "is_buy": True, "is_multi": False})
    else:
        await state.update_data({"idx": 0, "is_buy": False, "is_multi": False})

    await state.update_data(is_buy=new_is_buy)

    kb = token_info_kb(data["wallets"], 0, False, new_is_buy)

    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("change_active_status"), TokenInfo.info)
async def change_wallet_multi_active(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    wallets = data["wallets"]
    is_buy = data["is_buy"]
    wallet_id = callback.data.split(':')[-1]
    current_idx = data.get("idx", 0)

    for wallet in wallets:
        if wallet["id"] == int(wallet_id):
            wallet["is_active"] = not wallet["is_active"]
            break

    await state.update_data(wallets=wallets)

    kb = token_info_kb(data["wallets"], current_idx, True, is_buy)

    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("turn_all"), TokenInfo.info)
async def turn_all_wallet(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()

    wallets = data["wallets"]
    is_buy = data["is_buy"]
    method = callback.data.split(':')[-1]
    current_idx = data.get("idx", 0)

    for wallet in wallets:
        wallet["is_active"] = True if method == "on" else False

    await state.update_data(wallets=wallets)

    kb = token_info_kb(data["wallets"], current_idx, True, is_buy)

    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())


@router.callback_query(F.data.in_(["make_approve", "make_revoke"]), TokenInfo.info)
async def handle_allowance(
    callback: types.CallbackQuery, 
    state: FSMContext,
    session: AsyncSession
):
    is_approve = callback.data == "make_approve"
    operation = "Approve" if is_approve else "Revoke"
    target_allowance = 2 ** 256 - 1 if is_approve else 0

    data = await state.get_data()

    wallets = data["wallets"]
    current_idx = data.get("idx", 0)
    token_address = data["token_address"]
    user_id = data["_user_id"]
    chain_id = data["chain_id"]
    chain_config = registery.get(data["chain_id"])
    current_wallet = wallets[current_idx]

    user_chains_repo = UserChainRepository(session)
    chain_repo = ChainRepository(session)
    wallet_repo = WalletRepository(session)

    chain = await chain_repo.get_by_chain_id(chain_id)
    chain_settings = await user_chains_repo.get_by_chain_id_and_user_id(user_id, chain.id)
    user_wallet = await wallet_repo.get_by_id(current_wallet["id"])

    async with SwapClient(chain_config) as swap_client:
        allowance = await swap_client.check_allowance(
            token_address,
            user_wallet.address,
        )

    if (is_approve and allowance != 0) or (not is_approve and allowance == 0):
        status_msg = "No allowance approval needed" if is_approve else "Associated spender (router) has no allowance"
        await callback.message.answer(
            f"🪙 <b><a href='{chain_config.explorer}token/{token_address}'>{data['name']}</a></b> <code>(${data['ticker']})</code>\n\n"
            f"📝 <code>{token_address}</code>\n\n"
            f"{status_msg} for wallet 💳 {current_wallet['name']}. You can sell immediately when you need to.",
            disable_web_page_preview=True
        )
        return
    
    async with SwapClient(chain_config) as swap_client:
        approve_tx = await swap_client.approve(
            user_wallet.address,
            token_address,
            chain_settings.max_gas_price,
            chain_settings.max_gas_limit,
            chain_settings.approve_gas_delta,
            target_allowance
        )

    wallet_service = WalletService()
    pk = user_wallet.decrypt_private_key(wallet_service.get_cipher())

    async with WalletClient(chain_config, pk) as wallet_client:
        tx_hash = await wallet_client.execute_transaction(approve_tx)

        approve_message = await callback.message.answer(
            f"🪙 <b><a href='{chain_config.explorer}token/{token_address}'>{data['name']}</a></b> <code>(${data['ticker']})</code>\n\n" + 
            f"📝 <code>{token_address}</code>\n\n" +
            f"⚪️ <a href='{chain_config.explorer}tx/0x{tx_hash}'>{operation}</a> of spender allowance is pending | 💳 {current_wallet['name']}",
            disable_web_page_preview=True
        )

        receipt = await wallet_client.wait_transaction(tx_hash)

        await approve_message.edit_text(
            f"🪙 <b><a href='{chain_config.explorer}token/{token_address}'>{data['name']}</a></b> <code>(${data['ticker']})</code>\n\n" + 
            f"📝 <code>{token_address}</code>\n\n" +
            f"🟢 <a href='{chain_config.explorer}tx/0x{tx_hash}'>{operation}</a> succeeded | 💳 {current_wallet['name']}",
            disable_web_page_preview=True
        )


async def execute_swap(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
    amount: str,
    is_buy: bool = True
):
    data = await state.get_data()

    wallets = data["wallets"]
    current_idx = data.get("idx", 0)
    token_address = data["token_address"]
    user_id = data["_user_id"]
    chain_id = data["chain_id"]
    chain_config = registery.get(data["chain_id"])
    selected_wallet = wallets[current_idx]

    user_chains_repo = UserChainRepository(session)
    chain_repo = ChainRepository(session)
    wallet_repo = WalletRepository(session)

    chain = await chain_repo.get_by_chain_id(chain_id)
    chain_settings = await user_chains_repo.get_by_chain_id_and_user_id(user_id, chain.id)
    user_wallet = await wallet_repo.get_by_id(selected_wallet["id"])

    scan_data = await refresh_data(
        user_id, chain_id, token_address, session, session_factory, redis
    )

    # print(scan_data)
    
    wallets = scan_data.wallet_balances[chain_config.chain_id]["wallets"]

    current_wallet = next(
        (w for w in wallets if w["id"] == selected_wallet["id"]), 
        None
    )

    amount_raw = int(Decimal(amount) * (10 ** 18)) \
                if is_buy else \
                int(
                    (current_wallet["token_balance"] * Decimal(amount))
                    * (10 ** scan_data.token_meta.decimals)
                )
    
    action_name = "Buy" if is_buy else "Sell"
    price_impact_limit = chain_settings.buy_price_impact if is_buy else chain_settings.sell_price_impact
    slippage_limit = chain_settings.buy_slippage if is_buy else chain_settings.sell_slippage

    base_message = (
        f"🪙 <b><a href='{chain_config.explorer}token/{token_address}'>{data["name"]}</a></b> "
        f"<code>(${data["ticker"]})</code>\n\n"
        f"📝 <code>{token_address}</code>\n\n"
    )

    async with SwapClient(chain_config) as swap_client:
        simulation = await swap_client.simulate_swap(
            scan_data,
            current_wallet["address"],
            amount_raw,
            is_buy
        )
        # print(simulation)

    if not simulation.success:
        await message.answer(
            base_message +
            f"🟥 {action_name} failed | 💳 {current_wallet['wallet_name']}\n\n"
            f"<blockquote>ℹ️ Error: {simulation.error}</blockquote>",
            disable_web_page_preview=True
        )
        return
    
    if simulation.price_impact > price_impact_limit:
        await message.answer(
            base_message +
            f"⚠️ PRICE IMPACT WARNING {simulation.price_impact} > {price_impact_limit} | "
            f"💳 {current_wallet['wallet_name']}",
            disable_web_page_preview=True
        )
        return

    if simulation.slippage > slippage_limit:
        await message.answer(
            base_message +
            f"⚠️ SLIPPAGE WARNING {simulation.slippage} > {slippage_limit} | "
            f"💳 {current_wallet['wallet_name']}",
            disable_web_page_preview=True
        )
        return

    gas_delta = chain_settings.buy_gas_delta if is_buy else chain_settings.sell_gas_delta
    async with SwapClient(chain_config) as swap_client:
        swap_tx = await swap_client.make_swap(
            scan_data,
            current_wallet["address"],
            simulation.amount_in,
            simulation.amount_out,
            slippage_limit,
            chain_settings.max_gas_price,
            chain_settings.max_gas_limit,
            gas_delta,
            is_buy
        )

    wallet_service = WalletService()
    pk = user_wallet.decrypt_private_key(wallet_service.get_cipher())

    async with WalletClient(chain_config, pk) as wallet_client:
        tx_hash = await wallet_client.execute_transaction(swap_tx)
        
        pending_message = await message.answer(
            base_message +
            f"⚪️ <a href='{chain_config.explorer}tx/0x{tx_hash}'>{action_name}</a> tokens is pending | "
            f"💳 {current_wallet['wallet_name']}",
            disable_web_page_preview=True
        )
        
        receipt = await wallet_client.wait_transaction(tx_hash)
        
        await pending_message.edit_text(
            base_message +
            f"🟢 <a href='{chain_config.explorer}tx/0x{tx_hash}'>{action_name}</a> succeeded | "
            f"💳 {current_wallet['wallet_name']}",
            disable_web_page_preview=True
        )

@router.callback_query(F.data.startswith("buy_token:"), TokenInfo.info)
async def buy_token(
    callback: types.CallbackQuery, 
    state: FSMContext,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
):
    await execute_swap(
        callback.message,
        state,
        session,
        session_factory,
        redis,
        callback.data.split(":")[-1]
    )


@router.callback_query(F.data.startswith("sell_token"), TokenInfo.info)
async def sell_token(
    callback: types.CallbackQuery, 
    state: FSMContext,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
):
    await execute_swap(
        callback.message,
        state,
        session,
        session_factory,
        redis,
        callback.data.split(":")[-1],
        False
    )


@router.callback_query(F.data.startswith("buy_token_custom"), TokenInfo.info)
async def buy_token_custom(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Reply to this message with your amount for swap in ETH.\n\n" +
        "min 0.0001, max 100"
    )
    await state.set_state(TokenInfo.amount)



@router.message(F.text, TokenInfo.amount)
async def get_custom_amount(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession,
    session_factory: sessionmaker,
    redis: Redis,
) -> None:
    sta = await state.get_data()

    try:
        if 0.0001 <= float(message.text) <= 100:
            await execute_swap(
                message,
                state,
                session,
                session_factory,
                redis,
                message.text
            )
        else:
            await message.answer("❌ You must use a valid amount greater than 0.0001 and less than 100. Please try again.")

    except:    
        await message.answer("❌ You must use a valid amount greater than 0.0001 and less than 100. Please try again.")
