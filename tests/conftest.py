"""
conftest.py is a special pytest filename: fixtures defined here are
automatically available to every test file in this folder, with no
import needed. This is where shared setup/teardown lives.
"""
import gc
import sys
import tempfile
import warnings
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

    # On Windows (unlike Linux/Mac), a file can't be deleted while any
    # sqlite3.Connection to it is still open -- even one a test forgot
    # to .close() explicitly. Python closes a Connection's underlying
    # handle when it's garbage collected, so a forced GC pass here
    # releases any such leftover lock before we try to delete the file.
    # This is a safety net, not a substitute for tests closing their own
    # connections -- but it means one missed .close() in a test doesn't
    # take down an unrelated test's cleanup.
    gc.collect()

    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except PermissionError:
            # Still locked despite the GC pass -- warn instead of
            # failing the test itself over cleanup; the OS will reclaim
            # the temp file eventually, and failing here would make an
            # otherwise-passing test look broken.
            warnings.warn(
                f"Could not delete temp test database at {test_db_path} "
                f"(still locked). This doesn't affect the test result, "
                f"but check for an unclosed database.get_connection() "
                f"call in the test that just ran.",
                stacklevel=2,
            )