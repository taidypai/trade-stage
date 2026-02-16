import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

import time
import signal
from components.logger import logger
from services.run_service import run_all_services, stop_all_services

def main():
    """Главная функция запуска"""
    logger.info("=" * 50)
    logger.info("ЗАПУСК ВСЕХ СЕРВИСОВ")
    logger.info("=" * 50)

    # Запускаем все сервисы
    processes = run_all_services()

    # Обработка сигналов для graceful shutdown
    def signal_handler(signum, frame):
        logger.info(f"Получен сигнал {signum}, завершение работы...")
        stop_all_services(processes)
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Бесконечное ожидание
    try:
        while True:
            # Проверяем, живы ли процессы
            for i, p in enumerate(processes):
                if not p.is_alive():
                    logger.error(f"Процесс {p.name} умер, код: {p.exitcode}")
            time.sleep(5)
    except KeyboardInterrupt:
        stop_all_services(processes)

    logger.info("Все сервисы завершены")

if __name__ == "__main__":
    main()