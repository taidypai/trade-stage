# time_service.py
import asyncio
from datetime import datetime, timedelta
import pytz

class TimeService:
    def __init__(self):
        self.timeframe_minutes = {
            '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }
        self.trading_start_hour = 8  # 8:00 утра
        self.trading_end_hour = 0    # 00:00 (полночь)

    async def get_time_to_candle_close(self, timeframe):
        """Время до закрытия свечи для таймфрейма"""
        now = datetime.now()
        tf_minutes = {'5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440}

        minutes = tf_minutes.get(timeframe, 60)
        total_minutes = now.hour * 60 + now.minute
        next_candle = ((total_minutes // minutes) + 1) * minutes

        # Обрабатываем случай, когда next_candle >= 1440 (24 часа)
        if next_candle >= 1440:
            # Переход на следующий день
            next_run = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            next_run += timedelta(minutes=next_candle - 1440)
        else:
            # Остаемся в текущих сутках
            next_hour = next_candle // 60
            next_minute = next_candle % 60
            next_run = now.replace(hour=next_hour, minute=next_minute, second=0, microsecond=0)

            # Если время уже прошло, добавляем день
            if next_run < now:
                next_run += timedelta(days=1)
        return float((next_run - now).total_seconds())

    def get_time_until_trading_start(self):
        """Возвращает время до начала торговой сессии (8:00)"""
        now = datetime.now()
        current_hour = now.hour
        current_minute = now.minute
        current_second = now.second

        # Если сейчас ночное время (00:00 - 8:00)
        if current_hour < self.trading_start_hour:
            # До начала торгов осталось
            hours_left = self.trading_start_hour - current_hour - 1
            minutes_left = 60 - current_minute - 1
            seconds_left = 60 - current_second
            return f"{hours_left:02d}:{minutes_left:02d}:{seconds_left:02d}"
        else:
            # Уже торговая сессия
            return None

    def wait_until_trading_time(self):
        """Блокирующее ожидание до начала торгового времени"""
        while not self.is_trading_time():
            time_until_start = self.get_time_until_trading_start()
            if time_until_start:
                print(f"💤 Ожидание начала торгов. До старта: {time_until_start}")
                time.sleep(60)  # Проверяем каждую минуту
            else:
                break

    def get_time_until_midnight(self):
        """Возвращает время до конца торговой сессии (00:00)"""
        now = datetime.now()
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        time_left = midnight - now

        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        seconds = time_left.seconds % 60

        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    async def format_time_remaining(self, seconds):
        """Форматирует время в читаемый вид"""
        seconds = int(seconds)
        if seconds >= 3600:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        elif seconds >= 60:
            minutes = seconds // 60
            secs = seconds % 60
            return f"{minutes:02d}:{secs:02d}"
        else:
            return f"{seconds:02d}с"

    def is_trading_time(self):
        """Проверяет торговое время 8:00-00:00 по часам"""
        current_hour = datetime.now().hour
        return 8 <= current_hour <= 23

# Глобальный экземпляр
timeservice = TimeService()