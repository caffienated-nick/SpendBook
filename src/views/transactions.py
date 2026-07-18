import flet as ft

from database import get_transactions, get_balance, delete_transaction, get_daily_closing, DatabaseError
from views.ui_helpers import run_safely, confirm_delete, show_error


class TransactionsView(ft.Column):

    def __init__(self, page: ft.Page):
        super().__init__()

        # Stored so row taps can open the edit dialog, which needs `page`
        # to call page.show_dialog(). Set via main.py at construction time.
        self.page_ref = page

        self.expand = True

        self.balance_text = ft.Text(
            "₹0",
            size=42,
            weight=ft.FontWeight.BOLD,
        )

        self.closing_text = ft.Text("", size=12, color=ft.Colors.GREY)

        # This holds the list of transaction rows. We keep a reference to it
        # so refresh() can just replace its .controls instead of rebuilding
        # the whole view.
        self.transaction_list = ft.Column(spacing=4, expand=True)

        self.controls = [

            ft.Text(
                "Current Balance",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),

            self.balance_text,
            self.closing_text,

            ft.Divider(),

            self.transaction_list,
        ]

    def did_mount(self):
        # did_mount() is a Flet lifecycle hook: it runs once this control is
        # actually attached to the page. That's the right moment to load
        # data, since self.page isn't available before that.
        self.refresh()

    def refresh(self):
        # A read failure here (e.g. DB file briefly locked or unreadable)
        # would otherwise crash the whole app on load/reload. Instead show
        # a clear error and leave the view in its last-known-good state.
        try:
            balance = get_balance()
            closing = get_daily_closing()
            rows = get_transactions()
        except DatabaseError as e:
            show_error(self.page_ref, f"Couldn't load transactions: {e}")
            return

        self.balance_text.value = f"₹{balance:,.2f}"
        self.closing_text.value = (
            f"Today: +₹{closing['income']:,.0f} / -₹{closing['expense']:,.0f}  "
            f"(net {'+' if closing['net'] >= 0 else ''}₹{closing['net']:,.0f}, "
            f"{closing['count']} txns)"
        )

        if not rows:
            self.transaction_list.controls = [ft.Text("No transactions yet.")]
        else:
            self.transaction_list.controls = [
                self._build_row(row) for row in rows
            ]

        # update() re-renders just this control (and its children) instead
        # of the whole page, which is cheaper and avoids touching things
        # like the currently open tab.
        self.update()

    def _build_row(self, row):
        is_expense = row["type"] == "expense"
        sign = "-" if is_expense else "+"
        color = ft.Colors.RED_400 if is_expense else ft.Colors.GREEN_600

        label = row["label_emoji"] or "❓"
        label_name = row["label_name"] or "Uncategorized"

        def handle_delete(e, tid=row["id"], desc=f"{row['note'] or label_name} (₹{row['amount']:,.2f})"):
            def do_delete():
                run_safely(
                    self.page_ref,
                    action=lambda: delete_transaction(tid),
                    on_success=self.refresh,
                    error_prefix="Couldn't delete transaction",
                )
            confirm_delete(self.page_ref, desc, on_confirm=do_delete)

        def handle_edit(e, tx=row):
            # Local import avoids a circular import (add_transaction.py
            # imports from database, not from this file, so this is just
            # to keep the dependency direction easy to follow).
            from views.add_transaction import open_add_transaction_dialog
            open_add_transaction_dialog(self.page_ref, on_saved=self.refresh, existing=tx)

        return ft.Container(
            padding=ft.Padding(left=4, right=4, top=8, bottom=8),
            on_click=handle_edit,
            content=ft.Row(
                [
                    ft.Text(label, size=20),
                    ft.Column(
                        [
                            ft.Text(label_name, weight=ft.FontWeight.BOLD),
                            ft.Text(row["note"] or "", size=12, color=ft.Colors.GREY),
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    ft.Text(
                        f"{sign}₹{row['amount']:,.2f}",
                        color=color,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        on_click=handle_delete,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        )
