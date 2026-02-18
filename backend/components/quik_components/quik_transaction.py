# backend/components/quik_components/quik_simple_trader.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

from backend.QuikPy import QuikPy
from settings.backend_config import FIRM_ID, CLIENT_CODE, ACCOUNT_ID
import time
import itertools
from typing import Optional, Dict, Any

class SimpleTrader:
    """
    Трейдер для работы с QUIK
    """

    def __init__(self, account_id=None):
        """
        Подключаемся к QUIK

        Args:
            account_id: ID счета (если None, использует из конфига, но лучше указать явно)
        """
        # Подключаемся к QUIK
        self.qp = QuikPy()

        # Номер заявки будем получать из on_trans_reply
        self.order_num = 0
        self.trans_id = itertools.count(1)

        # Подписываемся на ответы транзакций
        self.qp.on_trans_reply.subscribe(self._on_trans_reply)

        # Получаем все счета для информации
        self.accounts = self._get_all_accounts()

        # Выбираем счет для работы
        if account_id:
            self.account_id = account_id
        else:
            # Если счет не указан, используем из конфига или первый активный
            self.account_id = ACCOUNT_ID if ACCOUNT_ID else self._get_first_active_account()

        # Для акций FIRM_ID не нужен, CLIENT_CODE берем из данных счета
        self.client_code = "971882RJJVK"  # Из ваших данных CLIENT_CODE всегда 971882RJJVK

        print(f"✅ Подключено к QUIK")
        print(f"👤 Код клиента: {self.client_code}")
        print(f"🏦 Выбранный счет: {self.account_id}")
        print(f"\n📋 Доступные счета:")
        for acc in self.accounts:
            status = "✅ АКТИВЕН" if acc['is_active'] else "❌ ПУСТОЙ"
            print(f"   {acc['account_id']} - {acc['description']} ({acc['balances']}) {status}")

    def _get_all_accounts(self):
        """Получает все счета из QUIK"""
        accounts = []
        try:
            trade_accounts = self.qp.get_trade_accounts()['data']
            money_limits = self.qp.get_money_limits()['data']

            for trade_account in trade_accounts:
                firm_id = trade_account['firmid']
                account_id = trade_account['trdaccid']
                description = trade_account['description'] or "без описания"

                # Получаем балансы
                firm_money_limits = [ml for ml in money_limits if ml['firmid'] == firm_id]
                balances = {}
                is_active = False

                for ml in firm_money_limits:
                    currency = ml['currcode']
                    balance = ml['currentbal']
                    balances[currency] = balance
                    if balance > 0:
                        is_active = True

                accounts.append({
                    'firm_id': firm_id,
                    'account_id': account_id,
                    'description': description,
                    'balances': balances,
                    'is_active': is_active
                })
        except Exception as e:
            print(f"⚠️ Ошибка получения счетов: {e}")

        return accounts

    def _get_first_active_account(self):
        """Возвращает первый активный счет"""
        for acc in self.accounts:
            if acc['is_active']:
                return acc['account_id']
        # Если нет активных, берем первый
        return self.accounts[0]['account_id'] if self.accounts else None

    def _on_trans_reply(self, data):
        """Обработчик ответа на транзакцию - ловим номер заявки!"""
        order_num = data['data'].get('order_num')
        trans_id = data['data'].get('trans_id')
        if order_num:
            self.order_num = int(order_num)
            print(f"✅ Получен номер заявки: {self.order_num} для транзакции {trans_id}")

    def get_price(self, ticker: str, class_code: str = "TQBR") -> Optional[float]:
        """
        Получить текущую цену

        Args:
            ticker: тикер (SPBE, SBER, GAZP...)
            class_code: TQBR - акции, SPBFUT - фьючерсы
        """
        try:
            price_data = self.qp.get_param_ex(class_code, ticker, 'LAST')
            if price_data and 'data' in price_data:
                price_val = price_data['data']['param_value']
                if price_val and price_val.strip():
                    price = float(price_val)
                    print(f"📊 {ticker}: {price}")
                    return price
        except Exception as e:
            print(f"❌ Ошибка получения цены {ticker}: {e}")

        return None

    def buy(self, ticker: str, quantity: int = 1, class_code: str = "TQBR") -> Dict[str, Any]:
        """
        Купить по рыночной цене

        Args:
            ticker: тикер (SPBE, SBER, GAZP...)
            quantity: сколько лотов
            class_code: TQBR - акции, SPBFUT - фьючерсы
        """
        return self._place_order(ticker, "B", quantity, class_code, "покупка")

    def sell(self, ticker: str, quantity: int = 1, class_code: str = "TQBR") -> Dict[str, Any]:
        """
        Продать по рыночной цене
        """
        return self._place_order(ticker, "S", quantity, class_code, "продажа")

    def _place_order(self, ticker: str, operation: str, quantity: int,
                     class_code: str, op_name: str) -> Dict[str, Any]:
        """
        Отправляем рыночную заявку
        """
        result = {
            'success': False,
            'message': '',
            'order_num': 0,
            'price': 0
        }

        if not self.account_id:
            result['message'] = 'Не выбран счет!'
            print(f"❌ {result['message']}")
            return result

        # Получаем текущую цену
        current_price = self.get_price(ticker, class_code)
        if not current_price:
            result['message'] = f'Не удалось получить цену для {ticker}'
            return result

        # Конвертируем цену для QUIK
        quik_price = self.qp.price_to_quik_price(class_code, ticker, current_price)

        # Сбрасываем номер заявки перед отправкой
        self.order_num = 0

        # Генерируем уникальный TRANS_ID
        current_trans_id = str(next(self.trans_id))

        # Формируем транзакцию в зависимости от класса
        if class_code == "SPBFUT":  # Для фьючерсов
            transaction = {
                'TRANS_ID': current_trans_id,
                'CLIENT_CODE': "FZQU337843A",
                'ACCOUNT': self.account_id,
                'FIRM_ID': "SPBFUT",  # Для фьючерсов FIRM_ID = SPBFUT
                'ACTION': 'NEW_ORDER',
                'CLASSCODE': class_code,
                'SECCODE': ticker,
                'OPERATION': operation,
                'PRICE': str(quik_price),
                'QUANTITY': str(quantity),
                'TYPE': 'L'
            }
        else:  # Для акций (TQBR и другие) - FIRM_ID НЕ НУЖЕН!
            transaction = {
                'TRANS_ID': current_trans_id,
                'CLIENT_CODE': "FZQU337843A",
                'ACCOUNT': self.account_id,
                'ACTION': 'NEW_ORDER',
                'CLASSCODE': class_code,
                'SECCODE': ticker,
                'OPERATION': operation,
                'PRICE': str(quik_price),
                'QUANTITY': str(quantity),
                'TYPE': 'L'
            }

        print(f"\n🔄 {op_name.upper()} {quantity} {ticker} по рынку...")
        print(f"📝 TRANS_ID: {current_trans_id}")
        print(f"📋 Параметры: {transaction}")

        try:
            # Отправляем заявку
            response = self.qp.send_transaction(transaction)
            print(f"📤 Ответ от QUIK: {response}")

            # Проверяем на ошибки в ответе
            if 'lua_error' in response:
                result['message'] = f'❌ Ошибка QUIK: {response["lua_error"]}'
                print(result['message'])
                return result

            if response.get('data') == True:
                # ЖДЕМ номер заявки из on_trans_reply (до 3 секунд)
                wait_time = 0
                max_wait = 3

                while self.order_num == 0 and wait_time < max_wait:
                    time.sleep(0.1)
                    wait_time += 0.1

                if self.order_num > 0:
                    result['success'] = True
                    result['order_num'] = self.order_num
                    result['price'] = current_price
                    result['message'] = f'✅ {op_name} #{self.order_num} отправлена'
                    print(result['message'])
                else:
                    result['message'] = f'Заявка отправлена (TRANS_ID: {current_trans_id}), но номер не получен. Проверьте в терминале QUIK.'
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
        try:
            self.qp.on_trans_reply.unsubscribe(self._on_trans_reply)
            self.qp.close_connection_and_thread()
            print("🔌 Отключились от QUIK")
        except:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Пример использования
if __name__ == "__main__":
    # Выбираем счет для работы
    ACCOUNT_TO_USE = "L01+00000F00"  # Счет УК ФИНАМ

    with SimpleTrader(account_id=ACCOUNT_TO_USE) as trader:
        # Покупаем акцию SPBE
        result = trader.buy("SPBE", 1, "TQBR")
        print(f"Результат: {result}")

        if result['success']:
            print(f"✅ Заявка #{result['order_num']} успешно отправлена")
        else:
            print(f"⚠️ {result['message']}")
