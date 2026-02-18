import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт папок
from settings import backend_config as config

# Импорт модулей
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import math

# Глобальный словарь для хранения текущих страниц по пользователям
user_pages = {}

def exchange_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора биржевой площадки"""
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(text="Фьючерсы", callback_data="exchange_SPBFUT"),
        InlineKeyboardButton(text="Акции", callback_data="exchange_TQBR")
    )

    return builder.as_markup()

def tickers_keyboard(exchange: str, user_id: int = None, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура с тикерами для выбранной биржи с постраничной навигацией"""
    builder = InlineKeyboardBuilder()

    # Получаем тикеры для выбранной биржи
    tickers = config.TRADING_TIKERS.get(exchange, {})
    ticker_items = list(tickers.items())

    # Определяем количество колонок в зависимости от типа
    if exchange == "SPBFUT":
        columns = 2  # Фьючерсы в 2 колонки
    else:
        columns = 3  # Акции в 3 колонки

    # Настройки пагинации
    rows = 3  # Всегда 3 строки
    items_per_page = columns * rows  # 6 для фьючерсов, 9 для акций
    total_pages = math.ceil(len(ticker_items) / items_per_page) if ticker_items else 1

    # Корректируем номер страницы
    page = max(0, min(page, total_pages - 1)) if total_pages > 0 else 0

    # Сохраняем страницу для пользователя
    if user_id:
        if user_id not in user_pages:
            user_pages[user_id] = {}
        user_pages[user_id][exchange] = page

    # Вычисляем начальный и конечный индексы для текущей страницы
    start_idx = page * items_per_page
    end_idx = min(start_idx + items_per_page, len(ticker_items))

    # Получаем элементы для текущей страницы
    current_page_items = ticker_items[start_idx:end_idx]

    # =================================================================
    # СОЗДАЕМ СЕТКУ 3x(columns) С ПУСТЫМИ КНОПКАМИ ДЛЯ ЗАПОЛНЕНИЯ
    # =================================================================
    for row in range(rows):
        row_buttons = []

        for col in range(columns):
            item_index = row * columns + col

            if item_index < len(current_page_items):
                # Есть реальный тикер на этой позиции
                ticker_text, ticker_code = current_page_items[item_index]
                display_name = ticker_text
                if len(display_name) > 10:  # Обрезаем длинные названия
                    display_name = display_name[:8] + ".."
                row_buttons.append(
                    InlineKeyboardButton(text=display_name, callback_data=f"pair_{ticker_text}")
                )
            else:
                # Пустая кнопка-заполнитель
                row_buttons.append(
                    InlineKeyboardButton(text=" ", callback_data="ignore")
                )

        builder.row(*row_buttons)
    # =================================================================

    # =================================================================
    # Строка навигации - ВСЕГДА 3 ПОЗИЦИИ
    # =================================================================
    nav_buttons = []

    # Кнопка предыдущей страницы (всегда присутствует, но может быть неактивной)
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="<", callback_data=f"page_{exchange}_{page-1}")
        )
    else:
        # Пустая кнопка-заглушка для сохранения 3 позиций
        nav_buttons.append(
            InlineKeyboardButton(text=" ", callback_data="ignore")
        )

    # Индикатор страницы (всегда присутствует)
    nav_buttons.append(
        InlineKeyboardButton(text=f"{page+1}/{total_pages if total_pages > 0 else 1}",
                           callback_data="current_page")
    )

    # Кнопка следующей страницы (всегда присутствует, но может быть неактивной)
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(text=">", callback_data=f"page_{exchange}_{page+1}")
        )
    else:
        # Пустая кнопка-заглушка для сохранения 3 позиций
        nav_buttons.append(
            InlineKeyboardButton(text=" ", callback_data="ignore")
        )

    builder.row(*nav_buttons)
    # =================================================================

    # Кнопка возврата к выбору биржи
    builder.row(
        InlineKeyboardButton(text="Назад", callback_data="back_to_exchanges")
    )

    return builder.as_markup()

def stoploss_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для ввода стоплосса"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Отменить сделку", callback_data="cancel_deal"),
        InlineKeyboardButton(text="Назад", callback_data="back_to_exchanges")
    )
    return builder.as_markup()

def confirmation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для подтверждения сделки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить сделку", callback_data="confirm_deal"),
        InlineKeyboardButton(text="Отменить", callback_data="cancel_deal")
    )
    return builder.as_markup()

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()