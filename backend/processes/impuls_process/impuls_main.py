import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-brain")

import asyncio
from impuls_process import detect_impuls
import config

async def run_timeframe(tf):
    """Запускает мониторинг для одного таймфрейма"""
    detect = detect_impuls.Detector_impuls(tf)
    await detect.start_detection()

async def impuls_main():
    # Запускаем все таймфреймы параллельно
    tasks = [run_timeframe(tf) for tf in config.TIMEFRAMES]

    print("Все процессы IMP запущены.")

    # Запускаем и ждем бесконечно
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    try:
        asyncio.run(impuls_main())
    except KeyboardInterrupt:
        print("Программа остановлена пользователем")