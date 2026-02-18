""" python backend/services/run_service/run_all.py """
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорты файлов
from backend.components.logger import logger
from backend.services.run import run_all_services, stop_all_services

# Импорты библиотек
import asyncio
import multiprocessing
import time
import gc
from typing import Optional, List


class Runner:
    """Класс для управления запуском всех сервисов"""

    def __init__(self):
        self.processes: List = []
        self.running = False

    def start_services_sync(self):
        logger.info("=" * 50)
        logger.info("ЗАПУСК СЕРВИСОВ (СИНХРОННЫЙ РЕЖИМ)")
        logger.info("=" * 50)

        try:
            # Запускаем все сервисы
            self.processes = run_all_services()

            logger.info(f"✅ Запущено {len(self.processes)} сервисов")

            # Бесконечное ожидание с проверкой процессов
            while True:
                # Проверяем состояние процессов
                for i, p in enumerate(self.processes):
                    if p and not p.is_alive():
                        logger.error(f"Процесс {p.name} умер, код: {p.exitcode}")
                        # Здесь можно добавить логику перезапуска при необходимости

                # Небольшая задержка для уменьшения нагрузки CPU
                time.sleep(3)

        except KeyboardInterrupt:
            logger.info("Получен сигнал остановки...")
            self._cleanup()
        except Exception as e:
            logger.error(f"Ошибка в сервисах: {e}")
            self._cleanup()
        finally:
            logger.info("✅ Все сервисы завершены")
    """Очистка ресурсов при завершении"""
    def _cleanup(self):
        if self.processes:
            logger.info("Запуск очистки ресурсов...")
            stop_all_services(self.processes)

            # Принудительный сбор мусора для освобождения ресурсов QuikPy
            gc.collect()
            logger.info("🧹 Очистка завершена")

    """Запуск сервисов в отдельном процессе"""
    def run_in_process(self):
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

    """Остановка всех сервисов"""
    def stop(self):
        if self.processes:
            logger.info("Останавливаю сервисы...")
            self._cleanup()
            self._running = False

"""Запускает все сервисы в quik_main"""
def run_all_services_in_process():
    runner = Runner()  # Создаем новый экземпляр для каждого запуска
    return runner.run_in_process()


# Асинхронная версия для обратной совместимости
async def run_all_async():
    """Асинхронная обертка для запуска сервисов"""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, run_all_services_in_process)