import os
from contextlib import contextmanager

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

# Параметри підключення до PostgreSQL
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5433"),
    "database": os.getenv("DB_NAME", "clothing_store"),
    "user": os.getenv("DB_USER", "store_admin"),
    "password": os.getenv("DB_PASS", "admin_password"),
}


def get_db_connection():
    """Створення нового з'єднання з PostgreSQL"""
    return psycopg2.connect(**DB_CONFIG)


@contextmanager
def _cursor(dict_rows: bool = False):
    """Відкриває з'єднання, commit-ить при успіху і ЗАВЖДИ закриває його."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor if dict_rows else None) as cur:
            yield cur
        conn.commit()
    finally:
        conn.close()


def execute_query(query: str, args: tuple = ()):
    """Виконання INSERT / UPDATE / DELETE"""
    with _cursor() as cur:
        cur.execute(query, args)


def fetch_all(query: str, args: tuple = ()):
    """Вибірка всіх рядків у вигляді списку словників"""
    with _cursor(dict_rows=True) as cur:
        cur.execute(query, args)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(query: str, args: tuple = ()):
    """Вибірка одного рядка у вигляді словника"""
    with _cursor(dict_rows=True) as cur:
        cur.execute(query, args)
        row = cur.fetchone()
        return dict(row) if row else None


def fetch_dataframe(query: str, args: tuple = ()):
    """Вибірка напряму в Pandas DataFrame для відображення в Streamlit"""
    conn = get_db_connection()
    try:
        return pd.read_sql_query(query, conn, params=args)
    finally:
        conn.close()