import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт папок
from frontend.helper_pro import keyboards
from settings import backend_config as config

# Импорт модулей
from aiogram.filters import Command, CommandStart
from aiogram import types, Router
import asyncio
from datetime import datetime, time
import pytz

start_router = Router()
bot = config.bot

# Глобальный словарь для хранения ID стартовых сообщений по пользователям
start_message_ids = {}

# Глобальная переменная для задачи запуска сервиса
scheduler_task = None

# ============================================================================
# ФУНКЦИЯ ДЛЯ ЗАПУСКА СЕРВИСА В 7 УТРА (КРОМЕ СБ И ВС)
# ============================================================================
async def run_daily_service():
    """Запускает сервис каждый день в 7 утра по Москве, кроме выходных"""
    while True:
        try:
            # Текущее время по Москве
            moscow_tz = pytz.timezone('Europe/Moscow')
            now = datetime.now(moscow_tz)

            # Время следующего запуска (сегодня в 7:00)
            next_run = now.replace(hour=7, minute=0, second=0, microsecond=0)

            # Если сейчас уже после 7:00, запускаем завтра
            if now >= next_run:
                next_run = next_run.replace(day=next_run.day + 1)

            # Ждем до времени запуска
            sleep_seconds = (next_run - now).total_seconds()
            await asyncio.sleep(sleep_seconds)

            # Проверяем, не выходной ли сегодня
            if next_run.weekday() < 5:  # 0-4: пн-пт
                print(f"🚀 Запуск сервиса в {next_run.strftime('%Y-%m-%d %H:%M')} МСК")

                # Сервис будет работать до 23:45, поэтому ничего не делаем
                # Он сам завершится

        except Exception as e:
            logger.error(f"Ошибка в планировщике сервиса: {e}")
            await asyncio.sleep(60)  # Пауза перед повторной попыткой

# ============================================================================

@start_router.message(CommandStart())
async def handle_start(message: types.Message):
    """Обработка команды /start"""
    try:
        user_id = message.from_user.id
        global scheduler_task

        welcome_text = '*Welcome to Trade & Stage*'

        # Проверяем, есть ли уже стартовое сообщение для этого пользователя
        if user_id in start_message_ids:
            try:
                # Редактируем существующее сообщение
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=start_message_ids[user_id],
                    text=welcome_text,
                    reply_markup=keyboards.exchange_keyboard(),
                    parse_mode='Markdown'
                )
                return
            except Exception:
                # Если редактирование не удалось (сообщение удалено), создаем новое
                pass

        # Отправляем новое стартовое сообщение
        start_message = await message.answer(
            welcome_text,
            reply_markup=keyboards.exchange_keyboard(),
            parse_mode='Markdown'
        )

        # Сохраняем ID сообщения для этого пользователя
        start_message_ids[user_id] = start_message.message_id

        # Запускаем планировщик сервиса при первом старте
        if scheduler_task is None or scheduler_task.done():
            scheduler_task = asyncio.create_task(run_daily_service())
            print("✅ Планировщик сервиса запущен")

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка при запуске бота")

@start_router.callback_query(lambda c: c.data == "main_menu")
async def handle_main_menu(callback: types.CallbackQuery):
    """Обработка кнопки главного меню"""
    try:
        user_id = callback.from_user.id

        welcome_text = '*Welcome to Trade & Stage*'

        # Обновляем стартовое сообщение
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=welcome_text,
                reply_markup=keyboards.exchange_keyboard(),
                parse_mode='Markdown'
            )
        else:
            # Создаем новое сообщение
            new_message = await callback.message.answer(
                welcome_text,
                reply_markup=keyboards.exchange_keyboard(),
                parse_mode='Markdown'
            )
            start_message_ids[user_id] = new_message.message_id

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in main menu handler: {e}")
        await callback.answer("Произошла ошибка")

# Обработка выбора биржи (SPBFUT или TQBR)
@start_router.callback_query(lambda c: c.data in ["exchange_SPBFUT", "exchange_TQBR"])
async def handle_exchange_selection(callback: types.CallbackQuery):
    """Обработка выбора биржевой площадки"""
    try:
        user_id = callback.from_user.id
        exchange = callback.data.replace("exchange_", "")

        # Получаем название площадки для отображения
        exchange_names = {
            "SPBFUT": "Фьючерсы",
            "TQBR": "Акции"
        }

        exchange_display = exchange_names.get(exchange, exchange)

        # Обновляем сообщение с клавиатурой выбранной площадки
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"*{exchange_display}*\n\nВыберите торговый инструмент:",
                reply_markup=keyboards.tickers_keyboard(exchange),
                parse_mode='Markdown'
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in exchange selection: {e}")
        await callback.answer("Произошла ошибка")