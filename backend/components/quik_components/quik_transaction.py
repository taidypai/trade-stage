import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from backend.QuikPy import QuikPy
from settings.backend_config import CLIENT_CODE, ACCOUNT_ID
from typing import Optional, Dict, Any

# ==================== БАЗОВЫЙ КЛАСС ====================
class BaseTrader:
    """Базовый класс для всех трейдеров"""

    def __init__(self, class_code: str):
        self.class_code = class_code
        self.qp = QuikPy()
        print(f"✅ Подключено к QUIK")
        print(f"👤 Клиент: {CLIENT_CODE}")
        print(f"🏦 Счет: {ACCOUNT_ID}")
        print(f"📈 Режим: {class_code}")

    def get_price(self, ticker: str) -> Optional[float]:
        """Получить текущую цену"""
        try:
            price_data = self.qp.get_param_ex(self.class_code, ticker, 'LAST')
            if price_data and 'data' in price_data:
                price_val = price_data['data']['param_value']
                if price_val and price_val.strip():
                    price = float(price_val)
                    print(f"📊 {ticker}: {price}")
                    return price
        except Exception as e:
            print(f"❌ Ошибка получения цены {ticker}: {e}")
        return None

    def _place_order(self, ticker: str, operation: str, quantity: int, op_name: str) -> Dict[str, Any]:
        """Внутренний метод для отправки заявки"""
        result = {
            'success': False,
            'message': '',
            'order_num': 0,
            'price': 0
        }

        # Получаем текущую цену
        current_price = self.get_price(ticker)
        if not current_price:
            result['message'] = f'Не удалось получить цену для {ticker}'
            return result

        # Конвертируем цену для QUIK
        quik_price = self.qp.price_to_quik_price(self.class_code, ticker, current_price)

        # Формируем транзакцию
        transaction = {
            'TRANS_ID': '1',
            'CLIENT_CODE': CLIENT_CODE,
            'ACCOUNT': ACCOUNT_ID,
            'ACTION': 'NEW_ORDER',
            'CLASSCODE': self.class_code,
            'SECCODE': ticker,
            'OPERATION': operation,
            'PRICE': str(quik_price),
            'QUANTITY': str(quantity),
            'TYPE': 'L'
        }

        print(f"\n🔄 {op_name.upper()} {quantity} {ticker} по рынку...")

        try:
            response = self.qp.send_transaction(transaction)

            # Отладка: посмотрим что реально приходит
            print(f"📥 Ответ от QuikPy: {response} (тип: {type(response)})")

            # QuikPy может вернуть:
            # 1. Число (номер заявки)
            # 2. Словарь с данными
            # 3. False (ошибка)

            if response is False:
                result['message'] = '❌ Ошибка отправки транзакции (соединение или параметры)'
                print(result['message'])

            elif isinstance(response, (int, str)) and response:
                # Если пришло число или строка - это номер заявки
                result['success'] = True
                result['order_num'] = int(response) if str(response).isdigit() else response
                result['price'] = current_price
                result['message'] = f'✅ {op_name} #{result["order_num"]} отправлена'
                print(result['message'])

            elif isinstance(response, dict):
                # Если пришел словарь - ищем номер заявки
                if 'order_num' in response:
                    result['success'] = True
                    result['order_num'] = response['order_num']
                    result['price'] = current_price
                    result['message'] = f'✅ {op_name} #{result["order_num"]} отправлена'
                    print(result['message'])
                elif 'data' in response:
                    data = response['data']
                    if isinstance(data, dict) and 'order_num' in data:
                        result['success'] = True
                        result['order_num'] = data['order_num']
                        result['price'] = current_price
                        result['message'] = f'✅ {op_name} #{result["order_num"]} отправлена'
                        print(result['message'])
                    elif data:
                        result['success'] = True
                        result['order_num'] = data
                        result['price'] = current_price
                        result['message'] = f'✅ {op_name} #{data} отправлена'
                        print(result['message'])
                    else:
                        result['message'] = f'⚠️ Заявка отправлена, но номер не получен: {response}'
                        print(result['message'])
                else:
                    result['message'] = f'⚠️ Неизвестный формат ответа: {response}'
                    print(result['message'])
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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ==================== ФЬЮЧЕРСЫ ====================
class FuturesTrader(BaseTrader):
    """Трейдер только для фьючерсов (SPBFUT)"""

    def __init__(self):
        super().__init__(class_code="SPBFUT")
        print("🔥 Режим: ТОРГОВЛЯ ФЬЮЧЕРСАМИ")

    def buy(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Купить фьючерс"""
        return self._place_order(ticker, "B", quantity, "покупка фьючерса")

    def sell(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Продать фьючерс"""
        return self._place_order(ticker, "S", quantity, "продажа фьючерса")


# ==================== АКЦИИ ====================
class StocksTrader(BaseTrader):
    """Трейдер только для акций (TQBR)"""

    def __init__(self):
        super().__init__(class_code="TQBR")
        print("📊 Режим: ТОРГОВЛЯ АКЦИЯМИ")

    def buy(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Купить акцию"""
        return self._place_order(ticker, "B", quantity, "покупка акции")

    def sell(self, ticker: str, quantity: int = 1) -> Dict[str, Any]:
        """Продать акцию"""
        return self._place_order(ticker, "S", quantity, "продажа акции")


# ==================== ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ ====================
if __name__ == "__main__":

    #===== ТОРГОВЛЯ ФЬЮЧЕРСАМИ =====
    print("\n" + "="*60)
    print("ТОРГОВЛЯ ФЬЮЧЕРСАМИ")
    print("="*60)

    with FuturesTrader() as futures:
        result = futures.buy("YDH6", 1)
        print(f"Результат: {result}")

    # ===== ТОРГОВЛЯ АКЦИЯМИ =====
    # print("\n" + "="*60)
    # print("ТОРГОВЛЯ АКЦИЯМИ")
    # print("="*60)

    # with StocksTrader() as stocks:
    #     result = stocks.buy("SPBE", 1)
    #     print(f"Результат: {result}")
