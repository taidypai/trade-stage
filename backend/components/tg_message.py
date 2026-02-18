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

# Экранирует специальные символы для MarkdownV2
def escape_markdown(text):
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
    escaped_text = ''
    for char in text:
        if char in special_chars:
            escaped_text += special_chars[char]
        else:
            escaped_text += char

    return escaped_text
# Оправка сообщения в Telegram
async def send_tg_message(message_text, parse_mode="MarkdownV2"):
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
        # Не задаем вопросы так надо
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, json=data, timeout=10) as response:
                if response.status == 200:
                    return True
                else:
                    error_text = await response.text()
                    logger.error(f"✗ Ошибка отправки сообщения в Telegram {response.status}: {error_text}")
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


if __name__ == "__main__":
    async def main():
        await send_message_main()

    asyncio.run(main())