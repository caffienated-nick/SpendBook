"""
Debounced auto-backup: silently backs up the database to
Downloads/SpendBook/ a short while after the user stops making changes,
instead of on every single add/edit/delete.

Why debounced, not immediate: create_backup_file() copies the entire
database file. Doing that on every single transaction add would mean
copying the whole file dozens of times during a normal day of shop
use -- real, noticeable lag, and each write is also a small window
where a crash mid-copy could leave a half-written backup. Debouncing
means: every change resets a short timer, and only once nothing has
changed for DEBOUNCE_SECONDS straight does a backup actually run. Rapid
bursts of edits collapse into a single backup at the end.

Usage: call notify_data_changed(page) after any successful add/edit/
delete/settle/restore anywhere in the app. Everything else is handled
internally.
"""

import asyncio

import flet as ft

DEBOUNCE_SECONDS = 30

# Per-page state, since each Flet session/page could in principle be a
# different "app instance" (e.g. desktop vs. a hot-reloaded session).
# Keyed by id(page) rather than stashed as a page attribute so this
# module has zero dependency on what other code has already attached to
# the page object.
_pending_tasks: dict[int, asyncio.Task] = {}


def notify_data_changed(page: ft.Page):
    """
    Call this after any successful data-changing operation (adding,
    editing, deleting, or settling a transaction/debt/label, or a
    restore). Resets the debounce timer -- if this is called again
    before DEBOUNCE_SECONDS elapses, the previous pending backup is
    cancelled and a new one is scheduled instead.

    Safe to call frequently and from anywhere; failures during the
    eventual backup are swallowed silently (see _run_debounced_backup)
    since this is a background convenience feature, not a user-facing
    action -- interrupting whatever the person is doing with a backup
    error would be worse than just skipping this one round silently.
    """
    key = id(page)
    existing_task = _pending_tasks.get(key)
    if existing_task is not None and not existing_task.done():
        existing_task.cancel()

    _pending_tasks[key] = asyncio.ensure_future(_run_debounced_backup(page))


async def _run_debounced_backup(page: ft.Page):
    try:
        await asyncio.sleep(DEBOUNCE_SECONDS)
    except asyncio.CancelledError:
        # A newer change came in and reset the timer -- this instance's
        # job is done, the new one will run instead. Not an error.
        return

    # Local imports: keeps this module import-safe even before the rest
    # of the app (database.py, settings.py's storage helpers) has
    # finished initializing, and avoids a circular import at module
    # load time.
    import database as db
    from views.settings import _get_or_create_storage_paths, _get_backup_path

    try:
        # Same "skip if there's nothing to back up yet" guard as the
        # on-update auto-backup, so a fresh install with no data doesn't
        # generate a pointless empty backup file every 30 seconds of
        # idle time after the first keystroke.
        if not db.get_transactions() and not db.get_debts() and not db.get_labels():
            return

        sp = _get_or_create_storage_paths(page)
        if sp is None:
            return

        downloads_dir = await sp.get_downloads_directory()
        if not downloads_dir:
            return

        destination = _get_backup_path(downloads_dir)
        db.create_backup_file(destination)
    except Exception:
        # Intentionally silent -- see module docstring.
        pass
