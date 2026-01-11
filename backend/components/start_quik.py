import subprocess
import time
import os
import psutil
import sys
import ctypes
from ctypes import wintypes
import pyautogui
from datetime import datetime
import traceback
from PIL import Image
import tempfile
import shutil

sys.path.append(r"C:\Users\Вадим\Documents\python\trade-brain")
import config

class Quik_START_Launcher:
    def __init__(self):
        # Настройки Quik
        self.quik_path = config.quik_path
        self.quik_dir = os.path.dirname(self.quik_path)
        self.password = config.quik_password

        # Счетчик попыток
        self.attempt_count = 0
        self.max_attempts = 5

        # Временный файл для скриншота
        self.temp_screenshot = None

        # Папки для удаления (если они существуют от старых запусков)
        self.folders_to_clean = [
            os.path.join(os.path.dirname(__file__), "quik_screenshots"),
            os.path.join(os.path.dirname(__file__), "screenshots"),
            os.path.join(os.path.dirname(__file__), "logs"),
            os.path.join(os.path.dirname(__file__), "quik_logs"),
            os.path.join(os.path.dirname(__file__), "login_screenshots"),
            os.path.join(os.path.dirname(__file__), "templates")
        ]

    def switch_layout(self):
        """Переключает на английскую раскладку"""
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        user32.PostMessageW(hwnd, 0x0050, 0, 0x0409)
        return True

    def take_and_analyze_screenshot(self):
        """
        Делает скриншот и сразу анализирует
        Возвращает: True - вход успешен, False - ошибка
        """
        try:
            # Размеры экрана
            screen_width, screen_height = pyautogui.size()

            # Область для маленького окна (400x250 в центре)
            region_width = 400
            region_height = 250
            left = (screen_width - region_width) // 2
            top = (screen_height - region_height) // 2

            # Делаем скриншот
            screenshot = pyautogui.screenshot(region=(left, top, region_width, region_height))

            # Сохраняем во временный файл (будет удален после анализа)
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            self.temp_screenshot = temp_file.name
            screenshot.save(self.temp_screenshot)

            # Анализируем
            return self.analyze_screenshot_in_memory(screenshot)

        except Exception as e:
            print(f"✗ Ошибка скриншота: {e}")
            return False

    def analyze_screenshot_in_memory(self, screenshot):
        """
        Анализирует скриншот в памяти (без сохранения файла)
        Делим пополам, ищем красный в левой части
        """
        try:
            # Конвертируем в RGB
            if screenshot.mode != 'RGB':
                screenshot = screenshot.convert('RGB')

            width, height = screenshot.size

            # Делим вертикально пополам
            left_half = screenshot.crop((0, 0, width // 2, height))

            # Ищем красный цвет в левой части
            red_count = 0
            total_checked = 0

            # Проверяем каждый 3-й пиксель
            step = 3
            for x in range(0, width // 2, step):
                for y in range(0, height, step):
                    r, g, b = left_half.getpixel((x, y))

                    # Красный: R высокий, G и B низкие
                    if r > 180 and g < 100 and b < 100:  # Ярко-красный
                        red_count += 3
                    elif r > 150 and g < 80 and b < 80:  # Средний
                        red_count += 2
                    elif r > 120 and g < 60 and b < 60:  # Светлый
                        red_count += 1

                    total_checked += 1

            # Процент красного
            if total_checked > 0:
                red_percent = (red_count / total_checked) * 100
                print(f"  Красных пикселей: {red_percent:.2f}%")

                # Правило: >0.5% красного = ошибка
                if red_percent > 0.5:
                    print("  ❌ Обнаружен красный цвет -> ОШИБКА")
                    return False
                else:
                    print("  ✅ Красного нет -> УСПЕХ")
                    return True

            return False

        except Exception as e:
            print(f"✗ Ошибка анализа: {e}")
            return False

    def cleanup_temp_files(self):
        """Очистка временных файлов"""
        # Удаляем временный скриншот
        if self.temp_screenshot and os.path.exists(self.temp_screenshot):
            try:
                os.remove(self.temp_screenshot)
                self.temp_screenshot = None
            except:
                pass

        # Удаляем все папки из списка
        self.cleanup_old_folders()

    def cleanup_old_folders(self):
        """Удаляет старые папки от предыдущих запусков"""
        for folder_path in self.folders_to_clean:
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path, ignore_errors=True)
                    print(f"✓ Удалена папка: {os.path.basename(folder_path)}")
                except Exception as e:
                    print(f"⚠ Не удалось удалить {folder_path}: {e}")

    def perform_login_attempt(self):
        """Одна попытка входа"""
        print(f"\n{'='*50}")
        print(f"🔹 ПОПЫТКА #{self.attempt_count}")
        print(f"{'='*50}")

        try:
            # Открываем окно пароля
            pyautogui.hotkey('ctrl', 'q')
            time.sleep(2)

            # Вводим пароль
            pyautogui.write(self.password)
            time.sleep(1)

            # Нажимаем Enter
            pyautogui.press('enter')

            # Ждем и делаем скриншот + анализ
            time.sleep(5)
            success = self.take_and_analyze_screenshot()

            # Очищаем временный файл
            self.cleanup_temp_files()

            return success

        except Exception as e:
            print(f"✗ Ошибка: {e}")
            self.cleanup_temp_files()
            return False

    def check_quik_running(self):
        """Проверяет, запущен ли QUIK"""
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'].lower()
                if 'quik' in name or 'info' in name:
                    return True
            except:
                pass
        return False

    def start_quik(self):
        """Запускает QUIK"""
        try:
            self.switch_layout()
            subprocess.Popen([self.quik_path], cwd=self.quik_dir)
            print("✓ QUIK запущен")
            time.sleep(25)  # Ждем загрузки
            return True
        except Exception as e:
            print(f"✗ Ошибка запуска: {e}")
            return False

    def activate_quik_window(self):
        """Активирует окно QUIK"""
        try:
            pyautogui.click(pyautogui.size().width // 2, pyautogui.size().height // 2)
            time.sleep(1)
            return True
        except:
            return False

    def run(self):
        """Главный цикл"""
        print("🚀 АВТОМАТИЧЕСКИЙ ВХОД В QUIK")

        # Сначала чистим старые папки
        self.cleanup_old_folders()

        # Запускаем QUIK если не запущен
        if not self.check_quik_running():
            print("🔄 Запускаем QUIK...")
            if not self.start_quik():
                return False
        else:
            print("✓ QUIK уже запущен")

        # Активируем окно
        self.activate_quik_window()
        time.sleep(2)

        # Цикл попыток входа
        login_success = False

        while self.attempt_count < self.max_attempts and not login_success:
            self.attempt_count += 1

            # Пробуем войти
            attempt_result = self.perform_login_attempt()

            if attempt_result:
                # Успех - проверяем файл подтверждения
                print("\n🎉 ВХОД УСПЕШЕН!")

                time.sleep(3)
                try:
                    with open(config.CREATE_PRICE, 'r') as f:
                        if f.read().strip():
                            print("✅ Файл подтверждения OK")
                        else:
                            print("⚠ Файл пуст")
                except:
                    print("⚠ Файл не найден")

                login_success = True
                break
            else:
                # Ошибка - закрываем окно и пробуем снова
                print("\n❌ ОШИБКА ВХОДА")

                pyautogui.press('enter')
                time.sleep(1)

                if self.attempt_count < self.max_attempts:
                    print(f"⏳ Пробуем снова через 3 секунды...")
                    time.sleep(3)
                    self.activate_quik_window()

        # Финальная очистка
        self.cleanup_temp_files()

        # Итог
        if login_success:
            print(f"\n🎊 УСПЕХ за {self.attempt_count} попыток")
            return True
        else:
            print(f"\n💀 НЕ УДАЛОСЬ ВОЙТИ за {self.attempt_count} попыток")
            return False


def quik_main():
    """Точка входа"""
    try:
        launcher = Quik_START_Launcher()
        result = launcher.run()

        print("\n" + "=" * 50)
        print("✅ УСПЕХ" if result else "❌ НЕУДАЧА")
        print("=" * 50)

        return result

    except KeyboardInterrupt:
        print("\n\n⚠ Прервано")
        return False
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Настройки pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.7

    success = main()
    sys.exit(0 if success else 1)