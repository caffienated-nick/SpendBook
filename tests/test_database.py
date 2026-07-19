"""
Tests for database.py -- the data layer, tested independent of any UI.

Run with:  uv run pytest              (from the project root)
      or:  uv run pytest -v           (verbose: shows each test name)
      or:  uv run pytest tests/test_database.py::test_add_balance_math
                                       (run just one test)
"""
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------

def test_fresh_database_has_no_labels(db):
    # `db` here is the fixture from conftest.py -- pytest sees this
    # parameter name and automatically runs the fixture before the test.
    assert db.get_labels() == []


def test_add_label_returns_new_id(db):
    label_id = db.add_label("Food", "🍔")
    assert isinstance(label_id, int)

    labels = db.get_labels()
    assert len(labels) == 1
    assert labels[0]["name"] == "Food"
    assert labels[0]["emoji"] == "🍔"


def test_delete_label_removes_it(db):
    label_id = db.add_label("Temp", "❓")
    db.delete_label(label_id)
    assert db.get_labels() == []


def test_deleting_a_label_does_not_delete_its_transactions(db):
    # This documents an intentional design choice: deleting a label
    # shouldn't erase transaction history, it should just show as
    # "Uncategorized" going forward (see get_transactions()'s LEFT JOIN).
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(100, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    db.delete_label(label_id)

    transactions = db.get_transactions()
    assert len(transactions) == 1
    assert transactions[0]["label_name"] is None


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def test_add_transaction_appears_in_list(db):
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(150.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")

    transactions = db.get_transactions()
    assert len(transactions) == 1
    assert transactions[0]["amount"] == 150.0
    assert transactions[0]["type"] == "expense"
    assert transactions[0]["note"] == "lunch"


def test_balance_is_income_minus_expense(db):
    label_id = db.add_label("Sales", "💰")
    db.add_transaction(1000.0, "income", label_id, "sales", "2026-07-01T10:00:00")
    db.add_transaction(300.0, "expense", label_id, "supplies", "2026-07-01T11:00:00")

    assert db.get_balance() == 700.0


def test_update_transaction_changes_amount_and_note(db):
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(100.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    transaction_id = db.get_transactions()[0]["id"]

    db.update_transaction(transaction_id, amount=150.0, type_="expense",
                           label_id=label_id, note="lunch (corrected)")

    updated = db.get_transactions()[0]
    assert updated["amount"] == 150.0
    assert updated["note"] == "lunch (corrected)"


def test_delete_transaction_removes_it(db):
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(100.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    transaction_id = db.get_transactions()[0]["id"]

    db.delete_transaction(transaction_id)

    assert db.get_transactions() == []


def test_transactions_are_sorted_newest_first(db):
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(100.0, "expense", label_id, "older", "2026-07-01T10:00:00")
    db.add_transaction(200.0, "expense", label_id, "newer", "2026-07-02T10:00:00")

    transactions = db.get_transactions()
    assert transactions[0]["note"] == "newer"
    assert transactions[1]["note"] == "older"


def test_transaction_search_matches_note(db):
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(100.0, "expense", label_id, "lunch at dhaba", "2026-07-01T10:00:00")
    db.add_transaction(200.0, "expense", label_id, "groceries", "2026-07-01T11:00:00")

    results = db.get_transactions(search="lunch")
    assert len(results) == 1
    assert results[0]["note"] == "lunch at dhaba"


def test_transaction_search_matches_label_name(db):
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(100.0, "expense", label_id, "lunch", "2026-07-01T10:00:00")
    db.add_transaction(200.0, "expense", label_id, "groceries", "2026-07-01T11:00:00")

    results = db.get_transactions(search="food")
    assert len(results) == 2


def test_transaction_search_is_case_insensitive(db):
    label_id = db.add_label("Food", "🍔")
    db.add_transaction(100.0, "expense", label_id, "LUNCH", "2026-07-01T10:00:00")

    results = db.get_transactions(search="lunch")
    assert len(results) == 1


def test_transaction_search_with_no_matches_returns_empty(db):
    label_id = db.add_label("Food", "🍔")
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
    label_id = db.add_label("Sales", "💰")
    recent = datetime.now().isoformat(timespec="seconds")
    old = (datetime.now() - timedelta(days=60)).isoformat(timespec="seconds")

    db.add_transaction(1000.0, "income", label_id, "recent sale", recent)
    db.add_transaction(5000.0, "income", label_id, "old sale", old)

    income, expense = db.get_summary_totals(days=30)
    assert income == 1000.0  # the 60-day-old one is outside the 30-day window


def test_spending_by_label_groups_correctly(db):
    food = db.add_label("Food", "🍔")
    rent = db.add_label("Rent", "🏠")
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
    label_id = db.add_label("Food", "🍔")
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