# backend/services/trading_engine/trade_main.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
import logging
from backend.services.trading_engine import TradingEngine
from backend.components.quik_components.quik_account import get_balance
from settings.backend_config import TRADING_TIKERS

# Настройка подробного логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def check_balance_first():
    """Сначала проверяем баланс"""
    print("\n" + "="*50)
    print("ПРОВЕРКА БАЛАНСА")
    print("="*50)

    try:
        account_data = get_balance()
        balance = account_data.get('balance', 0)
        positions = account_data.get('positions', [])

        print(f"💰 Баланс: {balance} RUB")
        print(f"📊 Открытых позиций: {len(positions)}")

        for pos in positions:
            print(f"   {pos['sec_code']}: {pos['quantity']} лотов, вход: {pos.get('entry_price')}")

        return balance, positions
    except Exception as e:
        print(f"❌ Ошибка при проверке баланса: {e}")
        return 0, []

async def show_available_tickers():
    """Показывает доступные тикеры"""
    print("\n📋 Доступные инструменты:")

    if "SPBFUT" in TRADING_TIKERS:
        print("\n🔥 ФЬЮЧЕРСЫ:")
        for name, ticker in TRADING_TIKERS["SPBFUT"].items():
            print(f"   • {name}: {ticker}")

    if "TQBR" in TRADING_TIKERS:
        print("\n📊 АКЦИИ (первые 10):")
        count = 0
        for name, ticker in TRADING_TIKERS["TQBR"].items():
            if count < 10:
                print(f"   • {name}: {ticker}")
                count += 1
            else:
                print(f"   ... и еще {len(TRADING_TIKERS['TQBR'])-10}")
                break

async def manual_trading_example():
    """Пример ручного ввода параметров"""

    # Сначала проверяем баланс
    balance, positions = await check_balance_first()

    if balance == 0:
        print("❌ Нет средств на счете или ошибка подключения к QUIK!")
        return

    # Показываем доступные тикеры
    await show_available_tickers()

    engine = TradingEngine()

    try:
        # Запускаем движок
        await engine.start()

        print("\n" + "="*50)
        print("ТОРГОВЛЯ С ТРЕЙЛИНГ-СТОПОМ")
        print("="*50)

        while True:
            print("\n" + "-"*30)
            print("1. Открыть новую позицию")
            print("2. Показать активные позиции")
            print("3. Выход")

            choice = input("Выберите действие (1-3): ").strip()

            if choice == "1":
                # ВВОД ПАРАМЕТРОВ
                ticker = input("\nВведите тикер (например YDH6, SBER): ").strip().upper()

                direction = input("Направление (long/short): ").strip().lower()
                if direction not in ['long', 'short']:
                    print("❌ Неверное направление")
                    continue

                try:
                    stop_loss = float(input("Введите уровень стоп-лосса: "))
                except ValueError:
                    print("❌ Неверный формат стоп-лосса")
                    continue

                # Опционально: риск в рублях
                risk_input = input("Риск в рублях (Enter для 2% от баланса): ").strip()
                risk_rub = float(risk_input) if risk_input else None

                print(f"\n🔄 Открываем позицию {direction.upper()} по {ticker}...")
                print(f"   Стоп-лосс: {stop_loss}")
                print(f"   Риск: {risk_rub if risk_rub else f'{balance*0.02:.2f} RUB (2% от {balance:.2f})'}")

                # Открываем позицию
                success = await engine.open_position_manual(
                    ticker=ticker,
                    direction=direction,
                    stop_loss=stop_loss,
                    risk_rub=risk_rub
                )

                if success:
                    print("\n✅ Позиция открыта, отслеживание запущено")
                    print("📱 Следите за уведомлениями в Telegram")
                else:
                    print("\n❌ Не удалось открыть позицию")
                    print("Проверьте:")
                    print("1. Запущен ли QUIK")
                    print("2. Правильно ли указан тикер")
                    print("3. Достаточно ли средств")

            elif choice == "2":
                positions = await engine.get_positions()
                if positions:
                    print(f"\n📊 Активные позиции ({len(positions)}):")
                    for pos in positions:
                        print(f"\n   🎯 {pos['ticker']} {pos['direction'].upper()}")
                        print(f"      Вход: {pos['entry_price']:.2f}")
                        print(f"      Тек.стоп: {pos['current_stop']:.2f}")
                        print(f"      Объем: {pos['current_quantity']} лотов")
                        print(f"      Макс.цена: {pos['highest_price']:.2f}")
                else:
                    print("\n📊 Нет активных позиций")

            elif choice == "3":
                print("\n👋 Выход...")
                break

            else:
                print("❌ Неверный выбор")

    except KeyboardInterrupt:
        print("\n⏹️ Остановка по Ctrl+C")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await engine.stop()

async def quick_trade(ticker: str, direction: str, stop_loss: float, risk_rub: float = None):
    """Быстрая торговля одной командой"""

    # Проверяем баланс
    balance, _ = await check_balance_first()
    if balance == 0:
        return

    engine = TradingEngine()

    try:
        await engine.start()

        print(f"\n🔄 Быстрая сделка: {direction.upper()} {ticker}")
        print(f"   Стоп: {stop_loss}, Риск: {risk_rub or balance*0.02:.2f} RUB")

        success = await engine.open_position_manual(ticker, direction, stop_loss, risk_rub)

        if success:
            print("✅ Позиция открыта, отслеживание запущено")
            # Держим соединение открытым для отслеживания
            while True:
                await asyncio.sleep(1)
        else:
            await engine.stop()

    except KeyboardInterrupt:
        await engine.stop()

if __name__ == "__main__":
    print("="*60)
    print("ТОРГОВЫЙ ДВИЖОК С ТРЕЙЛИНГ-СТОПОМ")
    print("="*60)

    # Выбор режима
    print("\nВыберите режим работы:")
    print("1 - Ручной режим (сам вводишь параметры)")
    print("2 - Демо-режим (тест с YDH6)")
    print("3 - Быстрая сделка (свои параметры в коде)")

    choice = input("\nВаш выбор (1-3): ").strip()

    if choice == "1":
        asyncio.run(manual_trading_example())
    elif choice == "2":
        # Демо-режим с YDH6
        asyncio.run(quick_trade(
            ticker="YDH6",
            direction="long",
            stop_loss=4800.0,  # Стоп-лосс
            risk_rub=1000       # Риск 1000 RUB
        ))
    else:
        # Здесь можно изменить параметры для быстрой сделки
        asyncio.run(quick_trade(
            ticker="SBER",      # Тикер
            direction="long",    # Направление
            stop_loss=300.0,     # Стоп-лосс
            risk_rub=50        # Риск в рублях
        ))
