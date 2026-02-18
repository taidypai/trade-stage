# backend/services/run_service/run_all.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
import multiprocessing
import time
from typing import Optional, List

from backend.components.logger import logger
from backend.services.run_service import run_all_services, stop_all_services

class ServicesRunner:
    """Класс для управления запуском всех сервисов"""

    def __init__(self):
        self.processes: List = []
        self._running = False

    def start_services_sync(self):
        """
        Синхронный запуск всех сервисов
        Запускается в отдельном процессе
        """
        logger.info("=" * 50)
        logger.info("ЗАПУСК ВСЕХ СЕРВИСОВ (СИНХРОННЫЙ РЕЖИМ)")
        logger.info("=" * 50)

        try:
            # Запускаем все сервисы (это ваша существующая функция)
            self.processes = run_all_services()

            logger.info(f"✅ Запущено {len(self.processes)} сервисов")

            # Бесконечное ожидание
            while True:
                # Проверяем состояние процессов
                for i, p in enumerate(self.processes):
                    if not p.is_alive():
                        logger.error(f"❌ Процесс {p.name} умер, код: {p.exitcode}")
                time.sleep(5)

        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки...")
            stop_all_services(self.processes)
        except Exception as e:
            logger.error(f"❌ Ошибка в сервисах: {e}")
            stop_all_services(self.processes)
        finally:
            logger.info("✅ Все сервисы завершены")

    def run_in_process(self) -> multiprocessing.Process:
        """
        Запускает сервисы в отдельном процессе
        Возвращает объект процесса
        """
        # ВАЖНО: daemon=True убираем, так как дочерние процессы не могут быть daemon
        process = multiprocessing.Process(
            target=self.start_services_sync,
            name="ServicesProcess",
            daemon=False  # Изменено с True на False
        )
        process.start()
        self._running = True
        logger.info(f"✅ Сервисы запущены в процессе PID: {process.pid}")
        return process

    def stop(self):
        """Остановка всех сервисов"""
        if self.processes:
            logger.info("🛑 Останавливаю сервисы...")
            stop_all_services(self.processes)
            self._running = False


# Функция для запуска всех сервисов (будет вызвана из quik_main)
def run_all_services_in_process():
    """
    Запускает все сервисы в отдельном процессе
    Эту функцию вызывает quik_main после успешного входа
    """
    runner = ServicesRunner()  # Создаем новый экземпляр для каждого запуска
    return runner.run_in_process()


# Асинхронная версия для обратной совместимости
async def run_all_async():
    """Асинхронная обертка для запуска сервисов"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_all_services_in_process)


if __name__ == "__main__":
    # Для тестирования
    logger.info("🧪 Тестовый запуск сервисов...")
    process = run_all_services_in_process()
    try:
        # Держим процесс живым
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Программа остановлена пользователем")
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)