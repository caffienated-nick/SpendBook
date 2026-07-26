import flet as ft

from database import initialize_database, DatabaseError
from theme import apply_theme

from views.transactions import TransactionsView
from views.debts import DebtsView
from views.stats import StatsView
from views.add_transaction import open_add_transaction_dialog
from views.add_debt import open_add_debt_dialog
from views.settings import open_settings_dialog
from views.setup_guide import maybe_show_setup_guide


def main(page: ft.Page):

    apply_theme(page)
    page.title = "SpendBook"

    # If the database can't even be opened/initialized (corrupt file,
    # permissions issue, disk full), show a real message instead of a
    # blank screen or an uncaught traceback the user can't do anything
    # with.
    try:
        initialize_database()
    except DatabaseError as e:
        page.add(
            ft.Column(
                [
                    ft.Icon(ft.Icons.ERROR_OUTLINE, size=40, color=ft.Colors.RED_400),
                    ft.Text("SpendBook couldn't start", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(str(e), size=12, color=ft.Colors.GREY, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            )
        )
        return

    transactions_view = TransactionsView(page)
    debts_view = DebtsView(page)
    stats_view = StatsView(page)

    pages = [transactions_view, debts_view, stats_view]

    # A plain container holding the active tab's view. Each view
    # (TransactionsView, DebtsView, StatsView) is itself a Column with
    # scroll=ADAPTIVE/AUTO already set -- that's what makes each tab
    # scrollable when its content is taller than the screen (e.g. after
    # rotating to landscape, where the available height shrinks a lot).
    #
    # Important: this Container must NOT set its own `expand=True` +
    # unbounded height combination on top of an already-scrollable
    # Column child -- doing that previously gave the inner Column
    # effectively unbounded height instead of the real viewport height,
    # so it never realized it needed to scroll and content below the
    # fold was simply unreachable. `expand=True` here is fine because
    # SafeArea (below) provides the actual bounding height.
    body = ft.Container(
        content=pages[0],
        expand=True,
    )

    # The FAB's behavior depends on which tab is currently open: on the
    # Transactions tab it adds a transaction, on the Dues tab it adds a
    # debt/due entry. On the Stats tab there's nothing to "add", so the
    # FAB is hidden there entirely.
    current_tab = {"index": 0}

    def change_tab(e):
        current_tab["index"] = e.control.selected_index
        body.content = pages[current_tab["index"]]
        page.floating_action_button = None if current_tab["index"] == 2 else fab
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

    # Top app bar with a settings icon on the right: manage labels and
    # export data.
    def handle_settings_click(e):
        open_settings_dialog(page, on_labels_changed=transactions_view.refresh)

    page.appbar = ft.AppBar(
        title=ft.Text("SpendBook"),
        center_title=False,
        actions=[
            ft.IconButton(
                icon=ft.Icons.SETTINGS_OUTLINED,
                tooltip="Settings",
                on_click=handle_settings_click,
            ),
        ],
    )

    def handle_fab_click(e):
        if current_tab["index"] == 1:
            open_add_debt_dialog(page, on_saved=debts_view.refresh)
        else:
            open_add_transaction_dialog(page, on_saved=transactions_view.refresh)

    fab = ft.FloatingActionButton(
        icon=ft.Icons.ADD,
        on_click=handle_fab_click,
    )
    page.floating_action_button = fab

    page.add(
        ft.SafeArea(
            content=body,
            expand=True,
        )
    )
    page.update()

    # Shows a one-time first-run guide (add your first label, etc.) if
    # this looks like a fresh install. No-op on every run after that.
    maybe_show_setup_guide(page, on_finished=transactions_view.refresh)


ft.run(main)