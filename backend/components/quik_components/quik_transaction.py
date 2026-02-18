import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from backend.QuikPy import QuikPy
import json
import os
from typing import Optional, Dict, Any

from settings.backend_config import FIRM_ID, CLIENT_CODE, ACCOUNT_ID

class SimpleTrader:

    def __init__(self, accounts_file: str = r"C:\Users\Вадим\Documents\trade-stage\accounts_data.json"):
        # Подключаемся к QUIK
        self.qp = QuikPy()

    # Получить текущую цену
    def get_price(self, ticker: str, class_code: str = "SPBFUT"):
        try:
            price_data = self.qp.get_param_ex(class_code, ticker, 'LAST')
            if price_data and 'data' in price_data:
                price_val = price_data['data']['param_value']
                if price_val and price_val.strip():
                    price = float(price_val)
                    print(f"📊 {ticker}: {price}")
                    return price
        except Exception as e:
            print(f"Ошибка получения цены {ticker}: {e}")

        return None

    # Купить по рыночной цене
    def buy(self, ticker: str, quantity: int = 1, class_code: str = "SPBFUT"):
        return self._place_order(ticker, "B", quantity, class_code, "покупка")
    # Продать по рыночной цене
    def sell(self, ticker: str, quantity: int = 1, class_code: str = "SPBFUT"):
        return self._place_order(ticker, "S", quantity, class_code, "продажа")

    def _place_order(self, ticker: str, operation: str, quantity: int,
                     class_code: str, op_name: str):
        """
        Отправляем рыночную заявку
        """
        result = {
            'success': False,
            'message': '',
            'order_num': 0,
            'price': 0
        }

        # Получаем текущую цену
        current_price = self.get_price(ticker, class_code)
        if not current_price:
            result['message'] = f'Не удалось получить цену для {ticker}'
            return result

        # Конвертируем цену для QUIK
        quik_price = self.qp.price_to_quik_price(class_code, ticker, current_price)

        # Формируем транзакцию (чисто по делу, ничего лишнего)
        transaction = {
            'TRANS_ID': '1',  # Можно и так, транзакции всё равно последовательные
            'CLIENT_CODE': CLIENT_CODE,
            'ACCOUNT': ACCOUNT_ID,
            'ACTION': 'NEW_ORDER',
            'CLASSCODE': class_code,
            'SECCODE': ticker,
            'OPERATION': operation,
            'PRICE': str(quik_price),
            'QUANTITY': str(quantity),
            'TYPE': 'L'  # В QUIK рыночные идут как лимитные с запасом
        }

        print(f"\n🔄 {op_name.upper()} {quantity} {ticker} по рынку...")

        try:
            # Отправляем заявку
            response = self.qp.send_transaction(transaction)

            if 'data' in response:
                # Пытаемся получить номер заявки из ответа
                order_num = response['data'].get('order_num', 0)
                if order_num:
                    result['success'] = True
                    result['order_num'] = order_num
                    result['price'] = current_price
                    result['message'] = f'✅ {op_name} #{order_num} отправлена'
                    print(result['message'])
                else:
                    result['message'] = 'Заявка отправлена, но номер не получен'
                    print(f"⚠️ {result['message']}")
            else:
                result['message'] = f'❌ Ошибка: {response}'
                print(result['message'])

        except Exception as e:
            result['message'] = f'❌ Ошибка: {e}'
            print(result['message'])

        return result

    def close(self):
        """Закрываем соединение"""
        self.qp.close_connection_and_thread()
        print("🔌 Отключились от QUIK")
trader = SimpleTrader()
# Пример использования
if __name__ == "__main__":

    try:
        #t.buy("VBH6", 1, "SPBFUT")  # купил фьючерс
        #t.sell("VBH6", 1, "SPBFUT")  # продал фьючерс
        trader.sell("SPBE", 1, "TQBR")    # купил акции

    finally:
        # Всегда закрываем соединение
        trader.close()
