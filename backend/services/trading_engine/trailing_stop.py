# backend/services/trading_engine/trailing_stop.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from backend.components.logger import logger
from backend.components.quik_components.quik_transaction import StocksTrader, FuturesTrader
from settings.backend_config import JSON_PRICE_PATH, TRADING_TIKERS


@dataclass
class TrailingStopConfig:
    """Конфигурация трейлинг-стопа"""
    ticker: str                     # Тикер инструмента
    direction: str                   # 'long' или 'short'
    entry_price: float               # Цена входа
    quantity: int                     # Количество лотов
    initial_stop: float               # Начальный стоп-лосс (ВВОДИТ ПОЛЬЗОВАТЕЛЬ)
    trail_step: float = 1.0           # Шаг трейлинга (в пунктах цены)
    take_profit_rr: float = 1.0       # RR для частичного закрытия (по умолчанию 1:1)
    part_close_percent: float = 50.0  # Процент для частичного закрытия

    # Для расчета объема позиции
    account_balance: float = 0.0
    risk_percent: float = 2.0         # Процент риска от баланса

    def __post_init__(self):
        # Определяем класс инструмента
        self.class_code = self._detect_class_code()
        # Загружаем данные инструмента
        self.instrument_data = self._load_instrument_data()

    def _detect_class_code(self) -> str:
        """Определяем класс инструмента (фьючерс или акция)"""
        ticker_upper = self.ticker.upper()

        for class_code, tickers in TRADING_TIKERS.items():
            # Проверяем по значениям (тикерам)
            for value in tickers.values():
                if value.upper() == ticker_upper:
                    print(f"🔍 Тикер {self.ticker} найден в {class_code} как {value}")
                    return class_code

            # Проверяем по ключам (названиям)
            for key in tickers.keys():
                if key.upper() == ticker_upper:
                    print(f"🔍 Название {self.ticker} найдено в {class_code} как {key}")
                    return class_code

        print(f"⚠️ Тикер {self.ticker} не найден в TRADING_TIKERS, используется TQBR по умолчанию")
        return "TQBR"

    def _load_instrument_data(self) -> Dict:
        """Загружает данные инструмента из market_data.json"""
        try:
            with open(JSON_PRICE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ищем данные для нашего тикера
                for class_code, instruments in data.items():
                    for name, instrument_data in instruments.items():
                        if instrument_data.get('ticker') == self.ticker:
                            return instrument_data
                        if name == self.ticker:
                            return instrument_data
            return {}
        except Exception as e:
            logger.error(f"Ошибка загрузки market_data.json: {e}")
            return {}

    @property
    def is_futures(self) -> bool:
        return self.class_code == "SPBFUT"

    @property
    def trader_class(self):
        return FuturesTrader if self.is_futures else StocksTrader

    @property
    def point_value(self) -> float:
        """Стоимость одного пункта цены в рублях"""
        if self.is_futures:
            # Для фьючерсов берем step_price из market_data.json
            return float(self.instrument_data.get('step_price', 1.0))
        else:
            # Для акций 1 пункт = 1 рубль (так как цена в рублях)
            return 1.0


class TrailingStop:
    """Управление трейлинг-стопом для одной позиции"""

    def __init__(self, config: TrailingStopConfig, position_id: str = None):
        self.config = config
        self.position_id = position_id or f"{config.ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.current_stop = config.initial_stop
        self.highest_price = config.entry_price if config.direction == 'long' else None
        self.lowest_price = config.entry_price if config.direction == 'short' else None
        self.partial_closed = False
        self.fully_closed = False
        self.current_quantity = config.quantity

        logger.info(f"🚀 Создан трейлинг-стоп для {config.ticker} ({config.direction})")
        logger.info(f"   Вход: {config.entry_price:.2f}, Стоп: {config.initial_stop:.2f}")
        logger.info(f"   Тип: {'Фьючерс' if config.is_futures else 'Акция'}")
        logger.info(f"   Шаг трейлинга: {config.trail_step} пунктов")
        logger.info(f"   Стоимость пункта: {config.point_value:.2f} RUB")

    def update_stop(self, current_price: float) -> Optional[float]:
        """
        Обновляет стоп-лосс на основе текущей цены
        +1 пункт цены = +1 пункт к стопу
        """
        if self.fully_closed:
            return None

        old_stop = self.current_stop

        if self.config.direction == 'long':
            # Для лонга - поднимаем стоп пропорционально росту цены
            if self.highest_price is None or current_price > self.highest_price:
                if self.highest_price is not None:
                    price_increase = current_price - self.highest_price
                    # Поднимаем стоп на ту же величину
                    new_stop = self.current_stop + price_increase
                    if new_stop > self.current_stop:
                        self.current_stop = new_stop
                self.highest_price = current_price

        else:  # short
            # Для шорта - опускаем стоп пропорционально падению цены
            if self.lowest_price is None or current_price < self.lowest_price:
                if self.lowest_price is not None:
                    price_decrease = self.lowest_price - current_price
                    # Опускаем стоп на ту же величину
                    new_stop = self.current_stop - price_decrease
                    if new_stop < self.current_stop:
                        self.current_stop = new_stop
                self.lowest_price = current_price

        if self.current_stop != old_stop:
            points_moved = abs(self.current_stop - old_stop)
            logger.info(f"📈 Стоп обновлен: {old_stop:.2f} -> {self.current_stop:.2f} (+{points_moved:.2f} пунктов)")
            return self.current_stop
        return None

    def should_close_partial(self, current_price: float) -> bool:
        """Проверяем, нужно ли закрыть часть позиции по RR"""
        if self.partial_closed or self.fully_closed:
            return False

        if self.config.direction == 'long':
            profit_points = current_price - self.config.entry_price
            stop_distance = self.config.entry_price - self.config.initial_stop
            rr = profit_points / stop_distance if stop_distance != 0 else 0
        else:
            profit_points = self.config.entry_price - current_price
            stop_distance = self.config.initial_stop - self.config.entry_price
            rr = profit_points / stop_distance if stop_distance != 0 else 0

        if rr >= self.config.take_profit_rr:
            profit_percent = (profit_points / self.config.entry_price) * 100
            logger.info(f"🎯 Достигнут целевой уровень RR={rr:.2f}, прибыль={profit_percent:.2f}%")
            return True
        return False

    def should_close_full(self, current_price: float) -> bool:
        """Проверяем, достиг ли стоп-лосс"""
        if self.fully_closed:
            return False

        if self.config.direction == 'long':
            return current_price <= self.current_stop
        else:  # short
            return current_price >= self.current_stop

    def calculate_position_size(self, risk_rub: float) -> int:
        """Рассчитывает объем позиции на основе риска в рублях"""
        stop_distance = abs(self.config.entry_price - self.config.initial_stop)
        risk_per_unit = stop_distance * self.config.point_value
        if risk_per_unit <= 0:
            return 1
        quantity = int(risk_rub / risk_per_unit)
        return max(1, quantity)

    def to_dict(self) -> Dict:
        """Сериализация для сохранения состояния"""
        return {
            'position_id': self.position_id,
            'ticker': self.config.ticker,
            'direction': self.config.direction,
            'entry_price': self.config.entry_price,
            'current_quantity': self.current_quantity,
            'initial_quantity': self.config.quantity,
            'current_stop': self.current_stop,
            'initial_stop': self.config.initial_stop,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price,
            'partial_closed': self.partial_closed,
            'fully_closed': self.fully_closed,
            'trail_step': self.config.trail_step,
            'class_code': self.config.class_code,
            'point_value': self.config.point_value,
            'is_futures': self.config.is_futures
        }