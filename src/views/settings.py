import flet as ft

from database import (
    get_labels, add_label, delete_label,
    build_transactions_csv, build_debts_csv,
    create_backup_file, restore_from_backup_file, BACKUP_FILENAME,
    DatabaseError,
)
from views.ui_helpers import show_error


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


def open_settings_dialog(page: ft.Page, on_labels_changed):
    """
    Opens the Settings dialog: manage labels and export data to CSV via
    the device's share sheet. `on_labels_changed` is called after every
    label change so the caller can refresh anything showing labels.
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
            on_labels_changed()

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
        on_labels_changed()
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

        destination = f"{downloads_dir}/{BACKUP_FILENAME}"
        try:
            create_backup_file(destination)
            backup_status.color = ft.Colors.GREEN_600
            backup_status.value = f"Backed up to Downloads/{BACKUP_FILENAME}"
        except DatabaseError as db_err:
            backup_status.color = ft.Colors.RED_400
            backup_status.value = f"Backup failed: {db_err}"
        page.update()

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
                f"labels) with what's in Downloads/{BACKUP_FILENAME}. "
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

        source = f"{downloads_dir}/{BACKUP_FILENAME}"
        try:
            restore_from_backup_file(source)
            backup_status.color = ft.Colors.GREEN_600
            backup_status.value = "Restored. Reopen the app to see the restored data."
        except DatabaseError as db_err:
            backup_status.color = ft.Colors.RED_400
            backup_status.value = f"Restore failed: {db_err}"
        page.update()
        # Refresh whatever's currently showing labels/transactions so
        # anything already on screen reflects the restored data without
        # forcing an app restart, where possible.
        refresh_list()
        on_labels_changed()

    # -----------------------------------------------------------------
    # Dialog assembly
    # -----------------------------------------------------------------

    def close_dialog(e=None):
        page.pop_dialog()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Settings"),
        content=ft.Container(
            width=280,
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
                        width=280,
                    ),
                    label_error_text,

                    ft.Divider(),

                    ft.Text("Export", weight=ft.FontWeight.BOLD, size=14),
                    ft.Text("Shares a CSV file via your device's share sheet.", size=11, color=ft.Colors.GREY),
                    ft.Row(
                        [
                            ft.OutlinedButton("Transactions", on_click=handle_export_transactions, expand=True),
                            ft.OutlinedButton("Debts/Dues", on_click=handle_export_debts, expand=True),
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
                            ft.FilledButton("Backup now", icon=ft.Icons.SAVE_ALT, on_click=handle_backup, expand=True),
                            ft.OutlinedButton("Restore", icon=ft.Icons.RESTORE, on_click=confirm_and_restore, expand=True),
                        ],
                        spacing=8,
                    ),
                    backup_status,
                ],
                tight=True,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                height=560,
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