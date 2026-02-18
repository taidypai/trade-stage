""" python backend\components\account.py """
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт файлов
from backend.QuikPy import QuikPy


def collect_accounts_data(qp_provider):

    accounts_data = {
        "balance": 0,
        "positions": []
    }

    # Получаем все необходимые данные
    class_codes = qp_provider.get_classes_list()['data']
    class_codes_list = class_codes[:-1].split(',')
    trade_accounts = qp_provider.get_trade_accounts()['data']
    money_limits = qp_provider.get_money_limits()['data']
    depo_limits = qp_provider.get_all_depo_limits()['data']

    # Ищем первый русский счет с деньгами (SUR)
    for trade_account in trade_accounts:
        firm_id = trade_account['firmid']
        trade_account_id = trade_account['trdaccid']

        # Получаем денежные лимиты для этого счета
        firm_money_limits = [ml for ml in money_limits if ml['firmid'] == firm_id]

        # Ищем лимиты в рублях (SUR) с деньгами
        rub_limits = [ml for ml in firm_money_limits if ml['currcode'] == 'SUR' and ml['currentbal'] > 0]

        if rub_limits:
            # Берем первый лимит с деньгами
            main_limit = rub_limits[0]
            accounts_data["balance"] = main_limit['currentbal']

            # Собираем все открытые позиции для этой фирмы
            all_positions = []
            firm_depo_limits = [dl for dl in depo_limits if dl['firmid'] == firm_id and dl['currentbal'] != 0]

            # Убираем дубликаты позиций
            seen_sec_codes = set()

            for depo_limit in firm_depo_limits:
                sec_code = depo_limit["sec_code"]

                if sec_code in seen_sec_codes:
                    continue
                seen_sec_codes.add(sec_code)

                # Получаем класс код для бумаги
                class_code = qp_provider.get_security_class(class_codes, sec_code)['data']

                # Получаем цену входа
                try:
                    entry_price = qp_provider.quik_price_to_price(
                        class_code, sec_code, float(depo_limit["wa_position_price"])
                    )
                except:
                    entry_price = None

                # Получаем последнюю цену
                try:
                    last_price_data = qp_provider.get_param_ex(class_code, sec_code, 'LAST')
                    if last_price_data and 'data' in last_price_data:
                        last_price_val = last_price_data['data']['param_value']
                        if last_price_val and last_price_val.strip():
                            last_price = qp_provider.quik_price_to_price(
                                class_code, sec_code, float(last_price_val)
                            )
                        else:
                            last_price = None
                    else:
                        last_price = None
                except:
                    last_price = None

                # Получаем информацию о бумаге
                si = qp_provider.get_symbol_info(class_code, sec_code)

                # Рассчитываем прибыль/убыток
                pnl = None
                pnl_percent = None
                if entry_price and last_price:
                    pnl = (last_price - entry_price) * int(depo_limit["currentbal"])
                    pnl_percent = ((last_price - entry_price) / entry_price) * 100

                position = {
                    "sec_code": sec_code,
                    "short_name": si.get("short_name", sec_code),
                    "quantity": int(depo_limit["currentbal"]),
                    "entry_price": round(entry_price, 2) if entry_price else None,
                    "last_price": round(last_price, 2) if last_price else None,
                    "pnl": round(pnl, 2) if pnl else None,
                    "pnl_percent": round(pnl_percent, 2) if pnl_percent else None
                }
                all_positions.append(position)

            accounts_data["positions"] = all_positions
            break

    return accounts_data

def get_balance():
    qp_provider = None
    try:
        qp_provider = QuikPy()
        accounts_data = collect_accounts_data(qp_provider)
        return accounts_data

    except Exception as e:
        logger.error(f'Ошибка: {e}')
        return {"balance": 0, "positions": [], "error": str(e)}
        
    finally:
        # Закрываем соединение в любом случае (и при успехе, и при ошибке)
        if qp_provider:
            qp_provider.close_connection_and_thread()

if __name__ == '__main__':
    result = get_balance()
    print(result)