import flet as ft
from datetime import datetime

from database import get_labels, add_transaction, update_transaction, DatabaseError
from views.ui_helpers import show_error


def open_add_transaction_dialog(page: ft.Page, on_saved, existing=None):
    """Build and open the 'add/edit transaction' dialog.

    on_saved: a callback with no args, invoked after a successful save so
    the caller (main.py) can refresh whatever view needs updating.
    existing: if provided (a transaction row from get_transactions()), the
    dialog opens pre-filled and updates that row instead of inserting a
    new one. This keeps add and edit as one code path instead of two
    near-identical dialogs to maintain.
    """

    try:
        labels = get_labels()
    except DatabaseError as e:
        show_error(page, f"Couldn't load labels: {e}")
        labels = []
    is_edit = existing is not None

    amount_field = ft.TextField(
        label="Amount",
        prefix="₹",
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
        value=str(existing["amount"]) if is_edit else None,
    )

    note_field = ft.TextField(
        label="Note (optional)",
        value=existing["note"] if is_edit else None,
    )

    type_toggle = ft.SegmentedButton(
        selected=[existing["type"]] if is_edit else ["income"],
        allow_multiple_selection=False,
        segments=[
            ft.Segment(value="expense", label=ft.Text("Expense")),
            ft.Segment(value="income", label=ft.Text("Income")),
        ],
    )

    # existing rows carry label_name/label_emoji (joined), not label_id --
    # so find the matching label's id from the current label list.
    existing_label_id = None
    if is_edit and existing["label_name"]:
        match = next((l for l in labels if l["name"] == existing["label_name"]), None)
        existing_label_id = str(match["id"]) if match else None

    label_dropdown = ft.Dropdown(
        label="Label" if labels else "Label (add some in Settings first)",
        options=[
            ft.dropdown.Option(key=str(l["id"]), text=f"{l['emoji']} {l['name']}")
            for l in labels
        ],
        value=existing_label_id if is_edit else (str(labels[0]["id"]) if labels else None),
        disabled=not labels,
    )

    error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

    def close_dialog(e=None):
        page.pop_dialog()

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

        try:
            if is_edit:
                update_transaction(
                    transaction_id=existing["id"],
                    amount=amount,
                    type_=type_,
                    label_id=label_id,
                    note=note_field.value or "",
                )
            else:
                add_transaction(
                    amount=amount,
                    type_=type_,
                    label_id=label_id,
                    note=note_field.value or "",
                    created_at=datetime.now().isoformat(timespec="seconds"),
                )
        except DatabaseError as db_err:
            # Leave the dialog open with the user's input intact rather
            # than losing what they typed -- they can retry the save.
            error_text.value = f"Couldn't save: {db_err}"
            error_text.visible = True
            page.update()
            return

        close_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Transaction" if is_edit else "Add Transaction"),
        content=ft.Container(
            width=280,
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
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_dialog),
            ft.FilledButton("Save", on_click=save),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.show_dialog(dialog)
