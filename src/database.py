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

    # Debts/Dues: money the shop owes someone ("due"), or money someone
    # owes the shop ("debt"/udhaar). `settled` marks it as cleared without
    # deleting the history.
    conn.execute("""
    CREATE TABLE IF NOT EXISTS debts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        person_name TEXT NOT NULL,
        amount REAL NOT NULL,
        type TEXT NOT NULL,          -- 'debt' (they owe shop) or 'due' (shop owes them)
        note TEXT,
        created_at TEXT NOT NULL,
        settled INTEGER NOT NULL DEFAULT 0
    );
    """)

    conn.commit()
    conn.close()


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


def delete_label(label_id: int):
    """
    Delete a label. Transactions that used it keep their label_id, which
    will just no longer match anything -- get_transactions()'s LEFT JOIN
    means they'll show as "Uncategorized" instead of erroring.
    """
    conn = get_connection()
    conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))
    conn.commit()
    conn.close()


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


# ---------------------------------------------------------------------------
# Debts / Dues
# ---------------------------------------------------------------------------

def get_debts(include_settled: bool = False):
    """
    Return debt/due entries, unsettled first (then newest first).
    By default hides settled ones so the list only shows what's outstanding.
    """
    conn = get_connection()
    query = "SELECT * FROM debts"
    if not include_settled:
        query += " WHERE settled = 0"
    query += " ORDER BY settled ASC, created_at DESC, id DESC"
    rows = conn.execute(query).fetchall()
    conn.close()
    return rows


def add_debt(person_name: str, amount: float, type_: str, note: str, created_at: str):
    """type_ is 'debt' (they owe the shop / udhaar) or 'due' (shop owes them)."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO debts (person_name, amount, type, note, created_at, settled) "
        "VALUES (?, ?, ?, ?, ?, 0)",
        (person_name, amount, type_, note, created_at),
    )
    conn.commit()
    conn.close()


def settle_debt(debt_id: int):
    """Mark a debt/due as cleared without deleting its history."""
    conn = get_connection()
    conn.execute("UPDATE debts SET settled = 1 WHERE id = ?", (debt_id,))
    conn.commit()
    conn.close()


def delete_debt(debt_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM debts WHERE id = ?", (debt_id,))
    conn.commit()
    conn.close()


def get_debt_totals():
    """
    Returns (total_they_owe_us, total_we_owe_them) for unsettled entries --
    handy for a summary line at the top of the Dues tab.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'debt' THEN amount ELSE 0 END), 0) AS owed_to_us,
            COALESCE(SUM(CASE WHEN type = 'due' THEN amount ELSE 0 END), 0) AS we_owe
        FROM debts
        WHERE settled = 0
    """).fetchone()
    conn.close()
    return row["owed_to_us"], row["we_owe"]

# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_spending_by_label(days: int = 30):
    """
    Total expense amount per label over the last `days` days, highest
    first. Uses SQLite's datetime('now', '-N days') to filter, so the
    cutoff is computed by the database, not Python -- keeps timezones and
    date math in one place.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            COALESCE(l.name, 'Uncategorized') AS label_name,
            COALESCE(l.emoji, '') AS label_emoji,
            SUM(t.amount) AS total
        FROM transactions t
        LEFT JOIN labels l ON l.id = t.label_id
        WHERE t.type = 'expense'
          AND t.created_at >= datetime('now', ?)
        GROUP BY t.label_id
        ORDER BY total DESC
    """, (f'-{days} days',)).fetchall()
    conn.close()
    return rows


def get_daily_totals(days: int = 14):
    """
    Income and expense totals per calendar day for the last `days` days,
    oldest first (natural order for a line/bar chart).
    Days with zero activity are included as 0/0 so the chart doesn't skip
    dates -- computed in Python by filling gaps around the SQL result.
    """
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            date(created_at) AS day,
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE created_at >= datetime('now', ?)
        GROUP BY day
        ORDER BY day ASC
    """, (f'-{days} days',)).fetchall()
    conn.close()

    from datetime import date, timedelta
    by_day = {r["day"]: (r["income"], r["expense"]) for r in rows}
    today = date.today()
    result = []
    for i in range(days - 1, -1, -1):
        d = (today - timedelta(days=i)).isoformat()
        income, expense = by_day.get(d, (0, 0))
        result.append({"day": d, "income": income, "expense": expense})
    return result


def get_summary_totals(days: int = 30):
    """
    Total income and expense over the last `days` days -- for a
    'this month at a glance' summary above the charts.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
            COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense
        FROM transactions
        WHERE created_at >= datetime('now', ?)
    """, (f'-{days} days',)).fetchone()
    conn.close()
    return row["income"], row["expense"]