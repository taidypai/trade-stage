import logging
from datetime import datetime, timedelta
import time
import sys
import json
import os
from typing import Dict, List, Optional, Any
import threading

sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")
from QuikPy import QuikPy


class PriceStreamer:
    def __init__(self, output_dir: str = "candles_data"):
        """
        Инициализация стримера цен и свечей

        Args:
            output_dir: Директория для сохранения JSON файлов
        """
        self.logger = logging.getLogger('PriceStreamer')
        self.qp_provider = QuikPy.QuikPy()
        self.output_dir = output_dir

        # Создаем директорию для сохранения данных, если её нет
        os.makedirs(output_dir, exist_ok=True)

        # Словари для хранения данных
        self.current_prices: Dict[str, Dict] = {}
        self.candles: Dict[str, Dict[str, List[Dict]]] = {}  # ticker -> timeframe -> список свечей
        self.subscriptions: List[tuple] = []
        self.running = False

        # Конфигурация таймфреймов (в секундах)
        self.timeframes = {
            "1min": 60,
            "5min": 300,
            "15min": 900,
            "30min": 1800,
            "1hour": 3600,
            "4hour": 14400,
            "1day": 86400
        }

        # Время начала текущих свечей
        self.candle_start_times: Dict[str, Dict[str, datetime]] = {}

        # Поток для обработки обновлений
        self.update_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()

        self._setup_logging()

    def _setup_logging(self):
        """Настройка логирования"""
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%d.%m.%Y %H:%M:%S',
            level=logging.INFO,
            handlers=[
                logging.FileHandler('PriceStreamer.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        logging.Formatter.converter = lambda *args: datetime.now(tz=self.qp_provider.tz_msk).timetuple()

    def _on_quote(self, data: Dict):
        """Обработчик обновлений стакана"""
        try:
            if 'data' in data and 'class_code' in data['data'] and 'sec_code' in data['data']:
                class_code = data['data']['class_code']
                ticker_code = data['data']['sec_code']
                ticker_key = f"{class_code}.{ticker_code}"

                # Извлекаем лучшие цены bid и ask
                if 'bids' in data['data'] and data['data']['bids']:
                    best_bid = float(data['data']['bids'][0][0])  # цена лучшей заявки на покупку
                else:
                    best_bid = None

                if 'offers' in data['data'] and data['data']['offers']:
                    best_ask = float(data['data']['offers'][0][0])  # цена лучшей заявки на продажу
                else:
                    best_ask = None

                # Рассчитываем среднюю цену
                current_price = None
                if best_bid is not None and best_ask is not None:
                    current_price = (best_bid + best_ask) / 2
                elif best_bid is not None:
                    current_price = best_bid
                elif best_ask is not None:
                    current_price = best_ask

                if current_price is not None:
                    with self.lock:
                        self.current_prices[ticker_key] = {
                            'price': current_price,
                            'bid': best_bid,
                            'ask': best_ask,
                            'timestamp': datetime.now(self.qp_provider.tz_msk).isoformat(),
                            'volume': self._get_volume(data['data'])
                        }

                    # Обновляем свечи
                    self._update_candles(ticker_key, current_price)

                    self.logger.debug(f'Обновление цены {ticker_key}: {current_price}')

        except Exception as e:
            self.logger.error(f'Ошибка в обработчике стакана: {e}')

    def _on_all_trade(self, data: Dict):
        """Обработчик обезличенных сделок (можно использовать для объема)"""
        try:
            if 'data' in data and 'class_code' in data['data'] and 'sec_code' in data['data']:
                class_code = data['data']['class_code']
                ticker_code = data['data']['sec_code']
                ticker_key = f"{class_code}.{ticker_code}"

                # Можно использовать информацию о сделках для уточнения объема
                # В данном примере просто логируем
                self.logger.debug(f'Сделка по {ticker_key}: {data["data"]}')

        except Exception as e:
            self.logger.error(f'Ошибка в обработчике сделок: {e}')

    def _get_volume(self, quote_data: Dict) -> float:
        """Извлечение объема из данных стакана"""
        try:
            # Пытаемся получить объем из разных источников
            if 'volume' in quote_data:
                return float(quote_data['volume'])
            elif 'bids' in quote_data and quote_data['bids']:
                # Суммируем объемы из стакана
                total_volume = sum(float(bid[1]) for bid in quote_data['bids'])
                return total_volume
            return 0.0
        except:
            return 0.0

    def _initialize_candles_for_ticker(self, ticker_key: str):
        """Инициализация структур данных для хранения свечей тикера"""
        if ticker_key not in self.candles:
            self.candles[ticker_key] = {}
            self.candle_start_times[ticker_key] = {}

            for timeframe_name in self.timeframes.keys():
                self.candles[ticker_key][timeframe_name] = []
                self.candle_start_times[ticker_key][timeframe_name] = None

    def _update_candles(self, ticker_key: str, price: float):
        """Обновление свечей для всех таймфреймов"""
        current_time = datetime.now(self.qp_provider.tz_msk)

        with self.lock:
            if ticker_key not in self.candles:
                self._initialize_candles_for_ticker(ticker_key)

            for timeframe_name, timeframe_sec in self.timeframes.items():
                candles_list = self.candles[ticker_key][timeframe_name]

                # Определяем время начала текущей свечи
                if self.candle_start_times[ticker_key][timeframe_name] is None:
                    # Первая свеча - округляем время до начала интервала
                    seconds = current_time.second + current_time.minute * 60
                    intervals_passed = seconds // timeframe_sec
                    start_seconds = intervals_passed * timeframe_sec

                    start_time = current_time.replace(
                        second=start_seconds % 60,
                        minute=(start_seconds // 60) % 60,
                        microsecond=0
                    )
                    self.candle_start_times[ticker_key][timeframe_name] = start_time

                candle_start = self.candle_start_times[ticker_key][timeframe_name]

                # Проверяем, не началась ли новая свеча
                if (current_time - candle_start).total_seconds() >= timeframe_sec:
                    # Сохраняем завершенную свечу
                    if candles_list and candles_list[-1]['open'] is not None:
                        self._save_candle_to_json(ticker_key, timeframe_name, candles_list[-1])

                    # Начинаем новую свечу
                    new_candle = {
                        'open': price,
                        'high': price,
                        'low': price,
                        'close': price,
                        'volume': self.current_prices.get(ticker_key, {}).get('volume', 0.0),
                        'timestamp': current_time.isoformat(),
                        'start_time': candle_start.isoformat(),
                        'end_time': (candle_start + timedelta(seconds=timeframe_sec)).isoformat()
                    }
                    candles_list.append(new_candle)

                    # Обновляем время начала свечи
                    self.candle_start_times[ticker_key][timeframe_name] = candle_start + timedelta(seconds=timeframe_sec)

                else:
                    # Обновляем текущую свечу
                    if candles_list:
                        current_candle = candles_list[-1]
                        current_candle['high'] = max(current_candle['high'], price)
                        current_candle['low'] = min(current_candle['low'], price)
                        current_candle['close'] = price

                        # Обновляем объем
                        if ticker_key in self.current_prices:
                            current_candle['volume'] += self.current_prices[ticker_key].get('volume', 0.0)

    def _save_candle_to_json(self, ticker_key: str, timeframe: str, candle: Dict):
        """Сохранение свечи в JSON файл"""
        try:
            # Создаем структуру директорий
            ticker_dir = os.path.join(self.output_dir, ticker_key.replace('.', '_'))
            os.makedirs(ticker_dir, exist_ok=True)

            # Формируем имя файла
            date_str = datetime.now().strftime("%Y-%m-%d")
            filename = os.path.join(ticker_dir, f"{timeframe}_{date_str}.json")

            # Загружаем существующие данные или создаем новые
            existing_data = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)

            # Добавляем новую свечу
            existing_data.append(candle)

            # Сохраняем обратно
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)

            self.logger.debug(f'Сохранена свеча {ticker_key} {timeframe}: {candle}')

        except Exception as e:
            self.logger.error(f'Ошибка при сохранении свечи в JSON: {e}')

    def subscribe_to_tickers(self, tickers_config: Dict):
        """
        Подписка на указанные тикеры

        Args:
            tickers_config: Конфигурация тикеров в формате:
                {
                    "class_code": ["ticker1", "ticker2", ...],
                    "SPBFUT": ["IMOEXF", "GLDRUBF", ...]
                }
        """
        self.logger.info(f'Начинаем подписку на {len(tickers_config)} классов тикеров')

        for class_code, tickers in tickers_config.items():
            for ticker_code in tickers:
                ticker_key = f"{class_code}.{ticker_code}"

                try:
                    # Получаем текущий стакан
                    quote_data = self.qp_provider.get_quote_level2(class_code, ticker_code)
                    self.logger.info(f'Текущий стакан {ticker_key}: {quote_data.get("data", {})}')

                    # Подписка на изменения стакана
                    subscription_result = self.qp_provider.subscribe_level2_quotes(class_code, ticker_code)
                    self.logger.info(f'Подписка на {ticker_key}: {subscription_result.get("data", {})}')

                    # Проверяем статус подписки
                    status_result = self.qp_provider.is_subscribed_level2_quotes(class_code, ticker_code)
                    self.logger.info(f'Статус подписки {ticker_key}: {status_result.get("data", {})}')

                    self.subscriptions.append((class_code, ticker_code))

                    # Инициализируем структуры для свечей
                    self._initialize_candles_for_ticker(ticker_key)

                    # Получаем начальную цену
                    self._on_quote({'data': quote_data.get('data', {})})

                except Exception as e:
                    self.logger.error(f'Ошибка при подписке на {ticker_key}: {e}')

    def start_streaming(self, duration_seconds: Optional[int] = None):
        """
        Запуск стриминга данных

        Args:
            duration_seconds: Длительность стриминга в секундах (None - бесконечно)
        """
        self.running = True

        # Подписываемся на обработчики событий
        self.qp_provider.on_quote.subscribe(self._on_quote)
        self.qp_provider.on_all_trade.subscribe(self._on_all_trade)

        self.logger.info(f'Стриминг запущен{" на " + str(duration_seconds) + " секунд" if duration_seconds else ""}')

        def streaming_loop():
            try:
                if duration_seconds:
                    time.sleep(duration_seconds)
                else:
                    # Бесконечный цикл
                    while self.running:
                        time.sleep(1)

                        # Периодическое сохранение текущих свечей
                        self._save_current_candles()

            except KeyboardInterrupt:
                self.logger.info('Получен сигнал прерывания')
            finally:
                self.stop_streaming()

        # Запускаем в отдельном потоке
        self.update_thread = threading.Thread(target=streaming_loop, daemon=True)
        self.update_thread.start()

    def _save_current_candles(self):
        """Периодическое сохранение текущих (незавершенных) свечей"""
        with self.lock:
            for ticker_key, timeframes in self.candles.items():
                for timeframe, candles_list in timeframes.items():
                    if candles_list:
                        last_candle = candles_list[-1]
                        # Сохраняем только если свеча имеет данные
                        if last_candle['open'] is not None:
                            # Создаем копию для сохранения
                            candle_to_save = last_candle.copy()
                            candle_to_save['timestamp'] = datetime.now(self.qp_provider.tz_msk).isoformat()
                            self._save_candle_to_json(ticker_key, timeframe, candle_to_save)

    def stop_streaming(self):
        """Остановка стриминга"""
        self.running = False

        if self.update_thread:
            self.update_thread.join(timeout=5)

        # Отписываемся от тикеров
        self.logger.info('Отмена подписок на все тикеры...')

        for class_code, ticker_code in self.subscriptions:
            try:
                unsubscribe_result = self.qp_provider.unsubscribe_level2_quotes(class_code, ticker_code)
                self.logger.info(f'Отмена подписки для {ticker_code}: {unsubscribe_result.get("data", {})}')
            except Exception as e:
                self.logger.error(f'Ошибка при отмене подписки для {ticker_code}: {e}')

        # Сохраняем все текущие свечи перед выходом
        self._save_current_candles()

        # Отменяем обработчики событий
        self.qp_provider.on_quote.unsubscribe(self._on_quote)
        self.qp_provider.on_all_trade.unsubscribe(self._on_all_trade)

        # Выход
        self.qp_provider.close_connection_and_thread()
        self.logger.info('Стриминг остановлен')

    def get_current_prices(self) -> Dict[str, Dict]:
        """Получение текущих цен всех подписанных тикеров"""
        with self.lock:
            return self.current_prices.copy()

    def get_candles(self, ticker_key: str, timeframe: str) -> List[Dict]:
        """Получение свечей для указанного тикера и таймфрейма"""
        with self.lock:
            return self.candles.get(ticker_key, {}).get(timeframe, []).copy()


def main():
    """
    Пример использования класса PriceStreamer
    """
    # Конфигурация тикеров (можно передавать как аргумент или читать из файла)
    tickers_config = {
        "SPBFUT": [
            "IMOEXF",    # Фьючерс на индекс Мосбиржи
            "GLDRUBF",   # Фьючерс на золото
            "NAH6",      # Фьючерс на NASDAQ
            "VBH6",      # Фьючерс на ВТБ
            "YDH6",      # Фьючерс на индекс
            "SRH6",      # Фьючерс на Сбербанк
            "GZH6",      # Фьючерс на газ
            "BRF6"       # Фьючерс на нефть Brent
        ],
        "TQBR": [
            "SBER",      # Акции Сбербанка
            "GAZP",      # Акции Газпрома
        ]
    }

    # Создаем стример
    streamer = PriceStreamer(output_dir="market_data")

    try:
        # Подписываемся на тикеры
        streamer.subscribe_to_tickers(tickers_config)

        # Запускаем стриминг на 300 секунд (5 минут)
        streamer.start_streaming(duration_seconds=300)

        # Можно также запустить бесконечный стриминг:
        # streamer.start_streaming()

        # В основном потоке можно делать что-то еще,
        # например, периодически выводить текущие цены
        while streamer.running:
            time.sleep(10)
            current_prices = streamer.get_current_prices()
            print(f"\nТекущие цены ({len(current_prices)} тикеров):")
            for ticker, data in current_prices.items():
                print(f"  {ticker}: {data['price']}")

    except KeyboardInterrupt:
        print("\nЗавершение по команде пользователя...")
    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        streamer.stop_streaming()


if __name__ == '__main__':
    main()