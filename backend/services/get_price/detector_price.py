""" python backend/services/get_price_service/detector_price.py """
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

# Импорт логера
from components.logger import logger

# Импорты файлов
from components.ticker import TICKERS_DATA, get_data
from settings.backend_config import JSON_PRICE_PATH

# Импорты библиотек
import json
import time
from datetime import datetime
from pathlib import Path

class PRICE_UPDATER:
    """Класс для обновления JSON файла с данными"""

    def __init__(self, json_file_path=None, update_interval=0.5):
        if json_file_path is None:
            base_dir = Path(__file__).parent
            self.json_file_path = base_dir / "market_data.json"
        else:
            self.json_file_path = Path(json_file_path)

        self.update_interval = update_interval
        self.running = False
        self.market_data = TICKERS_DATA()
        self.last_successful_data = None

        self.json_file_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(f"PRICE_UPDATER инициализирован, файл: {self.json_file_path}")

    def update_json_file(self, data):
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.error_count += 1
            logger.error(f"Ошибка сохранения цены в JSON: {e}")
            return False

    def update_loop(self):
        logger.info("Запущен мониторинг цен")

        while self.running:
            try:
                current_data = get_data()
                if current_data:
                    self.last_successful_data = current_data
                    self.update_json_file(current_data)
                else:
                    logger.error(f"Данные цен не получены {current_data}")
                    if self.last_successful_data:
                        self.update_json_file(self.last_successful_data)

                time.sleep(self.update_interval)

            except Exception as e:
                logger.error(f"Ошибка в цикле: {e}")
                time.sleep(self.update_interval)

    def start(self):
        if self.running:
            return

        self.running = True

        try:
            self.update_loop()
        except Exception as e:
            logger.error(f"Ошибка при запуске мониторинга цен: {e}")
            self.stop()

    def stop(self):
        logger.info("Остановка PRICE_UPDATER")
        self.running = False

        if self.last_successful_data:
            try:
                self.update_json_file(self.last_successful_data)
            except Exception as e:
                logger.error(f"Ошибка сохранения данных при остановке: {e}")