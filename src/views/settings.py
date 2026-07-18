import flet as ft

from database import (
    get_labels, add_label, delete_label,
    get_setting, set_setting,
    build_transactions_csv, build_debts_csv,
)


def open_settings_dialog(page: ft.Page, on_labels_changed):
    """
    Opens the Settings dialog: manage labels, export data to CSV, and
    (optionally) turn on a PIN lock. `on_labels_changed` is called after
    every label change so the caller can refresh anything showing labels.
    """

    # -----------------------------------------------------------------
    # Labels section
    # -----------------------------------------------------------------

    name_field = ft.TextField(label="Label name", autofocus=True, expand=True)
    emoji_field = ft.TextField(label="Emoji (optional)", width=90)
    label_error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

    label_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=140)

    dialog_mounted = {"value": False}

    def refresh_list():
        labels = get_labels()
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
            delete_label(lid)
            refresh_list()
            on_labels_changed()

        return ft.Row(
            [
                ft.Text(f"{label['emoji'] or ''} {label['name']}", expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=18,
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

        add_label(name=name, emoji=(emoji_field.value or "").strip())
        name_field.value = ""
        emoji_field.value = ""
        label_error_text.visible = False
        refresh_list()
        on_labels_changed()
        page.update()

    # -----------------------------------------------------------------
    # Export section
    # -----------------------------------------------------------------

    export_status = ft.Text("", size=12, color=ft.Colors.GREEN_600)

    file_picker = ft.FilePicker()
    page.overlay.append(file_picker)
    page.update()

    # Which CSV to write is decided by which button was tapped; stashed
    # here so the picker's completion (if we needed a callback) or the
    # direct await below can use it.
    async def handle_export_transactions(e):
        content = build_transactions_csv()
        result = await file_picker.save_file(
            dialog_title="Save transactions CSV",
            file_name="spendbook_transactions.csv",
            src_bytes=content.encode("utf-8"),
        )
        export_status.value = "Transactions exported." if result else ""
        page.update()

    async def handle_export_debts(e):
        content = build_debts_csv()
        result = await file_picker.save_file(
            dialog_title="Save debts/dues CSV",
            file_name="spendbook_debts.csv",
            src_bytes=content.encode("utf-8"),
        )
        export_status.value = "Debts/dues exported." if result else ""
        page.update()

    # -----------------------------------------------------------------
    # PIN lock section (optional, off by default)
    # -----------------------------------------------------------------

    pin_enabled = get_setting("pin_enabled", "false") == "true"

    pin_error_text = ft.Text("", size=12, color=ft.Colors.RED_400, visible=False)
    new_pin_field = ft.TextField(
        label="Set a 4-digit PIN",
        password=True,
        keyboard_type=ft.KeyboardType.NUMBER,
        visible=pin_enabled and not get_setting("pin_code"),
        max_length=4,
    )

    def handle_pin_toggle(e):
        enabling = pin_switch.value
        if enabling:
            if not get_setting("pin_code"):
                new_pin_field.visible = True
                page.update()
                return
            set_setting("pin_enabled", "true")
        else:
            set_setting("pin_enabled", "false")
        page.update()

    def handle_save_pin(e):
        pin = (new_pin_field.value or "").strip()
        if len(pin) != 4 or not pin.isdigit():
            pin_error_text.value = "PIN must be exactly 4 digits."
            pin_error_text.visible = True
            page.update()
            return
        set_setting("pin_code", pin)
        set_setting("pin_enabled", "true")
        pin_error_text.visible = False
        new_pin_field.visible = False
        page.update()

    pin_switch = ft.Switch(value=pin_enabled, on_change=handle_pin_toggle)

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
                    ft.TextButton("Add label", on_click=handle_add_label),
                    label_error_text,

                    ft.Divider(),

                    ft.Text("Export", weight=ft.FontWeight.BOLD, size=14),
                    ft.Row(
                        [
                            ft.OutlinedButton("Transactions", on_click=handle_export_transactions, expand=True),
                            ft.OutlinedButton("Debts/Dues", on_click=handle_export_debts, expand=True),
                        ],
                        spacing=8,
                    ),
                    export_status,

                    ft.Divider(),

                    ft.Text("App lock", weight=ft.FontWeight.BOLD, size=14),
                    ft.Row(
                        [ft.Text("Require PIN to open app", expand=True), pin_switch],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    new_pin_field,
                    ft.TextButton("Save PIN", on_click=handle_save_pin),
                    pin_error_text,
                ],
                tight=True,
                spacing=10,
                scroll=ft.ScrollMode.AUTO,
                height=460,
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