import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорты файлов
from backend.QuikPy import QuikPy
from settings.backend_config import TRADING_TIKERS

# Импорты библиотек
from datetime import datetime
import json


class TICKERS_DATA:
    def __init__(self):
        self.TICKERS = TRADING_TIKERS

    """ Получение данных """
    def get_prices(self, class_type="all"):
        qp = QuikPy()
        result = {}

        try:
            # Определяем какие классы запрашивать
            if class_type == "all":
                classes_to_fetch = ["SPBFUT", "TQBR"]
            else:
                classes_to_fetch = [class_type]

            # Обрабатываем каждый класс
            for ct in classes_to_fetch:
                if ct not in self.TICKERS:
                    continue

                result[ct] = {}

                # Обрабатываем каждый тикер в классе
                for finam_ticker, quik_ticker in self.TICKERS[ct].items():
                    try:
                        # Получаем код класса и код инструмента
                        cc, sc = qp.dataname_to_class_sec_codes(f"{ct}.{quik_ticker}")
                        if not cc:
                            continue

                        # Получаем цену LAST
                        price_data = qp.get_param_ex(cc, sc, 'LAST')
                        if not price_data or 'data' not in price_data:
                            continue

                        price_val = price_data['data']['param_value']
                        if not price_val or not price_val.strip():
                            continue

                        last_price = float(price_val)

                        # Получаем полную информацию об инструменте
                        si = qp.get_symbol_info(cc, sc)

                        # Получаем шаг цены
                        min_step = 0.01  # значение по умолчанию
                        if si and 'min_price_step' in si:
                            min_step = float(si['min_price_step'])

                        # Получаем стоимость шага цены
                        step_price = 0.0
                        stepprice_data = qp.get_param_ex(cc, sc, 'STEPPRICE')
                        if stepprice_data and 'data' in stepprice_data:
                            stepprice_val = stepprice_data['data']['param_value']
                            if stepprice_val and stepprice_val.strip():
                                step_price = float(stepprice_val)

                        # Формируем запись для инструмента
                        result[ct][finam_ticker] = {
                            "ticker": quik_ticker,
                            "name": si.get("short_name", finam_ticker) if si else finam_ticker,
                            "price": last_price,
                            "min_step": min_step,
                            "step_price": step_price,
                            "step_price_currency": si.get("step_price_currency", "SUR") if si else "SUR",
                            "currency": si.get("face_unit", "SUR") if si else "SUR",
                            "trade_currency": si.get("trade_currency", "SUR") if si else "SUR",
                            "lot": si.get('lot_size', 1) if si else 1,
                            "class_code": si.get('class_code', ct) if si else ct,
                            "sec_code": si.get('sec_code', quik_ticker) if si else quik_ticker,
                            "scale": si.get('scale', 1) if si else 1,
                        }

                    except Exception as e:
                        # Пропускаем ошибки для отдельных тикеров
                        logger.error(f'Ошибка получения тикера: {quik_ticker} : {e}')

        finally:
            qp.close_connection_and_thread()

        return result

# Получения рыночных данных
def get_data(class_type="all"):
    try:
        TD = TICKERS_DATA()
        return TD.get_prices(class_type)
    except Exception as e:
        logger.error(f'Ошибка получения тикеров: {e}')
        return False


# Использование при прямом запуске
if __name__ == "__main__":
    # Получить все данные
    data = get_data()
    print(f"Фьючерсов: {len(data.get('SPBFUT', {}))}")
    print(f"Акций: {len(data.get('TQBR', {}))}")
    print(json.dumps(data, indent=2, ensure_ascii=False))