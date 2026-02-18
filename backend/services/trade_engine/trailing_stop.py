# backend/services/trading_engine/trailing_stop.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
from backend.components.logger import logger

@dataclass
class TrailingStopConfig:
    """Конфигурация трейлинг-стопа"""
    ticker: str
    direction: str
    entry_price: float
    quantity: int
    initial_stop: float
    trail_step: float = 1.0
    point_value: float = 1.0

class TrailingStop:
    """Управляет стоп-лоссом"""

    def __init__(self, config: TrailingStopConfig):
        self.config = config
        self.position_id = f"{config.ticker}_{datetime.now().strftime('%H%M%S')}"
        self.current_stop = config.initial_stop
        self.highest_price = config.entry_price if config.direction == 'long' else None
        self.lowest_price = config.entry_price if config.direction == 'short' else None
        self.partial_closed = False
        self.fully_closed = False
        self.current_quantity = config.quantity

        logger.info(f"Стоп {config.ticker}: вход {config.entry_price}, стоп {config.initial_stop}")

    def update_stop(self, current_price: float) -> Optional[float]:
        if self.fully_closed:
            return None

        old_stop = self.current_stop

        if self.config.direction == 'long':
            if not self.highest_price or current_price > self.highest_price:
                if self.highest_price:
                    increase = current_price - self.highest_price
                    self.current_stop += increase
                self.highest_price = current_price
        else:
            if not self.lowest_price or current_price < self.lowest_price:
                if self.lowest_price:
                    decrease = self.lowest_price - current_price
                    self.current_stop -= decrease
                self.lowest_price = current_price

        if self.current_stop != old_stop:
            logger.info(f"Стоп {self.config.ticker}: {old_stop:.2f} -> {self.current_stop:.2f}")
            return self.current_stop
        return None

    def should_close_partial(self, current_price: float) -> bool:
        if self.partial_closed or self.fully_closed:
            return False

        if self.config.direction == 'long':
            profit = current_price - self.config.entry_price
            risk = self.config.entry_price - self.config.initial_stop
        else:
            profit = self.config.entry_price - current_price
            risk = self.config.initial_stop - self.config.entry_price

        return risk > 0 and profit >= risk

    def should_close_full(self, current_price: float) -> bool:
        if self.fully_closed:
            return False

        if self.config.direction == 'long':
            return current_price <= self.current_stop
        else:
            return current_price >= self.current_stop

    def to_dict(self) -> Dict:
        return {
            'ticker': self.config.ticker,
            'direction': self.config.direction,
            'entry_price': self.config.entry_price,
            'current_stop': self.current_stop,
            'current_quantity': self.current_quantity,
            'highest_price': self.highest_price,
            'lowest_price': self.lowest_price
        }