import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

import asyncio
import math
from typing import Optional

import config
from components.telegram_message import send_tg_message
from components.get_price_action import get_price
from components.finam_balance import get_finam_balance, get_finam_positions


class TradingEngine:
    def __init__(self, pair: str, stop_loss: float, url:str):
        """1. Поступление торговой пары и стоп-лосса"""
        self.PERCENT_RISK = 0.01  # 1% риска на сделку
        self.url = url
        # Проверяем наличие пары в конфигурации
        if pair not in config.TRADING_TIKERS:
            raise ValueError(f"Пара {pair} не найдена в конфигурации")

        self.ticker = config.TRADING_TIKERS[pair]
        self.pair = pair
        self.create_order_file = config.CREATE_ORDER
        self.kil_order_file = config.KIL_ORDER
        # Конфигурация инструмента
        instrument_data = config.INSTRUMENTS[self.pair]

        # Получаем начальную цену
        price_data = get_price()
        if pair not in price_data:
            raise ValueError(f"Цена для пары {pair} не найдена")

        self.entry_price = float(price_data[pair])
        self.initial_stop_loss = float(stop_loss)
        self.stop_loss = float(stop_loss)  # Текущий стоп-лосс (будет двигаться)
        self.cache_price = self.entry_price

        self.step = float(instrument_data['step'])
        self.step_cost = float(instrument_data['step_cost'])
        self.commission_for_limit = float(instrument_data['commission_for_limit'])
        self.commission_for_market = float(instrument_data['commission_for_market'])
        self.commission_for_cliring = float(instrument_data['commission_for_cliring'])
        # 2. Определение направления сделки
        if self.stop_loss > self.entry_price:
            self.direction = "short"
            print(f"Направление: SHORT (стоп-лосс {self.stop_loss} > входа {self.entry_price})")
            self.lot_price = float(instrument_data['lot_price_short'])
        else:
            self.direction = "long"
            print(f"Направление: LONG (стоп-лосс {self.stop_loss} < входа {self.entry_price})")

        self.lot_price = float(instrument_data['lot_price_'+self.direction])
        # Расчет дистанции риска (для объема)
        self.risk_distance = abs(self.entry_price - self.stop_loss)

        # Финансовые переменные
        self.balance: Optional[float] = None
        self.quantity: Optional[int] = None

    async def calculate_position_size(self):
        """Расчет объема для риска 1% от баланса"""
        try:
            # Получаем баланс
            self.balance = await get_finam_balance()
            print(f"Баланс: {self.balance:.2f}₽")

            # Максимум по маржинальным требованиям
            max_lots_by_balance = int(self.balance // self.lot_price)

            # Риск на 1 лот
            steps = self.risk_distance / self.step
            risk_per_lot = steps * self.step_cost

            # Рассчитываем количество лотов для 1% риска
            risk_amount = self.balance * self.PERCENT_RISK

            if risk_per_lot > 0:
                self.quantity = int(risk_amount // risk_per_lot)
            else:
                self.quantity = 1

            # Ограничения
            if self.quantity > max_lots_by_balance:
                self.quantity = max_lots_by_balance
            elif self.quantity < 1:
                self.quantity = 1

            print(f"Объем: {self.quantity} лотов")
            print(f"Риск на сделку: {risk_amount:.2f}₽")

            # Теперь, когда self.quantity рассчитан, можно вызвать calculate_limit_position()

            self.commission = (self.commission_for_limit + self.commission_for_market)*self.quantity + self.commission_for_cliring
            step_prices = self.get_decimal_places(self.step)

            if step_prices == 0:
                self.entry_price = round(self.entry_price)
                self.stop_loss = round(self.stop_loss)
            else:
                self.entry_price = round(self.entry_price, step_prices)
                self.stop_loss = round(self.stop_loss, step_prices)

            return True

        except Exception as e:
            print(f"Ошибка расчета объема: {e}")
            return False
    def calculate_limit_position(self):  # Исправлено название метода
        """Расчет лимитных цен для тейк-профитов"""
        try:
            # 7. Лимитка на 1:1
            if self.direction == "long":
                self.limit_price_2 = self.entry_price + self.risk_distance  # RR 1:1
                self.limit_price_1 = self.limit_price_2 - (self.risk_distance/4)  # Исправлено: деление на 4, а не целочисленное деление
            else:
                self.limit_price_2 = self.entry_price - self.risk_distance  # RR 1:1
                self.limit_price_1 = self.limit_price_2 + (self.risk_distance/4)  # Исправлено: деление на 4, а не целочисленное деление

            if self.quantity > 1:
                # Здесь вы хотите разделить объем на 60/40
                self.limit_price_1_qnt = math.floor(self.quantity * 60 / 100)
                self.limit_price_2_qnt = self.quantity - self.limit_price_1_qnt
            else:
                self.limit_price_1_qnt = self.quantity
                self.limit_price_2_qnt = 0

        except Exception as e:
            print(f"Ошибка расчета лимитных позиций: {e}")
            return False

    def get_operation(self, is_entry: bool) -> str:
        """Определение операции"""
        if self.direction == "long":
            return 'B' if is_entry else 'S'
        else:
            return 'S' if is_entry else 'B'

    def get_decimal_places(self, step):
        """Получение количества знаков после запятой для шага цены"""
        # Если шаг целый (1, 2, 3 и т.д.)
        if step == int(step):
            return 0

        # Преобразуем в строку для анализа
        step_str = str(step)

        # Если шаг в формате 0.1, 0.01, 0.001 и т.д.
        if '.' in step_str:
            decimal_part = step_str.split('.')[1]
            decimal_part = decimal_part.rstrip('0')
            return len(decimal_part)

        return 0

    def create_order(self, ticker: str, operation: str, order_type: str,
                    quantity: int, price: float) -> None:
        """Создание ордера"""
        with open(self.create_order_file, 'w', encoding='utf-8') as file:
            if self.get_decimal_places(self.step) == 0:
                file.write(f'DEAL:{ticker}/{operation}/{order_type}/{quantity}/{round(price)}')
            else:
                file.write(f'DEAL:{ticker}/{operation}/{order_type}/{quantity}/{round(price, self.get_decimal_places(self.step))}')

    def kill_order(self, ticker: str) -> None:
        """Отмена ордера"""
        with open(self.kil_order_file, 'w', encoding='utf-8') as file:
            file.write(ticker)

    def get_current_price(self) -> float:
        """Получение текущей цены"""
        price_data = get_price()
        return float(price_data[self.pair])

    def check_stop_loss_hit(self, current_price: float) -> bool:
        """Проверка срабатывания стоп-лосса"""
        if self.direction == "long":
            return current_price < self.stop_loss
        else:  # SHORT
            return current_price > self.stop_loss

    def check_limit_hit(self, current_price: float) -> bool:
        """Проверка срабатывания лимитки"""
        if self.direction == "long":
            if current_price >= self.limit_price_1 and current_price <= self.limit_price_2:
                return self.limit_price_1
            elif current_price >= self.limit_price_2:
                return self.limit_price_2
            else:
                return False
        else:  # SHORT
            if current_price <= self.limit_price_1 and current_price >= self.limit_price_2:
                return self.limit_price_1
            elif current_price <= self.limit_price_2:
                return self.limit_price_2
            else:
                return False

    async def check_and_create_position(self):
        entry_operation = self.get_operation(is_entry=True)
        original_quantity = self.quantity  # Сохраняем исходное количество
        while True:

            # Маркет ордер на вход
            self.create_order(self.ticker, entry_operation, 'M', original_quantity, 0.0)

            # Ждем немного дольше для исполнения маркет-ордера
            await asyncio.sleep(3)

            # Проверяем позиции
            positions = await get_finam_positions()
            # Ищем нашу позицию
            found_position = None
            for position in positions:
                # Более надежный способ проверки тикера
                if position.symbol[:-5] == self.ticker and position.quantity.value != '0.0':
                    print(position.quantity)
                    found_position = position
                    print(f"Найдена позиция: {position.symbol}")
                    self.quantity=original_quantity
                    return True
            else:
                print("Позиция не найдена после маркет-ордера")
                original_quantity -= 1
                if original_quantity == 0:
                    return False
    def send_rezult_message(self, status):
        if status:
            order = 'Прибыль'
        else:
            order = 'Убыток'
        message = (
            f'*{self.pair}*\n\nКоментарий\n'
            f'━━━━━━━━━━━━━━━\n'
            f'*{order}'
            f'\n\n                [Автор](https://t.me/Taidy_Pai) \\|\\ [YouTube](https://youtube.com/@afterr_rain?si=kxY2c9PxOn1wv2Ep)'

        )
        send_tg_message(message)
    async def execute_trading_strategy(self):
        """Основная стратегия - исправленная версия"""
        print(f"\n=== СДЕЛКА {self.pair} ===")

        # try:
        # Рассчитываем объем
        if not await self.calculate_position_size():
            print("Ошибка расчета объема")
            return False

        # Проверяем создание позиции
        if not await self.check_and_create_position():
            print("Не удалось создать позицию, завершаем сделку")
            send_tg_message(f"Не удалось создать позицию по {self.pair}")
            return False

        else:
            exit_operation = self.get_operation(is_entry=False)
            self.calculate_limit_position()
            if self.limit_price_2_qnt > 1:
                self.create_order(self.ticker, exit_operation, 'L', self.limit_price_1_qnt, abs(self.limit_price_1))
                await asyncio.sleep(5)
                self.create_order(self.ticker, exit_operation, 'L', self.limit_price_2_qnt, abs(self.limit_price_2))

                commission_profit = self.commission_for_limit*self.limit_price_1_qnt+self.commission_for_limit*self.limit_price_2_qnt+self.commission_for_market*self.quantity+self.commission_for_cliring
                profit_take_1 = abs(self.limit_price_1 - self.entry_price)/self.step*self.step_cost*self.limit_price_1_qnt
                profit_take_2 = abs(self.limit_price_2 - self.entry_price)/self.step*self.step_cost*self.limit_price_2_qnt
                full_profit = profit_take_1 + profit_take_2+ commission_profit
                loss =abs(self.limit_price_2 - self.entry_price)/self.step*self.step_cost*self.quantity+self.commission_for_market*self.quantity*2+self.commission_for_cliring
            else:
                self.create_order(self.ticker, exit_operation, 'L', self.quantity, abs(self.limit_price_2))
                commission_profit = self.commission_for_limit*self.quantity+self.commission_for_market*self.quantity+self.commission_for_cliring
                profit_take_1 = abs(self.limit_price_2 - self.entry_price)/self.step*self.step_cost*self.quantity
                full_profit = profit_take_1 + commission_profit
                commission_loss = (self.commission_for_market*self.quantity*2)+self.commission_for_cliring
                loss = profit_take_1 + commission_loss
            # Отправляем сообщение
            message = (
                f'\n*✅ Открыта позиция / {self.pair} *\n'
                f'═══════ ⋆*$*⋆ ═══════\n'
                f'  ├──  Объем: {self.quantity} шт\n'
                f'  ├─→  *Прибыль:* {round(full_profit, 1)}₽\n'
                f'  ├─→  *Убыток:* {round(loss, 1)}₽\n'
                f'  └─→  Клиринг: {self.commission_for_cliring}\n')
            send_tg_message(message)

            # Мониторинг позиции
            while True:
                current_price = self.get_current_price()

                # Проверка стоп-лосса
                if self.check_stop_loss_hit(current_price):
                    # Отменяем лимитный ордер
                    self.kill_order(self.ticker)

                    # Исполняем стоп по рынку
                    exit_operation = self.get_operation(is_entry=False)
                    self.create_order(self.ticker, exit_operation, 'M', self.quantity, 0.0)
                    self.send_rezult_message(False)
                    return False

                # Проверка лимитки
                if self.check_limit_hit(current_price) == self.limit_price_1:
                    self.stop_loss = self.entry_price
                    send_tg_message(f"✅ *TakeProfit_1* Ваш StopLoss перемещен в безуыбток")
                elif self.check_limit_hit(current_price) == self.limit_price_2:
                    self.send_rezult_message(True)
                    return True

                await asyncio.sleep(1)

        # except Exception as e:
        #     print(f"Ошибка: {e}")
        #     send_tg_message(f"Ошибка в сделке {self.pair}: {str(e)}")
        #     return False

        return True