import requests
import asyncio
import os
import sys
from datetime import datetime

sys.path.append(r"C:\Users\Вадим\Documents\python\trade-brain-main")
import config
from components.time_service import timeservice
from components.telegram_message import send_tg_message
from components.get_price_action import get_price
from trading_engine import trade_main

class Detector_order_block:
    def __init__(self, timeframe):
        # Используем те же названия пар, что и в QUIK
        self.trading_pairs = config.TRADING_TIKERS
        self.current_candle = {}  # Текущая формирующаяся свеча
        self.candle_history = {}  # История свечей (последние 2 свечи)
        self.work_file = config.ORDER_MANAGER
        self.timeframe = timeframe
        self.time_service = timeservice
        self.INSTRUMENTS = config.INSTRUMENTS

        # Инициализируем структуры для каждой пары
        for pair in self.trading_pairs:
            self.current_candle[pair] = {
                'open': None,
                'high': None,
                'low': None,
                'close': None,
                'is_bullish': None
            }
            self.candle_history[pair] = []

    def update_candle(self, pair, current_price):
        """Обновляет текущую свечу новым значением цены"""
        candle = self.current_candle[pair]

        # Если это первое значение - инициализируем свечу
        if candle['open'] is None:
            candle['open'] = current_price
            candle['high'] = current_price
            candle['low'] = current_price
            candle['close'] = current_price
            return

        # Обновляем максимум и минимум
        if current_price > candle['high']:
            candle['high'] = current_price
        if current_price < candle['low']:
            candle['low'] = current_price

        # Обновляем закрытие (текущая цена)
        candle['close'] = current_price
        # Определяем тип свечи (бычья/медвежья)
        candle['is_bullish'] = candle['close'] > candle['open']

    def finalize_candle(self, pair):
        """Завершает формирование свечи и добавляет в историю"""
        if self.current_candle[pair]['open'] is not None:
            # Сохраняем завершенную свечу
            completed_candle = self.current_candle[pair].copy()

            # Добавляем в историю (храним максимум 2 свечи)
            self.candle_history[pair].append(completed_candle)
            if len(self.candle_history[pair]) > 2:
                self.candle_history[pair].pop(0)

            # Сбрасываем текущую свечу
            self.reset_current_candle(pair)

    def reset_current_candle(self, pair):
        """Сбрасывает текущую свечу для нового периода"""
        self.current_candle[pair] = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'is_bullish': None
        }

    def wait_deal(pair, open_deal, stop_loss, direction):
        while True:
            current_price = get_price()
            if direction == "BULLISH":
                if current_price <= open_deal:
                    #trade_main.start_trade_main(pair, stop_loss)
                    send_tg_message(f'Сделка состоялась ORB {pair} [{self.timeframe}]')
                    break
            else:
                if current_price >= open_deal:
                    send_tg_message(f'Сделка состоялась ORB {pair} [{self.timeframe}]')
                    #trade_main.start_trade_main(pair, stop_loss)
                    break
        return True

    def check_order_block(self, pair):
        """Проверяет наличие ордерблока для пары на основе последних 2 свечей"""
        # Проверяем, есть ли 2 завершенные свечи
        if len(self.candle_history[pair]) < 2:
            return False

        # Получаем свечи (предпоследняя и последняя)
        first_candle = self.candle_history[pair][-2]  # Предпоследняя свеча
        second_candle = self.candle_history[pair][-1]  # Последняя свеча

        # 1. Проверяем, что свечи разного цвета
        if first_candle['is_bullish'] == second_candle['is_bullish']:
            return False

        first_candle_size = abs(first_candle['close'] - first_candle['open'])
        second_candle_size = abs(first_candle['close'] - first_candle['open'])
        if first_candle_size <= 0:
            return False

        # Проверяем условие: размер второй свечи >= 2 * размер первой свечи
        if second_candle_size >= 2 * first_candle_size:

            if not first_candle['is_bullish'] and second_candle['is_bullish']:
                direction = "BULLISH"
                # Для бычьего ордерблока важна зона в районе хая первой свечи
            else:
                direction = "BEARISH"
                # Для медвежьего ордерблока важна зона в районе лоу первой свечи

            # Вычисляем дополнительные параметры для торговли
            stop_loss = None
            if direction == "BULLISH":
                # Для бычьего ордерблока стоп ниже минимума второй свечи
                open_deal = second_candle['close']-second_candle_size//2
                stop_loss = second_candle['low'] - (second_candle['high'] - second_candle['low']) - self.INSTRUMENTS[pair]['step']
            else:
                # Для медвежьего ордерблока стоп выше максимума второй свечи
                open_deal = second_candle['close']+second_candle_size//2
                stop_loss = second_candle['high'] + (second_candle['high'] - second_candle['low']) + self.INSTRUMENTS[pair]['step']
            return True

        return False

    async def analyze_all_pairs(self,  time_remaining):
        """Асинхронный метод анализа всех пар на наличие ордерблоков"""
        data = []
        with open(self.work_file, 'r') as file:
            content = file.readlines()
            if content:
                content = content[0].split('/')
                data.append(content[0])
                content = content[1].split(':')
                for i in content:
                    data.append(i)

        order_blocks_found = []

        for pair in self.trading_pairs:
            order_block = self.check_order_block(pair)
            if order_block:
                order_blocks_found.append(order_block)
                message = f"✓ ОРДЕРБЛОК {pair} {self.timeframe}"
                send_tg_message(message)
            if data:
                if data[0] == 'ORB' and data[1] == pair and data[2] == self.timeframe:
                    if time_remaining <= 3:
                        send_tg_message(f'Сделка ORB одобрена {pair} [{self.timeframe}]')
                        wait_deal(pair, open_deal, stop_loss, direction)

        # Если не найдено ордерблоков
        if not order_blocks_found:
            print(f"[{self.timeframe}] Ордерблоки не найдены")

        # Очищаем файл после анализа
        with open(self.work_file, 'w') as file:
            file.write('')

    async def start_detection(self):
        """Основной цикл для всех пар на указанном таймфрейме"""
        # Ждем начало новой свечи
        wait_time = await self.time_service.get_time_to_candle_close(self.timeframe)
        if wait_time > 0:
            formatted_time = await self.time_service.format_time_remaining(wait_time)
            print(f"[{self.timeframe}] Ждем начало свечи: {formatted_time}")
            await asyncio.sleep(wait_time)

        # Получаем начальную цену (открытие новой свечи)
        start_prices = get_price()

        # Инициализируем текущие свечи
        for pair in self.trading_pairs:
            if pair in start_prices:
                self.current_candle[pair]['open'] = start_prices[pair]
                self.current_candle[pair]['high'] = start_prices[pair]
                self.current_candle[pair]['low'] = start_prices[pair]
                self.current_candle[pair]['close'] = start_prices[pair]
                self.current_candle[pair]['is_bullish'] = None  # Пока не определили

        # Основной цикл обновления в течение свечи
        while True:
            # Получаем текущие цены
            current_prices = get_price()

            # Обновляем текущие свечи для каждой пары
            for pair in self.trading_pairs:
                if pair in current_prices:
                    self.update_candle(pair, current_prices[pair])

            # Проверяем, не закончилась ли текущая свеча
            time_remaining = await self.time_service.get_time_to_candle_close(self.timeframe)

            # Если до конца свечи осталось мало времени - завершаем свечу
            if (time_remaining <= 30 and time_remaining >= 29) or (time_remaining >= 2 and time_remaining <= 3):
                # Завершаем свечи для всех пар
                for pair in self.trading_pairs:
                    self.finalize_candle(pair)

                # Вызываем асинхронный анализ на наличие ордерблоков
                await self.analyze_all_pairs(time_remaining)

                # Ждем начало новой свечи
                await asyncio.sleep(1)

                # Получаем новые начальные цены
                start_prices = get_price()

                # Инициализируем новые свечи
                for pair in self.trading_pairs:
                    if pair in start_prices:
                        self.current_candle[pair]['open'] = start_prices[pair]
                        self.current_candle[pair]['high'] = start_prices[pair]
                        self.current_candle[pair]['low'] = start_prices[pair]
                        self.current_candle[pair]['close'] = start_prices[pair]

            await asyncio.sleep(1)


# Пример запуска
if __name__ == "__main__":
    detector = Detector_order_block("5m")
    asyncio.run(detector.start_detection())