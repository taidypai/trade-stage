import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

import requests
import asyncio
import os
from datetime import datetime
import config
from components.time_service import timeservice
from components.telegram_message import send_tg_message
from components.get_price_action import get_price
from trading_engine import trade_main

class Detector_liquid:
    def __init__(self, timeframe):
        # Используем те же названия пар, что и в QUIK
        self.trading_pairs = config.TRADING_TIKERS
        self.candles = {}
        self.work_file = config.ORDER_MANAGER
        self.timeframe = timeframe
        self.time_service = timeservice
        # Создаем свечи для каждой пары
        for pair in self.trading_pairs:
            self.candles[pair] = {
                'open': None,
                'high': None,
                'low': None,
                'close': None
            }

    def update_candle(self, pair, current_price):
        """Обновляет свечу новым значением цены"""
        candle = self.candles[pair]

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

    def check_liquidity_removal(self, pair):
        """Проверяет снятие ликвидности для пары"""
        candle = self.candles[pair]

        # Проверяем, что все значения инициализированы
        if any(v is None for v in [candle['open'], candle['high'], candle['low'], candle['close']]):
            return False

        # Вычисляем тело свечи
        body_size = abs(candle['close'] - candle['open'])

        # Вычисляем нижний фитиль
        if candle['close'] > candle['open']:  # Бычья свеча
            lower_wick = candle['open'] - candle['low']
        else:  # Медвежья свеча
            lower_wick = candle['close'] - candle['low']

        if candle['close'] > candle['open']:  # Бычья свеча
            high_wick = candle['high'] - candle['close']
        else:  # Медвежья свеча
            high_wick = candle['high'] - candle['open']

        # Проверяем условие: фитиль > тела свечи в 2 раза
        # И нижний фитиль должен быть положительным (> 0)
        if body_size > 0 and lower_wick > 0 and high_wick > 0:
            if (lower_wick >= 2 * body_size and  high_wick < lower_wick) or \
               (high_wick >= 2 * body_size and lower_wick < high_wick):
                if high_wick > lower_wick:
                    return candle['high']
                else:
                    return candle['low']

        return False

    async def analyze_all_pairs(self, time_remaining):
        """Асинхронный метод анализа всех пар"""
        for pair in self.trading_pairs:
            stop_loss = self.check_liquidity_removal(pair)
            if stop_loss:  # Проверяем снятие ликвидности для текущей пары
                candle = self.candles[pair]
                message = f"✓ {pair} {self.timeframe}"
                # Отправляем сообщение синхронно или асинхронно в зависимости от реализации send_tg_message
                send_tg_message(message)

        # Очищаем файл после анализа
        with open(self.work_file, 'w') as file:
            file.write('')

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

        # Получаем начальную цену (открытие новой свечи)
        start_prices = get_price()

        # Инициализируем свечи
        for pair in self.trading_pairs:
            if pair in start_prices:
                self.candles[pair]['open'] = start_prices[pair]
                self.candles[pair]['high'] = start_prices[pair]
                self.candles[pair]['low'] = start_prices[pair]
                self.candles[pair]['close'] = start_prices[pair]

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

            # Если до конца свечи осталось меньше 2 секунд - завершаем свечу
            if (time_remaining <= 30 and time_remaining >= 29) or (time_remaining >= 2 and time_remaining <= 3):
                # Вызываем асинхронный анализ
                await self.analyze_all_pairs(time_remaining)

                # Сбрасываем свечи для следующего периода
                for pair in self.trading_pairs:
                    self.reset_candle(pair)

            await asyncio.sleep(1)


# Пример запуска
if __name__ == "__main__":
    detector = Detector_liquid("5m")
    asyncio.run(detector.start_detection())