import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт файлов
from settings import frontend_config as config

# Импорт библиотек
import requests

BOT_TOKEN = config.TELEGRAM_BOT_TOKEN
CHAT_ID = config.TELEGRAM_CHAT_ID

def send_tg_message(message_text, parse_mode="MarkdownV2"):

    # Если используется Markdown и есть спецсимволы
    if parse_mode in ["MarkdownV2"]:

        # экранирование точек и других спецсимволов
        message_text = message_text.replace('.', '\\.').replace('-', '\\-')

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        'chat_id': CHAT_ID,
        'text': message_text,
        'parse_mode': parse_mode
    }

    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info("Сообщение в Telegram отправлено")
            return True
        else:
            logger.error(f"Ошибка отправки сообщения в Telegram {response.status_code}: {response.text}")
            return False
    except Exception as e:
        logger.error(f"Ошибка подключения к Telegram: {e}")
        return False


def send_message_main():
    message = (
            f'*GLDRUBF*\n\nКоментарий\n'
            f'━━━━━━━━━━━━━━━\n'
            f'*Прибыль*'
            f'\n\n                [Автор](https://t.me/Taidy_Pai) \\|\\ [YouTube](https://youtube.com/@afterr_rain?si=kxY2c9PxOn1wv2Ep)'

        )
    send_tg_message(message)

if __name__ == "__main__":
   send_message_main()