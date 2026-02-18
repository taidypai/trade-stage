import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

# Импорт логера
from components.logger import logger

# Импорты файлов
from services.get_price_service import run_service as run_price

# Импорт библиотек
import multiprocessing

# Словарь всех сервисов
SERVICES = {
    'price': run_price,
}

def run_all_services():
    """Запуск всех сервисов в отдельных процессах"""
    processes = []

    for service_name, service_func in SERVICES.items():
        logger.info(f"Запуск сервиса: {service_name}")
        p = multiprocessing.Process(
            target=service_func,
            name=f"{service_name}_service"
        )
        processes.append(p)
        p.start()

    logger.info(f"Запущено сервисов: {len(processes)}")
    return processes

def run_service_by_name(service_name, **kwargs):
    """Запуск конкретного сервиса"""
    if service_name in SERVICES:
        logger.info(f"Запуск сервиса: {service_name}")
        return SERVICES[service_name](**kwargs)
    else:
        logger.error(f"Сервис {service_name} не найден")
        return None

def stop_all_services(processes):
    """Остановка всех сервисов"""
    logger.info("Остановка всех сервисов...")
    for p in processes:
        if p.is_alive():
            p.terminate()
            p.join()
    logger.info("Все сервисы остановлены")

__all__ = ['run_all_services', 'run_service_by_name', 'stop_all_services', 'SERVICES']