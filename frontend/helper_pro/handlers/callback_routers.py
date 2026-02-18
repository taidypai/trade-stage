import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт папок
from settings import backend_config as config
from frontend.helper_pro import keyboards

# Импорт торгового движка
from backend.services.trade_engine import trade_manager

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
    waiting_for_direction = State()  # Новое состояние для выбора направления

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

        # Устанавливаем состояние ожидания направления
        await state.set_state(TradeStates.waiting_for_direction)

        # Обновляем сообщение для выбора направления
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"📊 *{pair}*\n\nВыберите направление сделки:",
                reply_markup=keyboards.direction_keyboard(),  # Создадим новую клавиатуру
                parse_mode="Markdown"
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in pair selection: {e}")
        await callback.answer("Произошла ошибка")

# Обработка выбора направления (long/short)
@callback_router.callback_query(F.data.in_(["direction_long", "direction_short"]))
async def handle_direction_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора направления сделки"""
    try:
        user_id = callback.from_user.id
        direction = callback.data.replace("direction_", "")

        # Сохраняем направление
        await state.update_data(direction=direction)

        # Получаем сохраненную пару
        data = await state.get_data()
        pair = data.get('pair', 'неизвестная пара')

        # Устанавливаем состояние ожидания стоплосса
        await state.set_state(TradeStates.waiting_for_stoploss)

        # Обновляем сообщение
        direction_emoji = "📈" if direction == "long" else "📉"
        direction_text = "LONG (покупка)" if direction == "long" else "SHORT (продажа)"

        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"📊 *{pair}*\n{direction_emoji} *{direction_text}*\n\nВведите стоп-лосс (в процентах или абсолютное значение):\n\nПримеры:\n• 2.5 (2.5%)\n• 450 (абсолютное значение)",
                reply_markup=keyboards.stoploss_keyboard(),
                parse_mode="Markdown"
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in direction selection: {e}")
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
        logger.error(f"Error in back to exchanges: {e}")
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
        logger.error(f"Error in cancel deal: {e}")
        await callback.answer("Произошла ошибка")

# Обработка подтверждения сделки
@callback_router.callback_query(F.data == "confirm_deal")
async def handle_confirm_deal(callback: CallbackQuery, state: FSMContext):
    """Подтверждение сделки и запуск трейлинг-стопа"""
    try:
        user_id = callback.from_user.id

        # Получаем данные из состояния
        data = await state.get_data()
        pair = data.get('pair')
        direction = data.get('direction')
        stoploss_str = data.get('stoploss')

        # Парсим стоп-лосс (убираем % если есть)
        stoploss_value = float(stoploss_str.replace('%', ''))

        # Отправляем сообщение о запуске
        await bot.edit_message_text(
            chat_id=callback.message.chat.id,
            message_id=start_message_ids[user_id],
            text=f"🔄 *Запуск сделки...*\n\nПара: {pair}\nНаправление: {direction.upper()}\nСтоп-лосс: {stoploss_str}\n\nОжидайте подтверждения...",
            parse_mode='Markdown'
        )

        # ============================================================================
        # ЗАПУСК ТОРГОВОГО ДВИЖКА С ПЕРЕДАННЫМИ ПАРАМЕТРАМИ
        # ============================================================================
        logger.info(f"🚀 Запуск торгового движка: {pair}, {direction}, стоп {stoploss_str}")

        # Запускаем движок если ещё не запущен и открываем позицию
        success = await trade_manager.open_position(pair, direction, stoploss_value)

        # ============================================================================

        # Очищаем состояние
        await state.clear()

        if success:
            # Получаем текущие позиции для отображения
            positions = await trade_manager.get_positions()
            current_position = next((p for p in positions if p['ticker'] == pair), None)

            # Формируем сообщение об успешном запуске
            result_text = f"✅ *Сделка успешно запущена!*\n\n"
            result_text += f"📊 *{pair}*\n"
            result_text += f"📈 Направление: {direction.upper()}\n"
            result_text += f"📉 Стоп-лосс: {stoploss_str}\n"

            if current_position:
                result_text += f"💰 Цена входа: {current_position['entry_price']:.2f}\n"
                result_text += f"🛑 Текущий стоп: {current_position['current_stop']:.2f}\n"
                result_text += f"📦 Количество: {current_position['current_quantity']}\n"

            result_text += f"\nТрейлинг-стоп активен и будет автоматически подтягиваться."

            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=result_text,
                reply_markup=keyboards.position_menu_keyboard(),  # Создадим клавиатуру для управления позицией
                parse_mode='Markdown'
            )
        else:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"❌ *Ошибка при запуске сделки*\n\nПроверьте баланс и наличие инструмента в QUIK.",
                reply_markup=keyboards.main_menu_keyboard(),
                parse_mode='Markdown'
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in confirm deal: {e}")
        await callback.answer("Произошла ошибка")
        await state.clear()

# Обработка просмотра позиций
@callback_router.callback_query(F.data == "view_positions")
async def handle_view_positions(callback: CallbackQuery):
    """Просмотр открытых позиций"""
    try:
        user_id = callback.from_user.id

        positions = await trade_manager.get_positions()

        if not positions:
            text = "📭 *Нет открытых позиций*"
            reply_markup = keyboards.main_menu_keyboard()
        else:
            text = "📊 *Открытые позиции*\n\n"
            for p in positions:
                emoji = "📈" if p['direction'] == 'long' else "📉"
                text += f"{emoji} *{p['ticker']}* {p['direction'].upper()}\n"
                text += f"  Вход: {p['entry_price']:.2f}\n"
                text += f"  Тек. стоп: {p['current_stop']:.2f}\n"
                text += f"  Кол-во: {p['current_quantity']}\n"
                if p.get('highest_price'):
                    text += f"  Max: {p['highest_price']:.2f}\n"
                text += "\n"
            reply_markup = keyboards.positions_list_keyboard(positions)

        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in view positions: {e}")
        await callback.answer("Произошла ошибка")

# Обработка закрытия конкретной позиции
@callback_router.callback_query(F.data.startswith("close_pos_"))
async def handle_close_position(callback: CallbackQuery):
    """Закрытие конкретной позиции"""
    try:
        user_id = callback.from_user.id
        position_id = callback.data.replace("close_pos_", "")

        await trade_manager.close_position(position_id)

        await callback.answer("Позиция закрыта")

        # Обновляем список позиций
        await handle_view_positions(callback)

    except Exception as e:
        logger.error(f"Error in close position: {e}")
        await callback.answer("Ошибка при закрытии")

# Обработка остановки движка
@callback_router.callback_query(F.data == "stop_engine")
async def handle_stop_engine(callback: CallbackQuery):
    """Остановка торгового движка"""
    try:
        user_id = callback.from_user.id

        await trade_manager.stop_engine()

        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text="🛑 *Торговый движок остановлен*\n\nВсе позиции закрыты.",
                reply_markup=keyboards.main_menu_keyboard(),
                parse_mode='Markdown'
            )

        await callback.answer("Движок остановлен")

    except Exception as e:
        logger.error(f"Error in stop engine: {e}")
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
            # Получаем сохраненные данные
            data = await state.get_data()
            pair = data.get('pair', 'неизвестная пара')
            direction = data.get('direction', 'long')
            direction_emoji = "📈" if direction == "long" else "📉"

            if user_id in start_message_ids:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=start_message_ids[user_id],
                    text=f"{direction_emoji} *{pair}*\n\n❌ Пожалуйста, введите корректное число для стоп-лосса\n\nПримеры:\n• 2.5 (2.5%)\n• 450 (абсолютное значение)",
                    reply_markup=keyboards.stoploss_keyboard(),
                    parse_mode="Markdown"
                )
            await message.delete()
            return

        # Сохраняем стоплосс
        await state.update_data(stoploss=stoploss_display)

        # Получаем сохраненные данные
        data = await state.get_data()
        pair = data.get('pair', 'неизвестная пара')
        direction = data.get('direction', 'long')
        direction_emoji = "📈" if direction == "long" else "📉"
        direction_text = "LONG (покупка)" if direction == "long" else "SHORT (продажа)"

        # Обновляем сообщение с подтверждением
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"📊 *{pair}*\n{direction_emoji} *{direction_text}*\n\n📉 Стоп-лосс: {stoploss_display}\n\nПодтвердите запуск сделки:",
                reply_markup=keyboards.confirmation_keyboard(),
                parse_mode="Markdown"
            )

        # Удаляем сообщение пользователя
        await message.delete()

        # Переходим в состояние ожидания подтверждения
        await state.set_state(TradeStates.waiting_for_confirmation)

    except Exception as e:
        logger.error(f"Error in stoploss input: {e}")
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
        logger.error(f"Error in other messages: {e}")

# Обработка игнорируемых кнопок (пустых заглушек)
@callback_router.callback_query(F.data == "ignore")
async def handle_ignore(callback: CallbackQuery):
    """Заглушка для неактивных кнопок"""
    await callback.answer()

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

            # Обновляем страницу в keyboards
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
        logger.error(f"Error in page switch: {e}")
        await callback.answer("Ошибка навигации")

# Обработчик для индикатора страницы
@callback_router.callback_query(F.data == "current_page")
async def handle_current_page(callback: CallbackQuery):
    """Заглушка для индикатора страницы"""
    await callback.answer(f"Страница", show_alert=False)