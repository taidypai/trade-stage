import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорты библиотек
import json
from datetime import datetime
from locale import currency
from backend.QuikPy import QuikPy

futures_firm_id = 'SPBFUT'

def collect_accounts_data(qp_provider):
    """Собирает данные о счетах в структурированном виде"""

    accounts_data = {
        "timestamp": datetime.now().isoformat(),
        "accounts": []
    }

    class_codes = qp_provider.get_classes_list()['data']
    class_codes_list = class_codes[:-1].split(',')
    trade_accounts = qp_provider.get_trade_accounts()['data']
    money_limits = qp_provider.get_money_limits()['data']
    depo_limits = qp_provider.get_all_depo_limits()['data']
    orders = qp_provider.get_all_orders()['data']
    stop_orders = qp_provider.get_all_stop_orders()['data']

    for i, trade_account in enumerate(trade_accounts):
        account_info = {
            "account_number": i,
            "firmid": trade_account['firmid'],
            "trdaccid": trade_account['trdaccid'],
            "description": trade_account['description'],
            "trading_modes": [],
            "client_code": None,
            "positions": [],
            "orders": [],
            "stop_orders": [],
            "futures_data": {},
            "money_limits": []
        }

        # Режимы торгов
        trade_account_class_codes = trade_account['class_codes'][1:-1].split('|')
        intersection_class_codes = list(set(trade_account_class_codes).intersection(class_codes_list))
        account_info["trading_modes"] = intersection_class_codes

        # Код клиента
        firm_id = trade_account['firmid']
        client_code = next((moneyLimit['client_code'] for moneyLimit in money_limits if moneyLimit['firmid'] == firm_id), None)
        account_info["client_code"] = client_code

        # Для фьючерсных счетов
        if firm_id == futures_firm_id:
            # Фьючерсные позиции
            active_futures_holdings = [
                futuresHolding for futuresHolding in qp_provider.get_futures_holdings()['data']
                if futuresHolding['totalnet'] != 0
            ]

            futures_positions = []
            for active_futures_holding in active_futures_holdings:
                si = qp_provider.get_symbol_info('SPBFUT', active_futures_holding['sec_code'])
                position = {
                    "class_code": si["class_code"],
                    "sec_code": si["sec_code"],
                    "short_name": si["short_name"],
                    "quantity": active_futures_holding["totalnet"],
                    "average_price": active_futures_holding["cbplused"]
                }
                futures_positions.append(position)

            # Фьючерсные лимиты
            futures_limit = qp_provider.get_futures_limit(
                firm_id,
                trade_account['trdaccid'],
                0,
                qp_provider.currency
            )['data']

            account_info["futures_data"] = {
                "positions": futures_positions,
                "portfolio_value": futures_limit['cbplused'],
                "free_funds": futures_limit['cbplimit'] + futures_limit['varmargin'] + futures_limit['accruedint'],
                "currency": futures_limit["currcode"],
                "details": {
                    "limit_open_pos": futures_limit['cbplimit'],
                    "var_margin": futures_limit['varmargin'],
                    "accrued_income": futures_limit['accruedint']
                }
            }

        # Для остальных счетов
        else:
            firm_money_limits = [moneyLimit for moneyLimit in money_limits if moneyLimit['firmid'] == firm_id]

            for firm_money_limit in firm_money_limits:
                money_limit_info = {
                    "limit_kind": firm_money_limit['limit_kind'],
                    "current_balance": firm_money_limit['currentbal'],
                    "currency": firm_money_limit['currcode']
                }

                # Позиции по бумагам
                limit_kind = firm_money_limit['limit_kind']
                firm_kind_depo_limits = [
                    depoLimit for depoLimit in depo_limits
                    if depoLimit['firmid'] == firm_id
                    and depoLimit['limit_kind'] == limit_kind
                    and depoLimit['currentbal'] != 0
                ]

                positions = []
                for depo_limit in firm_kind_depo_limits:
                    sec_code = depo_limit["sec_code"]
                    class_code = qp_provider.get_security_class(class_codes, sec_code)['data']

                    try:
                        entry_price = qp_provider.quik_price_to_price(
                            class_code, sec_code, float(depo_limit["wa_position_price"])
                        )
                    except:
                        entry_price = None

                    try:
                        last_price = qp_provider.quik_price_to_price(
                            class_code, sec_code,
                            float(qp_provider.get_param_ex(class_code, sec_code, 'LAST')['data']['param_value'])
                        )
                    except:
                        last_price = None

                    si = qp_provider.get_symbol_info(class_code, sec_code)

                    position = {
                        "class_code": class_code,
                        "sec_code": sec_code,
                        "short_name": si["short_name"],
                        "quantity": int(depo_limit["currentbal"]),
                        "entry_price": entry_price,
                        "last_price": last_price
                    }
                    positions.append(position)

                money_limit_info["positions"] = positions
                account_info["money_limits"].append(money_limit_info)

        # Активные заявки
        firm_orders = [order for order in orders if order['firmid'] == firm_id and order['flags'] & 0b1 == 0b1]
        for order in firm_orders:
            buy = order['flags'] & 0b100 != 0b100
            class_code = order['class_code']
            sec_code = order["sec_code"]

            try:
                order_price = qp_provider.quik_price_to_price(class_code, sec_code, order['price'])
            except:
                order_price = None

            si = qp_provider.get_symbol_info(class_code, sec_code)
            order_qty = order['qty'] * si['lot_size'] if si else order['qty']

            order_info = {
                "order_num": order["order_num"],
                "operation": "BUY" if buy else "SELL",
                "class_code": class_code,
                "sec_code": sec_code,
                "quantity": order_qty,
                "price": order_price,
                "status": "ACTIVE"
            }
            account_info["orders"].append(order_info)

        # Стоп-заявки
        firm_stop_orders = [
            stopOrder for stopOrder in stop_orders
            if stopOrder['firmid'] == firm_id and stopOrder['flags'] & 0b1 == 0b1
        ]

        for stop_order in firm_stop_orders:
            buy = stop_order['flags'] & 0b100 != 0b100
            class_code = stop_order['class_code']
            sec_code = stop_order['sec_code']

            try:
                stop_order_price = qp_provider.quik_price_to_price(class_code, sec_code, stop_order['price'])
            except:
                stop_order_price = None

            si = qp_provider.get_symbol_info(class_code, sec_code)
            stop_order_qty = stop_order['qty'] * si['lot_size'] if si else stop_order['qty']

            stop_order_info = {
                "order_num": stop_order["order_num"],
                "operation": "BUY" if buy else "SELL",
                "class_code": class_code,
                "sec_code": sec_code,
                "quantity": stop_order_qty,
                "price": stop_order_price,
                "status": "ACTIVE"
            }
            account_info["stop_orders"].append(stop_order_info)

        accounts_data["accounts"].append(account_info)

    return accounts_data

if __name__ == '__main__':
    try:
        qp_provider = QuikPy()

        # Собираем данные
        accounts_data = collect_accounts_data(qp_provider)

        # Сохраняем в JSON файл
        output_file = "accounts_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(accounts_data, f, ensure_ascii=False, indent=2, default=str)

        print(f"Данные успешно сохранены в файл: {output_file}")
        print(f"Всего счетов: {len(accounts_data['accounts'])}")

        # Также можно вывести краткую информацию в консоль
        for account in accounts_data['accounts']:
            print(f"\nСчет #{account['account_number']}: {account['firmid']}/{account['trdaccid']}")
            print(f"  Описание: {account['description']}")
            print(f"  Позиций: {len(account.get('positions', [])) + len(account.get('futures_data', {}).get('positions', []))}")
            print(f"  Активных заявок: {len(account['orders'])}")
            print(f"  Стоп-заявок: {len(account['stop_orders'])}")

        qp_provider.close_connection_and_thread()

    except Exception as e:
        print(f"Произошла ошибка: {e}")
        # В случае ошибки все равно пытаемся сохранить что есть
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
            "accounts": []
        }
        with open("accounts_data_error.json", 'w', encoding='utf-8') as f:
            json.dump(error_data, f, ensure_ascii=False, indent=2)