# backend/components/tg_message.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт файлов
from settings import backend_config as config

# Импорт библиотек
import asyncio
import aiohttp
import re
import ssl
import certifi

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
CHAT_ID = config.TELEGRAM_CHAT_ID

def escape_markdown(text):
    """
    Экранирует специальные символы для MarkdownV2
    """
    # Список всех символов, которые нужно экранировать в MarkdownV2
    special_chars = {
        '_': r'\_',
        '[': r'\[',
        ']': r'\]',
        '(': r'\(',
        ')': r'\)',
        '~': r'\~',
        '`': r'\`',
        '>': r'\>',
        '#': r'\#',
        '+': r'\+',
        '-': r'\-',
        '=': r'\=',
        '|': r'\|',
        '{': r'\{',
        '}': r'\}',
        '.': r'\.',
        '!': r'\!'
    }

    # Экранируем все спецсимволы
    escaped_text = ''
    for char in text:
        if char in special_chars:
            escaped_text += special_chars[char]
        else:
            escaped_text += char

    return escaped_text

async def send_tg_message(message_text, parse_mode="MarkdownV2"):
    """
    Асинхронная отправка сообщения в Telegram
    """
    original_text = message_text  # Сохраняем для лога

    # Если используется Markdown, экранируем спецсимволы
    if parse_mode == "MarkdownV2":
        message_text = escape_markdown(message_text)
        logger.debug(f"Оригинальный текст: {original_text}")
        logger.debug(f"Экранированный текст: {message_text}")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': message_text,
        'parse_mode': parse_mode
    }

    try:
        # СОЗДАЕМ SSL КОНТЕКСТ С ИСПОЛЬЗОВАНИЕМ CERTIFI
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        # СОЗДАЕМ КОННЕКТОР С SSL КОНТЕКСТОМ
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=data, timeout=10) as response:
                if response.status == 200:
                    logger.info("✓ Сообщение в Telegram отправлено")
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"✗ Ошибка отправки сообщения в Telegram {response.status}: {error_text}")
                    logger.error(f"✗ Текст сообщения: {message_text}")
                    return False
    except asyncio.TimeoutError:
        logger.error("✗ Таймаут при отправке сообщения в Telegram")
        return False
    except aiohttp.ClientError as e:
        logger.error(f"✗ Ошибка подключения к Telegram: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Непредвиденная ошибка: {e}")
        return False

async def send_tg_message_safe(message_text, parse_mode="MarkdownV2", max_retries=3):
    """
    Асинхронная отправка с повторами при ошибке
    """
    for attempt in range(max_retries):
        success = await send_tg_message(message_text, parse_mode)
        if success:
            return True

        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Экспоненциальная задержка: 1, 2, 4 секунды
            logger.warning(f"Повторная попытка через {wait_time}с...")
            await asyncio.sleep(wait_time)

    logger.error(f"✗ Не удалось отправить сообщение после {max_retries} попыток")
    return False

async def send_message_main():
    """
    Асинхронная версия send_message_main
    """
    message = (
                        '*Все системы запущены → /start *'
                    )

    # Используем безопасную отправку с повторами
    await send_tg_message_safe(message)

# Для обратной совместимости (если где-то используется синхронный вызов)
def send_tg_message_sync(message_text, parse_mode="MarkdownV2"):
    """
    Синхронная обертка для обратной совместимости
    """
    async def _send():
        return await send_tg_message(message_text, parse_mode)

    return asyncio.run(_send())

def send_message_main_sync():
    """
    Синхронная обертка для обратной совместимости
    """
    async def _send():
        await send_message_main()

    asyncio.run(_send())


if __name__ == "__main__":
    # Асинхронный запуск для тестирования
    async def main():
        print("Тестирование отправки сообщения...")
        await send_message_main()
        print("Готово!")

    # Настройка логирования для отладки
    import logging
    logging.basicConfig(level=logging.DEBUG)

    asyncio.run(main())