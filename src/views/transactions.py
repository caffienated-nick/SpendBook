import flet as ft


class TransactionsView(ft.Column):

    def __init__(self):
        super().__init__()

        self.expand = True

        self.controls = [

            ft.Text(
                "Current Balance",
                size=18,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Text(
                "₹0",
                size=42,
                weight=ft.FontWeight.BOLD,
            ),

            ft.Divider(),

            ft.Text(
                "No transactions yet."
            )
        ]