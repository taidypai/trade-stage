import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import logging
from aiogram.filters import Command, CommandStart
from aiogram import types, Router
import asyncio

from frontend.helper_pro import keyboards
from frontend.helper_pro import config_bot

logger = logging.getLogger(__name__)
start_router = Router()
bot = config_bot.bot

# Глобальный словарь для хранения ID стартовых сообщений по пользователям
start_message_ids = {}

@start_router.message(CommandStart())
async def handle_start(message: types.Message):
    """Обработка команды /start"""
    try:
        user_id = message.from_user.id

        welcome_text = '*Добро пожаловать в экосистему!*'

        # Проверяем, есть ли уже стартовое сообщение для этого пользователя
        if user_id in start_message_ids:
            try:
                # Редактируем существующее сообщение
                await bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=start_message_ids[user_id],
                    text=welcome_text,
                    reply_markup=keyboards.main_keyboard(),
                    parse_mode='Markdown'
                )
                return
            except Exception:
                # Если редактирование не удалось (сообщение удалено), создаем новое
                pass

        # Отправляем новое стартовое сообщение
        start_message = await message.answer(
            welcome_text,
            reply_markup=keyboards.main_keyboard(),
            parse_mode='Markdown'
        )

        # Сохраняем ID сообщения для этого пользователя
        start_message_ids[user_id] = start_message.message_id

    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.answer("Произошла ошибка при запуске бота")

@start_router.callback_query(lambda c: c.data == "main_menu")
async def handle_main_menu(callback: types.CallbackQuery):
    """Обработка кнопки главного меню"""
    try:
        user_id = callback.from_user.id

        welcome_text = '*Добро пожаловать в экосистему!*'

        # Обновляем стартовое сообщение
        if user_id in start_message_ids:
            await bot.edit_message_text(
                chat_id=callback.message.chat.id,
                message_id=start_message_ids[user_id],
                text=welcome_text,
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )
        else:
            # Создаем новое сообщение
            new_message = await callback.message.answer(
                welcome_text,
                reply_markup=keyboards.main_keyboard(),
                parse_mode='Markdown'
            )
            start_message_ids[user_id] = new_message.message_id

        await callback.answer()

    except Exception as e:
        logger.error(f"Error in main menu handler: {e}")
        await callback.answer("Произошла ошибка")