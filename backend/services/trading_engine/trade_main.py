import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

import asyncio
from components.telegram_message import send_tg_message
from trading_engine.louncher import TradingEngine


async def trade(ticker, stop_loss, url):
    """Асинхронная главная функция"""
    trade_engine = TradingEngine(ticker, stop_loss, url)
    success = await trade_engine.execute_trading_strategy()
    return success


def start_trade_main(ticker, stop_loss, url):
    """Запуск торговли в отдельном event loop (для синхронного вызова)"""
    try:
        # Пытаемся получить текущий event loop
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # Если нет текущего loop, создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Если loop уже запущен, создаем задачу
    if loop.is_running():
        task = loop.create_task(trade(ticker, stop_loss, url))
        return task
    else:
        # Если loop не запущен, запускаем его
        return loop.run_until_complete(trade(ticker, stop_loss, url))


if __name__ == "__main__":
    # Пример использования
    asyncio.run(trade("GLDRUBF", 11011.0, 'https://www.tradingview.com/x/AOCTbQz2/'))