import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт папок
from settings import backend_config as config
from frontend.helper_pro import keyboards

# Импорт модулей
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

callback_router = Router()
bot = config.bot

# Импортируем словарь из start_router
from frontend.helper_pro.handlers.start_router import start_message_ids

# Определяем состояния FSM
class TradeStates(StatesGroup):
    waiting_for_stoploss = State()
    waiting_for_confirmation = State()

# Глобальное хранилище для данных сделки
trade_data = {}

# Обработка выбора торговой пары
@callback_router.callback_query(F.data.startswith("pair_"))
async def handle_pair_selection(callback: CallbackQuery, state: FSMContext):
    """Пользователь выбрал торговую пару"""
    try:
        user_id = callback.from_user.id

        # Извлекаем название пары
        pair = callback.data.replace("pair_", "")

        # Сохраняем выбранную пару
        await state.update_data(pair=pair)

        # Устанавливаем состояние ожидания стоплосса
        await state.set_state(TradeStates.waiting_for_stoploss)

        # Обновляем стартовое сообщение
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"📊 *{pair}*\n\nВведите стоп-лосс (в процентах или абсолютное значение):\n\nПримеры:\n• 2.5 (2.5%)\n• 450 (абсолютное значение)",
                reply_markup=keyboards.stoploss_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если ID не найден, отправляем новое сообщение
            new_message = await callback.message.answer(
                f"📊 *{pair}*\n\nВведите стоп-лосс:",
                reply_markup=keyboards.stoploss_keyboard(),
                parse_mode="Markdown"
            )
            start_message_ids[user_id] = new_message.message_id

        await callback.answer()

    except Exception as e:
        print(f"Error in pair selection: {e}")
        await callback.answer("Произошла ошибка")

# Обработка кнопки назад к выбору биржи
@callback_router.callback_query(F.data == "back_to_exchanges")
async def handle_back_to_exchanges(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору биржи"""
    try:
        user_id = callback.from_user.id

        # Очищаем состояние
        await state.clear()

        # Возвращаемся к выбору биржи
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text = '*Welcome to Trade & Stage*',
                reply_markup=keyboards.exchange_keyboard(),
                parse_mode='Markdown'
            )

        await callback.answer()

    except Exception as e:
        print(f"Error in back to exchanges: {e}")
        await callback.answer("Произошла ошибка")

# Обработка кнопки отмены сделки
@callback_router.callback_query(F.data == "cancel_deal")
async def handle_cancel_deal(callback: CallbackQuery, state: FSMContext):
    """Отмена сделки"""
    try:
        user_id = callback.from_user.id

        # Очищаем состояние
        await state.clear()

        # Возвращаемся к выбору биржи
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text = '*Welcome to Trade & Stage*',
                reply_markup=keyboards.exchange_keyboard(),
                parse_mode='Markdown'
            )

        await callback.answer("Сделка отменена")

    except Exception as e:
        print(f"Error in cancel deal: {e}")
        await callback.answer("Произошла ошибка")

# Обработка подтверждения сделки
@callback_router.callback_query(F.data == "confirm_deal")
async def handle_confirm_deal(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сделки и запуск торгового сервиса"""
    try:
        user_id = callback.from_user.id

        # Получаем данные из состояния
        data = await state.get_data()
        pair = data.get('pair')
        stoploss = data.get('stoploss')

        # ============================================================================
        # ЗДЕСЬ ЗАПУСКАЕТСЯ ТОРГОВЫЙ СЕРВИС С ПЕРЕДАННЫМИ ПАРАМЕТРАМИ
        # ============================================================================
        print(f"🚀 Запуск торгового сервиса:")
        print(f"  Пара: {pair}")
        print(f"  Стоп-лосс: {stoploss}")

        # ЗДЕСЬ ВСТАВЬТЕ КОД ЗАПУСКА ВАШЕГО ТОРГОВОГО СЕРВИСА
        # await trading_service.start(pair, stoploss)
        # ============================================================================

        # Очищаем состояние
        await state.clear()

        # Показываем подтверждение
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"✅ *Сделка запущена!*\n\nПара: {pair}\nСтоп-лосс: {stoploss}\n\nТорговый сервис активирован.",
                reply_markup=keyboards.main_menu_keyboard(),
                parse_mode='Markdown'
            )

        await callback.answer("Сделка подтверждена")

    except Exception as e:
        print(f"Error in confirm deal: {e}")
        await callback.answer("Произошла ошибка")

# Обработка ввода стоплосса
@callback_router.message(TradeStates.waiting_for_stoploss)
async def handle_stoploss_input(message: Message, state: FSMContext):
    """Обработка ввода стоплосса"""
    try:
        user_id = message.from_user.id

        # Проверяем, что введено число
        try:
            stoploss_input = message.text.strip().replace(',', '.')
            stoploss = float(stoploss_input)

            # Определяем, процент это или абсолютное значение
            if '%' in message.text:
                stoploss_type = "процент"
                stoploss_display = f"{stoploss}%"
            else:
                stoploss_type = "абсолютное"
                stoploss_display = str(stoploss)

        except ValueError:
            # Получаем сохраненную пару
            data = await state.get_data()
            pair = data.get('pair', 'неизвестная пара')

            if user_id in start_message_ids:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=start_message_ids[user_id],
                    text=f"❌ Пожалуйста, введите корректное число для стоп-лосса\n\nПримеры:\n• 2.5 (2.5%)\n• 450 (абсолютное значение)",
                    reply_markup=keyboards.stoploss_keyboard(),
                    parse_mode="Markdown"
                )
            await message.delete()
            return

        # Сохраняем стоплосс
        await state.update_data(stoploss=stoploss_display)

        # Получаем сохраненную пару
        data = await state.get_data()
        pair = data.get('pair', 'неизвестная пара')

        # Обновляем сообщение с подтверждением
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"📊 *{pair}*\n\n📉 Стоп-лосс: {stoploss_display}\n\nПодтвердите запуск сделки:",
                reply_markup=keyboards.confirmation_keyboard(),
                parse_mode="Markdown"
            )

        # Удаляем сообщение пользователя
        await message.delete()

        # Переходим в состояние ожидания подтверждения (хотя подтверждение будет через callback)
        await state.set_state(TradeStates.waiting_for_confirmation)

    except Exception as e:
        print(f"Error in stoploss input: {e}")
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text="❌ Произошла ошибка при обработке данных",
                reply_markup=keyboards.main_menu_keyboard(),
                parse_mode='Markdown'
            )
        await state.clear()
        await message.delete()

# Обработка любого другого текстового сообщения (не в состоянии)
@callback_router.message()
async def handle_other_messages(message: Message):
    """Обработка любых других сообщений"""
    try:
        user_id = message.from_user.id

        # Просто возвращаем в главное меню
        welcome_text = '*Welcome to Trade & Stage*'

        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text=welcome_text,
                reply_markup=keyboards.exchange_keyboard(),
                parse_mode='Markdown'
            )
        else:
            new_message = await message.answer(
                welcome_text,
                reply_markup=keyboards.exchange_keyboard(),
                parse_mode='Markdown'
            )
            start_message_ids[user_id] = new_message.message_id

        # Удаляем сообщение пользователя
        await message.delete()

    except Exception as e:
        print(f"Error in other messages: {e}")

# Добавьте этот обработчик в callback_routers.py

# Обработка игнорируемых кнопок (пустых заглушек)
@callback_router.callback_query(F.data == "ignore")
async def handle_ignore(callback: CallbackQuery):
    """Заглушка для неактивных кнопок"""
    await callback.answer()  # Просто игнорируем нажатие

# Обработка переключения страниц
@callback_router.callback_query(F.data.startswith("page_"))
async def handle_page_switch(callback: CallbackQuery):
    """Обработка переключения страниц с тикерами"""
    try:
        user_id = callback.from_user.id

        # Парсим данные: page_exchange_pageNumber
        parts = callback.data.split("_")
        if len(parts) >= 3:
            exchange = parts[1]
            page = int(parts[2])

            # Обновляем страницу в keyboards (нужно импортировать user_pages)
            from frontend.helper_pro import keyboards

            # Обновляем сообщение с новой страницей
            if user_id in start_message_ids:
                exchange_names = {
                    "SPBFUT": "Фьючерсы",
                    "TQBR": "Акции"
                }
                exchange_display = exchange_names.get(exchange, exchange)

                await bot.edit_message_text(
                    chat_id=callback.message.chat.id,
                    message_id=start_message_ids[user_id],
                    text=f"*{exchange_display}*\n\nВыберите торговый инструмент:",
                    reply_markup=keyboards.tickers_keyboard(exchange, user_id, page),
                    parse_mode='Markdown'
                )

        await callback.answer()

    except Exception as e:
        print(f"Error in page switch: {e}")
        await callback.answer("Ошибка навигации")

# Добавьте обработчик для заглушки индикатора страницы
@callback_router.callback_query(F.data == "current_page")
async def handle_current_page(callback: CallbackQuery):
    """Заглушка для индикатора страницы"""
    await callback.answer(f"Страница", show_alert=False)