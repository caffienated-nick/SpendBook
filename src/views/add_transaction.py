import flet as ft
from datetime import datetime

from database import get_labels, add_transaction


def open_add_transaction_dialog(page: ft.Page, on_saved):
    """Build and open the 'add transaction' dialog.

    on_saved: a callback with no args, invoked after a successful save so
    the caller (main.py) can refresh whatever view needs updating.
    """

    labels = get_labels()

    amount_field = ft.TextField(
        label="Amount",
        prefix_text="₹",
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
    )

    note_field = ft.TextField(label="Note (optional)")

    type_toggle = ft.SegmentedButton(
        selected={"expense"},
        allow_multiple_selection=False,
        segments=[
            ft.Segment(value="expense", label=ft.Text("Expense")),
            ft.Segment(value="income", label=ft.Text("Income")),
        ],
    )

    label_dropdown = ft.Dropdown(
        label="Label",
        options=[
            ft.dropdown.Option(key=str(l["id"]), text=f"{l['emoji']} {l['name']}")
            for l in labels
        ],
        value=str(labels[0]["id"]) if labels else None,
    )

    error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

    def close_dialog(e=None):
        page.close(dialog)

    def save(e):
        # Basic validation: amount must be present and a positive number.
        raw = amount_field.value.strip() if amount_field.value else ""
        try:
            amount = float(raw)
            if amount <= 0:
                raise ValueError
        except ValueError:
            error_text.value = "Enter a valid amount greater than 0."
            error_text.visible = True
            page.update()
            return

        type_ = next(iter(type_toggle.selected))
        label_id = int(label_dropdown.value) if label_dropdown.value else None

        add_transaction(
            amount=amount,
            type_=type_,
            label_id=label_id,
            note=note_field.value or "",
            created_at=datetime.now().isoformat(timespec="seconds"),
        )

        close_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Add Transaction"),
        content=ft.Column(
            [
                type_toggle,
                amount_field,
                label_dropdown,
                note_field,
                error_text,
            ],
            tight=True,
            spacing=12,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.FilledButton("Save", on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.open(dialog)
