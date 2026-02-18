""" python backend/components/start_quik.py """
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт файлов настроек сервиса
from settings import backend_config as config
from backend.components.tg_message import send_tg_message
from backend.services.run.run_all import run_all_services_in_process

# Импорт библиотек
import asyncio
import subprocess
import time
import os
import psutil
import ctypes
import pyautogui
import traceback
import tempfile
import shutil
import multiprocessing
from typing import Optional


class Quik_START:
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

        # Процесс с сервисами
        self.services_process: Optional[multiprocessing.Process] = None

        # Папки для удаления (если они существуют от старых запусков)
        self.folders_to_clean = [
            os.path.join(os.path.dirname(__file__), "quik_screenshots"),
            os.path.join(os.path.dirname(__file__), "screenshots"),
            os.path.join(os.path.dirname(__file__), "logs"),
            os.path.join(os.path.dirname(__file__), "quik_logs"),
            os.path.join(os.path.dirname(__file__), "login_screenshots"),
            os.path.join(os.path.dirname(__file__), "templates")
        ]
    # Переключает на английскую раскладку
    def switch_layout(self):
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        user32.PostMessageW(hwnd, 0x0050, 0, 0x0409)
        return True

    # Делает скриншот и анализ
    async def take_and_analyze_screenshot(self):
        try:
            # Размеры экрана
            screen_width, screen_height = pyautogui.size()

            # Область для маленького окна (400x250 в центре)
            region_width = 400
            region_height = 250
            left = (screen_width - region_width) // 2
            top = (screen_height - region_height) // 2

            # Делаем скриншот (это синхронная операция, но быстрая)
            screenshot = await asyncio.to_thread(
                pyautogui.screenshot,
                region=(left, top, region_width, region_height)
            )

            # Сохраняем во временный файл (будет удален после анализа)
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            self.temp_screenshot = temp_file.name
            await asyncio.to_thread(screenshot.save, self.temp_screenshot)

            # Анализируем
            return await self.analyze_screenshot_in_memory(screenshot)

        except Exception as e:
            logger.error(f"Ошибка анализа скриншота при входе в QUIK: {e}")
            return False
    # Анализирует скриншот
    async def analyze_screenshot_in_memory(self, screenshot):
        try:
            # Конвертируем в RGB
            if screenshot.mode != 'RGB':
                screenshot = await asyncio.to_thread(screenshot.convert, 'RGB')

            width, height = screenshot.size

            # Делим вертикально пополам
            left_half = await asyncio.to_thread(screenshot.crop, (0, 0, width // 2, height))

            # Ищем красный цвет в левой части
            red_count = 0
            total_checked = 0

            # Проверяем каждый 3-й пиксель
            step = 3
            for x in range(0, width // 2, step):
                for y in range(0, height, step):
                    r, g, b = await asyncio.to_thread(left_half.getpixel, (x, y))

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
                logger.info(f"  Красных пикселей: {red_percent:.2f}%")

                # Правило: >0.5% красного = ошибка
                if red_percent > 0.5:
                    logger.info("Обнаружен красный цвет -> ОШИБКА")
                    return False
                else:
                    logger.info("Красного нет -> УСПЕХ")
                    return True

            return False

        except Exception as e:
            logger.error(f"Ошибка анализа скриншота: {e}")
            return False
    # Очистка временных файлов
    def cleanup_temp_files(self):

        # Удаляем временный скриншот
        if self.temp_screenshot and os.path.exists(self.temp_screenshot):
            try:
                os.remove(self.temp_screenshot)
                self.temp_screenshot = None
            except:
                pass

        # Удаляем все папки из списка
        self.cleanup_old_folders()

    # Удаляет старые папки
    def cleanup_old_folders(self):

        for folder_path in self.folders_to_clean:
            if os.path.exists(folder_path):
                try:
                    shutil.rmtree(folder_path, ignore_errors=True)
                except Exception as e:
                    logger.error(f"Не удалось удалить {folder_path}: {e}")
    # Входа
    async def perform_login_attempt(self):
        try:
            # Открываем окно пароля
            await asyncio.to_thread(pyautogui.hotkey, 'ctrl', 'q')
            await asyncio.sleep(2)

            # Вводим пароль
            await asyncio.to_thread(pyautogui.write, self.password)
            await asyncio.sleep(1)

            # Нажимаем Enter
            await asyncio.to_thread(pyautogui.press, 'enter')

            # Ждем и делаем скриншот + анализ
            await asyncio.sleep(5)
            success = await self.take_and_analyze_screenshot()

            # Очищаем временный файл
            self.cleanup_temp_files()

            return success

        except Exception as e:
            logger.error(f"Ошибка ввода пароля при входе в QUIK: {e}")
            self.cleanup_temp_files()
            return False
    # Проверка, запущен ли QUIK
    def check_quik_running(self):
        for proc in psutil.process_iter(['name']):
            try:
                name = proc.info['name'].lower()
                if 'quik' in name or 'info' in name:
                    return True
            except:
                pass
        return False
    # Запуск QUIK
    async def start_quik(self):
        try:
            self.switch_layout()
            await asyncio.to_thread(subprocess.Popen, [self.quik_path], cwd=self.quik_dir)
            logger.info("✓ QUIK запущен")
            await asyncio.sleep(25)  # Ждем загрузки
            return True
        except Exception as e:
            logger.error(f"✗ Ошибка при запуске: {e}")
            return False
    # Активирует окно QUIK
    def activate_quik_window(self):
        try:
            pyautogui.click(pyautogui.size().width // 2, pyautogui.size().height // 2)
            time.sleep(1)
            return True
        except:
            return False
    # Запуска сервисов после входа
    def start_services(self):

        logger.info("=" * 50)
        logger.info("ЗАПУСК СЕРВИСОВ ПОСЛЕ ВХОДА В QUIK")
        logger.info("=" * 50)

        try:
            # Запускаем сервисы в отдельном процессе
            self.services_process = run_all_services_in_process()
            logger.info(f"Сервисы запущены в процессе: {self.services_process.pid}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при запуске сервисов: {e}")
            return False

    # Главный цикл запуска QUIK
    async def run(self):
        logger.info("=" * 60)
        logger.info("ВХОД В QUIK")
        logger.info("=" * 60)

        # Сначала чистим старые папки
        self.cleanup_old_folders()

        # Запускаем QUIK если не запущен
        if not self.check_quik_running():
            if not await self.start_quik():
                return False
        else:
            logger.info("✓ QUIK уже запущен")

        # Активируем окно
        self.activate_quik_window()
        await asyncio.sleep(2)

        # Цикл попыток входа
        login_success = False

        while self.attempt_count < self.max_attempts and not login_success:
            self.attempt_count += 1

            # Пробуем войти
            attempt_result = await self.perform_login_attempt()

            if attempt_result:
                # Успех - проверяем файл подтверждения
                logger.info("ВХОД В QUIK УСПЕШЕН!")

                await asyncio.sleep(3)
                try:
                    with open(config.CREATE_PRICE, 'r') as f:
                        if f.read().strip():
                            logger.info("Файл подтверждения OK")
                        else:
                            logger.info("Файл пуст")
                except:
                    logger.info("Файл не найден")

                login_success = True

                # Запускаем сервисы
                services_started = self.start_services()

                if services_started:
                    # Отправляем красивое сообщение с эмодзи
                    await send_tg_message(
                        '*Все процессы запущены* → /start'
                    )
                else:
                    logger.error("Ошибка при запуске сервисов")

                break
            else:
                # Ошибка - закрываем окно и пробуем снова
                logger.info("ОШИБКА ВХОДА")

                await asyncio.to_thread(pyautogui.press, 'enter')
                await asyncio.sleep(1)

                if self.attempt_count < self.max_attempts:
                    logger.info(f"Пробуем снова через 3 секунды...")
                    await asyncio.sleep(3)
                    self.activate_quik_window()

        # Финальная очистка
        self.cleanup_temp_files()

        # Итог
        if login_success:
            logger.info(f"УСПЕШНЫЙ ЗАПУСК за {self.attempt_count} попыток")
            return True
        else:
            logger.error(f"НЕ УДАЛОСЬ ВОЙТИ В QUIK за {self.attempt_count} попыток")
            # Отправляем сообщение об ошибке
            await send_tg_message(
                '*Не удалось войти в QUIK*\n\n'
                f'Попыток: {self.attempt_count}\n'
                'Проверьте настройки и повторите запуск.'
            )
            return False

# Главная функция запуска
async def quik_main():

    try:
        launcher = Quik_START()
        result = await launcher.run()
        return result

    except KeyboardInterrupt:
        logger.info(f"\n\n Программа прервана пользователем")
        return False
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False


if __name__ == "__main__":
    # Настройки pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.7

    async def main():
        success = await quik_main()

        if success:
            # Если запуск успешен, держим программу активной
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("Программа остановлена")

        sys.exit(0 if success else 1)

    asyncio.run(main())