# logger.py - для ленивых
import logging
import os

# Пути для логов
ERROR_LOG_PATH = r'C:\Users\Вадим\Documents\trade-stage\settings\logs\errors.txt'
INFO_LOG_PATH = r'C:\Users\Вадим\Documents\trade-stage\settings\logs\info.txt'

# Создаем директории, если их нет
os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
os.makedirs(os.path.dirname(INFO_LOG_PATH), exist_ok=True)

# Создаем логгер
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Устанавливаем минимальный уровень для логгера

# Форматтер для сообщений
formatter = logging.Formatter('%(asctime)s - %(funcName)s - %(levelname)s - %(message)s')

# Хендлер для ошибок (ERROR и выше)
error_handler = logging.FileHandler(ERROR_LOG_PATH, encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(formatter)

# Хендлер для информационных сообщений (INFO и выше, но без ERROR)
info_handler = logging.FileHandler(INFO_LOG_PATH, encoding='utf-8')
info_handler.setLevel(logging.INFO)
info_handler.setFormatter(formatter)

# Добавляем хендлеры к логгеру
logger.addHandler(error_handler)
logger.addHandler(info_handler)

# Опционально: добавляем вывод в консоль для отладки
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.DEBUG)
# console_handler.setFormatter(formatter)
# logger.addHandler(console_handler)

# Теперь можно использовать:
# logger.info("Какое-то событие")  # пойдет в info.txt
# logger.error("Какая-то ошибка")  # пойдет и в info.txt, и в errors.txt