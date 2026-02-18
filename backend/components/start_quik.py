# backend/components/start_quik.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

# Импорт логера
from backend.components.logger import logger

# Импорт файлов настроек сервиса
from settings import backend_config as config
# Импортируем асинхронную функцию отправки сообщений
from backend.components.tg_message import send_tg_message_safe as send_tg_message

# Импортируем функцию для запуска сервисов
from backend.services.run_service.run_all import run_all_services_in_process

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

    def switch_layout(self):
        """Переключает на английскую раскладку"""
        user32 = ctypes.WinDLL('user32', use_last_error=True)
        hwnd = user32.GetForegroundWindow()
        user32.PostMessageW(hwnd, 0x0050, 0, 0x0409)
        return True

    async def take_and_analyze_screenshot(self):
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
            logger.error(f"Ошибка при входе в QUIK ошибка анализа скриншота: {e}")
            return False

    async def analyze_screenshot_in_memory(self, screenshot):
        """
        Анализирует скриншот в памяти (без сохранения файла)
        Делим пополам, ищем красный в левой части
        """
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
                    logger.info(f"✓ Удалена папка: {os.path.basename(folder_path)}")
                except Exception as e:
                    logger.error(f"Не удалось удалить {folder_path}: {e}")

    async def perform_login_attempt(self):
        """Одна попытка входа"""
        logger.info(f"ПОПЫТКА #{self.attempt_count}")

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
            logger.error(f"Ошибка при вводе пароля: {e}")
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

    async def start_quik(self):
        """Запускает QUIK"""
        try:
            self.switch_layout()
            await asyncio.to_thread(subprocess.Popen, [self.quik_path], cwd=self.quik_dir)
            logger.info("✓ QUIK запущен")
            await asyncio.sleep(25)  # Ждем загрузки
            return True
        except Exception as e:
            logger.error(f"✗ Ошибка при запуске: {e}")
            return False

    def activate_quik_window(self):
        """Активирует окно QUIK"""
        try:
            pyautogui.click(pyautogui.size().width // 2, pyautogui.size().height // 2)
            time.sleep(1)
            return True
        except:
            return False

    def _start_services(self):
        """
        Запускает все сервисы после успешного входа в QUIK
        """
        logger.info("=" * 50)
        logger.info("ЗАПУСК ВСЕХ СЕРВИСОВ ПОСЛЕ ВХОДА В QUIK")
        logger.info("=" * 50)

        try:
            # Запускаем сервисы в отдельном процессе
            self.services_process = run_all_services_in_process()
            logger.info(f"✅ Сервисы запущены в процессе PID: {self.services_process.pid}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка при запуске сервисов: {e}")
            return False

    async def run(self):
        """Главный цикл запуска QUIK и последующий запуск сервисов"""
        logger.info("=" * 60)
        logger.info("ЭТАП 1: ВХОД В QUIK")
        logger.info("=" * 60)

        # Сначала чистим старые папки
        self.cleanup_old_folders()

        # Запускаем QUIK если не запущен
        if not self.check_quik_running():
            logger.info("Запускаем QUIK...")
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
                logger.info("✅ ВХОД В QUIK УСПЕШЕН!")

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

                # ===== ВАЖНО: ЗДЕСЬ ЗАПУСКАЕМ СЕРВИСЫ =====
                logger.info("=" * 60)
                logger.info("ЭТАП 2: ЗАПУСК ОСТАЛЬНЫХ СЕРВИСОВ")
                logger.info("=" * 60)

                # Запускаем сервисы
                services_started = self._start_services()

                if services_started:
                    logger.info("✅ ВСЕ СИСТЕМЫ ЗАПУЩЕНЫ УСПЕШНО!")
                    # Отправляем красивое сообщение с эмодзи
                    await send_tg_message(
                        '*Все системы запущены* → /start'
                    )
                else:
                    logger.error("❌ Ошибка при запуске сервисов")
                    await send_tg_message(
                        '*QUIK запущен, но сервисы не стартовали*\n\n'
                        'Проверьте логи для диагностики.'
                    )

                break
            else:
                # Ошибка - закрываем окно и пробуем снова
                logger.info("❌ ОШИБКА ВХОДА")

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
            logger.info(f"✅ УСПЕШНЫЙ ЗАПУСК за {self.attempt_count} попыток")
            return True
        else:
            logger.error(f"❌ НЕ УДАЛОСЬ ВОЙТИ В QUIK за {self.attempt_count} попыток")
            # Отправляем сообщение об ошибке
            await send_tg_message(
                '❌ *Не удалось войти в QUIK*\n\n'
                f'Попыток: {self.attempt_count}\n'
                'Проверьте настройки и повторите запуск.'
            )
            return False


async def quik_main():
    """
    Главная асинхронная функция запуска
    Сначала запускает QUIK и входит в него,
    потом запускает все остальные сервисы
    """
    try:
        launcher = Quik_START_Launcher()
        result = await launcher.run()

        if result:
            logger.info("=" * 60)
            logger.info("✅✅✅ ВСЕ СИСТЕМЫ УСПЕШНО ЗАПУЩЕНЫ ✅✅✅")
            logger.info("=" * 60)
        else:
            logger.error("=" * 60)
            logger.error("❌❌❌ ОШИБКА ЗАПУСКА СИСТЕМ ❌❌❌")
            logger.error("=" * 60)

        return result

    except KeyboardInterrupt:
        logger.info(f"\n\n Программа прервана пользователем")
        return False
    except Exception as e:
        logger.error(f"Критическая ошибка в start_quik: {e}")
        traceback.print_exc()
        # Отправляем сообщение о критической ошибке
        try:
            await send_tg_message(f'❌ *Критическая ошибка*\n\n```\n{str(e)[:200]}```')
        except:
            pass
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