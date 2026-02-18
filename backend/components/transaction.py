""" python backend/components/transaction.py """
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from backend.components.logger import logger
from backend.QuikPy import QuikPy
from settings.backend_config import CLIENT_CODE, ACCOUNT_ID
from typing import Optional, Dict, Any

class TRANS_SET:

    def __init__(self, class_code: str):
        self.class_code = class_code
        self.qp = QuikPy()

    # Отправка заявки
    def place_order(self, ticker: str, operation: str, quantity: int) -> Dict[str, Any]:
        """Возвращает словарь с результатом"""

        # Формируем транзакцию
        transaction = {
            'TRANS_ID': '1',
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

            # Проверяем ответ
            if response and isinstance(response, dict):
                if response.get('data') is True:  # Успешная отправка
                    logger.info(f'✅ Заявка на {ticker} {quantity} лотов отправлена')
                    return {'success': True, 'message': 'Заявка отправлена', 'data': response}
                else:
                    error_msg = f'Ошибка отправки: {response}'
                    logger.error(error_msg)
                    return {'success': False, 'message': error_msg}
            else:
                error_msg = 'Пустой ответ от QUIK'
                logger.error(error_msg)
                return {'success': False, 'message': error_msg}

        except Exception as e:
            error_msg = f'Ошибка: {e}'
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}

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

    def buy(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Купить фьючерс"""
        return self.place_order(ticker, "B", quantity)

    def sell(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Продать фьючерс"""
        return self.place_order(ticker, "S", quantity)


# ==================== АКЦИИ ====================
class TQBR(TRANS_SET):
    def __init__(self):
        super().__init__(class_code="TQBR")

    def buy(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Купить акцию"""
        return self.place_order(ticker, "B", quantity)

    def sell(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Продать акцию"""
        return self.place_order(ticker, "S", quantity)


def main():
    # Пример использования
    with TQBR() as trader:
        result = trader.buy('SBER', 1)
        if result.get('success'):
            logger.info("Заявка успешно отправлена")
        else:
            logger.error(f"Ошибка: {result.get('message')}")


if __name__ == "__main__":
    main()