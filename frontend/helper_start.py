import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
from datetime import datetime, time
from aiogram import Bot, Dispatcher
# Импорты из наших модулей
from frontend.helper_pro.config_bot import bot
from frontend.helper_pro.handlers.start_router import start_router
from frontend.helper_pro.handlers.callback_routers import callback_router

async def on_startup():
    """Действия при запуске бота"""
    print("✓ Helper Pro запущен...")

async def on_shutdown():
    await bot.session.close()

async def telegram_main():
    """Основная функция запуска бота"""
    dp = Dispatcher()

    # Регистрируем роутеры
    dp.include_router(start_router)
    dp.include_router(callback_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        print(f"Ошибка в боте: {e}")
    finally:
        await on_shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(telegram_main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")