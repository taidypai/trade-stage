# & C:/Python314/python.exe c:/Users/Вадим/Documents/trade-stage/backend/components/quik_components/quik_data_service.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

# Импорт логера
from components.logger import logger

# Импорты файлов
from components.quik_components.quik_ticker import MarketData, get_market_data
from settings.backend_config import JSON_PRICE_PATH

# Импорты библиотек
import json
import time
from datetime import datetime
from pathlib import Path

class MarketDataUpdater:
    """Класс для обновления JSON файла с данными"""

    def __init__(self, json_file_path=None, update_interval=0.5):
        if json_file_path is None:
            base_dir = Path(__file__).parent
            self.json_file_path = base_dir / "market_data.json"
        else:
            self.json_file_path = Path(json_file_path)

        self.update_interval = update_interval
        self.running = False
        self.market_data = MarketData()
        self.last_successful_data = None

        self.json_file_path.parent.mkdir(parents=True, exist_ok=True)

    def update_json_file(self, data):
        try:
            with open(self.json_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            logger.error(f"Ошибка сохранения JSON: {e}")
            return False

    def update_loop(self):
        logger.info("Запущен мониторинг цен")
        while self.running:
            try:
                current_data = get_market_data()
                if current_data and 'error' not in current_data:
                    self.last_successful_data = current_data
                    self.update_json_file(current_data)
                else:
                    error_msg = current_data.get('error', 'Неизвестная ошибка')
                    logger.error(f"Ошибка получения данных: {error_msg}")
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
        logger.info("Остановка MarketDataUpdater")
        self.running = False
        if self.last_successful_data:
            try:
                self.update_json_file(self.last_successful_data)
            except Exception as e:
                logger.error(f"Ошибка в сохранения данных с биржи: {e}")


class MarketDataReader:
    """Класс для чтения данных из JSON файла"""

    def __init__(self, json_file_path=None):
        if json_file_path is None:
            base_dir = Path(__file__).parent
            self.json_file_path = base_dir / "market_data.json"
        else:
            self.json_file_path = Path(json_file_path)

    def read_data(self):
        try:
            if not self.json_file_path.exists():
                logger.error(f"Файл с данными цен не найден: {self.json_file_path}")
                return None
            with open(self.json_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Ошибка чтения файла с данными цен: {e}")
            return None

    def get_all_prices(self):
        data = self.read_data()
        return data if data else None

    def get_ticker(self, ticker_symbol):
        data = self.read_data()
        if not data:
            return None
        ticker_symbol = ticker_symbol.upper()
        for class_code, tickers in data.items():
            if ticker_symbol in tickers:
                return {
                    'ticker': ticker_symbol,
                    'class_code': class_code,
                    'data': tickers[ticker_symbol]
                }
        return None