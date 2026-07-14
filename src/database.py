import sqlite3
from pathlib import Path

DB_PATH = Path("spendbook.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    conn = get_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS labels(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        emoji TEXT,
        color TEXT
    );
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        amount REAL NOT NULL,
        type TEXT NOT NULL,
        label_id INTEGER,
        note TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(label_id) REFERENCES labels(id)
    );
    """)

    conn.commit()
    conn.close()