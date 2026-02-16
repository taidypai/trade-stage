import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

import logging
from sys import exit
from datetime import datetime
from time import sleep
import itertools
from typing import Dict, Any, Optional
from backend.QuikPy import QuikPy

class VTB_FuturesTrader:
    """Класс для торговли фьючерсами ВТБ через QUIK"""

    def __init__(self):
        """Инициализация подключения к QUIK"""
        self.logger = logging.getLogger('VTB_FuturesTrader')
        try:
            self.qp_provider = QuikPy.QuikPy()
            self.logger.info("Успешное подключение к QUIK")
        except Exception as e:
            self.logger.error(f"Ошибка подключения к Quik: {e}")
            raise

        # Маппинг тикеров фьючерсов ВТБ
        self.vtb_futures_tickers = {
            "VTBR-3.26": "VBH6",  # Фьючерс на ВТБ, март 2026
        }

        self.order_num = 0
        self.trans_id = itertools.count(1)

        # Подписываемся на события
        self.qp_provider.on_trans_reply.subscribe(self._on_trans_reply)
        self.qp_provider.on_order.subscribe(self._on_order)
        self.qp_provider.on_trade.subscribe(self._on_trade)
        self.qp_provider.on_futures_client_holding.subscribe(self._on_futures_client_holding)

    def _on_trans_reply(self, data):
        """Обработчик события ответа на транзакцию"""
        self.logger.info(f'OnTransReply: {data}')
        self.order_num = int(data['data']['order_num'])
        self.logger.info(f'Номер транзакции: {data["data"]["trans_id"]}, Номер заявки: {self.order_num}')

    def _on_order(self, data):
        """Обработчик события заявки"""
        self.logger.info(f'Заявка - {data}')

    def _on_trade(self, data):
        """Обработчик события сделки"""
        self.logger.info(f'Сделка - {data}')

    def _on_futures_client_holding(self, data):
        """Обработчик события позиции по фьючерсам"""
        self.logger.info(f'OnFuturesClientHolding: {data}')

    def get_vtb_futures_account(self) -> Optional[Dict[str, Any]]:
        """Находит счет для торговли фьючерсами ВТБ"""
        class_code = 'SPBFUT'

        for account in self.qp_provider.accounts:
            if class_code in account['class_codes']:
                self.logger.info(f"Найден счет для фьючерсов: {account}")
                return account

        self.logger.error(f"Торговый счет для режима торгов {class_code} не найден")
        return None

    def get_vtb_futures_price(self, ticker: str = "VTBR-3.26") -> Optional[float]:
        """Получает текущую цену фьючерса ВТБ"""
        if ticker not in self.vtb_futures_tickers:
            self.logger.error(f"Тикер {ticker} не найден в списке")
            return None

        quik_ticker = self.vtb_futures_tickers[ticker]
        dataname = f"SPBFUT.{quik_ticker}"

        try:
            class_code, sec_code = self.qp_provider.dataname_to_class_sec_codes(dataname)
            last_price_data = self.qp_provider.get_param_ex(class_code, sec_code, 'LAST')

            if last_price_data and 'data' in last_price_data:
                param_value = last_price_data['data']['param_value']
                if param_value and param_value.strip():
                    last_price = float(param_value)
                    self.logger.info(f"Текущая цена {ticker}: {last_price}")
                    return last_price

            self.logger.error(f"Не удалось получить цену для {ticker}")
            return None

        except Exception as e:
            self.logger.error(f"Ошибка получения цены для {ticker}: {e}")
            return None

    def buy_vtb_futures_lot(self,
                           ticker: str = "VTBR-3.26",
                           quantity: int = 1,
                           order_type: str = "MARKET",
                           limit_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Покупает один лот фьючерса ВТБ

        Args:
            ticker: Тикер фьючерса (VTBR-3.26)
            quantity: Количество лотов (по умолчанию 1)
            order_type: Тип заявки - "MARKET" (рыночная) или "LIMIT" (лимитная)
            limit_price: Цена для лимитной заявки

        Returns:
            Результат операции
        """
        result = {
            "success": False,
            "message": "",
            "order_num": 0,
            "price": 0
        }

        if ticker not in self.vtb_futures_tickers:
            result["message"] = f"Тикер {ticker} не найден"
            return result

        # Находим счет для фьючерсов
        account = self.get_vtb_futures_account()
        if not account:
            result["message"] = "Не найден счет для торговли фьючерсами"
            return result

        client_code = account['client_code']
        trade_account_id = account['trade_account_id']
        quik_ticker = self.vtb_futures_tickers[ticker]
        class_code = 'SPBFUT'

        # Получаем текущую цену
        current_price = self.get_vtb_futures_price(ticker)
        if not current_price:
            result["message"] = "Не удалось получить текущую цену"
            return result

        # Получаем спецификацию инструмента
        try:
            si = self.qp_provider.get_symbol_info(class_code, quik_ticker)
            if not si:
                result["message"] = f"Не удалось получить спецификацию для {ticker}"
                return result
        except Exception as e:
            result["message"] = f"Ошибка получения спецификации: {e}"
            return result

        # Определяем тип заявки и цену
        if order_type.upper() == "MARKET":
            # Для фьючерсов рыночная цена должна быть выше при покупке
            market_price = self.qp_provider.price_to_quik_price(
                class_code, quik_ticker,
                self.qp_provider.quik_price_to_price(class_code, quik_ticker, current_price * 1.01)
            )
            price_str = str(market_price)
            order_type_char = 'M'
            order_desc = "рыночная"
        elif order_type.upper() == "LIMIT":
            if limit_price is None:
                # По умолчанию покупаем на 1% ниже текущей цены
                limit_price = current_price * 0.99

            limit_price_quik = self.qp_provider.price_to_quik_price(
                class_code, quik_ticker,
                self.qp_provider.quik_price_to_price(class_code, quik_ticker, limit_price)
            )
            price_str = str(limit_price_quik)
            order_type_char = 'L'
            order_desc = f"лимитная по цене {limit_price:.2f}"
        else:
            result["message"] = f"Неизвестный тип заявки: {order_type}"
            return result

        self.logger.info(f"Покупка {quantity} лотов {ticker} ({quik_ticker}) по {order_desc} цене")

        try:
            # Подготавливаем транзакцию
            transaction = {
                'TRANS_ID': str(next(self.trans_id)),
                'CLIENT_CODE': client_code,
                'ACCOUNT': trade_account_id,
                'ACTION': 'NEW_ORDER',
                'CLASSCODE': class_code,
                'SECCODE': quik_ticker,
                'OPERATION': 'B',  # Покупка
                'PRICE': price_str,
                'QUANTITY': str(quantity),
                'TYPE': order_type_char
            }

            # Отправляем заявку
            response = self.qp_provider.send_transaction(transaction)

            if 'data' in response:
                self.logger.info(f"Заявка отправлена: {response['data']}")

                # Ждем подтверждения заявки
                sleep(3)

                if self.order_num > 0:
                    result["success"] = True
                    result["message"] = f"Заявка #{self.order_num} успешно отправлена"
                    result["order_num"] = self.order_num
                    result["price"] = current_price

                    # Проверяем статус заявки
                    try:
                        order_info = self.qp_provider.get_order_by_number(class_code, str(self.order_num))
                        if order_info and 'data' in order_info:
                            result["order_status"] = order_info['data']
                            self.logger.info(f"Статус заявки: {order_info['data']}")
                    except Exception as e:
                        self.logger.warning(f"Не удалось получить статус заявки: {e}")
                else:
                    result["message"] = "Не получен номер заявки"
            else:
                result["message"] = f"Ошибка отправки заявки: {response}"

        except Exception as e:
            result["message"] = f"Ошибка выполнения транзакции: {e}"
            self.logger.error(f"Ошибка: {e}", exc_info=True)

        return result

    def get_vtb_futures_position(self, ticker: str = "VTBR-3.26") -> Dict[str, Any]:
        """Получает текущую позицию по фьючерсу ВТБ"""
        result = {
            "has_position": False,
            "quantity": 0,
            "average_price": 0,
            "current_price": 0,
            "pnl": 0
        }

        if ticker not in self.vtb_futures_tickers:
            result["message"] = f"Тикер {ticker} не найден"
            return result

        quik_ticker = self.vtb_futures_tickers[ticker]

        try:
            # Получаем все фьючерсные позиции
            holdings_data = self.qp_provider.get_futures_holdings()

            if holdings_data and 'data' in holdings_data:
                for holding in holdings_data['data']:
                    if holding['sec_code'] == quik_ticker and holding['totalnet'] != 0:
                        result["has_position"] = True
                        result["quantity"] = holding['totalnet']
                        result["average_price"] = holding['cbplused']

                        # Получаем текущую цену
                        current_price = self.get_vtb_futures_price(ticker)
                        if current_price:
                            result["current_price"] = current_price
                            # Рассчитываем P&L
                            result["pnl"] = (current_price - holding['cbplused']) * result["quantity"]

                        self.logger.info(f"Позиция по {ticker}: {result['quantity']} лотов")
                        break

            if not result["has_position"]:
                result["message"] = f"Нет открытой позиции по {ticker}"

        except Exception as e:
            result["message"] = f"Ошибка получения позиции: {e}"

        return result

    def close(self):
        """Закрывает соединение с QUIK"""
        try:
            # Отменяем подписки
            self.qp_provider.on_trans_reply.unsubscribe(self._on_trans_reply)
            self.qp_provider.on_order.unsubscribe(self._on_order)
            self.qp_provider.on_trade.unsubscribe(self._on_trade)
            self.qp_provider.on_futures_client_holding.unsubscribe(self._on_futures_client_holding)

            # Закрываем соединение
            self.qp_provider.close_connection_and_thread()
            self.logger.info("Соединение с QUIK закрыто")

        except Exception as e:
            self.logger.error(f"Ошибка при закрытии соединения: {e}")

def buy_vtb_futures():
    """Основная функция для покупки фьючерса ВТБ"""

    # Настройка логирования
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%d.%m.%Y %H:%M:%S',
        level=logging.INFO,
        handlers=[
            logging.FileHandler('vtb_futures_trade.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger('Main')

    trader = None

    try:
        logger.info("="*50)
        logger.info("ПОКУПКА ФЬЮЧЕРСА ВТБ")
        logger.info("="*50)

        # Создаем трейдера
        trader = VTB_FuturesTrader()

        # Проверяем текущую позицию
        position = trader.get_vtb_futures_position()
        logger.info(f"Текущая позиция: {position}")

        # Если уже есть позиция, спрашиваем подтверждение
        if position["has_position"]:
            logger.warning(f"Уже есть открытая позиция: {position['quantity']} лотов")
            confirm = input("Продолжить покупку? (y/n): ")
            if confirm.lower() != 'y':
                logger.info("Покупка отменена пользователем")
                return

        # Получаем текущую цену
        current_price = trader.get_vtb_futures_price()
        if not current_price:
            logger.error("Не удалось получить цену")
            return

        logger.info(f"Текущая цена VTBR-3.26: {current_price}")

        # Спрашиваем тип заявки
        order_type = input("Тип заявки (market/limit): ").strip().lower()
        limit_price = None

        if order_type == 'limit':
            try:
                limit_input = input(f"Цена для лимитной заявки (текущая: {current_price:.2f}): ")
                if limit_input:
                    limit_price = float(limit_input)
            except ValueError:
                logger.warning("Некорректная цена, используем рыночную заявку")
                order_type = 'market'

        # Покупаем 1 лот
        result = trader.buy_vtb_futures_lot(
            ticker="VTBR-3.26",
            quantity=1,
            order_type="MARKET" if order_type == 'market' else "LIMIT",
            limit_price=limit_price
        )

        # Выводим результат
        logger.info("="*50)
        logger.info("РЕЗУЛЬТАТ ОПЕРАЦИИ:")
        logger.info(f"Успешно: {result['success']}")
        logger.info(f"Сообщение: {result['message']}")
        if result['success']:
            logger.info(f"Номер заявки: {result['order_num']}")
            logger.info(f"Цена: {result['price']}")

        # Ждем немного и проверяем позицию
        if result['success']:
            sleep(5)
            position = trader.get_vtb_futures_position()
            logger.info(f"Обновленная позиция: {position}")

    except Exception as e:
        logger.error(f"Критическая ошибка: {e}", exc_info=True)

    finally:
        if trader:
            trader.close()

if __name__ == '__main__':
    buy_vtb_futures()