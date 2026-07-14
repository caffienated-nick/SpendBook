import flet as ft

from database import get_debts, get_debt_totals, settle_debt, delete_debt


class DebtsView(ft.Column):

    def __init__(self):
        super().__init__()

        self.expand = True

        self.owed_to_us_text = ft.Text("₹0", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600)
        self.we_owe_text = ft.Text("₹0", size=22, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)

        self.debt_list = ft.Column(spacing=4, expand=True)

        self.controls = [
            ft.Text("Debts & Dues", size=24, weight=ft.FontWeight.BOLD),

            ft.Row(
                [
                    ft.Column(
                        [ft.Text("They owe us", size=12, color=ft.Colors.GREY), self.owed_to_us_text],
                        spacing=0,
                        expand=True,
                    ),
                    ft.Column(
                        [ft.Text("We owe them", size=12, color=ft.Colors.GREY), self.we_owe_text],
                        spacing=0,
                        expand=True,
                    ),
                ],
            ),

            ft.Divider(),

            self.debt_list,
        ]

    def did_mount(self):
        self.refresh()

    def refresh(self):
        owed_to_us, we_owe = get_debt_totals()
        self.owed_to_us_text.value = f"₹{owed_to_us:,.2f}"
        self.we_owe_text.value = f"₹{we_owe:,.2f}"

        rows = get_debts()
        if not rows:
            self.debt_list.controls = [ft.Text("No outstanding debts or dues.")]
        else:
            self.debt_list.controls = [self._build_row(row) for row in rows]

        self.update()

    def _build_row(self, row):
        is_debt = row["type"] == "debt"  # they owe us
        color = ft.Colors.GREEN_600 if is_debt else ft.Colors.RED_400
        sign = "+" if is_debt else "-"

        def handle_settle(e, did=row["id"]):
            settle_debt(did)
            self.refresh()

        def handle_delete(e, did=row["id"]):
            delete_debt(did)
            self.refresh()

        return ft.Container(
            padding=ft.Padding(left=4, right=4, top=8, bottom=8),
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(row["person_name"], weight=ft.FontWeight.BOLD),
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
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                        icon_size=18,
                        tooltip="Mark as settled",
                        on_click=handle_settle,
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
