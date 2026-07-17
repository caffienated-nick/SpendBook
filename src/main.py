import flet as ft

from database import initialize_database
from theme import apply_theme

from views.transactions import TransactionsView
from views.debts import DebtsView
from views.stats import StatsView
from views.add_transaction import open_add_transaction_dialog
from views.add_debt import open_add_debt_dialog
from views.settings import open_settings_dialog


def main(page: ft.Page):

    initialize_database()

    apply_theme(page)

    page.title = "SpendBook"

    transactions_view = TransactionsView()
    debts_view = DebtsView()
    stats_view = StatsView()

    pages = [transactions_view, debts_view, stats_view]

    body = ft.Container(
        expand=True,
        content=pages[0],
    )

    # The FAB's behavior depends on which tab is currently open: on the
    # Transactions tab it adds a transaction, on the Dues tab it adds a
    # debt/due entry. We track the current tab index for this.
    current_tab = {"index": 0}

    def change_tab(e):
        current_tab["index"] = e.control.selected_index
        body.content = pages[current_tab["index"]]
        page.update()

    page.navigation_bar = ft.NavigationBar(
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.RECEIPT_LONG,
                label="Transactions",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.HANDSHAKE_OUTLINED,
                label="Dues",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.INSIGHTS,
                label="Stats",
            ),
        ],
        on_change=change_tab,
    )

    # Top app bar with a settings icon on the right, opening the label
    # manager. Labels are no longer pre-seeded, so this is how you add them.
    def handle_settings_click(e):
        open_settings_dialog(page, on_labels_changed=transactions_view.refresh)

    page.appbar = ft.AppBar(
        title=ft.Text("SpendBook"),
        center_title=False,
        actions=[
            ft.IconButton(
                icon=ft.Icons.SETTINGS_OUTLINED,
                tooltip="Manage labels",
                on_click=handle_settings_click,
            ),
        ],
    )

    def handle_fab_click(e):
        if current_tab["index"] == 1:
            open_add_debt_dialog(page, on_saved=debts_view.refresh)
        else:
            open_add_transaction_dialog(page, on_saved=transactions_view.refresh)

    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        on_click=handle_fab_click,
    )

    page.add(
        ft.SafeArea(
            ft.Container(
                content=body,
                expand=True,
            )
        )
    )


ft.run(main)