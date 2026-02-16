import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время
import sys  # Выход из точки входа
import traceback  # Для отладки ошибок

sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")
from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    logger = logging.getLogger('QuikPy.Ticker')  # Будем вести лог

    try:
        qp_provider = QuikPy.QuikPy()  # Исправлено: было QuikPy.QuikPy()
    except Exception as e:
        logger.error(f"Ошибка подключения к Quik: {e}")
        sys.exit(1)

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.INFO,  # Уменьшим до INFO для лучшей читаемости
                        handlers=[logging.FileHandler('Ticker.log', encoding='utf-8'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль
    logging.Formatter.converter = lambda *args: datetime.now().timetuple()  # В логе время указываем по МСК

    # Пробуем разные тикеры
    datanames = ('SPBFUT.IMOEXF', 'SPBFUT.SiH6', 'TQBR.SBER')  # Кортеж тикеров (добавлена запятая!)

    for dataname in datanames:  # Пробегаемся по всем тикерам
        logger.info(f"\n{'='*50}")
        logger.info(f"Обработка тикера: {dataname}")
        logger.info(f"{'='*50}")

        try:
            # Получаем класс и код инструмента
            class_code, sec_code = qp_provider.dataname_to_class_sec_codes(dataname)  # Код режима торгов и тикер
            logger.info(f"Класс: {class_code}, Тикер: {sec_code}")

            # Получаем спецификацию тикера
            si = qp_provider.get_symbol_info(class_code, sec_code)  # Спецификация тикера
            print
            if si:
                logger.debug(f'Ответ от сервера: {si}')

                # Проверяем наличие ключей
                short_name = si.get("short_name", "N/A")
                logger.info(f'Информация о тикере {si.get("class_code", "N/A")}.{si.get("sec_code", "N/A")} ({short_name}):')

                face_unit = si.get("face_unit", "N/A")
                logger.info(f'- Валюта: {face_unit}')

                lot_size = si.get('lot_size', 0)  # Лот
                logger.info(f'- Лот: {lot_size}')

                min_price_step = si.get('min_price_step', 0)  # Шаг цены
                logger.info(f'- Шаг цены: {min_price_step}')

                scale = si.get('scale', 0)  # Кол-во десятичных знаков
                logger.info(f'- Кол-во десятичных знаков: {scale}')

                # Торговый счет для класса тикера
                try:
                    trade_account_data = qp_provider.get_trade_account(class_code)
                    if trade_account_data and 'data' in trade_account_data:
                        trade_account = trade_account_data['data']
                        logger.info(f'- Торговый счет: {trade_account}')
                    else:
                        logger.warning(f'- Торговый счет: не найден')
                except Exception as e:
                    logger.warning(f'- Торговый счет: ошибка получения - {e}')

                # Последняя цена сделки
                try:
                    last_price_data = qp_provider.get_param_ex(class_code, sec_code, 'LAST')
                    if last_price_data and 'data' in last_price_data:
                        param_value = last_price_data['data']['param_value']
                        if param_value and param_value.strip():
                            last_price = float(param_value)
                            logger.info(f'- Последняя цена сделки: {last_price}')
                        else:
                            logger.warning(f'- Последняя цена сделки: нет данных (пустое значение)')
                    else:
                        logger.warning(f'- Последняя цена сделки: нет данных')
                except Exception as e:
                    logger.error(f'- Ошибка получения последней цены: {e}')

                # Стоимость шага цены
                try:
                    step_price_data = qp_provider.get_param_ex(class_code, sec_code, 'STEPPRICE')
                    if step_price_data and 'data' in step_price_data:
                        step_price_value = step_price_data['data']['param_value']
                        if step_price_value and step_price_value.strip():
                            step_price = float(step_price_value)
                            logger.info(f'- Стоимость шага цены: {step_price}')

                            # Расчет цены за лот
                            if lot_size > 0 and min_price_step > 0:
                                try:
                                    lot_price = last_price // min_price_step * step_price  # Цена за лот в рублях
                                    logger.info(f'- Цена за лот: {last_price} / {min_price_step} * {step_price} = {lot_price:.2f} руб.')

                                    if lot_size > 0:
                                        pcs_price = lot_price / lot_size  # Цена за штуку в рублях
                                        logger.info(f'- Цена за штуку: {lot_price:.2f} / {lot_size} = {pcs_price:.2f} руб.')
                                except Exception as e:
                                    logger.error(f'- Ошибка расчета цен: {e}')
                        else:
                            logger.warning(f'- Стоимость шага цены: нет данных')
                    else:
                        logger.warning(f'- Стоимость шага цены: нет данных')
                except Exception as e:
                    logger.warning(f'- Стоимость шага цены: ошибка получения - {e}')

                # Дополнительные параметры для фьючерсов
                if class_code == 'SPBFUT':
                    try:
                        # Время экспирации
                        expiry_data = qp_provider.get_param_ex(class_code, sec_code, 'EXPIRATION_DATE')
                        if expiry_data and 'data' in expiry_data:
                            expiry = expiry_data['data']['param_value']
                            logger.info(f'- Дата экспирации: {expiry}')
                    except:
                        pass

                    try:
                        # Текущий объем
                        volume_data = qp_provider.get_param_ex(class_code, sec_code, 'VOLUME')
                        if volume_data and 'data' in volume_data:
                            volume = volume_data['data']['param_value']
                            logger.info(f'- Объем: {volume}')
                    except:
                        pass

                    try:
                        # Открытый интерес
                        open_interest_data = qp_provider.get_param_ex(class_code, sec_code, 'NUMCONTRACTS')
                        if open_interest_data and 'data' in open_interest_data:
                            open_interest = open_interest_data['data']['param_value']
                            logger.info(f'- Открытый интерес: {open_interest}')
                    except:
                        pass

            else:
                logger.error(f"Не удалось получить информацию о тикере {dataname}")

        except Exception as e:
            logger.error(f"Ошибка обработки тикера {dataname}: {e}")
            logger.error(traceback.format_exc())

    # Также можно попробовать получить список всех доступных инструментов
    logger.info(f"\n{'='*50}")
    logger.info("Попытка получить список классов инструментов...")
    logger.info(f"{'='*50}")

    try:
        classes = qp_provider.get_classes_list()
        logger.info(f"Доступные классы: {classes}")
    except Exception as e:
        logger.error(f"Ошибка получения списка классов: {e}")

    qp_provider.close_connection_and_thread()  # Перед выходом закрываем соединение для запросов и поток обработки функций обратного вызова