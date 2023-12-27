import asyncio
import json
import logging
from urllib.parse import quote

from aiogram import Bot, Dispatcher, executor, types

from services_api import Service
from tools import *

logging.basicConfig(level=logging.INFO)
bot = Bot(token="6766163800:AAEiePkz6fEDRXdyAEF6s5lRsev4bo6220M", parse_mode=types.ParseMode.MARKDOWN)
dp = Dispatcher(bot)

services = Service()
config = {}


async def config_update():
    global config
    while True:
        gram_ton_balances = await services.get_balances()
        gram_ton_wallets = await services.get_wallet_config()
        gram_ton_config = await services.get_app_config()
        config = {"balances": gram_ton_balances, "wallets": gram_ton_wallets["wallets"], "config": gram_ton_config}
        await asyncio.sleep(5)


async def on_startup(dispatcher: Dispatcher):
    asyncio.create_task(config_update())


@dp.message_handler(commands=["start"])
async def start_app(message: types.Message):
    if config["config"]["clientbot_status"] == "Inactive":
        await message.reply("Service under maintenance.")
        return

    buttons = [
        types.InlineKeyboardButton(text="🔁 Exchange", callback_data="ex_menu"),
        types.InlineKeyboardButton(text="📃 Inscribe", url="https://t.me/gram20bot/app"),
    ]
    keyboard = types.InlineKeyboardMarkup(row_width=1).add(*buttons)

    welcome_text = (
        "Welcome to Umbrella\n\n" "It's the first OTC bot for Gram-20 inscriptions.\n\n" "Feel free to use it."
    )
    await message.reply(welcome_text, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == "menu")
async def select_pair(query: types.CallbackQuery):
    await query.answer()

    if config["config"]["clientbot_status"] == "Inactive":
        await bot.send_message(chat_id=query.from_user.id, text="Service under maintenance.")
        return

    buttons = [
        types.InlineKeyboardButton(text="🔁 Exchange", callback_data="ex_menu"),
        types.InlineKeyboardButton(text="📃 Inscribe", url="https://t.me/gram20bot/app"),
    ]

    keyboard = types.InlineKeyboardMarkup(row_width=1).add(*buttons)

    await bot.edit_message_text(
        text="Welcome to Umbrella\n\nIt's the first OTC bot for Gram-20 inscriptions.\n\nFeel free to use it.",
        chat_id=query.from_user.id,
        message_id=query.message.message_id,
        reply_markup=keyboard,
    )


@dp.callback_query_handler(lambda c: c.data == "ex_menu")
async def select_pair(query: types.CallbackQuery):
    await query.answer()

    if config["config"]["clientbot_status"] == "Inactive":
        await bot.send_message(chat_id=query.from_user.id, text="Service under maintenance.")
        return

    keyboard = types.InlineKeyboardMarkup(row_width=1).add(
        types.InlineKeyboardButton(text="GRAM/TON", callback_data="exchange:GRAM_TON"),
        types.InlineKeyboardButton(text="⬅️ Back", callback_data="menu"),
    )

    await bot.edit_message_text(
        text="🔁 What do you want to exchange?",
        chat_id=query.from_user.id,
        message_id=query.message.message_id,
        reply_markup=keyboard,
    )


@dp.callback_query_handler(lambda c: c.data.startswith("exchange"))
async def pair_selected(data: types.CallbackQuery):
    await data.answer()

    if config["config"]["clientbot_status"] == "Inactive":
        await bot.send_message(chat_id=data.from_user.id, text="Service under maintenance.")
        return

    pair_from, pair_to = data.data.replace("exchange:", "").split("_")

    await bot.edit_message_text(
        message_id=data.message.message_id,
        chat_id=data.from_user.id,
        text=f"🔁 Selected pair *{pair_from}/{pair_to}*\n\nWhat you gonna do?",
        reply_markup=types.InlineKeyboardMarkup(2).add(
            types.InlineKeyboardButton(text=f"Buy {pair_from}", callback_data="buy:" + pair_from + "_" + pair_to),
            types.InlineKeyboardButton(text=f"Sell {pair_from}", callback_data="sell:" + pair_from + "_" + pair_to),
            types.InlineKeyboardButton(text="⬅️ Back", callback_data="ex_menu"),
        ),
    )


@dp.callback_query_handler(lambda c: c.data.startswith("buy"))
async def pair_selected(data: types.CallbackQuery):
    await data.answer()

    if config["config"]["clientbot_status"] == "Inactive":
        await bot.send_message(chat_id=data.from_user.id, text="Service under maintenance.")
        return

    pair_from, pair_to = data.data.replace("buy:", "").split("_")

    price = config["config"]["sellprice_per_gram"]  # in tons, /10000

    hot_grams_balance = config["balances"]["gram"]["send"]["balance"]  # in grams
    # hot_grams_balance_ton = convert_g2t(hot_grams_balance, price)

    min_by_config = config["config"]["minsell_in_ton"]  # in tons
    # min_by_config_gram = convert_t2g(min_by_config, price)  # in grams

    max_by_config = config["config"]["maxsell_in_ton"]  # in tons
    max_by_config_gram = convert_t2g(max_by_config, price)  # in grams

    wallet_to_send_to = config["wallets"]["ton_receive_address"]

    available_max = convert_g2t(min(hot_grams_balance, max_by_config_gram), price)

    if min_by_config > available_max:
        await bot.send_message(chat_id=data.from_user.id, text="Pool not available")
        return

    buy_message = (
        f"🔁 You want to buy *{pair_from}*\n\n"
        f"Price: *{round(price * 10000, 4)} TON* for 10,000 {pair_from}\n\n"
        f"Minimum: *{min_by_config} {pair_to}*\nMaximum: *{available_max} {pair_to}*\n\n"
        f"Wallet address: `{wallet_to_send_to}` (Click to copy)\n\n"
        "_If you send less or more than limits, you will lose your funds._"
    )

    # @wallet, tonkeeper, tonhub, mytonwallet

    await bot.edit_message_text(
        text=buy_message,
        chat_id=data.from_user.id,
        message_id=data.message.message_id,
        reply_markup=types.InlineKeyboardMarkup(1).add(
            types.InlineKeyboardButton(text="💸 Pay with default wallet", url=f"ton://transfer/{wallet_to_send_to}"),
            types.InlineKeyboardButton(text="💸 Pay with @Wallet",
                                       url=f"https://t.me/wallet?startattach"),
            types.InlineKeyboardButton(text="💸 Pay with Tonkeeper",
                                       url=f"https://app.tonkeeper.com/transfer/{wallet_to_send_to}?amount=0"),
            types.InlineKeyboardButton(text="💸 Pay with Tonhub",
                                       url=f"https://tonhub.com/transfer/{wallet_to_send_to}?amount=0"),
            types.InlineKeyboardButton(text="⬅️ Back", callback_data=f"exchange:{pair_from}_{pair_to}"),
        ),
    )


@dp.callback_query_handler(lambda c: c.data.startswith("sell"))
async def pair_selected(data: types.CallbackQuery):
    await data.answer()

    if config["config"]["clientbot_status"] == "Inactive":
        await bot.send_message(chat_id=data.from_user.id, text="Service under maintenance.")
        return

    pair_from, pair_to = data.data.replace("sell:", "").split("_")

    price = config["config"]["buyprice_per_gram"]  # in tons, /10000

    hot_ton_balance = config["balances"]["ton"]["send"]["balance"]  # in tons
    hot_ton_balance_gram = convert_t2g(hot_ton_balance, price)

    min_by_config = config["config"]["minbuy_in_ton"]  # in tons
    min_by_config_gram = convert_t2g(min_by_config, price)  # in grams

    max_by_config = config["config"]["maxbuy_in_ton"]  # in tons
    max_by_config_gram = convert_t2g(max_by_config, price)  # in grams

    wallet_to_send_to = config["wallets"]["gram20_receive_address"]

    available_max = min(max_by_config_gram, hot_ton_balance_gram)

    # print('hot_ton_balance_gram', hot_ton_balance_gram)
    # print('max_by_config_gram', max_by_config_gram)
    # print('min_by_config_gram', min_by_config_gram)

    if min_by_config_gram > available_max:
        await bot.send_message(chat_id=data.from_user.id, text="Pool not available")
        return

    sell_message = (
        f"🔁 You want to sell *{pair_from}*\n\n"
        f"Price: *{round(price * 10000, 4)} TON* for 10,000 {pair_from}\n\n"
        f"Minimum: *{'{:,}'.format(int(min_by_config_gram))} {pair_from}*\nMaximum: *{'{:,}'.format(int(available_max))} {pair_from}*\n\n"
        f"Wallet address: `{wallet_to_send_to}` (Click to copy)\n\n"
        "_If you send less or more than limits, you will lose your funds._"
    )

    to_user_send = 10000 if int(available_max) > 10000 else int(available_max)

    await bot.edit_message_text(
        text=sell_message,
        chat_id=data.from_user.id,
        message_id=data.message.message_id,
        reply_markup=types.InlineKeyboardMarkup().add(
            types.InlineKeyboardButton(
                text="💸 Transfer GRAM",
                url="https://t.me/gram20stagingbot/app?startapp="
                + quote(
                    json.dumps(
                        {
                            "to": wallet_to_send_to,
                            "amount": to_user_send,
                            "tick": "gram",
                            "memo": "exchange",
                            "type": "transfer",
                        }
                    )
                )
                .replace("%", "--")
                .replace(
                    "=",
                    "__",
                )
                .replace("&", "-"),
            ),
            types.InlineKeyboardButton(text="⬅️ Back", callback_data=f"exchange:{pair_from}_{pair_to}"),
        ),
    )


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)
