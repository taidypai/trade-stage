import tkinter as tk
import random
import datetime
import json
import os

class CandleStickChart:
    def __init__(self, root):
        self.root = root
        self.root.title("Генератор свечных графиков")
        self.root.geometry("1200x700")

        # Данные для свечей
        self.candles = []
        self.current_price = 100  # Начальная цена
        self.levels = []  # Список уровней для отрисовки (теперь с номерами свечей)
        self.gaps = []   # Список гэпов для отрисовки

        # Для рисования линии и отображения цены
        self.drawing = False
        self.line_start_y = 0
        self.price_label = None
        self.horizontal_line_id = None
        self.current_line_y = 0
        self.drawn_levels = []  # Список ID нарисованных уровней
        self.drawn_gaps = []    # Список ID нарисованных гэпов

        # Создание главного фрейма
        main_frame = tk.Frame(root, bg="#212121", padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Панель управления
        control_frame = tk.Frame(main_frame, bg="#212121")
        control_frame.pack(fill=tk.X)

        # Кнопки управления
        tk.Button(control_frame, text="Сгенерировать график",
                 command=self.generate_and_analyze, bg="white",
                 font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        # Количество свечей
        tk.Label(control_frame, text="Количество свечей",
                bg="#212121", fg="white", font=("Arial", 10)).pack(side=tk.LEFT, padx=(20, 5))

        self.candle_count = tk.IntVar(value=50)
        spinbox = tk.Spinbox(control_frame, from_=10, to=200,
                            textvariable=self.candle_count, width=10,
                            font=("Arial", 10))
        spinbox.pack(side=tk.LEFT, padx=5)

        # Метка для информации об уровнях и гэпах
        self.levels_info = tk.Label(control_frame, text="Уровней: 0 | Гэпов: 0",
                                   bg="#212121", fg="white", font=("Arial", 10))
        self.levels_info.pack(side=tk.RIGHT, padx=20)

        # Контейнер для графика
        chart_frame = tk.Frame(main_frame)
        chart_frame.pack(fill=tk.BOTH, expand=True)

        # Холст для графика
        self.canvas = tk.Canvas(chart_frame, bg='#212121', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Привязка событий мыши
        self.canvas.bind("<ButtonPress-1>", self.start_drawing)
        self.canvas.bind("<B1-Motion>", self.draw_horizontal_line)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drawing)
        self.canvas.bind("<Motion>", self.show_price)

        # Полоса прокрутки для графика
        self.scrollbar = tk.Scrollbar(chart_frame, orient=tk.HORIZONTAL,
                                     command=self.canvas.xview)
        self.scrollbar.pack(fill=tk.X)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)

        # Автоматическая генерация начального графика
        self.generate_and_analyze()

    def generate_and_analyze(self):
        """Генерация графика, сохранение и автоматический анализ"""
        self.generate_candles()
        self.save_data()
        self.analyze_levels()

    def analyze_levels(self):
        """Анализ уровней и гэпов из файла data.json"""
        # Проверяем существование файла
        if not os.path.exists('data.json'):
            print("Файл data.json не найден.")
            return

        # Импортируем функцию анализа
        try:
            from analis import analis_levels, get_gaps, get_candels
        except ImportError as e:
            print(f"Ошибка импорта модуля analis: {e}")
            return

        # Загружаем данные
        with open('data.json', 'r', encoding='utf-8') as file:
            data = json.load(file)

        # Анализируем уровни
        self.levels = analis_levels(data)

        # Получаем гэпы
        self.gaps = get_gaps()

        # Очищаем старые уровни и гэпы
        self.clear_drawn_levels()
        self.clear_drawn_gaps()

        # Рисуем новые уровни
        self.draw_analysis_levels()

        # Рисуем гэпы
        self.draw_gaps()

        # Обновляем информацию
        self.levels_info.config(text=f"Уровней: {len(self.levels)} | Гэпов: {len(self.gaps)}")

        print(f"Найдено {len(self.levels)} уровней")
        for i, (level, candle_num) in enumerate(self.levels):
            print(f"  Уровень {i+1}: {level:.2f} (со свечи #{candle_num})")

        print(f"Найдено {len(self.gaps)} гэпов")
        for i, gap in enumerate(self.gaps):
            print(f"  Гэп {i+1}: Верх {gap['top']:.2f}, Низ {gap['bottom']:.2f}, Свеча #{gap['candle_number']}")


    def clear_drawn_levels(self):
        """Очистка нарисованных уровней"""
        for level_id in self.drawn_levels:
            self.canvas.delete(level_id)
        self.drawn_levels = []

    def clear_drawn_gaps(self):
        """Очистка нарисованных гэпов"""
        for gap_id in self.drawn_gaps:
            self.canvas.delete(gap_id)
        self.drawn_gaps = []

    def clear_levels(self):
        """Очистка всех уровней и гэпов"""
        self.levels = []
        self.gaps = []
        self.clear_drawn_levels()
        self.clear_drawn_gaps()
        self.levels_info.config(text="Уровней: 0 | Гэпов: 0")
    def draw_gaps(self):
        """Рисование гэпов на графике"""
        if not self.gaps or not self.candles:
            return

        # Получаем размеры холста
        canvas_width = self.canvas.winfo_width() - 40
        canvas_height = self.canvas.winfo_height() - 40

        if canvas_width <= 0 or canvas_height <= 0:
            canvas_width = 800
            canvas_height = 500

        # Находим минимальные и максимальные значения для масштабирования
        all_lows = [candle['low'] for candle in self.candles]
        all_highs = [candle['high'] for candle in self.candles]

        min_price = min(all_lows)
        max_price = max(all_highs)
        price_range = max_price - min_price

        # Добавляем отступы сверху и снизу
        padding = price_range * 0.1
        min_price -= padding
        max_price += padding
        price_range = max_price - min_price

        if price_range == 0:
            price_range = 1

        # Масштабирующий коэффициент
        scale_y = canvas_height / price_range

        # Параметры свечей для расчета координат
        candle_width = 6
        spacing = 2

        # Рассчитываем общую ширину графика
        total_width = len(self.candles) * (candle_width + spacing) + 40

        # Рисуем каждый гэп
        for gap in self.gaps:
            try:
                top_price = float(gap['top'])
                bottom_price = float(gap['bottom'])
                candle_num = int(gap['candle_number'])

                # Рассчитываем Y координаты верхней и нижней точки гэпа
                y_top = canvas_height - (top_price - min_price) * scale_y + 20
                y_bottom = canvas_height - (bottom_price - min_price) * scale_y + 20

                # Убедимся, что y_top < y_bottom (для прямоугольника)
                if y_top > y_bottom:
                    y_top, y_bottom = y_bottom, y_top

                # Добавим минимальную высоту, чтобы прямоугольник был виден
                min_height = 3
                if (y_bottom - y_top) < min_height:
                    y_bottom = y_top + min_height

                # Рассчитываем X координату гэпа (на своей свече)
                # Вычитаем 1, потому что номера свечей начинаются с 1, а индекс с 0
                candle_index = max(0, candle_num - 1)
                start_x = candle_index * (candle_width + spacing) + 20
                end_x = start_x + 200  # Длина 100 пикселей

                # Ограничиваем позицию
                start_x = max(20, start_x)
                if end_x > total_width:
                    end_x = total_width

                # Рисуем полупрозрачный БЕЛЫЙ прямоугольник для гэпа
                # Полный набор параметров для корректного отображения
                gap_rect = self.canvas.create_rectangle(
                    start_x,      # x1
                    y_top,        # y1
                    end_x,        # x2
                    y_bottom,     # y2
                    fill="#ffffff",      # Белая заливка
                    # outline="#ffffff",   # Белый контур (ОБЯЗАТЕЛЬНО!)
                    width=0,             # Толщина контура
                    stipple="gray12"     # 12.5% непрозрачность
                )

                # Добавляем небольшую метку с ценой гэпа

                # Сохраняем ID нарисованных элементов
                self.drawn_gaps.extend([gap_rect])

            except (ValueError, TypeError) as e:
                print(f"Ошибка при рисовании гэпа {gap}: {e}")
                continue

    def draw_analysis_levels(self):
        """Рисование уровней анализа на графике"""
        if not self.levels or not self.candles:
            return

        # Получаем размеры холста
        canvas_width = self.canvas.winfo_width() - 40
        canvas_height = self.canvas.winfo_height() - 40

        if canvas_width <= 0 or canvas_height <= 0:
            canvas_width = 800
            canvas_height = 500

        # Находим минимальные и максимальные значения для масштабирования
        all_lows = [candle['low'] for candle in self.candles]
        all_highs = [candle['high'] for candle in self.candles]

        min_price = min(all_lows)
        max_price = max(all_highs)
        price_range = max_price - min_price

        # Добавляем отступы сверху и снизу
        padding = price_range * 0.1
        min_price -= padding
        max_price += padding
        price_range = max_price - min_price

        if price_range == 0:
            price_range = 1

        # Масштабирующий коэффициент
        scale_y = canvas_height / price_range

        # Параметры свечей для расчета координат
        candle_width = 6
        spacing = 2

        # Рассчитываем общую ширину графика
        total_width = len(self.candles) * (candle_width + spacing) + 40

        # Рисуем каждый уровень
        for level_data in self.levels:
            try:
                # Распаковываем данные уровня
                if isinstance(level_data, tuple) and len(level_data) == 2:
                    level_value, start_candle_num = level_data
                    level_value = float(level_value)
                    start_candle_num = int(start_candle_num)
                else:
                    # Если формат другой, используем весь уровень
                    level_value = float(level_data)
                    start_candle_num = 0

                # Рассчитываем Y координату уровня
                y = canvas_height - (level_value - min_price) * scale_y + 20

                # Рассчитываем X координату начала уровня (со свечи start_candle_num)
                # Вычитаем 1, потому что номера свечей начинаются с 1, а индекс с 0
                candle_index = max(0, start_candle_num - 1)
                start_x = candle_index * (candle_width + spacing) + candle_width/2 + 20

                # Ограничиваем начальную позицию
                start_x = max(20, start_x)

                # Рассчитываем конечную X координату (300 пикселей от начальной свечи)
                end_x = start_x + 300

                # Не позволяем линии выходить за границы графика
                if end_x > total_width:
                    end_x = total_width

                # Рисуем горизонтальную линию уровня от начальной свечи на 300 пикселей вправо
                # Линия сплошная (без dash) и в 2 раза уже (width=1 вместо 2)
                level_line = self.canvas.create_line(
                    start_x, y,
                    end_x, y,
                    fill="white",
                    width=1,  # В 2 раза уже
                    dash=None  # Сплошная линия
                )

                # Добавляем текстовую метку с ценой уровня в конце линии
                level_text = self.canvas.create_text(
                    end_x + 5, y - 10,
                    text=f"{level_value:.2f}",
                    fill="white",
                    font=("Arial", 9, "bold"),
                    anchor=tk.W
                )

                # Сохраняем ID нарисованных элементов
                self.drawn_levels.extend([level_line, level_text])

            except (ValueError, TypeError) as e:
                print(f"Ошибка при рисовании уровня {level_data}: {e}")
                continue

    def start_drawing(self, event):
        """Начало рисования горизонтальной линии"""
        self.drawing = True
        self.line_start_y = event.y
        self.current_line_y = event.y

        # Сразу создаем горизонтальную линию
        self.draw_horizontal_line(event)

    def draw_horizontal_line(self, event):
        """Рисование горизонтальной линии при движении мыши"""
        if not self.drawing:
            return

        # Обновляем текущую Y координату
        self.current_line_y = event.y

        # Удаляем предыдущую линию
        if self.horizontal_line_id:
            self.canvas.delete(self.horizontal_line_id)

        # Получаем размеры холста
        canvas_width = self.canvas.winfo_width()
        if canvas_width <= 0:
            canvas_width = 800

        # Рисуем горизонтальную линию через весь график
        self.horizontal_line_id = self.canvas.create_line(
            0, self.current_line_y,
            canvas_width, self.current_line_y,
            fill="white",
            width=1,
            dash=(5, 2)
        )

        # Обновляем отображение цены
        self.update_price_display(event.x, self.current_line_y)

    def stop_drawing(self, event):
        """Завершение рисования линии"""
        # Фиксируем окончательную горизонтальную линию
        self.draw_horizontal_line(event)
        self.drawing = False

    def show_price(self, event):
        """Показ цены при движении мыши"""
        if not self.drawing:
            # Показываем цену только при рисовании
            if self.price_label:
                self.canvas.delete(self.price_label)
                self.price_label = None
            return

        self.update_price_display(event.x, self.current_line_y)

    def update_price_display(self, x, y):
        """Обновление отображения цены"""
        # Удаляем предыдущую метку
        if self.price_label:
            self.canvas.delete(self.price_label)

        if not self.candles:
            return

        # Получаем размеры холста
        canvas_width = self.canvas.winfo_width() - 40
        canvas_height = self.canvas.winfo_height() - 40

        if canvas_width <= 0 or canvas_height <= 0:
            canvas_width = 800
            canvas_height = 500

        # Находим минимальные и максимальные значения
        all_lows = [candle['low'] for candle in self.candles]
        all_highs = [candle['high'] for candle in self.candles]

        min_price = min(all_lows)
        max_price = max(all_highs)
        price_range = max_price - min_price

        # Добавляем отступы
        padding = price_range * 0.1
        min_price -= padding
        max_price += padding
        price_range = max_price - min_price

        if price_range == 0:
            return

        # Масштабирующий коэффициент
        scale_y = canvas_height / price_range

        # Преобразуем координату Y в цену
        price = max_price - (y - 20) / scale_y

        # Создаем метку с ценой
        self.price_label = self.canvas.create_text(
            x + 15, y - 15,
            text=f"{price:.2f}",
            fill="red",
            font=("Arial", 10, "bold"),
            anchor=tk.NW
        )

    def clear_lines(self):
        """Очистка всех нарисованных линий"""
        # Удаляем горизонтальные линии
        if self.horizontal_line_id:
            self.canvas.delete(self.horizontal_line_id)
            self.horizontal_line_id = None

        # Удаляем метки цен
        if self.price_label:
            self.canvas.delete(self.price_label)
            self.price_label = None

        # Сбрасываем состояние рисования
        self.drawing = False
        self.line_start_y = 0
        self.current_line_y = 0

    def generate_candle(self):
        """Генерация одной случайной свечи"""
        volatility = random.uniform(0.5, 2.0)

        # Изменение цены
        change = random.uniform(-volatility, volatility)
        new_price = self.current_price * (1 + change / 100)

        # Определение открытия и закрытия
        open_price = self.current_price
        close_price = new_price

        # Определение максимума и минимума
        price_range = max(abs(open_price - close_price), 0.5) * random.uniform(0.5, 1.0)

        if open_price > close_price:
            high = open_price + price_range * random.uniform(0.3, 0.7)
            low = close_price - price_range * random.uniform(0.3, 0.7)
        else:
            high = close_price + price_range * random.uniform(0.3, 0.7)
            low = open_price - price_range * random.uniform(0.3, 0.7)

        # Гарантируем, что high > low и они охватывают open/close
        high = max(high, max(open_price, close_price) + 0.1)
        low = min(low, min(open_price, close_price) - 0.1)

        # Обновление текущей цены
        self.current_price = close_price

        return {
            'open': round(open_price, 4),
            'close': round(close_price, 4),
            'high': round(high, 4),
            'low': round(low, 4)
        }

    def generate_candles(self):
        """Генерация заданного количества свечей"""
        num_candles = self.candle_count.get()
        self.candles = []
        self.current_price = 100  # Сброс начальной цены
        self.clear_levels()  # Очищаем уровни и гэпы при генерации новых свечей

        for _ in range(num_candles):
            self.candles.append(self.generate_candle())

        self.update_display()

    def update_display(self):
        """Обновление графика и отображения данных"""
        # Очистка холста (кроме линий, уровней и гэпов)
        items = self.canvas.find_all()
        for item in items:
            # Сохраняем только горизонтальные линии, уровни анализа и гэпы
            if ((self.horizontal_line_id and item == self.horizontal_line_id) or
                item in self.drawn_levels or
                item in self.drawn_gaps):
                continue
            self.canvas.delete(item)

        if not self.candles:
            return

        # Получаем размеры холста
        canvas_width = self.canvas.winfo_width() - 40
        canvas_height = self.canvas.winfo_height() - 40

        if canvas_width <= 0 or canvas_height <= 0:
            canvas_width = 800
            canvas_height = 500

        # Уменьшаем размер свечей
        candle_width = 6
        spacing = 2

        # Находим минимальные и максимальные значения для масштабирования
        all_lows = [candle['low'] for candle in self.candles]
        all_highs = [candle['high'] for candle in self.candles]

        min_price = min(all_lows)
        max_price = max(all_highs)
        price_range = max_price - min_price

        # Добавляем отступы сверху и снизу
        padding = price_range * 0.1
        min_price -= padding
        max_price += padding
        price_range = max_price - min_price

        if price_range == 0:
            price_range = 1

        # Масштабирующий коэффициент
        scale_y = canvas_height / price_range

        # Рассчитываем общую ширину графика
        total_width = len(self.candles) * (candle_width + spacing) + 40

        # Рисование свечей
        for i, candle in enumerate(self.candles):
            x = i * (candle_width + spacing) + candle_width/2 + 20

            # Координаты для тела свечи
            y_open = canvas_height - (candle['open'] - min_price) * scale_y + 20
            y_close = canvas_height - (candle['close'] - min_price) * scale_y + 20

            # Координаты для теней
            y_high = canvas_height - (candle['high'] - min_price) * scale_y + 20
            y_low = canvas_height - (candle['low'] - min_price) * scale_y + 20

            # Определение цвета свечи
            if candle['close'] >= candle['open']:
                color = '#089981'  # Зеленый для бычьей свечи
                body_top = min(y_open, y_close)
                body_bottom = max(y_open, y_close)
                shadow_color = '#089981'  # Темно-зеленый для тени
            else:
                color = '#F23645'  # Красный для медвежьей свечи
                body_top = min(y_open, y_close)
                body_bottom = max(y_open, y_close)
                shadow_color = '#F23645'  # Темно-красный для тени

            # Рисование тени (high-low line)
            self.canvas.create_line(x, y_high, x, y_low, fill=shadow_color, width=1)

            # Рисование тела свечи
            self.canvas.create_rectangle(x - candle_width/2, body_top,
                                        x + candle_width/2, body_bottom,
                                        fill=color, outline=color, width=1)

        # Перерисовываем горизонтальную линию если она была
        if self.drawing and self.horizontal_line_id:
            # Сохраняем Y координату линии
            line_y = self.current_line_y
            # Удаляем старую линию
            self.canvas.delete(self.horizontal_line_id)
            # Рисуем новую линию через весь график
            self.horizontal_line_id = self.canvas.create_line(
                0, line_y,
                total_width, line_y,
                fill="white",
                width=1,
                dash=(5, 2)
            )

        # Обновляем область прокрутки
        self.canvas.config(scrollregion=(0, 0, total_width, canvas_height + 40))

    def save_data(self):
        """Сохранение данных в JSON файл"""
        filename = "data.json"

        try:
            # Подготавливаем данные для сохранения
            save_data = {
                "candles": []
            }

            # Добавляем номера и цвета свечей
            for i, candle in enumerate(self.candles):
                candle_data = candle.copy()
                candle_data["candle_number"] = i + 1

                # Определяем и добавляем цвет свечи
                if candle_data["close"] > candle_data["open"]:
                    candle_data["color"] = "green"  # Бычья свеча
                elif candle_data["close"] < candle_data["open"]:
                    candle_data["color"] = "red"    # Медвежья свеча
                else:
                    candle_data["color"] = "gray"   # Нейтральная (додж)

                save_data["candles"].append(candle_data)

            # Сохраняем в JSON
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)

            print(f"Данные автоматически сохранены в файл: {filename}")

        except Exception as e:
            print(f"Ошибка при сохранении файла: {e}")

    def clear_chart(self):
        """Очистка графика и данных"""
        self.candles = []
        self.current_price = 100
        self.levels = []
        self.gaps = []
        self.canvas.delete("all")

        # Очищаем все нарисованные элементы
        self.clear_drawn_levels()
        self.clear_drawn_gaps()
        self.clear_lines()
        self.levels_info.config(text="Уровней: 0 | Гэпов: 0")

def main():
    root = tk.Tk()
    app = CandleStickChart(root)
    root.mainloop()

if __name__ == "__main__":
    main()