import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

# Импорт логера
from components.logger import logger

# Импорты файлов
from services.get_price_service.detector_price import MarketDataUpdater, MarketDataReader
from settings.backend_config import JSON_PRICE_PATH

# Импорт библиотек
import signal
import argparse
import time
from pathlib import Path


def run_service(interval=0.5):
    """Запуск обновления JSON файла с ценами"""
    json_path = JSON_PRICE_PATH
    updater = MarketDataUpdater(json_path, interval)

    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        updater.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info(f"Запуск обновления цен в файл: {json_path}")
    updater.start()

__all__ = ['run_service']

if __name__ == "__main__":
    run_updater(interval=0.5)