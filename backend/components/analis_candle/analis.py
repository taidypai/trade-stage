import json

# Чтение из файла
def get_candels():
    with open('data.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data

def get_total_veriebels(candle):
    try:
        if candle['color'] == 'green':
            total_max = float(candle['close'])
            total_low = float(candle['open'])
        elif candle['color'] == 'red':
            total_max = float(candle['open'])
            total_low = float(candle['close'])
        else:
            # Для серых свечей или других случаев
            total_max = float(candle['high'])
            total_low = float(candle['low'])
        return total_max, total_low
    except (KeyError, ValueError, TypeError):
        # Возвращаем значения по умолчанию в случае ошибки
        return float(candle.get('high', 100)), float(candle.get('low', 100))

def check_gap_overlap(gap_top, gap_bottom, start_index, candles):
    current_top = gap_top
    current_bottom = gap_bottom

    # Проверяем все свечи после гэпа
    for j in range(start_index, len(candles)):
        high_j = float(candles[j]['high'])
        low_j = float(candles[j]['low'])
        if high_j >= current_bottom and high_j < current_top:
        # Обновляем верхнюю границу - опускаем ее до уровня касания
            current_bottom = high_j

        if low_j <= current_top and low_j > current_bottom:
            # Обновляем нижнюю границу - поднимаем ее до уровня касания
            current_top = low_j

        # Если свеча полностью перекрывает текущий гэп
        # (для медвежьего гэпа: low_j <= current_bottom и high_j >= current_top)
        if low_j <= current_bottom and high_j >= current_top:
            # Гэп полностью перекрыт
            return None

    # Если гэп еще существует (верхняя граница больше нижней)
    if current_top > current_bottom:
        return (current_top, current_bottom)
    else:
        return None


def get_gaps():
    """Функция для получения НЕПЕРЕКРЫТЫХ гэпов из данных свечей"""
    candels_data = get_candels()

    # Проверяем формат данных
    if isinstance(candels_data, dict) and 'candles' in candels_data:
        candles = candels_data['candles']
    elif isinstance(candels_data, list):
        candles = candels_data
    else:
        return []

    gaps = []

    # Проверяем, что свечей достаточно для анализа
    if len(candles) < 3:
        return gaps

    # Проходим по свечам, начиная с третьей
    for i in range(2, len(candles)):
        candle_1 = candles[i-2]  # Первая свеча (самая старая)
        candle_2 = candles[i-1]  # Вторая свеча
        candle_3 = candles[i]    # Третья свеча (самая новая)

        # Получаем HIGH и LOW для каждой свечи
        high1, low1 = float(candle_1['high']), float(candle_1['low'])
        high2, low2 = float(candle_2['high']), float(candle_2['low'])
        high3, low3 = float(candle_3['high']), float(candle_3['low'])

        # Определяем имбаланс - место, которое не перекрыто фитилями
        # Медвежий гэп (нисходящий): верхняя точка 3-й свечи ниже нижней точки 1-й свечи
        if high3 < low1:
            gap_top = low1  # Верхняя точка гэпа = low первой свечи
            gap_bottom = high3  # Нижняя точка гэпа = high третьей свечи

            # Проверяем перекрытие гэпа
            result = check_gap_overlap(gap_top, gap_bottom, i + 1, candles)

            if result is not None:
                current_top, current_bottom = result
                is_partial = (current_top != gap_top) or (current_bottom != gap_bottom)

                gap_info = {
                    'top': current_top,
                    'bottom': current_bottom,
                    'candle_number': i + 1,  # Номер свечи, на которой появился гэп
                    'type': 'bearish',  # Медвежий гэп
                    'imbalance': current_top - current_bottom,
                }
                gaps.append(gap_info)

        # Бычий гэп (восходящий): нижняя точка 3-й свечи выше верхней точки 1-й свечи
        elif low3 > high1:
            gap_top = low3  # Верхняя точка гэпа = low третьей свечи
            gap_bottom = high1  # Нижняя точка гэпа = high первой свечи

            # Для бычьего гэпа нужно инвертировать логику проверки
            # В бычьем гэпе: low3 (верх) > high1 (низ)
            # Проверяем перекрытие гэпа
            result = check_gap_overlap(gap_top, gap_bottom, i + 1, candles)

            if result:
                current_top, current_bottom = result
                is_partial = (current_top != gap_top) or (current_bottom != gap_bottom)

                gap_info = {
                    'top': current_top,
                    'bottom': current_bottom,
                    'candle_number': i + 1,  # Номер свечи, на которой появился гэп
                    'type': 'bullish',  # Бычий гэп
                    'imbalance': current_top - current_bottom,
                }
                gaps.append(gap_info)

    return gaps

def analis_lev(level, candle):
    try:
        if candle['color'] == 'red':
            if float(level) <= float(candle['open']) and float(level) >= float(candle['close']):
                return False
        elif candle['color'] == 'green':
            if float(level) >= float(candle['open']) and float(level) <= float(candle['close']):
                return False
        # Для серых свечей всегда возвращаем True
        return True
    except (KeyError, ValueError, TypeError):
        return True

def analis_levels(data):
    """Функция для анализа уровней поддержки и сопротивления"""
    if isinstance(data, dict) and 'candles' in data:
        candles = data['candles']
    elif isinstance(data, list):
        candles = data
    else:
        return []

    if not candles:
        return []

    total_max, total_low = get_total_veriebels(candles[0])
    color = candles[0].get('color', 'green')
    LEVELS = []

    if color == 'red':
        start_flag = False
    else:
        start_flag = True

    for candle in candles:
        current_color = candle.get('color', 'green')

        if current_color == 'red':
            flag = False
        else:
            flag = True

        work_total_max, work_total_low = get_total_veriebels(candle)

        # Проверяем, что значения не None
        if work_total_max is not None and work_total_low is not None:
            if work_total_max > total_max:
                total_max = work_total_max
            elif work_total_low < total_low:
                total_low = work_total_low

        if flag != start_flag:
            if flag == False:  # Переход на красную свечу
                LEVELS.append((total_max, candle.get('candle_number', 0)))
                total_low = work_total_low if work_total_low is not None else total_low
            else:  # Переход на зеленую свечу
                LEVELS.append((total_low, candle.get('candle_number', 0)))
                total_max = work_total_max if work_total_max is not None else total_max
        start_flag = flag

    VALIDE_LEVELS = []
    for level in LEVELS:
        lev, number = level
        valid = True

        for candle in candles:
            candle_num = candle.get('candle_number', 0)
            if candle_num > number:
                if not analis_lev(lev, candle):
                    valid = False
                    break

        if valid:
            # Проверяем, что уровень не None и является числом
            try:
                level_value = float(lev)
                VALIDE_LEVELS.append((level_value, number))
            except (ValueError, TypeError):
                continue

    return VALIDE_LEVELS

def main():
    try:
        candels = get_candels()
        # Получаем уровни
        rezult = analis_levels(candels)
        # Фильтруем только уникальные уровни
        unique_levels = list(set(rezult))
        # Сортируем по возрастанию
        unique_levels.sort()
        # Получаем гэпы
        gaps = get_gaps()
        return unique_levels, gaps
    except Exception as e:
        print(f"Ошибка в анализе: {e}")
        return [], []

if __name__ == "__main__":
    levels, gaps = main()
    print(f"Найдено уровней: {len(levels)}")
    for level in levels:
        if isinstance(level, tuple):
            print(f"  Уровень: {level[0]:.2f} (свеча #{level[1]})")
        else:
            print(f"  {level:.2f}")

    print(f"\nНайдено гэпов: {len(gaps)}")
    for i, gap in enumerate(gaps):
        print(f"  Гэп {i+1}: Верх {gap['top']:.2f}, Низ {gap['bottom']:.2f}, Свеча #{gap['candle_number']}, Тип: {gap['type']}")
