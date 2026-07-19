import flet as ft

from database import (
    get_labels, add_label, delete_label,
    build_transactions_csv, build_debts_csv,
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
    emoji_field = ft.TextField(label="Emoji (optional)", width=90)
    label_error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

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
                ft.Text(f"{label['emoji'] or ''} {label['name']}", expand=True, size=13),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=16,
                    on_click=handle_delete,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def handle_add_label(e):
        name = (name_field.value or "").strip()
        if not name:
            label_error_text.value = "Enter a label name."
            label_error_text.visible = True
            page.update()
            return

        try:
            add_label(name=name, emoji=(emoji_field.value or "").strip())
        except DatabaseError as db_err:
            label_error_text.value = f"Couldn't save: {db_err}"
            label_error_text.visible = True
            page.update()
            return

        name_field.value = ""
        emoji_field.value = ""
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
                    ft.Row([name_field, emoji_field], spacing=8),
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
                ],
                tight=True,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                height=380,
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