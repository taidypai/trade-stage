""" python backend/components/transaction.py """
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт файлов
from backend.QuikPy import QuikPy
from settings.backend_config import CLIENT_CODE, ACCOUNT_ID, TRADING_TIKERS
from typing import Optional, Dict, Any

class TRANS_SET:

    def __init__(self, class_code: str):
        self.class_code = class_code
        self.qp = QuikPy()
        self.result = False

    # Отправка заявки
    def place_order(self, ticker: str, operation: str, quantity: int):
        # Формируем транзакцию
        transaction = {
            'TRANS_ID': '1',  # Лучше генерировать уникальный ID
            'CLIENT_CODE': CLIENT_CODE,
            'ACCOUNT': ACCOUNT_ID,
            'ACTION': 'NEW_ORDER',
            'CLASSCODE': self.class_code,
            'SECCODE': ticker,
            'OPERATION': operation,
            'PRICE': '0',
            'QUANTITY': str(quantity),
            'TYPE': 'M'
        }

        try:
            response = self.qp.send_transaction(transaction)

            if response:
                self.result = True
                # Проверяем наличие ошибок в ответе
                if response.get('result_code') == '0' or response.get('success'):
                    if 'order_num' in response:
                        logger.info(f'✅ Заявка №{response["order_num"]} отправлена')
                else:
                    logger.error(f'Ошибка в ответе транзакции: {response}')
                    self.result = False
            else:
                logger.error('Ошибка отправки транзакции (пустой ответ)')
                self.result = False

        except Exception as e:
            logger.error(f'Ошибка при отправке заявки: {e}')
            self.result = False

        return self.result

    # Закрываем соединение
    def close(self):
        if hasattr(self, 'qp'):
            self.qp.close_connection_and_thread()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ==================== ФЬЮЧЕРСЫ ====================
class SPBFUT(TRANS_SET):
    def __init__(self):
        super().__init__(class_code="SPBFUT")

    def buy(self, ticker: str, quantity: int = 1) -> bool:
        """Купить фьючерс"""
        return self.place_order(ticker, "B", quantity)

    def sell(self, ticker: str, quantity: int = 1) -> bool:
        """Продать фьючерс"""
        return self.place_order(ticker, "S", quantity)


# ==================== АКЦИИ ====================
class TQBR(TRANS_SET):
    def __init__(self):
        super().__init__(class_code="TQBR")

    def buy(self, ticker: str, quantity: int = 1) -> bool:
        """Купить акцию"""
        return self.place_order(ticker, "B", quantity)

    def sell(self, ticker: str, quantity: int = 1) -> bool:
        """Продать акцию"""
        return self.place_order(ticker, "S", quantity)

def main():
    # Лучше использовать контекстный менеджер
    with TQBR() as trader_stocks:
        result = trader_stocks.buy('SBER', 1)
        if result:
            logger.info("Заявка успешно отправлена")
        else:
            logger.error("Не удалось отправить заявку")


if __name__ == "__main__":
    main()