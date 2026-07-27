import flet as ft

from database import (
    get_labels, add_label, delete_label,
    build_transactions_csv, build_debts_csv,
    create_backup_file, restore_from_backup_file, BACKUP_FILENAME, BACKUP_SUBFOLDER,
    get_overdue_days, set_overdue_days,
    DatabaseError,
)
from version import APP_VERSION, RELEASES_URL
from views.ui_helpers import show_error


# Slightly smaller text than a button's default, used for the buttons
# that sit two-in-a-row (CSV export, Backup/Restore) -- these were
# reported as visually chopped/cramped even after widening the dialog,
# since the row still splits available width in half between two labels
# plus an icon each.
_SMALL_BUTTON_STYLE = ft.ButtonStyle(
    text_style=ft.TextStyle(size=12),
    icon_size=16,
    padding=ft.Padding(left=8, right=8, top=8, bottom=8),
)


def _get_or_create_share(page: ft.Page):
    """
    Reuse a single Share service stashed on the page instead of creating a
    fresh one every time Settings is opened. Share is a "Service" control
    (page.services, not page.overlay) -- it opens Android's native share
    sheet, which is far more reliably supported across Flet versions than
    FilePicker's save-file dialog was (that one threw "Unknown control:
    FilePicker" on real device builds).
    """
    existing = getattr(page, "_spendbook_share", None)
    if existing is not None:
        return existing
    try:
        share = ft.Share()
        page.services.append(share)
        page.update()
    except Exception:
        return None
    page._spendbook_share = share
    return share


def _get_or_create_storage_paths(page: ft.Page):
    """
    Reuse a single StoragePaths service stashed on the page, same pattern
    as _get_or_create_share. StoragePaths gives access to the device's
    Downloads folder without needing FilePicker -- backup/restore write
    to and read from a fixed filename there instead of an interactive
    file-open dialog.
    """
    existing = getattr(page, "_spendbook_storage_paths", None)
    if existing is not None:
        return existing
    try:
        sp = ft.StoragePaths()
        page.services.append(sp)
        page.update()
    except Exception:
        return None
    page._spendbook_storage_paths = sp
    return sp


def _get_backup_path(downloads_dir: str) -> str:
    """
    Builds the full backup file path inside a dedicated SpendBook
    subfolder within Downloads (Downloads/SpendBook/SpendBook_backup.db)
    instead of dropping the file directly into Downloads -- keeps it out
    of the way of a person's other downloaded files. Creates the
    subfolder if it doesn't exist yet.
    """
    import os
    folder = os.path.join(downloads_dir, BACKUP_SUBFOLDER)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, BACKUP_FILENAME)


def _get_or_create_clipboard(page: ft.Page):
    """
    Reuse a single Clipboard service stashed on the page, same pattern as
    _get_or_create_share/_get_or_create_storage_paths. page.clipboard
    (the older API) is deprecated in this Flet version in favor of the
    ft.Clipboard() service.
    """
    existing = getattr(page, "_spendbook_clipboard", None)
    if existing is not None:
        return existing
    try:
        clipboard = ft.Clipboard()
        page.services.append(clipboard)
        page.update()
    except Exception:
        return None
    page._spendbook_clipboard = clipboard
    return clipboard


def open_settings_dialog(page: ft.Page, on_data_changed):
    """
    Opens the Settings dialog: manage labels, export data to CSV, and
    backup/restore the full database. `on_data_changed` is called after
    any change that could affect data shown elsewhere in the app (adding/
    deleting a label, or a full restore) -- callers should wire this to
    refresh every visible tab, not just one, since a restore in
    particular replaces transactions, debts, AND labels all at once.
    """

    # -----------------------------------------------------------------
    # Labels section
    # -----------------------------------------------------------------

    name_field = ft.TextField(label="Label name", autofocus=True, expand=True)
    label_error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

    # A fixed palette instead of free-text color entry -- tapping a
    # swatch is much easier on a phone than typing a hex code, and a
    # small fixed set keeps labels visually distinct without needing a
    # full color picker control.
    PALETTE = [
        ft.Colors.RED_400, ft.Colors.ORANGE_400, ft.Colors.AMBER_400,
        ft.Colors.GREEN_400, ft.Colors.TEAL_400, ft.Colors.BLUE_400,
        ft.Colors.INDIGO_400, ft.Colors.PURPLE_400, ft.Colors.PINK_400,
        ft.Colors.BROWN_400, ft.Colors.GREY_500, ft.Colors.CYAN_400,
    ]
    selected_color = {"value": PALETTE[0]}

    def _build_swatch(color):
        is_selected = color == selected_color["value"]
        border = None
        if is_selected:
            side = ft.BorderSide(width=2, color=ft.Colors.WHITE)
            border = ft.Border(top=side, right=side, bottom=side, left=side)

        def handle_pick(e):
            selected_color["value"] = color
            swatch_row.controls = [_build_swatch(c) for c in PALETTE]
            swatch_row.update()

        return ft.Container(
            width=28, height=28, border_radius=14, bgcolor=color,
            border=border,
            on_click=handle_pick,
        )

    swatch_row = ft.Row(
        [_build_swatch(c) for c in PALETTE],
        wrap=True, spacing=8, run_spacing=8,
    )

    # Shorter than before (was 140) so the Add Label button below it stays
    # visible without scrolling even when there are many labels -- this
    # list scrolls internally instead of pushing everything else down.
    label_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=90)

    dialog_mounted = {"value": False}

    def refresh_list():
        try:
            labels = get_labels()
        except DatabaseError as e:
            label_list.controls = [ft.Text(f"Couldn't load labels: {e}", color=ft.Colors.RED_400)]
            if dialog_mounted["value"]:
                label_list.update()
            return

        if not labels:
            label_list.controls = [ft.Text("No labels yet. Add one below.", color=ft.Colors.GREY)]
        else:
            label_list.controls = [_build_label_row(l) for l in labels]
        # Only call update() once the dialog has actually been shown --
        # before that, this control isn't attached to the page and
        # accessing/using .page raises instead of returning None.
        if dialog_mounted["value"]:
            label_list.update()

    def _build_label_row(label):
        def handle_delete(e, lid=label["id"]):
            try:
                delete_label(lid)
            except DatabaseError as db_err:
                show_error(page, f"Couldn't delete label: {db_err}")
                return
            refresh_list()
            on_data_changed()

        return ft.Row(
            [
                ft.Container(width=14, height=14, border_radius=7, bgcolor=label["color"] or ft.Colors.GREY_500),
                ft.Text(label["name"], expand=True, size=13),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=16,
                    on_click=handle_delete,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            spacing=8,
        )

    def handle_add_label(e):
        name = (name_field.value or "").strip()
        if not name:
            label_error_text.value = "Enter a label name."
            label_error_text.visible = True
            page.update()
            return

        try:
            add_label(name=name, color=selected_color["value"])
        except DatabaseError as db_err:
            label_error_text.value = f"Couldn't save: {db_err}"
            label_error_text.visible = True
            page.update()
            return

        name_field.value = ""
        label_error_text.visible = False
        refresh_list()
        on_data_changed()
        page.update()

    # -----------------------------------------------------------------
    # Export section (share sheet, not a save-file dialog)
    # -----------------------------------------------------------------

    export_status = ft.Text("", size=12, color=ft.Colors.GREEN_600)

    async def _export(build_fn, filename: str, label: str):
        share = _get_or_create_share(page)
        if share is None:
            export_status.value = "Export isn't available on this device/build."
            export_status.color = ft.Colors.RED_400
            page.update()
            return

        try:
            content = build_fn()
        except DatabaseError as db_err:
            export_status.value = f"Export failed: {db_err}"
            export_status.color = ft.Colors.RED_400
            page.update()
            return

        try:
            await share.share_files(
                files=[ft.ShareFile(data=content.encode("utf-8"), mime_type="text/csv", name=filename)],
                subject=f"SpendBook {label} export",
            )
            export_status.color = ft.Colors.GREEN_600
            export_status.value = f"{label} ready to share."
        except Exception as share_err:
            export_status.color = ft.Colors.RED_400
            export_status.value = f"Share failed: {share_err}"
        page.update()

    async def handle_export_transactions(e):
        await _export(build_transactions_csv, "spendbook_transactions.csv", "Transactions")

    async def handle_export_debts(e):
        await _export(build_debts_csv, "spendbook_debts.csv", "Debts/Dues")

    # -----------------------------------------------------------------
    # Backup & Restore (full database, for moving to a new phone)
    #
    # Writes/reads a fixed filename in the device's Downloads folder
    # instead of using FilePicker (which crashes on real Android builds
    # in this Flet version) -- to move data to a new phone: back up on
    # the old phone, transfer that one file to the new phone's Downloads
    # folder by any means (USB, cloud, etc.), then restore there.
    # -----------------------------------------------------------------

    backup_status = ft.Text("", size=12, color=ft.Colors.GREEN_600)

    async def handle_backup(e):
        try:
            sp = _get_or_create_storage_paths(page)
            if sp is None:
                backup_status.value = "Backup isn't available on this device/build."
                backup_status.color = ft.Colors.RED_400
                page.update()
                return

            try:
                downloads_dir = await sp.get_downloads_directory()
            except Exception as path_err:
                backup_status.value = f"Couldn't find Downloads folder: {path_err}"
                backup_status.color = ft.Colors.RED_400
                page.update()
                return

            if not downloads_dir:
                backup_status.value = "Downloads folder isn't available on this device."
                backup_status.color = ft.Colors.RED_400
                page.update()
                return

            destination = _get_backup_path(downloads_dir)
            try:
                create_backup_file(destination)
                backup_status.color = ft.Colors.GREEN_600
                backup_status.value = f"Backed up to Downloads/{BACKUP_SUBFOLDER}/{BACKUP_FILENAME}"
            except DatabaseError as db_err:
                backup_status.color = ft.Colors.RED_400
                backup_status.value = f"Backup failed: {db_err}"
            page.update()
        except Exception as unexpected_err:
            # Same reasoning as _perform_restore's catch-all: a caught-
            # but-uncaught-type exception here (e.g. a storage permission
            # error) previously failed with no visible feedback at all.
            backup_status.color = ft.Colors.RED_400
            backup_status.value = f"Backup failed unexpectedly: {unexpected_err}"
            try:
                page.update()
            except Exception:
                pass

    def confirm_and_restore(e):
        def do_restore(confirm_e):
            page.pop_dialog()
            page.run_task(_perform_restore)

        def cancel(confirm_e):
            page.pop_dialog()

        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Restore from backup?"),
            content=ft.Text(
                f"This replaces ALL current data (transactions, debts, "
                f"labels) with what's in Downloads/{BACKUP_SUBFOLDER}/{BACKUP_FILENAME}. "
                f"This can't be undone. Make sure that file is the backup "
                f"you actually want."
            ),
            actions=[
                ft.TextButton("Cancel", on_click=cancel),
                ft.TextButton("Restore", style=ft.ButtonStyle(color=ft.Colors.RED_400), on_click=do_restore),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(confirm_dialog)

    async def _perform_restore():
        try:
            sp = _get_or_create_storage_paths(page)
            if sp is None:
                backup_status.value = "Restore isn't available on this device/build."
                backup_status.color = ft.Colors.RED_400
                page.update()
                return

            try:
                downloads_dir = await sp.get_downloads_directory()
            except Exception as path_err:
                backup_status.value = f"Couldn't find Downloads folder: {path_err}"
                backup_status.color = ft.Colors.RED_400
                page.update()
                return

            if not downloads_dir:
                backup_status.value = "Downloads folder isn't available on this device."
                backup_status.color = ft.Colors.RED_400
                page.update()
                return

            import os
            new_style_source = os.path.join(downloads_dir, BACKUP_SUBFOLDER, BACKUP_FILENAME)
            old_style_source = os.path.join(downloads_dir, BACKUP_FILENAME)

            # Backups are now stored in a Downloads/SpendBook subfolder
            # (previously directly in Downloads). Check the new location
            # first, but fall back to the old flat path so anyone who
            # backed up before this change doesn't see a false "file not
            # found" just because where we look changed underneath them.
            source = new_style_source if os.path.exists(new_style_source) else old_style_source

            try:
                restore_from_backup_file(source)
                backup_status.color = ft.Colors.GREEN_600
                backup_status.value = "Restored successfully."
            except DatabaseError as db_err:
                backup_status.color = ft.Colors.RED_400
                backup_status.value = f"Restore failed: {db_err}"
            page.update()
            # Refresh whatever's currently showing labels/transactions so
            # anything already on screen reflects the restored data
            # without forcing an app restart, where possible.
            refresh_list()
            on_data_changed()
        except Exception as unexpected_err:
            # This is the critical addition: previously only DatabaseError
            # was caught, so anything else -- e.g. a permissions error
            # reading Downloads after a fresh reinstall, since Android
            # storage permission grants are wiped on uninstall and must
            # be re-granted -- failed completely silently. The Restore
            # button appeared to "do nothing" with no error shown at all.
            # This catch-all guarantees the user always sees *something*
            # went wrong instead of nothing happening.
            backup_status.color = ft.Colors.RED_400
            backup_status.value = f"Restore failed unexpectedly: {unexpected_err}"
            try:
                page.update()
            except Exception:
                pass

    # -----------------------------------------------------------------
    # Preferences
    # -----------------------------------------------------------------

    OVERDUE_OPTIONS = [3, 7, 14, 30]

    overdue_days_dropdown = ft.Dropdown(
        value=str(get_overdue_days()),
        options=[ft.dropdown.Option(key=str(d), text=f"{d} days") for d in OVERDUE_OPTIONS],
        dense=True,
        width=110,
    )

    def handle_overdue_days_change(e):
        try:
            days = int(overdue_days_dropdown.value)
        except (TypeError, ValueError):
            return
        set_overdue_days(days)

    overdue_days_dropdown.on_select = handle_overdue_days_change

    # -----------------------------------------------------------------
    # About / manual update check
    #
    # Deliberately minimal: opens the GitHub Releases page in the
    # device's browser so the person can see if a newer version exists
    # and download it themselves. No auto-download, no background
    # checking, no install prompts -- an in-app auto-updater would need
    # Android install-package permissions and a fair bit of extra
    # complexity/risk for a beta, minimal, offline-first app.
    # -----------------------------------------------------------------

    def handle_check_updates(e):
        # Shows an in-app dialog instead of immediately opening a
        # browser -- launch_url() previously fired straight away, which
        # jumped the person out of the app with no confirmation. This
        # keeps them in SpendBook; opening the Releases page is now an
        # explicit, separate tap, and the link can be copied instead if
        # they'd rather check on another device.
        def open_in_browser(dialog_e):
            page.launch_url(RELEASES_URL)
            page.pop_dialog()

        async def copy_link(dialog_e):
            clipboard = _get_or_create_clipboard(page)
            if clipboard is None:
                copy_status.value = "Couldn't access clipboard on this device."
                copy_status.color = ft.Colors.RED_400
            else:
                try:
                    await clipboard.set(RELEASES_URL)
                    copy_status.value = "Link copied."
                    copy_status.color = ft.Colors.GREEN_600
                except Exception as clip_err:
                    copy_status.value = f"Couldn't copy: {clip_err}"
                    copy_status.color = ft.Colors.RED_400
            copy_status.visible = True
            page.update()

        def close(dialog_e):
            page.pop_dialog()

        copy_status = ft.Text("", size=11, visible=False)

        update_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Check for updates"),
            content=ft.Container(
                width=280,
                content=ft.Column(
                    [
                        ft.Text(f"You have version {APP_VERSION} installed.", size=13),
                        ft.Text(
                            "SpendBook doesn't check for updates automatically. "
                            "To see if a newer version is available, visit the "
                            "Releases page:",
                            size=13,
                        ),
                        ft.Text(RELEASES_URL, size=11, color=ft.Colors.GREY, selectable=True),
                        copy_status,
                    ],
                    tight=True,
                    spacing=10,
                ),
            ),
            actions=[
                ft.TextButton("Copy link", on_click=copy_link),
                ft.TextButton("Cancel", on_click=close),
                ft.FilledButton("Open in browser", on_click=open_in_browser),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        page.show_dialog(update_dialog)

    # -----------------------------------------------------------------
    # Dialog assembly
    # -----------------------------------------------------------------

    def close_dialog(e=None):
        page.pop_dialog()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Settings"),
        content=ft.Container(
            # Widened from 280 -> 320: at 280 several button labels
            # ("Check for updates", "Transactions"/"Debts/Dues" side by
            # side, "Backup now"/"Restore" side by side) were tight
            # enough to visually squish/wrap awkwardly. 320 gives more
            # breathing room while still comfortably fitting on a phone
            # screen (typical usable width after system padding is
            # ~340-360px on most devices).
            width=320,
            content=ft.Column(
                [
                    ft.Text("Labels", weight=ft.FontWeight.BOLD, size=14),
                    label_list,
                    name_field,
                    swatch_row,
                    ft.FilledButton(
                        "Add label",
                        icon=ft.Icons.ADD,
                        on_click=handle_add_label,
                        width=320,
                    ),
                    label_error_text,

                    ft.Divider(),

                    ft.Text("Export", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text("Shares a CSV file via your device's share sheet.", size=11, color=ft.Colors.GREY),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Transactions",
                                on_click=handle_export_transactions,
                                expand=True,
                                style=_SMALL_BUTTON_STYLE,
                            ),
                            ft.OutlinedButton(
                                "Debts/Dues",
                                on_click=handle_export_debts,
                                expand=True,
                                style=_SMALL_BUTTON_STYLE,
                            ),
                        ],
                        spacing=8,
                    ),
                    export_status,

                    ft.Divider(),

                    ft.Text("Backup & Restore", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text(
                        "Saves the full database to Downloads. To move to a "
                        "new phone: back up here, transfer the file to the "
                        "new phone's Downloads folder, then restore there.",
                        size=11, color=ft.Colors.GREY,
                    ),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Backup now",
                                icon=ft.Icons.SAVE_ALT,
                                on_click=handle_backup,
                                expand=True,
                                style=_SMALL_BUTTON_STYLE,
                            ),
                            ft.OutlinedButton(
                                "Restore",
                                icon=ft.Icons.RESTORE,
                                on_click=confirm_and_restore,
                                expand=True,
                                style=_SMALL_BUTTON_STYLE,
                            ),
                        ],
                        spacing=8,
                    ),
                    backup_status,

                    ft.Divider(),

                    ft.Text("Preferences", weight=ft.FontWeight.BOLD, size=14),
                    ft.Row(
                        [
                            ft.Text("Flag debts as overdue after", size=13, expand=True),
                            overdue_days_dropdown,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),

                    ft.Divider(),

                    ft.Text("About", weight=ft.FontWeight.BOLD, size=14),
                    ft.Row(
                        [
                            ft.Text(f"Version {APP_VERSION}", size=12, color=ft.Colors.GREY, expand=True),
                            ft.TextButton(
                                "Check for updates",
                                icon=ft.Icons.OPEN_IN_NEW,
                                on_click=handle_check_updates,
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ],
                tight=True,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                height=670,
            ),
        ),
        actions=[
            ft.FilledButton("Done", on_click=close_dialog),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    refresh_list()
    page.show_dialog(dialog)
    dialog_mounted["value"] = True
    refresh_list()


async def maybe_auto_backup_on_update(page: ft.Page):
    """
    Called once at app startup (see main.py). If the app's version has
    changed since the last recorded launch (i.e. an update just
    happened, or this is the very first launch ever), silently creates
    a backup to Downloads/SpendBook/ before the person does anything
    else -- an update is exactly the moment data is most at risk if
    something in the new version has a bug, so this is the cheapest
    insurance against that.

    Deliberately backup-only, never auto-restore: silently restoring an
    old backup over current data on every update would risk overwriting
    real, newer data with stale data -- a much worse failure mode than
    "no automatic backup happened." Restore stays a manual, deliberate
    action in Settings.

    Fails silently (no error shown to the user) if anything goes wrong
    -- this runs unprompted in the background, and interrupting app
    startup with an error dialog for a background convenience feature
    would be worse than just skipping it for this one launch.
    """
    from database import get_setting  # local import: avoids a circular
    # import at module load time, since database.py doesn't need to
    # know about this Settings-specific feature.
    from version import APP_VERSION
    import database as db

    try:
        is_update_or_first_launch = db.check_and_record_version(APP_VERSION)
        if not is_update_or_first_launch:
            return

        # Nothing to back up yet on a genuinely fresh install with no
        # data -- skip rather than create a pointless empty backup file.
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
        # See docstring: intentionally silent. A background auto-backup
        # failing shouldn't interrupt the person opening the app.
        pass