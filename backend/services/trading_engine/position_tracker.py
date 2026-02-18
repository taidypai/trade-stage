# backend/services/trading_engine/position_tracker.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
import time
from typing import Optional, Dict, Any

from backend.components.logger import logger
from backend.components.tg_message import send_tg_message_safe
from backend.components.quik_components.quik_account import get_balance
from backend.components.quik_components.quik_transaction import StocksTrader, FuturesTrader
from .trailing_stop import TrailingStop, TrailingStopConfig


class PositionTracker:
    """Отслеживает одну позицию и управляет ее закрытием"""

    def __init__(self, trailing_stop: TrailingStop, check_interval: float = 0.5):
        self.trailing_stop = trailing_stop
        self.check_interval = check_interval
        self.running = False
        self.task = None
        self.order_confirmed = False  # Флаг подтверждения открытия позиции

    async def start(self):
        """Запускает отслеживание позиции"""
        self.running = True
        self.task = asyncio.create_task(self._track_loop())
        logger.info(f"▶️ Начато отслеживание {self.trailing_stop.config.ticker}")

        # Отправляем уведомление о попытке открытия
        await self._send_notification('attempt')

        # Запускаем проверку исполнения ордера
        asyncio.create_task(self._check_order_execution())

    async def stop(self):
        """Останавливает отслеживание"""
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info(f"⏹️ Остановлено отслеживание {self.trailing_stop.config.ticker}")

    async def _check_order_execution(self):
        """Проверяет, исполнился ли ордер на покупку/продажу"""
        start_time = time.time()
        timeout = 60  # 60 секунд на ожидание

        while time.time() - start_time < timeout and self.running:
            try:
                # Получаем баланс и открытые позиции
                account_data = get_balance()

                # Ищем нашу позицию среди открытых
                found = False
                for position in account_data.get('positions', []):
                    if position.get('sec_code') == self.trailing_stop.config.ticker:
                        # Проверяем, что количество совпадает с нашим ордером
                        if abs(position.get('quantity', 0)) >= self.trailing_stop.config.quantity:
                            found = True
                            break

                if found:
                    self.order_confirmed = True
                    logger.info(f"✅ Ордер на {self.trailing_stop.config.ticker} исполнился")
                    await self._send_notification('executed')
                    return

            except Exception as e:
                logger.error(f"Ошибка при проверке исполнения ордера: {e}")

            await asyncio.sleep(2)  # Проверяем каждые 2 секунды

        # Если вышли по таймауту и ордер не исполнился
        if not self.order_confirmed and self.running:
            logger.error(f"❌ Ордер на {self.trailing_stop.config.ticker} НЕ ИСПОЛНИЛСЯ за 60 секунд")
            await self._send_notification('failed')
            await self.stop()

    async def _track_loop(self):
        """Основной цикл отслеживания цены"""
        trader = None

        try:
            # Ждем подтверждения ордера (максимум 60 секунд)
            wait_start = time.time()
            while not self.order_confirmed and time.time() - wait_start < 60:
                await asyncio.sleep(0.5)

            if not self.order_confirmed:
                logger.error(f"❌ Отслеживание отменено - ордер не исполнился")
                return

            # Создаем трейдера для данного инструмента
            trader_class = self.trailing_stop.config.trader_class
            trader = trader_class()

            while self.running and not self.trailing_stop.fully_closed:
                try:
                    # Получаем текущую цену
                    current_price = trader.get_price(self.trailing_stop.config.ticker)

                    if current_price is None:
                        await asyncio.sleep(self.check_interval)
                        continue

                    # Обновляем трейлинг-стоп
                    self.trailing_stop.update_stop(current_price)

                    # Проверяем частичное закрытие
                    if (not self.trailing_stop.partial_closed and
                        self.trailing_stop.should_close_partial(current_price)):
                        await self._close_partial(trader, current_price)

                    # Проверяем полное закрытие
                    if self.trailing_stop.should_close_full(current_price):
                        await self._close_full(trader, current_price)
                        break

                except Exception as e:
                    logger.error(f"Ошибка в цикле отслеживания: {e}")

                await asyncio.sleep(self.check_interval)

        except asyncio.CancelledError:
            logger.info(f"Отслеживание отменено для {self.trailing_stop.config.ticker}")
        except Exception as e:
            logger.error(f"Критическая ошибка в PositionTracker: {e}")
        finally:
            if trader:
                trader.close()
            self.running = False

    async def _close_partial(self, trader, current_price: float):
        """Частичное закрытие позиции (50%)"""
        config = self.trailing_stop.config
        close_quantity = int(config.quantity * config.part_close_percent / 100)

        if close_quantity < 1:
            return

        # Выполняем сделку
        if config.direction == 'long':
            result = trader.sell(config.ticker, close_quantity)
        else:
            result = trader.buy(config.ticker, close_quantity)

        if result.get('success'):
            self.trailing_stop.partial_closed = True
            self.trailing_stop.current_quantity -= close_quantity

            # Рассчитываем PnL в пунктах и рублях
            if config.direction == 'long':
                points_pnl = current_price - config.entry_price
            else:
                points_pnl = config.entry_price - current_price

            rub_pnl = points_pnl * config.point_value * close_quantity

            await self._send_notification('partial', {
                'price': current_price,
                'quantity': close_quantity,
                'points_pnl': points_pnl,
                'rub_pnl': rub_pnl
            })
        else:
            logger.error(f"❌ Ошибка частичного закрытия: {result.get('message')}")

    async def _close_full(self, trader, current_price: float):
        """Полное закрытие позиции по стопу"""
        config = self.trailing_stop.config

        if self.trailing_stop.current_quantity <= 0:
            self.trailing_stop.fully_closed = True
            return

        # Выполняем сделку
        if config.direction == 'long':
            result = trader.sell(config.ticker, self.trailing_stop.current_quantity)
        else:
            result = trader.buy(config.ticker, self.trailing_stop.current_quantity)

        if result.get('success'):
            self.trailing_stop.fully_closed = True

            # Рассчитываем PnL в пунктах и рублях
            if config.direction == 'long':
                points_pnl = current_price - config.entry_price
            else:
                points_pnl = config.entry_price - current_price

            rub_pnl = points_pnl * config.point_value * config.quantity

            await self._send_notification('full', {
                'price': current_price,
                'quantity': self.trailing_stop.current_quantity,
                'points_pnl': points_pnl,
                'rub_pnl': rub_pnl,
                'stop_price': self.trailing_stop.current_stop
            })
        else:
            logger.error(f"❌ Ошибка полного закрытия: {result.get('message')}")

    async def _send_notification(self, event_type: str, data: Dict = None):
        """Отправляет уведомление в Telegram"""
        config = self.trailing_stop.config

        if event_type == 'attempt':
            message = (
                f"🔄 *Попытка открытия позиции*\n"
                f"Инструмент: {config.ticker}\n"
                f"Тип: {'Фьючерс' if config.is_futures else 'Акция'}\n"
                f"Направление: {config.direction.upper()}\n"
                f"Цена входа: {config.entry_price:.2f}\n"
                f"Стоп-лосс: {config.initial_stop:.2f}\n"
                f"Объем: {config.quantity} лотов\n"
                f"Риск: {abs(config.entry_price - config.initial_stop) * config.point_value * config.quantity:.2f} RUB\n"
                f"Ожидание исполнения..."
            )
        elif event_type == 'executed':
            message = (
                f"✅ *Позиция открыта*\n"
                f"Инструмент: {config.ticker}\n"
                f"Цена входа: {config.entry_price:.2f}\n"
                f"Объем: {config.quantity} лотов\n"
                f"Начато отслеживание цены"
            )
        elif event_type == 'failed':
            message = (
                f"❌ *Ошибка открытия позиции*\n"
                f"Инструмент: {config.ticker}\n"
                f"Ордер не исполнился за 60 секунд\n"
                f"Проверьте терминал QUIK"
            )
        elif event_type == 'partial':
            message = (
                f"📊 *Частичное закрытие (50%)*\n"
                f"Инструмент: {config.ticker}\n"
                f"Цена закрытия: {data['price']:.2f}\n"
                f"Объем: {data['quantity']} лотов\n"
                f"PnL: {data['points_pnl']:.2f} пунктов ({data['rub_pnl']:.2f} RUB)"
            )
        elif event_type == 'full':
            message = (
                f"🔴 *Позиция закрыта*\n"
                f"Инструмент: {config.ticker}\n"
                f"Цена закрытия: {data['price']:.2f}\n"
                f"Цена стопа: {data['stop_price']:.2f}\n"
                f"Объем: {data['quantity']} лотов\n"
                f"PnL: {data['points_pnl']:.2f} пунктов ({data['rub_pnl']:.2f} RUB)"
            )
        else:
            return

        await send_tg_message_safe(message)