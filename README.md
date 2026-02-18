Предисловие: Из за тафталогии в словах Backend и Frontend, я заменю их на back = Backend и Front = Frontend и буду употреблять как один так и другой вариант, поэтому если увидите B знайте я имею ввиду слово Backend и также для f.

connect/ - 3 Соединение Backend и Frontend
    Струтура
        trade-stage/
         │
         ├── backend/
         │   ├── components/
         │   │    ├── analis_candle/
         │   │    │    ├── analis.py
         │   │    │    ├── config_init.py
         │   │    │    └── del.py
         │   │    │
         │   │    ├── quik_components/
         │   │    │    ├── quik_account.py
         │   │    │    ├── quik_ticker.py
         │   │    │    └── quik_transaction.py
         │   │    │
         │   │    ├── logger.py
         │   │    ├── start_quik.py
         │   │    ├── tg_message.py
         │   │    └── time_service.py
         │   │
         │   ├── QuikPy/
         │   │    ├── __init__.py
         │   │    ├── QuikPy.py
         │   │    ├── README.md
         │   │    └── setup.py
         │   │
         │   └── services/
         │        ├── get_price_service/
         │        │    ├── __init__.py
         │        │    └── detector_price.py
         │        │
         │        ├── impuls_service/
         │        │    ├── __init__.py
         │        │    └── detector_impuls.py
         │        │
         │        ├── liquidity_service/
         │        │    ├── __init__.py
         │        │    └── detector_liquid.py
         │        │
         │        ├── order_block_service/
         │        │    ├── __init__.py
         │        │    └── detector_orb.py
         │        │
         │        ├── run_service/
         │        │    ├── __init__.py
         │        │    └── run_all.py
         │        │
         │        └── trading_engine/
         │             └── __init__.py
         │
         ├── docs/
         │    ├── QuikPy/
         │    │    ├── Examples/
         │    │    ├── QUIK/
         │    │    │    └── lua/
         │    │    │         ├── config.json
         │    │    │         ├── dkjson.lua
         │    │    │         ├── qscallbacks.lua
         │    │    │         ├── qsfunctions.lua
         │    │    │         ├── qsutils.lua
         │    │    │         ├── Quik_2.lua
         │    │    │         ├── QuikSharp.lua
         │    │    │         ├── socket.lua
         │    │    │         └── socket/
         │    │    │              └── core.dll
         │    │    ├── __init__.py
         │    │    ├── QuikPy.py
         │    │    ├── README.md
         │    │    └── setup.py
         │    ├── README.md
         │    └── Структура.txt
         │
         │
         ├── frontend/
         │    └── helper_pro/
         │         ├── handlers/
         │         │    ├── callback_routers.py
         │         │    └── start_router.py
         │         │
         │         ├── helper_start.py
         │         ├── keyboards.py
         │         └── config_bot.py
         │
         ├── settings/
         │    ├── logs/
         │    │    ├── errors.txt
         │    │    └── info.txt
         │    │
         │    ├── backend_config.py
         │    ├── frontend_config.py
         │    └── market_data.json
         │
         └── README.md
    Файл 3.1 - CONFIG.json

        Файл хранения статичных данных и настроек пользователя.

        3.1.1 - "quik_path" -> Путь к Бирже
        3.1.2 - "quik_password" -> Пароль от биржи
        3.1.3 - "quik_account_number" -> Номер аккаунта для транзакций
        3.1.4 - "finam_api_token" -> Api токен биржи
        3.1.5 - "finam_api_account_id" Api id от аккаунта биржи
        3.1.7 - "FILES"  -> Файловая структура работы Back части
        3.1.8 - "TRADING_TIKERS" -> Торговые пары
        3.1.9 - "INSTRUMENTS" -> Cash словарь для хранения данных с биржи
        3.1.10 -  "TIMEFRAMES" -> Таймфреймы

    Файл 3.2 - CONFIG_PROCESS.json

        Файл для управления процессами Backend-части, он нужен для того, чтобы было проще соединять Front и Back, если они написаны не разных языках и это архитектурное решение упрощает маштабизацию проэкта. В этом документе Frontend часть будет изменять параметры в словарях, а Backend будет обрабатывать измененные параметры.

        3.2.1 - Словарь "start_settings"
            Словарь для стартовых параметров системы Back. Он нужен для того, чтобы корректно запускать Front часть и обрабатывать ошибки.

            1. "status_backend": true or false
                Статус проверки Backend, заполняется автоматически. true - все процессы работают исправно, false - ошибка в back части (При условии ошибки Frontend часть не дает подключиться к данных и высвечивает сообщение об ошибке)
                -> По умолчанию False

            2. "status_day":true or false
                Статус торгового дня, заполняется автоматически. true - торговый день, false - не торговый день (вс и сб)
                -> По умолчанию False

        3.2.2 - Словарь "trade_settings"
            Словарь торговых настроек. С помощью этого словаря Front будет общаться с Back.

            1. "get_data": "Торговая пара (Например VTB-12.25)" -> "VTB-12.25"
                Заполняется Front часть после того, как пользователь выбрал со второй страницы торговую пару для просмотра
                -> Изначально ""

            2. "status_data": true or false
                Заполняется автоматически Back частью. Front ожидает изменения статуса на true и начинает работу по обработке данных.
                -> По умолчанию false

    Файл 3.3 - CRATE_PRICE.json
        Файл для хрянения текущих цен. Файл создасться атоматически и будет постоянно обновляться Back системой (изначально файла не будет).
        3.3.1 "FINAM" -> Словарь цен для биржи Finam
        3.3.2 "OKX" -> Словарь цен для биржи okx
        3.3.3 "FOREX" -> Словарь цен для биржи Forex

    Файл 3.4 - GET_GAP.json
        Файл для хранения данных GAP-ов. Файл, создасться заполниться автоматически, по выбранной торговой паре пользователем (изначально файла не будет).

        3.4.1 "TIMEFRAMES" -> Словарь создаст контейнеры для каждого таймфрема
            1. "candle_id": 0,
            2. "heigh": 0,
            3. "low": 0
            Все по умолчанию 0

    Файл 3.5 - GET_LEVEL.json
        Файл для хрянения текущих уровней. Файл создасться атоматически и будет постоянно обновляться Back системой (изначально файла не будет).

        3.4.1 "TIMEFRAMES" -> Словарь создаст контейнеры для каждого таймфрема
            1. "candle_id": 0,
            2. "price": 0

        Все по умолчанию 0


    Файл 3.6 - 1h.json │
    Файл 3.7 - 4h.json ├─ Файлы для хрянения истории уровней. Все создасться и заполниться Back системой.
    Файл 3.8 - 1d.json │

        "candles": Список свечь в таймфрейме
        [
            {
            "candle_id": 0, -> ID свечи. (Номер по порядку)
            "open": 0, -> Открытие свечи
            "close": 0, -> Закрытие свечи
            "heigh": 0, -> Верхний пик свечи
            "low": 0 -> Нижний пик свечи
            }
        ]

