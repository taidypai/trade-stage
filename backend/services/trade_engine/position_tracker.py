# backend/services/trading_engine/position_tracker.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
import time
import json
from backend.components.logger import logger
from backend.components.tg_message import send_tg_message
from backend.components.account import get_balance
from backend.components.transaction import TQBR, SPBFUT
from settings.backend_config import JSON_PRICE_PATH
from .trailing_stop import TrailingStop

class PositionTracker:
    """Отслеживает позицию по ценам из JSON"""

    def __init__(self, trailing_stop: TrailingStop, get_price_func, ticker: str):
        self.trailing_stop = trailing_stop
        self.get_price = get_price_func
        self.ticker = ticker
        self.running = False
        self.task = None
        self.order_confirmed = False

    def _get_trader_class(self):
        """Определяет класс трейдера по тикеру"""
        try:
            with open(JSON_PRICE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for class_code, instruments in data.items():
                for name, instrument in instruments.items():
                    if instrument.get('ticker') == self.ticker or name == self.ticker:
                        return SPBFUT if class_code == "SPBFUT" else TQBR
            return TQBR
        except:
            return TQBR

    async def start(self):
        self.running = True
        self.task = asyncio.create_task(self._run())
        logger.info(f"Слежу за {self.ticker}")

    async def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

    async def _run(self):
        """Основной цикл"""
        await self._wait_order()
        if not self.order_confirmed:
            return

        trader_class = self._get_trader_class()
        trader = trader_class()

        try:
            while self.running and not self.trailing_stop.fully_closed:
                price = self.get_price(self.ticker)

                if price and price > 0:
                    self.trailing_stop.update_stop(price)

                    if (not self.trailing_stop.partial_closed and
                        self.trailing_stop.should_close_partial(price)):
                        await self._close_partial(trader, price)

                    if self.trailing_stop.should_close_full(price):
                        await self._close_full(trader, price)
                        break

                await asyncio.sleep(0.5)
        finally:
            trader.close()
            self.running = False

    async def _wait_order(self):
        """Проверяет исполнение ордера 60 секунд"""
        start = time.time()
        while time.time() - start < 60 and self.running:
            data = get_balance()
            for pos in data.get('positions', []):
                if (pos.get('sec_code') == self.ticker and
                    abs(pos.get('quantity', 0)) >= self.trailing_stop.config.quantity):
                    self.order_confirmed = True
                    logger.info(f"Ордер исполнен {self.ticker}")
                    return
            await asyncio.sleep(2)

        if not self.order_confirmed:
            logger.error(f"Ордер не исполнен {self.ticker}")
            await send_tg_message(f"❌ Ордер не исполнен за 60с")
            await self.stop()

    async def _close_partial(self, trader, price):
        """Закрывает 50% позиции"""
        config = self.trailing_stop.config
        close_qty = config.quantity // 2

        if close_qty < 1:
            return

        if config.direction == 'long':
            result = trader.sell(config.ticker, close_qty)
        else:
            result = trader.buy(config.ticker, close_qty)

        if result.get('success'):
            self.trailing_stop.partial_closed = True
            self.trailing_stop.current_quantity -= close_qty

            points = price - config.entry_price if config.direction == 'long' else config.entry_price - price
            rub = points * config.point_value * close_qty

            await send_tg_message(f"📊 Частично {config.ticker}\n{points:.2f} п. ({rub:.2f} RUB)")

    async def _close_full(self, trader, price):
        """Закрывает позицию полностью"""
        config = self.trailing_stop.config

        if config.direction == 'long':
            result = trader.sell(config.ticker, self.trailing_stop.current_quantity)
        else:
            result = trader.buy(config.ticker, self.trailing_stop.current_quantity)

        if result.get('success'):
            self.trailing_stop.fully_closed = True

            points = price - config.entry_price if config.direction == 'long' else config.entry_price - price
            rub = points * config.point_value * config.quantity

            await send_tg_message(f"🔴 Закрыто {config.ticker}\n{points:.2f} п. ({rub:.2f} RUB)")