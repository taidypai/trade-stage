import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re

from frontend.helper_pro import config_bot
#from trading_engine import trade_main
from backend import config_main as config

from frontend.helper_pro import keyboards

callback_router = Router()
bot = config_bot.bot

# Импортируем словарь из start_router
from frontend.helper_pro.handlers.start_router import start_message_ids

# Определяем состояния FSM
class TradeStates(StatesGroup):
    waiting_for_stoploss = State()
    waiting_for_link = State()

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
                text=f"Введите стоплосс:",
                reply_markup=keyboards.stoploss_keyboard(),
                parse_mode="Markdown"
            )
        else:
            # Если ID не найден, отправляем новое сообщение
            new_message = await callback.message.answer(
                f"Введите стоплосс:",
                reply_markup=keyboards.stoploss_keyboard(),
                parse_mode="Markdown"
            )
            start_message_ids[user_id] = new_message.message_id

        await callback.answer()

    except Exception as e:
        print(f"Error in pair selection: {e}")
        await callback.answer("Произошла ошибка")

# Обработка кнопки отмены сделки
@callback_router.callback_query(F.data == "cancel_deal", TradeStates.waiting_for_link)
async def handle_cancel_deal(callback: CallbackQuery, state: FSMContext):
    """Отмена сделки"""
    try:
        user_id = callback.from_user.id

        # Очищаем состояние
        await state.clear()

        # Возвращаемся в главное меню
        welcome_text = '*Добро пожаловать в экосистему!*'

        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=welcome_text,
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )

        await callback.answer("Сделка отменена")

    except Exception as e:
        print(f"Error in cancel deal: {e}")
        await callback.answer("Произошла ошибка")

# Обработка ввода стоплосса
@callback_router.message(TradeStates.waiting_for_stoploss)
async def handle_stoploss_input(message: Message, state: FSMContext):
    """Обработка ввода стоплосса"""
    try:
        user_id = message.from_user.id

        # Проверяем, что введено число
        try:
            stoploss = float(message.text.strip().replace(',', '.'))
        except ValueError:
            # Получаем сохраненную пару
            data = await state.get_data()
            pair = data.get('pair', 'неизвестная пара')

            if user_id in start_message_ids:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=start_message_ids[user_id],
                    text=f"Пожалуйста, введите корректное число для стоплосса\nНапример: 450.5 или 1.2",
                    reply_markup=keyboards.stoploss_keyboard(),
                    parse_mode="Markdown"
                )
            return

        # Сохраняем стоплосс
        await state.update_data(stoploss=stoploss)

        # Меняем состояние на ожидание ссылки
        await state.set_state(TradeStates.waiting_for_link)

        # Получаем сохраненную пару
        data = await state.get_data()
        pair = data.get('pair', 'неизвестная пара')

        # Обновляем сообщение
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"Вставьте ссылку на сделку:",
                reply_markup=keyboards.link_keyboard(),
                parse_mode="Markdown"
            )

        # Удаляем сообщение пользователя
        await message.delete()

    except Exception as e:
        print(f"Error in stoploss input: {e}")
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text=f"Произошла ошибка при обработке данных",
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )
        await state.clear()

# Обработка ввода ссылки
@callback_router.message(TradeStates.waiting_for_link)
async def handle_link_input(message: Message, state: FSMContext):
    """Обработка ввода ссылки на сделку"""
    try:
        user_id = message.from_user.id

        # Получаем данные из состояния
        data = await state.get_data()
        pair = data.get('pair')
        stoploss = data.get('stoploss')
        link = message.text.strip()

        # Проверяем, что это похоже на ссылку (простая проверка)
        if not re.match(r'^(http|https)://', link, re.IGNORECASE):
            if user_id in start_message_ids:
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=start_message_ids[user_id],
                    text=f"Пожалуйста, введите корректную ссылку\nНачинается с http:// или https://",
                    reply_markup=keyboards.link_keyboard(),
                    parse_mode="Markdown"
                )
            return

        # ЗАПУСКАЕМ ТОРГОВЫЙ ДВИЖОК С ПЕРЕДАННЫМИ ПАРАМЕТРАМИ
        # Здесь вы можете использовать сохраненные переменные:
        # pair - торговая пара
        # stoploss - стоплосс
        # link - ссылка на сделку

        print(f"Запуск торгового движка:")
        print(f"  Пара: {pair}")
        print(f"  Стоплосс: {stoploss}")
        print(f"  Ссылка: {link}")

        # Вызываем ваш торговый движок (раскомментируйте когда будете готовы)
        trade_main.start_trade_main(pair, stoploss, link)

        # Очищаем состояние
        await state.clear()

        # Обновляем сообщение с подтверждением
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text="*Добро пожаловать в экосистему!*",
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )

        # Удаляем сообщение пользователя
        await message.delete()

    except Exception as e:
        print(f"Error in link input: {e}")
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text="Произошла ошибка при обработке данных",
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )
        await state.clear()

# Обработка любого другого текстового сообщения (не в состоянии)
@callback_router.message()
async def handle_other_messages(message: Message):
    """Обработка любых других сообщений"""
    try:
        user_id = message.from_user.id

        # Просто возвращаем в главное меню
        welcome_text = '*Добро пожаловать в экосистему!*'

        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=start_message_ids[user_id],
                text=welcome_text,
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )
        else:
            new_message = await message.answer(
                welcome_text,
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )
            start_message_ids[user_id] = new_message.message_id

        # Удаляем сообщение пользователя
        await message.delete()

    except Exception as e:
        print(f"Error in other messages: {e}")