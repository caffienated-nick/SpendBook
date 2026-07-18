import flet as ft
from datetime import datetime

from database import add_debt, update_debt


def open_add_debt_dialog(page: ft.Page, on_saved, existing=None):
    """
    Dialog for recording or editing a debt/due entry.

    'debt'  = someone owes the shop money (udhaar / credit given to a customer)
    'due'   = the shop owes someone money (e.g. a supplier)

    existing: if provided (a row from get_debts()), the dialog opens
    pre-filled and updates that row instead of inserting a new one.
    """

    is_edit = existing is not None

    name_field = ft.TextField(
        label="Person / party name",
        autofocus=True,
        value=existing["person_name"] if is_edit else None,
    )
    amount_field = ft.TextField(
        label="Amount",
        prefix="₹",
        keyboard_type=ft.KeyboardType.NUMBER,
        value=str(existing["amount"]) if is_edit else None,
    )
    note_field = ft.TextField(
        label="Note (optional)",
        value=existing["note"] if is_edit else None,
    )

    type_toggle = ft.SegmentedButton(
        selected=[existing["type"]] if is_edit else ["debt"],
        allow_multiple_selection=False,
        segments=[
            ft.Segment(value="debt", label=ft.Text("They owe us")),
            ft.Segment(value="due", label=ft.Text("We owe them")),
        ],
    )

    error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

    def close_dialog(e=None):
        page.pop_dialog()

    def save(e):
        name = (name_field.value or "").strip()
        raw_amount = (amount_field.value or "").strip()

        if not name:
            error_text.value = "Enter a name."
            error_text.visible = True
            page.update()
            return

        try:
            amount = float(raw_amount)
            if amount <= 0:
                raise ValueError
        except ValueError:
            error_text.value = "Enter a valid amount greater than 0."
            error_text.visible = True
            page.update()
            return

        type_ = next(iter(type_toggle.selected))

        if is_edit:
            update_debt(
                debt_id=existing["id"],
                person_name=name,
                amount=amount,
                type_=type_,
                note=note_field.value or "",
            )
        else:
            add_debt(
                person_name=name,
                amount=amount,
                type_=type_,
                note=note_field.value or "",
                created_at=datetime.now().isoformat(timespec="seconds"),
            )

        close_dialog()
        on_saved()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Debt / Due" if is_edit else "Add Debt / Due"),
        content=ft.Container(
            width=280,
            content=ft.Column(
                [
                    type_toggle,
                    name_field,
                    amount_field,
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