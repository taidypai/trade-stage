import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

import asyncio
from order_block_process import detect_order_block
import config

async def run_timeframe(tf):
    """Запускает мониторинг для одного таймфрейма"""
    detect = detect_order_block.Detector_order_block(tf)
    await detect.start_detection()

async def ob_main_main():
    # Запускаем все таймфреймы параллельно
    tasks = [run_timeframe(tf) for tf in config.TIMEFRAMES]

    print("Все процессы ORB запущены.")

    # Запускаем и ждем бесконечно
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(ob_main_main_main())
    except KeyboardInterrupt:
        print("Программа остановлена пользователем")