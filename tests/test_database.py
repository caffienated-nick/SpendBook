"""
Tests for database.py -- the data layer, tested independent of any UI.

Run with:  uv run pytest              (from the project root)
      or:  uv run pytest -v           (verbose: shows each test name)
      or:  uv run pytest tests/test_database.py::test_add_balance_math
                                       (run just one test)
"""
from datetime import datetime, timedelta

import pytest


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def test_fresh_database_has_no_labels(db):
    # `db` here is the fixture from conftest.py -- pytest sees this
    # parameter name and automatically runs the fixture before the test.
    assert db.get_labels() == []


def test_add_label_returns_new_id(db):
    label_id = db.add_label(name="Food", color="#FFA726")
    assert isinstance(label_id, int)

    labels = db.get_labels()
    assert len(labels) == 1
    assert labels[0]["name"] == "Food"
    assert labels[0]["color"] == "#FFA726"


def test_add_label_color_persists_with_keyword_args(db):
    # Regression test: add_label's parameters are (name, color, emoji).
    # Always call with keyword arguments -- this guards against a color
    # value accidentally landing in the wrong column if the parameter
    # order ever changes again.
    db.add_label(name="Rent", color="blue400")
    labels = db.get_labels()
    assert labels[0]["color"] == "blue400"


def test_delete_label_removes_it(db):
    label_id = db.add_label(name="Temp", color="grey500")
    db.delete_label(label_id)
    assert db.get_labels() == []


def test_deleting_a_label_does_not_delete_its_transactions(db):
    # This documents an intentional design choice: deleting a label
    # shouldn't erase transaction history, it should just show as
    # "Uncategorized" going forward (see get_transactions()'s LEFT JOIN).
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    db.delete_label(label_id)

    transactions = db.get_transactions()
    assert len(transactions) == 1
    assert transactions[0]["label_name"] is None


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def test_add_transaction_appears_in_list(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(150.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")

    transactions = db.get_transactions()
    assert len(transactions) == 1
    assert transactions[0]["amount"] == 150.0
    assert transactions[0]["type"] == "expense"
    assert transactions[0]["note"] == "lunch"


def test_balance_is_income_minus_expense(db):
    label_id = db.add_label(name="Sales", color="grey500")
    db.add_transaction(1000.0, "income", label_id, "sales", "2026-07-01T10:00:00")
    db.add_transaction(300.0, "expense", label_id, "supplies", "2026-07-01T11:00:00")

    assert db.get_balance() == 700.0


def test_update_transaction_changes_amount_and_note(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    transaction_id = db.get_transactions()[0]["id"]

    db.update_transaction(transaction_id, amount=150.0, type_="expense",
                           label_id=label_id, note="lunch (corrected)")

    updated = db.get_transactions()[0]
    assert updated["amount"] == 150.0
    assert updated["note"] == "lunch (corrected)"


def test_delete_transaction_removes_it(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    transaction_id = db.get_transactions()[0]["id"]

    db.delete_transaction(transaction_id)

    assert db.get_transactions() == []


def test_transactions_are_sorted_newest_first(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100.0, "expense", label_id, "older", "2026-07-01T10:00:00")
    db.add_transaction(200.0, "expense", label_id, "newer", "2026-07-02T10:00:00")

    transactions = db.get_transactions()
    assert transactions[0]["note"] == "newer"
    assert transactions[1]["note"] == "older"


def test_transaction_search_matches_note(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100.0, "expense", label_id, "lunch at dhaba", "2026-07-01T10:00:00")
    db.add_transaction(200.0, "expense", label_id, "groceries", "2026-07-01T11:00:00")

    results = db.get_transactions(search="lunch")
    assert len(results) == 1
    assert results[0]["note"] == "lunch at dhaba"


def test_transaction_search_matches_label_name(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    db.add_transaction(200.0, "expense", label_id, "groceries", "2026-07-01T11:00:00")

    results = db.get_transactions(search="food")
    assert len(results) == 2


def test_transaction_search_is_case_insensitive(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100.0, "expense", label_id, "LUNCH", "2026-07-01T10:00:00")

    results = db.get_transactions(search="lunch")
    assert len(results) == 1


def test_transaction_search_with_no_matches_returns_empty(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(100.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")

    results = db.get_transactions(search="nonexistent")
    assert results == []


# ---------------------------------------------------------------------------
# Debts / Dues
# ---------------------------------------------------------------------------

def test_add_debt_and_totals(db):
    db.add_debt("Ramesh", 500.0, "debt", "udhaar", "2026-07-01T10:00:00")
    db.add_debt("Supplier Co", 1200.0, "due", "invoice", "2026-07-01T11:00:00")

    owed_to_us, we_owe = db.get_debt_totals()
    assert owed_to_us == 500.0
    assert we_owe == 1200.0


def test_settled_debts_are_hidden_by_default(db):
    db.add_debt("Ramesh", 500.0, "debt", "udhaar", "2026-07-01T10:00:00")
    debt_id = db.get_debts()[0]["id"]

    db.settle_debt(debt_id)

    assert db.get_debts() == []  # hidden from the default (unsettled-only) view
    assert len(db.get_debts(include_settled=True)) == 1  # still in history


def test_update_debt_changes_person_and_amount(db):
    db.add_debt("Ramesh", 500.0, "debt", "udhaar", "2026-07-01T10:00:00")
    debt_id = db.get_debts()[0]["id"]

    db.update_debt(debt_id, person_name="Ramesh Kumar", amount=600.0,
                    type_="debt", note="udhaar (corrected)")

    updated = db.get_debts()[0]
    assert updated["person_name"] == "Ramesh Kumar"
    assert updated["amount"] == 600.0


def test_is_debt_overdue_respects_threshold(db):
    ten_days_ago = (datetime.now() - timedelta(days=10)).isoformat(timespec="seconds")
    two_days_ago = (datetime.now() - timedelta(days=2)).isoformat(timespec="seconds")

    assert db.is_debt_overdue(ten_days_ago, overdue_days=7) is True
    assert db.is_debt_overdue(two_days_ago, overdue_days=7) is False


def test_overdue_days_setting_defaults_to_seven(db):
    assert db.get_overdue_days() == 7


def test_overdue_days_setting_persists(db):
    db.set_overdue_days(3)
    assert db.get_overdue_days() == 3


def test_overdue_days_setting_falls_back_on_bad_value(db):
    db.set_setting("overdue_days", "not a number")
    assert db.get_overdue_days() == db.DEFAULT_OVERDUE_DAYS


def test_is_debt_overdue_uses_configured_setting_by_default(db):
    # Without an explicit overdue_days argument, is_debt_overdue should
    # read the user's configured setting instead of a hardcoded value.
    db.set_overdue_days(3)
    five_days_ago = (datetime.now() - timedelta(days=5)).isoformat(timespec="seconds")
    assert db.is_debt_overdue(five_days_ago) is True  # overdue at the new 3-day threshold

    db.set_overdue_days(10)
    assert db.is_debt_overdue(five_days_ago) is False  # not overdue at the new 10-day threshold


def test_debt_search_matches_person_name(db):
    db.add_debt("Ramesh Kumar", 500.0, "debt", "udhaar", "2026-07-01T10:00:00")
    db.add_debt("Suresh", 200.0, "debt", "udhaar", "2026-07-01T10:00:00")

    results = db.get_debts(search="ramesh")
    assert len(results) == 1
    assert results[0]["person_name"] == "Ramesh Kumar"


def test_debt_search_matches_note(db):
    db.add_debt("Ramesh", 500.0, "debt", "rice purchase", "2026-07-01T10:00:00")
    db.add_debt("Suresh", 200.0, "debt", "sugar purchase", "2026-07-01T10:00:00")

    results = db.get_debts(search="rice")
    assert len(results) == 1
    assert results[0]["person_name"] == "Ramesh"


def test_debt_search_combines_with_settled_filter(db):
    db.add_debt("Ramesh", 500.0, "debt", "udhaar", "2026-07-01T10:00:00")
    debt_id = db.get_debts()[0]["id"]
    db.settle_debt(debt_id)

    # Settled entries stay hidden by default even when they match a search.
    assert db.get_debts(search="ramesh") == []
    assert len(db.get_debts(search="ramesh", include_settled=True)) == 1


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def test_summary_totals_only_counts_within_window(db):
    label_id = db.add_label(name="Sales", color="grey500")
    recent = datetime.now().isoformat(timespec="seconds")
    old = (datetime.now() - timedelta(days=60)).isoformat(timespec="seconds")

    db.add_transaction(1000.0, "income", label_id, "recent sale", recent)
    db.add_transaction(5000.0, "income", label_id, "old sale", old)

    income, expense = db.get_summary_totals(days=30)
    assert income == 1000.0  # the 60-day-old one is outside the 30-day window


def test_spending_by_label_groups_correctly(db):
    food = db.add_label(name="Food", color="grey500")
    rent = db.add_label(name="Rent", color="grey500")
    now = datetime.now().isoformat(timespec="seconds")

    db.add_transaction(200.0, "expense", food, "groceries", now)
    db.add_transaction(300.0, "expense", food, "snacks", now)
    db.add_transaction(1000.0, "expense", rent, "rent", now)

    breakdown = {row["label_name"]: row["total"] for row in db.get_spending_by_label(days=30)}
    assert breakdown["Food"] == 500.0
    assert breakdown["Rent"] == 1000.0


def test_daily_totals_fills_gaps_with_zero(db):
    # No transactions added at all -- every day in the window should
    # still appear, with 0/0, rather than being skipped.
    days = db.get_daily_totals(days=7)
    assert len(days) == 7
    assert all(d["income"] == 0 and d["expense"] == 0 for d in days)


def test_stats_window_days_defaults_to_thirty(db):
    assert db.get_stats_window_days() == 30


def test_stats_window_days_persists(db):
    db.set_stats_window_days(90)
    assert db.get_stats_window_days() == 90


def test_stats_window_days_falls_back_on_bad_value(db):
    db.set_setting("stats_window_days", "garbage")
    assert db.get_stats_window_days() == db.DEFAULT_STATS_WINDOW_DAYS


def test_transaction_stats_counts_and_averages(db):
    label_id = db.add_label(name="Sales", color="grey500")
    now = datetime.now().isoformat(timespec="seconds")

    db.add_transaction(1000.0, "income", label_id, "sale1", now)
    db.add_transaction(2000.0, "income", label_id, "sale2", now)
    db.add_transaction(100.0, "expense", label_id, "exp1", now)
    db.add_transaction(300.0, "expense", label_id, "exp2", now)

    stats = db.get_transaction_stats(days=30)
    assert stats["count"] == 4
    assert stats["avg_income"] == 1500.0
    assert stats["avg_expense"] == 200.0
    assert stats["max_income"] == 2000.0
    assert stats["max_expense"] == 300.0


def test_transaction_stats_with_no_data_returns_zeros(db):
    stats = db.get_transaction_stats(days=30)
    assert stats["count"] == 0
    assert stats["avg_income"] == 0
    assert stats["max_expense"] == 0


def test_period_comparison_compares_current_vs_previous_window(db):
    label_id = db.add_label(name="Sales", color="grey500")
    now = datetime.now()

    # Current 30-day window: net = 2000 - 100 = 1900
    db.add_transaction(2000.0, "income", label_id, "recent sale",
                        now.isoformat(timespec="seconds"))
    db.add_transaction(100.0, "expense", label_id, "recent expense",
                        now.isoformat(timespec="seconds"))

    # Previous 30-day window (31-60 days ago): net = 500 - 200 = 300
    old = (now - timedelta(days=45)).isoformat(timespec="seconds")
    db.add_transaction(500.0, "income", label_id, "old sale", old)
    db.add_transaction(200.0, "expense", label_id, "old expense", old)

    current_net, previous_net, pct_change = db.get_period_comparison(days=30)
    assert current_net == 1900.0
    assert previous_net == 300.0
    assert pct_change == pytest.approx(((1900 - 300) / 300) * 100)


def test_period_comparison_returns_none_percent_when_previous_period_empty(db):
    label_id = db.add_label(name="Sales", color="grey500")
    db.add_transaction(1000.0, "income", label_id, "sale",
                        datetime.now().isoformat(timespec="seconds"))

    # No transactions at all in the previous period -- percent_change
    # should be None (not a divide-by-zero or a meaningless "infinite%").
    current_net, previous_net, pct_change = db.get_period_comparison(days=30)
    assert previous_net == 0
    assert pct_change is None


# ---------------------------------------------------------------------------
# App settings (key-value)
# ---------------------------------------------------------------------------

def test_get_setting_returns_default_when_missing(db):
    assert db.get_setting("nonexistent_key", "fallback") == "fallback"


def test_set_and_get_setting_roundtrip(db):
    db.set_setting("pin_enabled", "true")
    assert db.get_setting("pin_enabled") == "true"


def test_set_setting_overwrites_existing_value(db):
    db.set_setting("pin_code", "1111")
    db.set_setting("pin_code", "2222")
    assert db.get_setting("pin_code") == "2222"


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

def test_transactions_csv_contains_expected_row(db):
    label_id = db.add_label(name="Food", color="grey500")
    db.add_transaction(150.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")

    csv_content = db.build_transactions_csv()
    assert "lunch" in csv_content
    assert "150.0" in csv_content
    assert "Food" in csv_content


def test_debts_csv_includes_settled_entries(db):
    db.add_debt("Ramesh", 500.0, "debt", "udhaar", "2026-07-01T10:00:00")
    debt_id = db.get_debts()[0]["id"]
    db.settle_debt(debt_id)

    csv_content = db.build_debts_csv()
    assert "Ramesh" in csv_content
    assert "yes" in csv_content  # the settled=yes column


# ---------------------------------------------------------------------------
# Backup / Restore
# ---------------------------------------------------------------------------

def test_create_backup_file_produces_valid_sqlite_file(db, tmp_path):
    db.add_label(name="Food", color="orange400")
    backup_path = tmp_path / "backup.db"

    db.create_backup_file(str(backup_path))

    assert backup_path.exists()
    # Verify independently, not through our own DB_PATH, that the backup
    # actually contains the data.
    import sqlite3
    conn = sqlite3.connect(str(backup_path))
    conn.row_factory = sqlite3.Row
    labels = conn.execute("SELECT * FROM labels").fetchall()
    conn.close()
    assert len(labels) == 1
    assert labels[0]["color"] == "orange400"


def test_restore_from_backup_file_replaces_live_data(db, tmp_path):
    db.add_label(name="Food", color="orange400")
    db.add_transaction(500.0, "expense", db.get_labels()[0]["id"], "lunch", "2026-07-01T10:00:00")

    backup_path = tmp_path / "backup.db"
    db.create_backup_file(str(backup_path))

    # Wipe live data
    db.delete_transaction(db.get_transactions()[0]["id"])
    db.delete_label(db.get_labels()[0]["id"])
    assert db.get_labels() == []
    assert db.get_transactions() == []

    db.restore_from_backup_file(str(backup_path))

    restored_labels = db.get_labels()
    restored_txns = db.get_transactions()
    assert len(restored_labels) == 1
    assert restored_labels[0]["color"] == "orange400"
    assert len(restored_txns) == 1


def test_restore_rejects_missing_file(db, tmp_path):
    missing_path = tmp_path / "does_not_exist.db"
    with pytest.raises(db.DatabaseError):
        db.restore_from_backup_file(str(missing_path))


def test_restore_rejects_file_that_is_not_a_database(db, tmp_path):
    bad_path = tmp_path / "not_a_db.db"
    bad_path.write_text("this is not a sqlite database")

    with pytest.raises(db.DatabaseError):
        db.restore_from_backup_file(str(bad_path))


def test_restore_rejects_sqlite_file_missing_required_tables(db, tmp_path):
    # A real SQLite file, but not a SpendBook backup -- should still be
    # rejected rather than silently "restoring" into a broken state.
    import sqlite3
    wrong_path = tmp_path / "wrong_schema.db"
    conn = sqlite3.connect(str(wrong_path))
    conn.execute("CREATE TABLE something_else (id INTEGER)")
    conn.commit()
    conn.close()

    with pytest.raises(db.DatabaseError):
        db.restore_from_backup_file(str(wrong_path))


# ---------------------------------------------------------------------------
# Schema migrations
# ---------------------------------------------------------------------------

def test_fresh_database_reaches_latest_schema_version(db):
    conn = db.get_connection()
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    conn.close()
    assert version == len(db.MIGRATIONS)


def test_initialize_database_is_safe_to_call_repeatedly(db):
    # Simulates the app being closed and reopened multiple times --
    # must not re-run migrations, error, or touch existing data.
    label_id = db.add_label(name="Food", color="orange400")
    db.add_transaction(100.0, "expense", label_id, "some data", "2026-01-01T10:00:00")

    db.initialize_database()
    db.initialize_database()

    assert len(db.get_transactions()) == 1
    assert db.get_transactions()[0]["note"] == "some data"


def test_migration_preserves_existing_data_from_before_migration_system(db, tmp_path):
    # Simulates a real upgrading user: a database created by the schema
    # that existed before this migration system, with real data in it
    # and user_version left at its default of 0.
    import sqlite3

    old_db_path = tmp_path / "pre_migration.db"
    conn = sqlite3.connect(str(old_db_path))
    conn.execute("""
        CREATE TABLE labels(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL, emoji TEXT, color TEXT
        );
    """)
    conn.execute("""
        CREATE TABLE transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            amount REAL NOT NULL, type TEXT NOT NULL, label_id INTEGER,
            note TEXT, created_at TEXT NOT NULL
        );
    """)
    conn.execute("""
        CREATE TABLE debts(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_name TEXT NOT NULL, amount REAL NOT NULL, type TEXT NOT NULL,
            note TEXT, created_at TEXT NOT NULL, settled INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.execute("CREATE TABLE app_settings(key TEXT PRIMARY KEY, value TEXT);")
    conn.execute("INSERT INTO labels (name, color) VALUES ('Food', 'orange400')")
    conn.execute(
        "INSERT INTO transactions (amount, type, label_id, note, created_at) "
        "VALUES (500, 'expense', 1, 'pre-existing important data', '2026-01-01T10:00:00')"
    )
    conn.commit()
    conn.close()

    # Point the module at this simulated old database and run the real
    # initialize_database() against it.
    original_path = db.DB_PATH
    db.DB_PATH = old_db_path
    try:
        db.initialize_database()

        transactions = db.get_transactions()
        assert len(transactions) == 1
        assert transactions[0]["note"] == "pre-existing important data"

        conn = db.get_connection()
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(db.MIGRATIONS)
        conn.close()
    finally:
        db.DB_PATH = original_path


def test_failed_migration_rolls_back_without_losing_data(db):
    # A broken future migration must not corrupt the schema or lose data
    # already in the database -- the whole batch should roll back.
    label_id = db.add_label(name="Food", color="orange400")
    db.add_transaction(100.0, "expense", label_id, "data before broken migration", "2026-01-01T10:00:00")

    def _broken_migration(conn):
        conn.execute("ALTER TABLE labels ADD COLUMN this_should_not_persist TEXT")
        conn.execute("THIS IS NOT VALID SQL")

    original_migrations = db.MIGRATIONS[:]
    db.MIGRATIONS.append(_broken_migration)
    try:
        with pytest.raises(db.DatabaseError):
            db.initialize_database()

        # Schema version must not have advanced
        conn = db.get_connection()
        assert conn.execute("PRAGMA user_version").fetchone()[0] == len(original_migrations)

        # The partial ALTER TABLE from the broken migration must not persist
        columns = [row[1] for row in conn.execute("PRAGMA table_info(labels)").fetchall()]
        assert "this_should_not_persist" not in columns
        conn.close()

        # Original data must be untouched
        assert len(db.get_transactions()) == 1
        assert db.get_transactions()[0]["note"] == "data before broken migration"
    finally:
        db.MIGRATIONS[:] = original_migrations


# ---------------------------------------------------------------------------
# Version-change detection (for auto-backup-on-update)
# ---------------------------------------------------------------------------

def test_check_and_record_version_true_on_first_call(db):
    # No prior version recorded yet -- first-ever launch, treated the
    # same as "an update just happened" so a first backup gets made.
    assert db.check_and_record_version("1.0.0") is True


def test_check_and_record_version_false_when_unchanged(db):
    db.check_and_record_version("1.0.0")
    assert db.check_and_record_version("1.0.0") is False


def test_check_and_record_version_true_when_version_changes(db):
    db.check_and_record_version("1.0.0")
    assert db.check_and_record_version("1.1.0") is True


def test_check_and_record_version_false_after_recording_new_version(db):
    db.check_and_record_version("1.0.0")
    db.check_and_record_version("1.1.0")
    assert db.check_and_record_version("1.1.0") is False