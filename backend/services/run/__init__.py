""" python backend/services/run_service/__init__.py """
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")

# Импорт логера
from components.logger import logger

# Импорты файлов
from services.get_price import run_service

# Импорт библиотек
import multiprocessing
import time
import signal
import os

# Словарь всех сервисов
SERVICES = {
    'price': run_service,
    # Добавьте другие сервисы по мере необходимости
    # 'another_service': run_another_service,
}

# Глобальный список процессов для отслеживания
active_processes = []

def run_all_services():
    """Запуск всех сервисов в отдельных процессах"""
    global active_processes

    processes = []

    if not SERVICES:
        logger.info("Нет сервисов для запуска")
        return processes

    for service_name, service_func in SERVICES.items():
        try:
            logger.info(f"▶️ Запуск сервиса: {service_name}")
            p = multiprocessing.Process(
                target=run_service_wrapper,
                args=(service_name, service_func),
                name=f"{service_name}_service",
                daemon=False  # Важно: daemon=False для дочерних процессов
            )
            processes.append(p)
            p.start()
            logger.info(f"  └── PID: {p.pid}")

            # Небольшая задержка между запусками сервисов
            time.sleep(1)

        except Exception as e:
            logger.error(f"Ошибка запуска сервиса {service_name}: {e}")

    logger.info(f"✅ Запущено сервисов: {len(processes)} из {len(SERVICES)}")

    # Сохраняем в глобальный список
    active_processes.extend(processes)

    return processes

"""Обертка для запуска сервиса с обработкой исключений"""
def run_service_wrapper(service_name: str, service_func):
    try:
        logger.info(f"Сервис {service_name} запущен в процессе {os.getpid()}")
        service_func()
    except KeyboardInterrupt:
        logger.info(f"Сервис {service_name} получил сигнал остановки")
    except Exception as e:
        logger.error(f"Сервис {service_name} завершился с ошибкой: {e}")
    finally:
        logger.info(f"Сервис {service_name} завершен")

def stop_all_services(processes=None):
    """Остановка всех сервисов"""
    global active_processes

    if processes is None:
        processes = active_processes

    if not processes:
        logger.info("Нет активных сервисов для остановки")
        return

    logger.info("=" * 50)
    logger.info("🛑 ОСТАНОВКА ВСЕХ СЕРВИСОВ")
    logger.info("=" * 50)

    # Сначала отправляем сигнал завершения всем процессам
    for p in processes:
        if p and p.is_alive():
            logger.info(f"Останавливаю процесс {p.name} (PID: {p.pid})")
            try:
                # Пытаемся завершить процесс мягко
                p.terminate()
            except Exception as e:
                logger.error(f"Ошибка при завершении процесса: {e}")

    # Ждем завершения процессов
    for p in processes:
        if p and p.is_alive():
            logger.info(f"Ожидаю завершения {p.name} (PID: {p.pid})...")
            p.join(timeout=5)  # Ждем не более 5 секунд

            if p.is_alive():
                logger.warning(f"Процесс {p.name} не завершился, принудительно убиваем")
                try:
                    p.kill()  # Принудительное завершение
                    p.join(timeout=2)
                except Exception as e:
                    logger.error(f"Ошибка при kill: {e}")

            # Проверяем финальный статус
            if not p.is_alive():
                logger.info(f"✅ Процесс {p.name} завершен, код: {p.exitcode}")

    # Очищаем список
    processes.clear()
    active_processes = []

    logger.info("✅ Все сервисы остановлены")

def get_services_status():
    """Получение статуса всех сервисов"""
    global active_processes

    status = {}

    for service_name in SERVICES.keys():
        found = False
        for p in active_processes:
            if p and p.name == f"{service_name}_service":
                status[service_name] = {
                    'running': p.is_alive() if p else False,
                    'pid': p.pid if p else None,
                    'exitcode': p.exitcode if p and not p.is_alive() else None
                }
                found = True
                break

        if not found:
            status[service_name] = {
                'running': False,
                'pid': None,
                'exitcode': None
            }

    return status

# Обработчик сигналов для корректного завершения
def signal_handler(signum, frame):
    logger.info(f"📡 Получен сигнал {signum}")
    stop_all_services()

# Регистрируем обработчики сигналов (только в главном процессе)
if __name__ != "__main__":
    try:
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    except (ValueError, AttributeError):
        # Не в главном потоке или не в Windows
        pass

__all__ = [
    'run_all_services',
    'stop_all_services',
    'SERVICES'
]