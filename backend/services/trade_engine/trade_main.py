# backend/services/trading_engine/trade_main.py
import sys
sys.path.append(r"C:\Users\Вадим\Documents\trade-stage")

import asyncio
import json
from backend.services.trade_engine.engine import TradeEngine
from backend.components.account import get_balance
from settings.backend_config import JSON_PRICE_PATH

async def show_prices():
    """Показывает текущие цены из JSON"""
    try:
        with open(JSON_PRICE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print("\nТЕКУЩИЕ ЦЕНЫ:")
        print("="*40)

        if "SPBFUT" in data:
            print("\n🔥 ФЬЮЧЕРСЫ:")
            for name, inst in data["SPBFUT"].items():
                print(f"  {inst['ticker']}: {inst['price']} ({name})")

        if "TQBR" in data:
            print("\n📊 АКЦИИ:")
            count = 0
            for name, inst in data["TQBR"].items():
                if count < 10:
                    print(f"  {inst['ticker']}: {inst['price']}")
                    count += 1
    except Exception as e:
        print(f"Ошибка чтения цен: {e}")

async def main():
    print("\nТОРГОВЛЯ С ТРЕЙЛИНГ-СТОПОМ")
    print("="*40)

    data = get_balance()
    balance = data.get('balance', 0)
    print(f"Баланс: {balance} RUB")

    if balance <= 0:
        print("Нет средств!")
        return

    await show_prices()

    engine = TradeEngine()
    await engine.start()

    try:
        while True:
            print("\n1 - Открыть позицию")
            print("2 - Список позиций")
            print("3 - Выход")

            choice = input("Выбор: ").strip()

            if choice == "1":
                ticker = input("Тикер (например YDH6, SBER): ").upper()
                direction = input("long/short: ").lower()
                if direction not in ['long', 'short']:
                    print("Ошибка")
                    continue

                try:
                    stop = float(input("Стоп-лосс: "))
                except:
                    print("Ошибка")
                    continue

                await engine.open_position(ticker, direction, stop)

            elif choice == "2":
                positions = await engine.get_positions()
                if positions:
                    for p in positions:
                        print(f"\n{p['ticker']} {p['direction']}")
                        print(f"  Вход: {p['entry_price']:.2f}")
                        print(f"  Стоп: {p['current_stop']:.2f}")
                        print(f"  Max: {p.get('highest_price', 0):.2f}")
                else:
                    print("Нет позиций")

            elif choice == "3":
                break

    except KeyboardInterrupt:
        pass
    finally:
        await engine.stop()

if __name__ == "__main__":
    asyncio.run(main())