import sqlite3
import logging
from typing import List, Dict, Any, Optional, Tuple

class Database:
    """
    Класс для работы с базой данных SQLite.
    Предоставляет простые методы для работы с таблицами.
    """

    def __init__(self, db_name: str = "my_database.db"):
        """
        Инициализация подключения к базе данных.

        Args:
            db_name: Имя файла базы данных
        """
        self.db_name = db_name
        self.connection = None
        self.cursor = None
        self.connect()

        # Настройка логирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def connect(self):
        """Установить соединение с базой данных"""
        try:
            self.connection = sqlite3.connect(self.db_name)
            self.cursor = self.connection.cursor()
            self.logger.info(f"Подключение к базе данных {self.db_name} установлено")
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка подключения к базе данных: {e}")
            raise

    def close(self):
        """Закрыть соединение с базой данных"""
        if self.connection:
            self.connection.close()
            self.logger.info("Соединение с базой данных закрыто")

    def execute_query(self, query: str, params: tuple = ()):
        """
        Выполнить SQL-запрос

        Args:
            query: SQL-запрос
            params: Параметры для запроса

        Returns:
            Результат выполнения запроса
        """
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor
        except sqlite3.Error as e:
            self.logger.error(f"Ошибка выполнения запроса: {e}")
            self.logger.error(f"Запрос: {query}")
            self.logger.error(f"Параметры: {params}")
            self.connection.rollback()
            raise

    # ============ ОСНОВНЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С ТАБЛИЦАМИ ============

    def create_table(self, table_name: str, columns: Dict[str, str]):
        """
        Создать новую таблицу

        Args:
            table_name: Имя таблицы
            columns: Словарь с названиями столбцов и их типами
                    Пример: {"id": "INTEGER PRIMARY KEY", "name": "TEXT"}
        """
        if not columns:
            raise ValueError("Необходимо указать хотя бы один столбец")

        # Формируем строку с определением столбцов
        columns_def = ", ".join([f"{col_name} {col_type}"
                                for col_name, col_type in columns.items()])

        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def})"
        self.execute_query(query)
        self.logger.info(f"Таблица '{table_name}' создана или уже существует")

    def insert_row(self, table_name: str, data: Dict[str, Any]) -> int:
        """
        Добавить одну строку в таблицу

        Args:
            table_name: Имя таблицы
            data: Словарь с данными {столбец: значение}

        Returns:
            ID добавленной строки
        """
        if not data:
            raise ValueError("Нет данных для вставки")

        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?" for _ in data])
        values = tuple(data.values())

        query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        self.execute_query(query, values)

        # Получаем ID последней вставленной строки
        last_id = self.cursor.lastrowid
        self.logger.info(f"Добавлена строка в таблицу '{table_name}' с ID={last_id}")
        return last_id

    def insert_many_rows(self, table_name: str, columns: List[str], rows: List[tuple]):
        """
        Добавить несколько строк в таблицу

        Args:
            table_name: Имя таблицы
            columns: Список названий столбцов
            rows: Список кортежей с данными
        """
        if not columns or not rows:
            raise ValueError("Необходимо указать столбцы и данные")

        columns_str = ", ".join(columns)
        placeholders = ", ".join(["?" for _ in columns])

        query = f"INSERT INTO {table_name} ({columns_str}) VALUES ({placeholders})"
        self.cursor.executemany(query, rows)
        self.connection.commit()

        self.logger.info(f"Добавлено {len(rows)} строк в таблицу '{table_name}'")

    def select_all(self, table_name: str,
                   columns: List[str] = None,
                   order_by: str = None,
                   limit: int = None) -> List[tuple]:
        """
        Выбрать все строки из таблицы

        Args:
            table_name: Имя таблицы
            columns: Список столбцов для выборки (None - все столбцы)
            order_by: Столбец для сортировки
            limit: Максимальное количество строк

        Returns:
            Список строк
        """
        columns_str = "*" if columns is None else ", ".join(columns)
        query = f"SELECT {columns_str} FROM {table_name}"

        if order_by:
            query += f" ORDER BY {order_by}"
        if limit:
            query += f" LIMIT {limit}"

        self.execute_query(query)
        return self.cursor.fetchall()

    def select_where(self, table_name: str,
                     conditions: Dict[str, Any],
                     columns: List[str] = None,
                     operator: str = "AND") -> List[tuple]:
        """
        Выбрать строки по условиям

        Args:
            table_name: Имя таблицы
            conditions: Словарь условий {столбец: значение}
            columns: Список столбцов для выборки
            operator: Логический оператор для условий (AND или OR)

        Returns:
            Список строк, удовлетворяющих условиям
        """
        if not conditions:
            return self.select_all(table_name, columns)

        columns_str = "*" if columns is None else ", ".join(columns)
        where_clause = f" {operator} ".join([f"{key} = ?" for key in conditions.keys()])
        values = tuple(conditions.values())

        query = f"SELECT {columns_str} FROM {table_name} WHERE {where_clause}"
        self.execute_query(query, values)
        return self.cursor.fetchall()

    def update_row(self, table_name: str,
                   data: Dict[str, Any],
                   conditions: Dict[str, Any]) -> int:
        """
        Обновить строки по условиям

        Args:
            table_name: Имя таблицы
            data: Словарь с данными для обновления
            conditions: Словарь условий

        Returns:
            Количество обновленных строк
        """
        if not data or not conditions:
            raise ValueError("Необходимо указать данные и условия")

        set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
        where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])

        values = tuple(data.values()) + tuple(conditions.values())
        query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"

        self.execute_query(query, values)
        updated_count = self.cursor.rowcount
        self.logger.info(f"Обновлено {updated_count} строк в таблице '{table_name}'")
        return updated_count

    def delete_row(self, table_name: str, conditions: Dict[str, Any]) -> int:
        """
        Удалить строки по условиям

        Args:
            table_name: Имя таблицы
            conditions: Словарь условий

        Returns:
            Количество удаленных строк
        """
        if not conditions:
            raise ValueError("Необходимо указать условия для удаления")

        where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])
        values = tuple(conditions.values())

        query = f"DELETE FROM {table_name} WHERE {where_clause}"
        self.execute_query(query, values)

        deleted_count = self.cursor.rowcount
        self.logger.info(f"Удалено {deleted_count} строк из таблицы '{table_name}'")
        return deleted_count

    def get_table_info(self, table_name: str) -> List[tuple]:
        """
        Получить информацию о структуре таблицы

        Args:
            table_name: Имя таблицы

        Returns:
            Информация о столбцах таблицы
        """
        query = f"PRAGMA table_info({table_name})"
        self.execute_query(query)
        return self.cursor.fetchall()

    def add_column(self, table_name: str, column_name: str, column_type: str):
        """
        Добавить новый столбец в таблицу

        Args:
            table_name: Имя таблицы
            column_name: Имя нового столбца
            column_type: Тип нового столбца
        """
        query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        self.execute_query(query)
        self.logger.info(f"Добавлен столбец '{column_name}' в таблицу '{table_name}'")

    def count_rows(self, table_name: str, conditions: Dict[str, Any] = None) -> int:
        """
        Подсчитать количество строк в таблице

        Args:
            table_name: Имя таблицы
            conditions: Условия для фильтрации

        Returns:
            Количество строк
        """
        query = f"SELECT COUNT(*) FROM {table_name}"
        values = ()

        if conditions:
            where_clause = " AND ".join([f"{key} = ?" for key in conditions.keys()])
            query += f" WHERE {where_clause}"
            values = tuple(conditions.values())

        self.execute_query(query, values)
        return self.cursor.fetchone()[0]

    def get_column_names(self, table_name: str) -> List[str]:
        """
        Получить список названий столбцов таблицы

        Args:
            table_name: Имя таблицы

        Returns:
            Список названий столбцов
        """
        query = f"SELECT * FROM {table_name} LIMIT 0"
        self.execute_query(query)
        return [description[0] for description in self.cursor.description]


    def __exit__(self, exc_type, exc_val, exc_tb):
        """Автоматическое закрытие соединения при выходе из контекста"""
        self.close()