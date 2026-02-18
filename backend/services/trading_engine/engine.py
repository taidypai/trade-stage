# backend/services/trading_engine/engine.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
from typing import Dict, List, Optional
from datetime import datetime

from backend.components.logger import logger
from backend.components.quik_components.quik_account import get_balance
from backend.components.quik_components.quik_transaction import StocksTrader, FuturesTrader
from backend.components.tg_message import send_tg_message_safe
from settings.backend_config import TRADING_TIKERS
from .trailing_stop import TrailingStop, TrailingStopConfig
from .position_tracker import PositionTracker


class TradingEngine:
    """Главный движок для управления всеми трейлинг-стопами"""

    def __init__(self):
        self.trackers: Dict[str, PositionTracker] = {}
        self.running = False
        self.main_task = None

    async def start(self):
        """Запускает движок"""
        self.running = True
        self.main_task = asyncio.create_task(self._monitor_loop())
        logger.info("🚀 Trading Engine запущен")
        await send_tg_message_safe("🚀 *Trading Engine запущен*\nОжидание команд...")

    async def stop(self):
        """Останавливает движок"""
        self.running = False

        # Останавливаем все трекеры
        for tracker in self.trackers.values():
            await tracker.stop()

        if self.main_task:
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass

        logger.info("⏹️ Trading Engine остановлен")
        await send_tg_message_safe("⏹️ *Trading Engine остановлен*")

    def _detect_trader_class(self, ticker: str):
        """Определяет класс трейдера по тикеру"""
        # Собираем все фьючерсные тикеры из SPBFUT
        futures_tickers = []
        if "SPBFUT" in TRADING_TIKERS:
            # Добавляем значения (тикеры)
            futures_tickers.extend(TRADING_TIKERS["SPBFUT"].values())
            # Добавляем ключи (названия инструментов)
            futures_tickers.extend(TRADING_TIKERS["SPBFUT"].keys())

        # Приводим к верхнему регистру для сравнения
        ticker_upper = ticker.upper()
        futures_tickers_upper = [t.upper() for t in futures_tickers if t]

        if ticker_upper in futures_tickers_upper:
            logger.info(f"🔍 Тикер {ticker} определен как ФЬЮЧЕРС")
            return FuturesTrader

        logger.info(f"🔍 Тикер {ticker} определен как АКЦИЯ")
        return StocksTrader

    def _calculate_position_size(self, config: TrailingStopConfig, risk_rub: float) -> int:
        """Рассчитывает объем позиции на основе риска в рублях"""
        stop_distance = abs(config.entry_price - config.initial_stop)
        risk_per_unit = stop_distance * config.point_value
        if risk_per_unit <= 0:
            return 1
        quantity = int(risk_rub / risk_per_unit)
        return max(1, quantity)

    async def open_position_manual(self, ticker: str, direction: str,
                                   stop_loss: float, risk_rub: float = None) -> bool:
        """
        Открывает новую позицию с ручным вводом параметров

        Параметры:
        - ticker: тикер инструмента (например "YDH6", "SBER")
        - direction: 'long' или 'short'
        - stop_loss: уровень стоп-лосса (ВВОДИТ ПОЛЬЗОВАТЕЛЬ)
        - risk_rub: риск в рублях (если None, берется 2% от баланса)
        """
        try:
            # Получаем данные баланса
            account_data = get_balance()
            balance = account_data.get('balance', 0)

            if balance == 0:
                logger.error("❌ Нет доступных средств")
                await send_tg_message_safe("❌ *Ошибка*: Нет доступных средств на счете")
                return False

            # Определяем класс инструмента и получаем текущую цену
            trader_class = self._detect_trader_class(ticker)
            trader = trader_class()
            entry_price = trader.get_price(ticker)
            trader.close()

            if entry_price is None:
                logger.error(f"❌ Не удалось получить цену для {ticker}")
                await send_tg_message_safe(f"❌ *Ошибка*: Не удалось получить цену для {ticker}")
                return False

            # Проверяем корректность стоп-лосса
            if direction == 'long' and stop_loss >= entry_price:
                logger.error(f"❌ Для LONG стоп должен быть ниже цены входа ({entry_price:.2f})")
                await send_tg_message_safe(f"❌ *Ошибка*: Для LONG стоп должен быть ниже цены входа ({entry_price:.2f})")
                return False
            elif direction == 'short' and stop_loss <= entry_price:
                logger.error(f"❌ Для SHORT стоп должен быть выше цены входа ({entry_price:.2f})")
                await send_tg_message_safe(f"❌ *Ошибка*: Для SHORT стоп должен быть выше цены входа ({entry_price:.2f})")
                return False

            # Рассчитываем риск
            if risk_rub is None:
                risk_rub = balance * 0.02  # 2% от баланса

            # Создаем конфиг
            config = TrailingStopConfig(
                ticker=ticker,
                direction=direction,
                entry_price=entry_price,
                quantity=1,  # Будет пересчитано
                initial_stop=stop_loss,
                trail_step=1.0,  # Шаг трейлинга в пунктах
                account_balance=balance,
                risk_percent=2.0
            )

            # Рассчитываем объем позиции (используем локальный метод)
            config.quantity = self._calculate_position_size(config, risk_rub)

            logger.info(f"📊 Расчет позиции для {ticker}:")
            logger.info(f"   Баланс: {balance:.2f} RUB")
            logger.info(f"   Риск: {risk_rub:.2f} RUB")
            logger.info(f"   Объем: {config.quantity} лотов")
            logger.info(f"   Стоп расстояние: {abs(entry_price - stop_loss):.2f} пунктов")
            logger.info(f"   Риск на 1 лот: {abs(entry_price - stop_loss) * config.point_value:.2f} RUB")

            # Открываем позицию
            trader = config.trader_class()

            if direction == 'long':
                result = trader.buy(ticker, config.quantity)
            else:
                result = trader.sell(ticker, config.quantity)

            trader.close()

            if not result.get('success'):
                error_msg = f"❌ Ошибка открытия позиции: {result.get('message')}"
                logger.error(error_msg)
                await send_tg_message_safe(error_msg)
                return False

            # Создаем трейлинг-стоп
            trailing_stop = TrailingStop(config)

            # Создаем и запускаем трекер
            tracker = PositionTracker(trailing_stop)
            self.trackers[trailing_stop.position_id] = tracker
            await tracker.start()

            return True

        except Exception as e:
            error_msg = f"❌ Ошибка при открытии позиции: {e}"
            logger.error(error_msg)
            await send_tg_message_safe(error_msg)
            return False

    async def close_position(self, position_id: str):
        """Принудительно закрывает позицию"""
        if position_id in self.trackers:
            await self.trackers[position_id].stop()
            del self.trackers[position_id]
            logger.info(f"🔴 Позиция {position_id} закрыта принудительно")
            await send_tg_message_safe(f"🔴 *Позиция {position_id} закрыта принудительно*")

    async def get_positions(self) -> List[Dict]:
        """Возвращает список активных позиций"""
        positions = []
        for tracker in self.trackers.values():
            if tracker.running and not tracker.trailing_stop.fully_closed:
                positions.append(tracker.trailing_stop.to_dict())
        return positions

    async def _monitor_loop(self):
        """Фоновый мониторинг всех позиций"""
        while self.running:
            try:
                # Проверяем, не зависли ли какие-то трекеры
                for position_id, tracker in list(self.trackers.items()):
                    if not tracker.running and not tracker.trailing_stop.fully_closed:
                        # Трекер умер, но позиция не закрыта - перезапускаем
                        logger.warning(f"🔄 Перезапуск трекера для {position_id}")
                        await tracker.start()

                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка в monitor_loop: {e}")
                await asyncio.sleep(5)

    def __enter__(self):
        """Для использования с 'with'"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие при выходе из with"""
        if self.running:
            asyncio.create_task(self.stop())