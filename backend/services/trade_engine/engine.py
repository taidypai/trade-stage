"""python backend/services/trading_engine/engine.py"""

import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from backend.components.logger import logger
from backend.components.account import get_balance
from backend.components.transaction import TQBR, SPBFUT
from backend.components.tg_message import send_tg_message
from settings.backend_config import TRADING_TIKERS, JSON_PRICE_PATH
from .trailing_stop import TrailingStop, TrailingStopConfig
from .position_tracker import PositionTracker

import asyncio
import json
from typing import Dict, List

class TradeEngine:
    """Управляет всеми трейлинг-стопами"""

    def __init__(self):
        self.trackers: Dict[str, PositionTracker] = {}
        self.running = False
        self.main_task = None

    async def start(self):
        self.running = True
        self.main_task = asyncio.create_task(self.monitor_loop())
        logger.info("Trade Engine запущен")

    async def stop(self):
        self.running = False
        for tracker in self.trackers.values():
            await tracker.stop()
        if self.main_task:
            self.main_task.cancel()
            try:
                await self.main_task
            except asyncio.CancelledError:
                pass
        logger.info("Trade Engine остановлен")

    def _get_price_from_json(self, ticker: str) -> float:
        """Получает цену из market_data.json"""
        try:
            with open(JSON_PRICE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for class_code, instruments in data.items():
                for name, instrument in instruments.items():
                    if instrument.get('ticker') == ticker or name == ticker:
                        return float(instrument.get('price', 0))
            return 0
        except Exception as e:
            logger.error(f"Ошибка чтения цены: {e}")
            return 0

    def _get_point_value(self, ticker: str) -> float:
        """Получает стоимость пункта из market_data.json"""
        try:
            with open(JSON_PRICE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for class_code, instruments in data.items():
                for name, instrument in instruments.items():
                    if instrument.get('ticker') == ticker or name == ticker:
                        if class_code == "SPBFUT":
                            return float(instrument.get('step_price', 1.0))
                        return 1.0
            return 1.0
        except:
            return 1.0

    def _get_trader_class(self, ticker: str):
        """Определяет класс трейдера по тикеру"""
        try:
            with open(JSON_PRICE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for class_code, instruments in data.items():
                for name, instrument in instruments.items():
                    if instrument.get('ticker') == ticker or name == ticker:
                        if class_code == "SPBFUT":
                            return SPBFUT
                        return TQBR
            return TQBR
        except:
            return TQBR

    def _calc_quantity(self, entry_price: float, stop_loss: float, balance: float, point_value: float = 1.0) -> int:
        """Рассчитывает количество лотов с проверкой на достаточность средств"""

        # Риск 2% от баланса
        risk_rub = balance * 0.02

        # Расстояние до стопа
        stop_distance = abs(entry_price - stop_loss)
        if stop_distance <= 0:
            return 1

        # Риск на 1 лот
        risk_per_lot = stop_distance * point_value
        if risk_per_lot <= 0:
            return 1

        # Объем по риску
        quantity_by_risk = int(risk_rub / risk_per_lot)
        if quantity_by_risk < 1:
            quantity_by_risk = 1

        # Проверяем, хватит ли денег на покупку
        # Для акций: цена * количество, для фьючерсов: примерно ГО
        if point_value == 1.0:  # Акция
            cost_per_lot = entry_price  # Стоимость 1 лота
            max_by_balance = int(balance / cost_per_lot)-1 if cost_per_lot > 0 else 0
        else:  # Фьючерс
            # Примерно 10-15% от стоимости как ГО, берем с запасом 20%
            go_per_lot = entry_price * 0.2 * point_value
            max_by_balance = int(balance / go_per_lot) if go_per_lot > 0 else 0

        # Если денег не хватает даже на 1 лот по риску
        if quantity_by_risk > max_by_balance and max_by_balance > 0:
            logger.info(f"Не хватает средств на {quantity_by_risk} лотов, беру максимум {max_by_balance}")
            return max_by_balance

        # Если по риску получилось меньше 1, но деньги есть - берем 1 лот
        if quantity_by_risk < 1 and max_by_balance >= 1:
            return 1

        return max(1, quantity_by_risk)

    async def open_position(self, ticker: str, direction: str, stop_loss: float):
        """Открывает позицию"""
        try:
            # Проверяем баланс
            account_data = get_balance()
            balance = account_data.get('balance', 0)
            if balance <= 0:
                logger.error("Нет средств")
                await send_tg_message("❌ Нет средств")
                return False

            # Получаем цену из JSON
            entry_price = self._get_price_from_json(ticker)
            if entry_price <= 0:
                logger.error(f"Нет цены для {ticker}")
                await send_tg_message(f"❌ Нет цены для {ticker}")
                return False

            # Проверяем стоп
            if direction == 'long' and stop_loss >= entry_price:
                await send_tg_message(f"❌ Стоп должен быть ниже {entry_price:.2f}")
                return False
            if direction == 'short' and stop_loss <= entry_price:
                await send_tg_message(f"❌ Стоп должен быть выше {entry_price:.2f}")
                return False

            # Получаем стоимость пункта
            point_value = self._get_point_value(ticker)

            # Рассчитываем количество лотов
            quantity = self._calc_quantity(entry_price, stop_loss, balance, point_value)

            # Финальная проверка - хватит ли денег
            if point_value == 1.0:  # Акция
                needed = entry_price * quantity
            else:  # Фьючерс
                needed = entry_price * 0.2 * point_value * quantity  # Примерно ГО

            if needed > balance:
                logger.error(f"Не хватает средств: нужно {needed:.2f}, есть {balance:.2f}")
                await send_tg_message(f"❌ Не хватает средств: нужно {needed:.2f}, есть {balance:.2f}")
                return False

            # Создаем конфиг
            config = TrailingStopConfig(
                ticker=ticker,
                direction=direction,
                entry_price=entry_price,
                quantity=quantity,
                initial_stop=stop_loss,
                trail_step=1.0,
                point_value=point_value
            )

            # Открываем позицию через QUIK
            trader_class = self._get_trader_class(ticker)
            trader = trader_class()
            if direction == 'long':
                result = trader.buy(ticker, quantity)
            else:
                result = trader.sell(ticker, quantity)
            trader.close()

            if not result.get('success'):
                logger.error(f"Ошибка: {result.get('message')}")
                await send_tg_message(f"❌ {result.get('message')}")
                return False

            # Запускаем отслеживание
            trailing_stop = TrailingStop(config)
            tracker = PositionTracker(trailing_stop, self._get_price_from_json, ticker)
            self.trackers[trailing_stop.position_id] = tracker
            await tracker.start()

            # Уведомление
            risk_rub = abs(entry_price - stop_loss) * point_value * quantity
            msg = (f"✅ {ticker} {direction.upper()}\n"
                   f"Цена: {entry_price:.2f}\n"
                   f"Лотов: {quantity}\n"
                   f"Риск: {risk_rub:.2f} RUB\n"
                   f"Нужно средств: {needed:.2f} RUB")
            await send_tg_message(msg)

            return True

        except Exception as e:
            logger.error(f"Ошибка: {e}")
            await send_tg_message(f"❌ Ошибка: {e}")
            return False

    async def close_position(self, position_id: str):
        if position_id in self.trackers:
            await self.trackers[position_id].stop()
            del self.trackers[position_id]
            logger.info(f"Позиция {position_id} закрыта")

    async def get_positions(self) -> List[Dict]:
        positions = []
        for tracker in self.trackers.values():
            if tracker.running and not tracker.trailing_stop.fully_closed:
                positions.append(tracker.trailing_stop.to_dict())
        return positions

    async def monitor_loop(self):
        while self.running:
            try:
                for position_id, tracker in list(self.trackers.items()):
                    if not tracker.running and not tracker.trailing_stop.fully_closed:
                        logger.warning(f"Перезапуск {position_id}")
                        await tracker.start()
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ошибка: {e}")
                await asyncio.sleep(5)