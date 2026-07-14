import flet as ft

from database import initialize_database
from theme import apply_theme

from views.transactions import TransactionsView
from views.stats import StatsView
 

def main(page: ft.Page):

    initialize_database()

    apply_theme(page)

    page.title = "SpendBook"

    pages = [
        TransactionsView(),
        StatsView(),
    ]

    body = ft.Container(
        expand=True,
        content=pages[0],
    )

    def change_tab(e):

        body.content = pages[e.control.selected_index]
        page.update()

    page.navigation_bar = ft.NavigationBar(

        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.RECEIPT_LONG,
                label="Transactions",
            ),

            ft.NavigationBarDestination(
                icon=ft.Icons.INSIGHTS,
                label="Stats",
            ),
        ],

        on_change=change_tab,
    )

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
    )

    page.add(body)


ft.run(main)