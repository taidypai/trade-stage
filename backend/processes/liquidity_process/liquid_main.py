# liquid_main.py C:\Users\Вадим\Documents\python\trade-brain-main\liquidity_process

import asyncio
import sys
sys.path.append(r"C:\Users\Вадим\Documents\python\trade-brain-main")
from liquidity_process import detect_liquid
import config

async def run_timeframe(tf):
    """Запускает мониторинг для одного таймфрейма"""
    detect = detect_liquid.Detector_liquid(tf)
    await detect.start_detection()

async def liquidity_main():
    # Запускаем все таймфреймы параллельно
    tasks = [run_timeframe(tf) for tf in config.TIMEFRAMES]

    print("Все процессы LIQ запущены.")

    # Запускаем и ждем бесконечно
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(liquidity_main())
    except KeyboardInterrupt:
        print("Программа остановлена пользователем")