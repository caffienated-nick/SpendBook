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

    # Seed a few default labels the first time the app runs, so the
    # "add transaction" form isn't empty on a fresh install.
    cursor = conn.execute("SELECT COUNT(*) FROM labels")
    if cursor.fetchone()[0] == 0:
        defaults = [
            ("Food", "🍔", "orange"),
            ("Transport", "🚌", "blue"),
            ("Shopping", "🛍️", "purple"),
            ("Salary", "💼", "green"),
            ("Other", "📦", "grey"),
        ]
        conn.executemany(
            "INSERT INTO labels (name, emoji, color) VALUES (?, ?, ?)",
            defaults,
        )
        conn.commit()

    conn.close()


def get_labels():
    """Return all labels as a list of sqlite3.Row (dict-like access)."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM labels ORDER BY name").fetchall()
    conn.close()
    return rows


def add_transaction(amount: float, type_: str, label_id: int | None, note: str, created_at: str):
    """Insert a new transaction. type_ is 'expense' or 'income'."""
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO transactions (amount, type, label_id, note, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (amount, type_, label_id, note, created_at),
    )
    conn.commit()
    conn.close()


def get_transactions():
    """Return all transactions, newest first, joined with their label info."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT t.id, t.amount, t.type, t.note, t.created_at,
               l.name AS label_name, l.emoji AS label_emoji
        FROM transactions t
        LEFT JOIN labels l ON l.id = t.label_id
        ORDER BY t.created_at DESC, t.id DESC
        """
    ).fetchall()
    conn.close()
    return rows


def delete_transaction(transaction_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()


def get_balance():
    """Income total minus expense total."""
    conn = get_connection()
    row = conn.execute(
        """
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0)
            AS balance
        FROM transactions
        """
    ).fetchone()
    conn.close()
    return row["balance"]

# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def get_labels():
    """Return all labels as a list of sqlite3.Row (dict-like) objects."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM labels ORDER BY name").fetchall()
    conn.close()
    return rows


def add_label(name: str, emoji: str = "", color: str = ""):
    """Insert a new label and return its new id."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO labels (name, emoji, color) VALUES (?, ?, ?)",
        (name, emoji, color),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def get_transactions():
    """
    Return all transactions, newest first, each row also carrying the
    joined label name/emoji so the UI doesn't need a second query per row.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            t.id, t.amount, t.type, t.note, t.created_at,
            l.name AS label_name, l.emoji AS label_emoji
        FROM transactions t
        LEFT JOIN labels l ON l.id = t.label_id
        ORDER BY t.created_at DESC, t.id DESC
    """).fetchall()
    conn.close()
    return rows


def add_transaction(amount: float, type_: str, label_id, note: str, created_at: str):
    """
    Insert a transaction. `type_` should be "income" or "expense".
    `created_at` is stored as an ISO date string so it sorts naturally.
    """
    conn = get_connection()
    conn.execute(
        "INSERT INTO transactions (amount, type, label_id, note, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (amount, type_, label_id, note, created_at),
    )
    conn.commit()
    conn.close()


def delete_transaction(transaction_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()


def get_balance():
    """
    Sum incomes minus expenses. Using SQL's CASE/SUM here instead of pulling
    all rows into Python and looping -- it's one query instead of N.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) -
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0)
            AS balance
        FROM transactions
    """).fetchone()
    conn.close()
    return row["balance"]

