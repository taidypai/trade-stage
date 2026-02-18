# backend/services/trading_engine/trade_manager.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
from typing import Dict, Optional
from backend.components.logger import logger
from backend.services.trade_engine.engine import TradeEngine

class TradeManager:
    """Менеджер для управления торговым движком из бота"""

    _instance = None
    _engine: Optional[TradeEngine] = None
    _task: Optional[asyncio.Task] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def start_engine(self):
        """Запускает торговый движок"""
        if self._engine is None:
            self._engine = TradeEngine()
            await self._engine.start()
            logger.info("TradeEngine запущен через TradeManager")
            return True
        return False

    async def stop_engine(self):
        """Останавливает торговый движок"""
        if self._engine:
            await self._engine.stop()
            self._engine = None
            logger.info("TradeEngine остановлен через TradeManager")

    async def open_position(self, ticker: str, direction: str, stop_loss: float) -> bool:
        """Открывает позицию через движок"""
        if not self._engine:
            await self.start_engine()

        return await self._engine.open_position(ticker, direction, stop_loss)

    async def get_positions(self):
        """Получает список открытых позиций"""
        if not self._engine:
            return []
        return await self._engine.get_positions()

    async def close_position(self, position_id: str):
        """Закрывает конкретную позицию"""
        if self._engine:
            await self._engine.close_position(position_id)

    @property
    def is_running(self) -> bool:
        return self._engine is not None and self._engine.running

# Создаем глобальный экземпляр
trade_manager = TradeManager()