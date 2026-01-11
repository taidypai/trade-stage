def transform_file_to_dict(data_line):
    instruments = {}
    line = data_line.strip()

    # Разделяем тикер и остальное
    ticker, rest = line.split(':', 1)
    ticker = ticker.strip()

    # Убираем пробел между числами в конце: "6 869.93" -> "6869.93"
    import re
    rest = re.sub(r'(\d)\s+(\d)', r'\1\2', rest)

    # Теперь разделяем по слешам (должно быть 7 частей)
    parts = rest.split('/')

    if len(parts) != 7:
        raise ValueError(f"Неправильный формат строки. Ожидается 7 параметров через '/', получено {len(parts)}: {parts}")

    # Извлекаем все параметры
    step = parts[0].strip().replace(',', '.')
    step_cost = parts[1].strip().replace(',', '.')
    commission_for_limit = parts[2].strip().replace(',', '.')
    commission_for_market = parts[3].strip().replace(',', '.')
    commission_for_cliring = parts[4].strip().replace(',', '.')
    lot_price_long = parts[5].strip().replace(',', '.')
    lot_price_short = parts[6].strip().replace(',', '.')

    instruments[ticker] = {
        'step': step,
        'step_cost': step_cost,
        'commission_for_limit': commission_for_limit,
        'commission_for_market': commission_for_market,
        'commission_for_cliring': commission_for_cliring,
        'lot_price_long': lot_price_long,
        'lot_price_short': lot_price_short
    }

    return instruments


# Пример использования с новым форматом
if __name__ == "__main__":
    # Тест с новым форматом
    test_data = 'IMOEXF:0,5/5/0.025/0.05/0.01/6869.93/6869.93'
    result = transform_file_to_dict(test_data)
    print(f"Результат: {result}")

    # Или так (как у вас в коде):
    ticker = "IMOEXF"
    step = "0,5"
    step_cost = "5"
    commission_for_limit = "0.025"
    commission_for_market = "0.05"
    commission_for_cliring = "0.01"
    lot_price_long = "6869.93"
    lot_price_short = "6869.93"

    data_string = f'{ticker}:{step}/{step_cost}/{commission_for_limit}/{commission_for_market}/{commission_for_cliring}/{lot_price_long}/{lot_price_short}'
    result2 = transform_file_to_dict(data_string)
    print(f"Результат 2: {result2}")