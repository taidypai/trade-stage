import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from backend import config_main as config

def main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура со всеми торговыми парами"""
    builder = InlineKeyboardBuilder()

    # Берем все пары из TRADING_TIKERS
    tickers = list(config.TRADING_TIKERS.items())

    # Создаем кнопки парами (по 2 в ряд)
    for i in range(0, len(tickers), 2):
        if i + 1 < len(tickers):
            # Есть пара кнопок для ряда
            ticker1_text, ticker1_code = tickers[i]
            ticker2_text, ticker2_code = tickers[i + 1]

            builder.row(
                InlineKeyboardButton(text=ticker1_text, callback_data=f"pair_{ticker1_text}"),
                InlineKeyboardButton(text=ticker2_text, callback_data=f"pair_{ticker2_text}")
            )
        else:
            # Последняя нечетная кнопка
            ticker_text, ticker_code = tickers[i]
            builder.row(
                InlineKeyboardButton(text=ticker_text, callback_data=f"pair_{ticker_text}")
            )

    return builder.as_markup()

def stoploss_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ввода стоплосса"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()

def link_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ввода ссылки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отменить сделку", callback_data="cancel_deal")
    )
    return builder.as_markup()