import asyncio
from finam_trade_api import Client, TokenManager
import sys
import os

sys.path.append(r"C:\Users\Вадим\Documents\python\trade-brain-main")
import config

token = config.finam_api_token
account_id = config.finam_api_account_id

async def get_finam_api():
    """Асинхронное получение данных с Finam"""
    client = Client(TokenManager(token))
    await client.access_tokens.set_jwt_token()

    try:
        # Получение информации об аккаунте
        account_info = await client.account.get_account_info(account_id)
        return account_info

    except Exception as e:
        print(f"Ошибка получения данных Finam: {e}")
        return None

async def get_finam_balance():
    """Асинхронное получение баланса"""
    account_info = await get_finam_api()

    if account_info is None:
        return 0.0

    available_balance = 0.0
    # Используем getattr для безопасного доступа к атрибуту cash
    if hasattr(account_info, 'cash') and account_info.cash:
        for cash in account_info.cash:
            if getattr(cash, 'currency_code', None) == 'RUB':
                # Конвертируем FinamMoney в обычное число
                units = float(getattr(cash, 'units', 0))
                nanos = float(getattr(cash, 'nanos', 0))
                amount = units + (nanos / 1_000_000_000)
                available_balance = amount
                break
    return available_balance

async def get_finam_positions():
    """Асинхронное получение позиций"""
    account_info = await get_finam_api()

    if account_info is None:
        return []

    # Возвращаем позиции, если они есть
    return getattr(account_info, 'positions', [])

# Основная асинхронная функция
async def main():
    try:
        # Получаем баланс
        balance = await get_finam_balance()
        print(f"Баланс: {balance} RUB")

        # Получаем позиции
        positions = await get_finam_positions()
        print((positions[1].symbol)[:-5])
        print(f"Количество позиций: {len(positions)}")

        # Если нужно вывести информацию о позициях
        for pos in positions:
            print(f"Позиция: {pos}")

        return balance

    except Exception as e:
        print(f"Ошибка в main: {e}")
        return 0.0

# Синхронные обертки для использования в обычном коде
def get_sync_balance():
    """Синхронная версия для получения баланса"""
    return asyncio.run(get_finam_balance())

def get_sync_positions():
    """Синхронная версия для получения позиций"""
    return asyncio.run(get_finam_positions())

if __name__ == "__main__":
    # Запуск асинхронной функции
    balance = asyncio.run(main())
    print(f"Текущий баланс: {balance} RUB")