# helper_start.py (альтернативная версия с фоновым запуском QUIK)
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт папок
from settings import backend_config as config
from frontend.helper_pro.handlers.start_router import start_router
from frontend.helper_pro.handlers.callback_routers import callback_router

# Импортируем quik_main для запуска QUIK
from backend.components.start_quik import quik_main

# Импортируем торговый менеджер
from backend.services.trade_engine import trade_manager

# Импорт модулей
import asyncio
from datetime import datetime, time
from aiogram import Bot, Dispatcher

# Глобальный экземпляр бота
bot = config.bot

# Множество для хранения фоновых задач
background_tasks = set()

async def on_startup():
    """Действия при запуске бота"""
    print("✓ Helper Pro запущен...")
    print("✓ Бот готов к работе")

    # Запускаем QUIK в фоне после старта бота
    print("🟡 Запускаю QUIK в фоновом режиме...")
    quik_task = asyncio.create_task(quik_main())
    background_tasks.add(quik_task)
    quik_task.add_done_callback(background_tasks.discard)

    # Добавляем callback для отслеживания результата
    def on_quik_done(task):
        try:
            result = task.result()
            if result:
                print("✅ QUIK успешно запущен в фоне")
            else:
                print("❌ Ошибка при запуске QUIK в фоне")
        except Exception as e:
            print(f"❌ Ошибка в фоновой задаче QUIK: {e}")

    quik_task.add_done_callback(on_quik_done)

    # Торговый движок будет запускаться при первой сделке через trade_manager

async def on_shutdown():
    """Действия при остановке бота"""
    print("Останавливаю бота...")

    # Останавливаем торговый движок если он запущен
    if trade_manager.is_running:
        print("🟡 Останавливаю торговый движок...")
        await trade_manager.stop_engine()
        print("✅ Торговый движок остановлен")

    # Отменяем все фоновые задачи
    for task in background_tasks:
        task.cancel()

    await bot.session.close()
    print("✓ Бот остановлен")

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
        logger.error(f"Ошибка в telegram боте: {e}")
    finally:
        await on_shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(telegram_main())
    except KeyboardInterrupt:
        print("\n\n🟡 Бот остановлен пользователем")
    except Exception as e:
        print(f"\n🔴 Необработанная ошибка: {e}")
        import traceback
        traceback.print_exc()