import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

import requests
import asyncio
import os
import sys
from collections import deque
from datetime import datetime
import config
from components.time_service import TimeService
from components.telegram_message import send_tg_message
from components.get_price_action import get_price

class Detector_impuls:
    def __init__(self, timeframe):
        # Используем те же названия пар, что и в QUIK
        self.trading_pairs = config.TRADING_TIKERS
        self.candles = {}
        self.timeframe = timeframe
        self.time_service = TimeService()
        # Храним историю импульсных свечей для каждой пары отдельно
        self.impuls_history = {}

        # Инициализируем структуры данных для каждой пары
        for pair in self.trading_pairs:
            self.candles[pair] = {
                'open': None,
                'high': None,
                'low': None,
                'close': None
            }
            self.impuls_history[pair] = deque(maxlen=4)  # храним последние 4 свечи

    def update_candle(self, pair, current_price):
        """Обновляет свечу новым значением цены"""
        candle = self.candles[pair]

        # Если это первое значение - инициализируем свечу
        if candle['open'] is None:
            candle['open'] = current_price
            candle['close'] = current_price
            candle['high'] = current_price
            candle['low'] = current_price
            return

        # Обновляем закрытие (текущая цена)
        candle['close'] = current_price

        # Обновляем хай и лоу
        if current_price > candle['high']:
            candle['high'] = current_price
        if current_price < candle['low']:
            candle['low'] = current_price

    def check_impuls_down(self, pair):
        """Проверяет импульс вниз для пары"""
        candle = self.candles[pair]

        # Проверяем, что все значения инициализированы
        if any(v is None for v in [candle['open'], candle['high'], candle['low'], candle['close']]):
            return False

        # Определяем красную свечу (импульс вниз): закрытие ниже открытия
        is_red_candle = candle['close'] < candle['open']

        # Добавляем результат в историю
        self.impuls_history[pair].append(1 if is_red_candle else 0)

        # Если в истории накопилось 4 свечи, проверяем условие
        if len(self.impuls_history[pair]) == 4:
            # Проверяем, что 3 или 4 из последних 4 свечей - красные
            red_count = sum(self.impuls_history[pair])
            return red_count >= 3

        return False

    def reset_candle(self, pair):
        """Сбрасывает свечу для нового периода"""
        self.candles[pair] = {
            'open': None,
            'high': None,
            'low': None,
            'close': None
        }

    async def start_detection(self):
        """Основной цикл для всех пар на указанном таймфрейме"""
        # Ждем начало новой свечи
        wait_time = await self.time_service.get_time_to_candle_close(self.timeframe)
        if wait_time > 0:
            formatted_time = await self.time_service.format_time_remaining(wait_time)
            await asyncio.sleep(wait_time)

        while True:
            # Получаем начальную цену (открытие новой свечи)
            start_prices = get_price()

            # Инициализируем свечи
            for pair in self.trading_pairs:
                if pair in start_prices:
                    self.candles[pair]['open'] = start_prices[pair]
                    self.candles[pair]['close'] = start_prices[pair]
                    self.candles[pair]['high'] = start_prices[pair]
                    self.candles[pair]['low'] = start_prices[pair]

            # Основной цикл обновления в течение свечи
            while True:
                # Получаем текущие цены
                current_prices = get_price()

                # Обновляем свечи для каждой пары
                for pair in self.trading_pairs:
                    if pair in current_prices:
                        self.update_candle(pair, current_prices[pair])

                # Проверяем, не закончилась ли текущая свеча
                time_remaining = await self.time_service.get_time_to_candle_close(self.timeframe)

                # Если до конца свечи осталось меньше 1 секунды - завершаем свечу
                if time_remaining <= 1:
                    # Проверяем импульс для каждой пары
                    for pair in self.trading_pairs:
                        if pair in current_prices:
                            if self.check_impuls_down(pair):
                                message = f"Импульс вниз ✓ {pair} {self.timeframe}"
                                print(message)
                                send_tg_message(message)

                    # for pair in self.trading_pairs:
                    #     if self.impuls_history[pair]:
                    #         print(f'  {pair}: {list(self.impuls_history[pair])}')

                    # Сбрасываем свечи для следующего периода
                    for pair in self.trading_pairs:
                        self.reset_candle(pair)

                    # Ждем 1 секунду перед следующим обновлением
                    await asyncio.sleep(1)
                    break  # Выходим из внутреннего цикла для начала новой свечи

                # Ждем 1 секунду перед следующим обновлением
                await asyncio.sleep(1)