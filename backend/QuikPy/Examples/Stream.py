# import logging
# from datetime import datetime
# import time
# import sys

# sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")
# from QuikPy import QuikPy


# def _on_quote(data):
#     logger.info(f'Стакан - {data}')


# def _on_all_trade(data):
#     logger.info(f'Обезличенные сделки - {data}')


# if __name__ == '__main__':
#     logger = logging.getLogger('QuikPy.Stream')
#     qp_provider = QuikPy.QuikPy()

#     logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#                         datefmt='%d.%m.%Y %H:%M:%S',
#                         level=logging.DEBUG,
#                         handlers=[logging.FileHandler('Stream.log', encoding='utf-8'),
#                                 logging.StreamHandler()])
#     logging.Formatter.converter = lambda *args: datetime.now(tz=qp_provider.tz_msk).timetuple()

#     # Ваши тикеры для подписки
#     TRADING_TICKERS = {
#         "FINAM": {
#             "IMOEXF": "IMOEXF"
#             # "GLDRUBF": "GLDRUBF",
#             # "NASD-3.26": "NAH6",
#             # "VTBR-3.26": "VBH6",
#             # "YDEX-3.26": "YDH6",
#             # "SBRF-3.26": "SRH6",
#             # "GAZR-3.26": "GZH6",
#             # "BR-1.26": "BRF6"
#         }
#     }

#     # Определяем классы для тикеров (TQBR - акции, SPBFUT - фьючерсы)
#     ticker_classes = {
#         "IMOEXF": "SPBFUT",  # Фьючерс на индекс Мосбиржи
#         "GLDRUBF": "SPBFUT",  # Фьючерс на золото
#         "NAH6": "SPBFUT",    # Фьючерс на NASDAQ (предположительно)
#         "VBH6": "SPBFUT",    # Фьючерс на ВТБ
#         "YDH6": "SPBFUT",    # Фьючерс на индекс
#         "SRH6": "SPBFUT",    # Фьючерс на Сбербанк
#         "GZH6": "SPBFUT",    # Фьючерс на газ
#         "BRF6": "SPBFUT"     # Фьючерс на нефть Brent
#     }

#     # Подписка на все тикеры
#     subscriptions = []

#     # Подписываемся на стаканы для каждого тикера
#     for ticker_key, ticker_code in TRADING_TICKERS["FINAM"].items():
#         class_code = ticker_classes.get(ticker_code, "SPBFUT")  # По умолчанию SPBFUT для фьючерсов

#         # Запрос текущего стакана
#         try:
#             quote_data = qp_provider.get_quote_level2(class_code, ticker_code)
#             print(quote_data)
#             logger.info(f'Текущий стакан {class_code}.{ticker_code}: {quote_data["data"]}')
#         except Exception as e:
#             logger.error(f'Ошибка при получении стакана для {ticker_code}: {e}')
#             continue

#         # Подписка на изменения стакана
#         try:
#             subscription_result = qp_provider.subscribe_level2_quotes(class_code, ticker_code)
#             logger.info(f'Подписка на изменения стакана {class_code}.{ticker_code}: {subscription_result["data"]}')

#             # Проверяем статус подписки
#             status_result = qp_provider.is_subscribed_level2_quotes(class_code, ticker_code)
#             logger.info(f'Статус подписки для {ticker_code}: {status_result["data"]}')

#             subscriptions.append((class_code, ticker_code))

#         except Exception as e:
#             logger.error(f'Ошибка при подписке на {ticker_code}: {e}')

#     # Подписываемся на события обновления стакана
#     qp_provider.on_quote.subscribe(_on_quote)

#     # Получаем обновления в течение заданного времени
#     sleep_secs = 60  # Слушаем 60 секунд (можно изменить)
#     logger.info(f'Получаем обновления в течение {sleep_secs} секунд')

#     try:
#         time.sleep(sleep_secs)
#     except KeyboardInterrupt:
#         logger.info('Получен сигнал прерывания')

#     # Отписываемся от всех тикеров
#     logger.info('Отмена подписок на все тикеры...')

#     for class_code, ticker_code in subscriptions:
#         try:
#             unsubscribe_result = qp_provider.unsubscribe_level2_quotes(class_code, ticker_code)
#             logger.info(f'Отмена подписки для {ticker_code}: {unsubscribe_result["data"]}')

#             # Проверяем статус подписки после отмены
#             status_result = qp_provider.is_subscribed_level2_quotes(class_code, ticker_code)
#             logger.info(f'Статус подписки для {ticker_code} после отмены: {status_result["data"]}')
#         except Exception as e:
#             logger.error(f'Ошибка при отмене подписки для {ticker_code}: {e}')

#     # Отменяем обработчик событий
#     qp_provider.on_quote.unsubscribe(_on_quote)

#     # Выход
#     qp_provider.close_connection_and_thread()

import logging  # Выводим лог на консоль и в файл
from datetime import datetime  # Дата и время
from time import time
import os.path

import pandas as pd
import sys  # Выход из точки входа
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage\backend")
from QuikPy import QuikPy  # Работа с QUIK из Python через LUA скрипты QUIK#


logger = logging.getLogger('QuikPy.Bars')  # Будем вести лог. Определяем здесь, т.к. возможен внешний вызов ф-ии
datapath = os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'Data', 'QUIK', '')  # Путь сохранения файла истории
delimiter = '\t'  # Разделитель значений в файле истории. По умолчанию табуляция
dt_format = '%d.%m.%Y %H:%M'  # Формат представления даты и времени в файле истории. По умолчанию русский формат


# noinspection PyShadowingNames
def load_candles_from_file(class_code, security_code, tf) -> pd.DataFrame:
    """Получение бар из файла

    :param str class_code: Код режима торгов
    :param str security_code: Код тикера
    :param str tf: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм
    """
    filename = f'{datapath}{class_code}.{security_code}_{tf}.txt'
    if os.path.isfile(filename):  # Если файл существует
        logger.info(f'Получение файла {filename}')
        file_bars = pd.read_csv(filename,  # Имя файла
                                sep=delimiter,  # Разделитель значений
                                usecols=['datetime', 'open', 'high', 'low', 'close', 'volume'],  # Для ускорения обработки задаем колонки, которые будут нужны для исследований
                                parse_dates=['datetime'],  # Колонку datetime разбираем как дату/время
                                dayfirst=True,  # В дате/времени сначала идет день, затем месяц и год
                                index_col='datetime')  # Индексом будет колонка datetime
        file_bars['datetime'] = file_bars.index  # Колонка datetime нужна, чтобы не удалять одинаковые OHLCV на разное время
        logger.info(f'Первый бар    : {file_bars.index[0]:{dt_format}}')
        logger.info(f'Последний бар : {file_bars.index[-1]:{dt_format}}')
        logger.info(f'Кол-во бар    : {len(file_bars)}')
        return file_bars
    else:  # Если файл не существует
        logger.warning(f'Файл {filename} не найден')
        return pd.DataFrame()


# noinspection PyShadowingNames
def get_candles_from_provider(qp_provider, class_code, security_code, tf) -> pd.DataFrame:
    """Получение бар из провайдера

    :param QuikPy qp_provider: Провайдер QUIK
    :param str class_code: Код режима торгов
    :param str security_code: Код тикера
    :param str tf: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм
    """
    # Сопоставление пользовательских таймфреймов с QUIK
    tf_mapping = {
        '1h': 'M60',  # 1 час = 60 минут
        '4h': 'H4',   # 4 часа (проверим, поддерживает ли QUIK)
        '1d': 'D1'    # 1 день
    }

    quik_tf = tf_mapping.get(tf, tf)  # Преобразуем пользовательский TF в QUIK TF

    try:
        time_frame, _ = qp_provider.timeframe_to_quik_timeframe(quik_tf)  # Временной интервал QUIK
    except Exception as e:
        logger.warning(f'Таймфрейм {tf} ({quik_tf}) не распознан. Пробую напрямую: {e}')
        time_frame = quik_tf  # Пробуем использовать как есть

    logger.info(f'Получение истории {class_code}.{security_code} {tf} ({time_frame}) из QUIK')

    try:
        history = qp_provider.get_candles_from_data_source(class_code, security_code, time_frame)  # Получаем все бары из QUIK
    except Exception as e:
        logger.error(f'Ошибка при получении истории для {class_code}.{security_code} {tf}: {e}')
        return pd.DataFrame()

    if not history:  # Если бары не получены
        logger.error('Ошибка при получении истории: История не получена')
        return pd.DataFrame()  # то выходим, дальше не продолжаем
    if 'data' not in history:  # Если бар нет в словаре
        logger.error(f'Ошибка при получении истории: {history}')
        return pd.DataFrame()  # то выходим, дальше не продолжаем
    new_bars = history['data']  # Получаем все бары из QUIK
    if len(new_bars) == 0:  # Если новых бар нет
        logger.info('Новых записей нет')
        return pd.DataFrame()  # то выходим, дальше не продолжаем

    try:
        pd_bars = pd.json_normalize(new_bars)  # Переводим список бар в pandas DataFrame
        pd_bars.rename(columns={'datetime.year': 'year', 'datetime.month': 'month', 'datetime.day': 'day',
                                'datetime.hour': 'hour', 'datetime.min': 'minute', 'datetime.sec': 'second'},
                       inplace=True)  # Чтобы получить дату/время переименовываем колонки
        pd_bars['datetime'] = pd.to_datetime(pd_bars[['year', 'month', 'day', 'hour', 'minute', 'second']])  # Собираем дату/время из колонок
        pd_bars = pd_bars[['datetime', 'open', 'high', 'low', 'close', 'volume']]  # Отбираем нужные колонки
        pd_bars.index = pd_bars['datetime']  # Дата/время также будет индексом
        pd_bars.volume = pd.to_numeric(pd_bars.volume, downcast='integer')  # Объемы могут быть только целыми
        pd_bars.drop_duplicates(keep='last', inplace=True)  # Могут быть получены дубли, удаляем их
        logger.info(f'Первый бар    : {pd_bars.index[0]:{dt_format}}')
        logger.info(f'Последний бар : {pd_bars.index[-1]:{dt_format}}')
        logger.info(f'Кол-во бар    : {len(pd_bars)}')
        return pd_bars
    except Exception as e:
        logger.error(f'Ошибка обработки данных для {class_code}.{security_code}: {e}')
        return pd.DataFrame()


# noinspection PyShadowingNames
def save_candles_to_file(qp_provider, class_code, security_codes, tf='D1',
                         skip_first_date=False, skip_last_date=False, four_price_doji=False):
    """Получение новых бар из провайдера, объединение с имеющимися барами в файле (если есть), сохранение бар в файл

    :param QuikPy qp_provider: Провайдер QUIK
    :param str class_code: Код режима торгов
    :param tuple[str] security_codes: Коды тикеров в виде кортежа
    :param str tf: Временной интервал https://ru.wikipedia.org/wiki/Таймфрейм
    :param bool skip_first_date: Убрать бары на первую полученную дату
    :param bool skip_last_date: Убрать бары на последнюю полученную дату
    :param bool four_price_doji: Оставить бары с дожи 4-х цен
    """
    for security_code in security_codes:  # Пробегаемся по всем тикерам
        logger.info(f"\n{'='*60}")
        logger.info(f"Обработка тикера: {class_code}.{security_code} на таймфрейме {tf}")
        logger.info(f"{'='*60}")

        file_bars = load_candles_from_file(class_code, security_code, tf)  # Получаем бары из файла
        pd_bars = get_candles_from_provider(qp_provider, class_code, security_code, tf)  # Получаем бары из провайдера

        if pd_bars.empty:  # Если бары не получены
            logger.warning('Бары не получены, возможно тикер не существует или временной интервал не поддерживается')
            continue  # то переходим к следующему тикеру, дальше не продолжаем

        if file_bars.empty and skip_first_date:  # Если файла нет, и убираем бары на первую дату
            len_with_first_date = len(pd_bars)  # Кол-во баров до удаления на первую дату
            first_date = pd_bars.index[0].date()  # Первая дата
            pd_bars.drop(pd_bars[pd_bars.index.date == first_date].index, inplace=True)  # Удаляем их
            logger.warning(f'Удалено баров на первую дату {first_date:{dt_format}}: {len_with_first_date - len(pd_bars)}')

        if skip_last_date:  # Если убираем бары на последнюю дату
            len_with_last_date = len(pd_bars)  # Кол-во баров до удаления на последнюю дату
            last_date = pd_bars.index[-1].date()  # Последняя дата
            pd_bars.drop(pd_bars[pd_bars.index.date == last_date].index, inplace=True)  # Удаляем их
            logger.warning(f'Удалено баров на последнюю дату {last_date:{dt_format}}: {len_with_last_date - len(pd_bars)}')

        if not four_price_doji:  # Если удаляем дожи 4-х цен
            len_with_doji = len(pd_bars)  # Кол-во баров до удаления дожи
            pd_bars.drop(pd_bars[pd_bars.high == pd_bars.low].index, inplace=True)  # Удаляем их по условию High == Low
            logger.warning(f'Удалено дожи 4-х цен: {len_with_doji - len(pd_bars)}')

        if len(pd_bars) == 0:  # Если нечего объединять
            logger.info('Новых бар нет')
            continue  # то переходим к следующему тикеру, дальше не продолжаем

        if not file_bars.empty:  # Если файл существует
            pd_bars = pd.concat([file_bars, pd_bars])  # Объединяем файл с данными из QUIK
            pd_bars = pd_bars[~pd_bars.index.duplicated(keep='last')]  # Убираем дубликаты
            pd_bars.sort_index(inplace=True)  # Сортируем по индексу заново

        pd_bars = pd_bars[['open', 'high', 'low', 'close', 'volume']]  # Отбираем нужные колонки
        filename = f'{datapath}{class_code}.{security_code}_{tf}.txt'

        # Создаем директорию, если она не существует
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        logger.info(f'Сохранение файла: {filename}')
        pd_bars.to_csv(filename, sep=delimiter, date_format=dt_format)
        logger.info(f'Первый бар    : {pd_bars.index[0]:{dt_format}}')
        logger.info(f'Последний бар : {pd_bars.index[-1]:{dt_format}}')
        logger.info(f'Кол-во бар    : {len(pd_bars)}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    start_time = time()  # Время начала запуска скрипта
    qp_provider = QuikPy()  # Подключение к локальному запущенному терминалу QUIK

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',  # Формат сообщения
                        datefmt='%d.%m.%Y %H:%M:%S',  # Формат даты
                        level=logging.INFO,  # Уровень логируемых событий INFO для меньшего шума
                        handlers=[logging.FileHandler('Bars.log', encoding='utf-8'), logging.StreamHandler()])  # Лог записываем в файл и выводим на консоль

    # Определяем тикеры из вашего списка
    FINAM_TICKERS = {
        "IMOEXF": "IMOEXF",
        "GLDRUBF": "GLDRUBF",
        "NASD-3.26": "NAH6",
        "VTBR-3.26": "VBH6",
        "YDEX-3.26": "YDH6",
        "SBRF-3.26": "SRH6",
        "GAZR-3.26": "GZH6",
        "BR-1.26": "BRF6"
    }

    # Преобразуем в кортеж тикеров Quik
    security_codes = tuple(FINAM_TICKERS.values())
    class_code = 'SPBFUT'  # Все тикеры - фьючерсы

    logger.info(f"\n{'='*60}")
    logger.info(f"Начало загрузки данных для {len(security_codes)} тикеров")
    logger.info(f"Таймфреймы: 1h, 4h, 1d")
    logger.info(f"{'='*60}")

    # Проверяем соединение и получаем список доступных классов
    try:
        classes = qp_provider.get_classes_list()
        logger.info(f"Доступные классы: {classes}")
    except Exception as e:
        logger.warning(f"Не удалось получить список классов: {e}")

    # Проверяем каждый тикер перед загрузкой
    logger.info("\nПроверка доступности тикеров:")
    available_tickers = []

    for ticker_name, ticker_code in FINAM_TICKERS.items():
        try:
            # Пробуем получить информацию о тикере
            si = qp_provider.get_symbol_info(class_code, ticker_code)
            if si:
                logger.info(f"✓ {ticker_name} ({ticker_code}): {si.get('short_name', 'доступен')}")
                available_tickers.append(ticker_code)
            else:
                logger.warning(f"✗ {ticker_name} ({ticker_code}): не найден")
        except Exception as e:
            logger.warning(f"✗ {ticker_name} ({ticker_code}): ошибка - {str(e)[:50]}")

    if not available_tickers:
        logger.error("Нет доступных тикеров для загрузки!")
        qp_provider.close_connection_and_thread()
        sys.exit(1)

    logger.info(f"\nДоступно для загрузки: {len(available_tickers)} тикеров")

    # Параметры загрузки
    skip_last_date = True  # Если получаем данные внутри сессии, то не берем бары за дату незавершенной сессии
    # skip_last_date = False  # Если получаем данные, когда рынок не работает, то берем все бары

    # Загружаем данные на разных таймфреймах
    timeframes = ['1h', '4h', '1d']

    for tf in timeframes:
        logger.info(f"\n{'='*60}")
        logger.info(f"ЗАГРУЗКА ДАННЫХ НА ТАЙМФРЕЙМЕ: {tf}")
        logger.info(f"{'='*60}")

        start_tf_time = time()
        save_candles_to_file(qp_provider, class_code, available_tickers, tf,
                            skip_last_date=skip_last_date, four_price_doji=True)

        logger.info(f"Загрузка таймфрейма {tf} завершена за {(time() - start_tf_time):.2f} сек")

    qp_provider.close_connection_and_thread()  # Закрываем соединение для запросов и поток обработки функций обратного вызова

    total_time = time() - start_time
    logger.info(f"\n{'='*60}")
    logger.info(f"СКРИПТ ВЫПОЛНЕН ЗА {total_time:.2f} СЕКУНД")
    logger.info(f"{'='*60}")

    print(f'\nСкрипт выполнен за {total_time:.2f} с')
    print(f'\nФайлы сохранены в директории: {datapath}')
    print('\nЗагружены следующие тикеры:')
    for ticker_name, ticker_code in FINAM_TICKERS.items():
        if ticker_code in available_tickers:
            print(f'  ✓ {ticker_name}: {ticker_code}')