""" pythonbackend/services/get_price_service/__init__.py"""
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

# Импорт логера
from components.logger import logger

# Импорты файлов
from services.get_price.detector_price import PRICE_UPDATER
from settings.backend_config import JSON_PRICE_PATH

# Импорт библиотек
import signal
import argparse
import time
from pathlib import Path


def run_service(interval=0.5):
    """Запуск обновления JSON файла с ценами"""
    json_path = JSON_PRICE_PATH
    updater = PRICE_UPDATER(json_path, interval)

    def signal_handler(signum, frame):
        logger.info(f"📡 Получен сигнал {signum}, завершение работы...")
        updater.stop()
        sys.exit(0)

    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


    try:
        updater.start()
    except Exception as e:
        logger.error(f"Критическая ошибка : {e}")
        updater.stop()
        raise

__all__ = ['run_service']

if __name__ == "__main__":
    # Исправлено: run_updater -> run_service
    run_service(interval=0.5)