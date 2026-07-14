import flet as ft

from database import get_transactions, get_balance, delete_transaction


class TransactionsView(ft.Column):

    def __init__(self):
        super().__init__()

        self.expand = True

        self.balance_text = ft.Text(
            "₹0",
            size=42,
            weight=ft.FontWeight.BOLD,
        )

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

            ft.Divider(),

            self.transaction_list,
        ]

    def did_mount(self):
        # did_mount() is a Flet lifecycle hook: it runs once this control is
        # actually attached to the page. That's the right moment to load
        # data, since self.page isn't available before that.
        self.refresh()

    def refresh(self):
        balance = get_balance()
        self.balance_text.value = f"₹{balance:,.2f}"

        rows = get_transactions()

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

        def handle_delete(e, tid=row["id"]):
            delete_transaction(tid)
            self.refresh()

        return ft.Container(
            padding=ft.padding.symmetric(vertical=8, horizontal=4),
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

