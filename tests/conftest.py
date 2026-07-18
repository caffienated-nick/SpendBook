"""
conftest.py is a special pytest filename: fixtures defined here are
automatically available to every test file in this folder, with no
import needed. This is where shared setup/teardown lives.
"""
import sys
import tempfile
from pathlib import Path

import pytest

# So `import database` works from the tests folder -- database.py lives
# in ../src relative to this file.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import database


@pytest.fixture
def db():
    """
    Gives each test a brand-new, empty SpendBook database in a temp file.
    Runs before the test (everything before `yield`), then cleans up
    after (everything after `yield`) -- even if the test fails.

    Usage: just add `db` as a parameter to any test function and pytest
    wires this up automatically, e.g. `def test_something(db): ...`
    """
    tmp_dir = tempfile.mkdtemp()
    test_db_path = Path(tmp_dir) / "test_spendbook.db"

    # Point the database module at our temp file instead of the real one.
    original_path = database.DB_PATH
    database.DB_PATH = test_db_path
    database.initialize_database()

    yield database  # the test gets the database module itself

    # Cleanup: restore the real path and delete the temp file, so temp
    # files don't pile up on disk and the next test run starts clean.
    database.DB_PATH = original_path
    if test_db_path.exists():
        test_db_path.unlink()
