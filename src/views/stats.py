import flet as ft


class StatsView(ft.Column):

    def __init__(self):
        super().__init__()

        self.controls = [

            ft.Text(
                "Statistics",
                size=30,
                weight=ft.FontWeight.BOLD
            ),

            ft.Text("Coming soon...")
        ]