import sqlite3
from pathlib import Path

# Anchored to this file's directory rather than the process's current
# working directory. CWD can differ depending on how the app is launched
# (double-clicked exe, `flet run` from a different folder, packaged
# Android build) -- a relative path risks creating/reading a *different*
# spendbook.db each time, which would look like data silently vanishing.
DB_PATH = Path(__file__).resolve().parent / "spendbook.db"


class DatabaseError(Exception):
    """Raised when a database operation fails. UI code catches this
    specifically (rather than bare Exception) so a real bug elsewhere
    doesn't get silently swallowed by the same handler."""
    pass


def get_connection():
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        # busy_timeout makes SQLite retry for up to 5s instead of raising
        # "database is locked" immediately if another connection is
        # mid-write -- unlikely with this app's short-lived connections,
        # but cheap insurance.
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        raise DatabaseError(f"Could not open database: {e}") from e


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

    # Simple key-value store for app-level settings (currently used for
    # the first-run setup guide's "already seen" flag; a general-purpose
    # place for future toggles). One row per key, so we don't need to
    # migrate the schema every time we add a new setting.
    conn.execute("""
    CREATE TABLE IF NOT EXISTS app_settings(
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """)

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# App settings (key-value)
# ---------------------------------------------------------------------------

def get_setting(key: str, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row is not None else default


def set_setting(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO app_settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


DEFAULT_OVERDUE_DAYS = 7


def get_overdue_days() -> int:
    """
    How many days an unsettled debt/due sits before it's flagged
    "overdue" in the UI. User-configurable in Settings rather than a
    fixed 7 -- shops have very different norms for how long they extend
    credit before following up. Falls back to DEFAULT_OVERDUE_DAYS if
    unset or if a bad value somehow got stored.
    """
    raw = get_setting("overdue_days", str(DEFAULT_OVERDUE_DAYS))
    try:
        value = int(raw)
        return value if value > 0 else DEFAULT_OVERDUE_DAYS
    except (TypeError, ValueError):
        return DEFAULT_OVERDUE_DAYS


def set_overdue_days(days: int):
    set_setting("overdue_days", str(days))


DEFAULT_STATS_WINDOW_DAYS = 30


def get_stats_window_days() -> int:
    """
    How many days back the Stats tab's summary and label breakdown cover.
    User-configurable (Settings) instead of a fixed 30 -- some shops may
    want a tighter weekly view, others a full quarter.
    """
    raw = get_setting("stats_window_days", str(DEFAULT_STATS_WINDOW_DAYS))
    try:
        value = int(raw)
        return value if value > 0 else DEFAULT_STATS_WINDOW_DAYS
    except (TypeError, ValueError):
        return DEFAULT_STATS_WINDOW_DAYS


def set_stats_window_days(days: int):
    set_setting("stats_window_days", str(days))
# ---------------------------------------------------------------------------

def get_labels():
    """Return all labels as a list of sqlite3.Row (dict-like) objects."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM labels ORDER BY name").fetchall()
    conn.close()
    return rows


def add_label(name: str, color: str = "", emoji: str = ""):
    """
    Insert a new label and return its new id. `emoji` is a legacy column
    kept for backward compatibility with existing databases -- the UI no
    longer sets it (labels are distinguished by `color` instead). Always
    call with keyword arguments to avoid ambiguity between the two.
    """
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

def get_transactions(search: str = None):
    """
    Return all transactions, newest first, each row also carrying the
    joined label name/color so the UI doesn't need a second query per row.

    If `search` is given, only returns transactions whose note or label
    name contains it (case-insensitive). SQLite's LIKE is
    case-insensitive for ASCII by default, which covers the common case
    here without extra setup.
    """
    conn = get_connection()
    if search:
        pattern = f"%{search}%"
        rows = conn.execute("""
            SELECT
                t.id, t.amount, t.type, t.note, t.created_at,
                l.name AS label_name, l.color AS label_color
            FROM transactions t
            LEFT JOIN labels l ON l.id = t.label_id
            WHERE t.note LIKE ? OR l.name LIKE ?
            ORDER BY t.created_at DESC, t.id DESC
        """, (pattern, pattern)).fetchall()
    else:
        rows = conn.execute("""
            SELECT
                t.id, t.amount, t.type, t.note, t.created_at,
                l.name AS label_name, l.color AS label_color
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


def update_transaction(transaction_id: int, amount: float, type_: str, label_id, note: str):
    """Edit an existing transaction in place. created_at is left untouched."""
    conn = get_connection()
    conn.execute(
        "UPDATE transactions SET amount = ?, type = ?, label_id = ?, note = ? WHERE id = ?",
        (amount, type_, label_id, note, transaction_id),
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

def get_debts(include_settled: bool = False, search: str = None):
    """
    Return debt/due entries, unsettled first (then newest first).
    By default hides settled ones so the list only shows what's outstanding.
    If `search` is given, only returns entries whose person name or note
    contains it (case-insensitive).
    """
    conn = get_connection()
    conditions = []
    params = []
    if not include_settled:
        conditions.append("settled = 0")
    if search:
        conditions.append("(person_name LIKE ? OR note LIKE ?)")
        pattern = f"%{search}%"
        params.extend([pattern, pattern])

    query = "SELECT * FROM debts"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY settled ASC, created_at DESC, id DESC"

    rows = conn.execute(query, params).fetchall()
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


def update_debt(debt_id: int, person_name: str, amount: float, type_: str, note: str):
    """Edit an existing debt/due entry in place. created_at/settled untouched."""
    conn = get_connection()
    conn.execute(
        "UPDATE debts SET person_name = ?, amount = ?, type = ?, note = ? WHERE id = ?",
        (person_name, amount, type_, note, debt_id),
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


def is_debt_overdue(created_at: str, overdue_days: int = None) -> bool:
    """
    A simple, dependency-free overdue check: parse the stored ISO date and
    compare against today. Used by the UI to color/badge old unsettled
    entries -- kept in Python (not SQL) since it's just for display, not
    filtering a large table.

    If `overdue_days` isn't given, uses the user's configured threshold
    (Settings -> Overdue after N days, default 7) instead of a fixed
    number, so different shops can set this to match how long they
    actually extend credit before following up.
    """
    from datetime import datetime
    if overdue_days is None:
        overdue_days = get_overdue_days()
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return False
    return (datetime.now() - created).days >= overdue_days


# ---------------------------------------------------------------------------
# Daily closing summary
# ---------------------------------------------------------------------------

def get_daily_closing(day_iso: str = None):
    """
    Totals for a single calendar day (defaults to today): income, expense,
    net, and transaction count -- for a shop's end-of-day check.
    `day_iso` should be 'YYYY-MM-DD'; if omitted, uses SQLite's local
    'now' date.
    """
    conn = get_connection()
    if day_iso is None:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense,
                COUNT(*) AS count
            FROM transactions
            WHERE date(created_at) = date('now')
        """).fetchone()
    else:
        row = conn.execute("""
            SELECT
                COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) AS income,
                COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) AS expense,
                COUNT(*) AS count
            FROM transactions
            WHERE date(created_at) = ?
        """, (day_iso,)).fetchone()
    conn.close()
    return {
        "income": row["income"],
        "expense": row["expense"],
        "net": row["income"] - row["expense"],
        "count": row["count"],
    }

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
            COALESCE(l.color, '') AS label_color,
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


def get_transaction_stats(days: int = 30):
    """
    A few extra numbers that are cheap to compute and genuinely useful
    for a shop owner glancing at Stats: how many transactions happened,
    the average size of an income/expense entry, and the single largest
    of each -- helps spot an unusually large one-off vs. normal day-to-
    day activity.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*) AS count,
            COALESCE(AVG(CASE WHEN type = 'income' THEN amount END), 0) AS avg_income,
            COALESCE(AVG(CASE WHEN type = 'expense' THEN amount END), 0) AS avg_expense,
            COALESCE(MAX(CASE WHEN type = 'income' THEN amount END), 0) AS max_income,
            COALESCE(MAX(CASE WHEN type = 'expense' THEN amount END), 0) AS max_expense
        FROM transactions
        WHERE created_at >= datetime('now', ?)
    """, (f'-{days} days',)).fetchone()
    conn.close()
    return {
        "count": row["count"],
        "avg_income": row["avg_income"],
        "avg_expense": row["avg_expense"],
        "max_income": row["max_income"],
        "max_expense": row["max_expense"],
    }


def get_period_comparison(days: int = 30):
    """
    Compares the current window (last `days` days) against the
    immediately preceding window of the same length -- e.g. this 30 days
    vs. the 30 days before that. Lets the Stats tab show "up/down vs
    last period" instead of just a flat snapshot, which is a much more
    useful signal for spotting trends.

    Returns (current_net, previous_net, percent_change). percent_change
    is None if the previous period had zero net (avoids a divide-by-zero
    and a meaningless "infinite %" swing).
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN type = 'income' AND created_at >= datetime('now', ?) THEN amount ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN type = 'expense' AND created_at >= datetime('now', ?) THEN amount ELSE 0 END), 0)
              AS current_net,
            COALESCE(SUM(CASE WHEN type = 'income' AND created_at >= datetime('now', ?) AND created_at < datetime('now', ?) THEN amount ELSE 0 END), 0)
              - COALESCE(SUM(CASE WHEN type = 'expense' AND created_at >= datetime('now', ?) AND created_at < datetime('now', ?) THEN amount ELSE 0 END), 0)
              AS previous_net
        FROM transactions
    """, (
        f'-{days} days', f'-{days} days',
        f'-{days * 2} days', f'-{days} days',
        f'-{days * 2} days', f'-{days} days',
    )).fetchone()
    conn.close()

    current_net = row["current_net"]
    previous_net = row["previous_net"]

    if previous_net == 0:
        percent_change = None
    else:
        percent_change = ((current_net - previous_net) / abs(previous_net)) * 100

    return current_net, previous_net, percent_change


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def build_transactions_csv() -> str:
    """Build the transactions CSV as a string, for direct use with
    FilePicker.save_file(src_bytes=...) -- no temp file needed."""
    import csv
    import io
    rows = get_transactions()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "date", "type", "amount", "label", "note"])
    for r in rows:
        writer.writerow([
            r["id"], r["created_at"], r["type"], r["amount"],
            r["label_name"] or "", r["note"] or "",
        ])
    return buf.getvalue()


def build_debts_csv() -> str:
    """Build the debts/dues CSV (including settled) as a string."""
    import csv
    import io
    rows = get_debts(include_settled=True)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "date", "person", "type", "amount", "note", "settled"])
    for r in rows:
        writer.writerow([
            r["id"], r["created_at"], r["person_name"], r["type"],
            r["amount"], r["note"] or "", "yes" if r["settled"] else "no",
        ])
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Backup / Restore
#
# Rather than round-tripping through CSV (which loses labels' colors,
# settled/unsettled state nuance, and IDs), backup/restore works with the
# actual SQLite file -- a true 1:1 copy. This also sidesteps needing a
# file-picker control: FilePicker is known to break on real Android
# builds in this Flet version ("Unknown control: FilePicker"), so backup
# writes to, and restore reads from, a fixed filename in the device's
# Downloads folder instead of an interactive file-open dialog.
# ---------------------------------------------------------------------------

BACKUP_FILENAME = "SpendBook_backup.db"


def create_backup_file(destination_path: str):
    """
    Copies the live database file to `destination_path` (a full directory
    + filename). Uses SQLite's own backup API rather than a raw file copy
    so it's safe even if something else has the database open at the same
    moment -- a plain file copy could grab a half-written page mid-write.
    """
    import shutil

    conn = get_connection()
    try:
        dest_conn = sqlite3.connect(destination_path)
        try:
            conn.backup(dest_conn)
        finally:
            dest_conn.close()
    except sqlite3.Error as e:
        raise DatabaseError(f"Could not create backup: {e}") from e
    finally:
        conn.close()


def restore_from_backup_file(source_path: str):
    """
    Replaces the live database with the one at `source_path`. Validates
    the source file actually looks like a SpendBook database (has the
    expected tables) before touching anything, so a wrong/corrupt file
    can't silently wipe out real data.
    """
    import shutil

    if not Path(source_path).exists():
        raise DatabaseError(f"Backup file not found at {source_path}")

    try:
        check_conn = sqlite3.connect(source_path)
        try:
            tables = {
                row[0] for row in
                check_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            }
        finally:
            check_conn.close()
    except sqlite3.Error as e:
        raise DatabaseError(f"That file doesn't look like a valid backup: {e}") from e

    required = {"labels", "transactions", "debts"}
    if not required.issubset(tables):
        raise DatabaseError("That file doesn't look like a SpendBook backup.")

    try:
        shutil.copyfile(source_path, DB_PATH)
    except OSError as e:
        raise DatabaseError(f"Could not restore backup: {e}") from e