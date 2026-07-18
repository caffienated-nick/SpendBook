import flet as ft

from database import initialize_database, get_setting, DatabaseError
from theme import apply_theme

from views.transactions import TransactionsView
from views.debts import DebtsView
from views.stats import StatsView
from views.add_transaction import open_add_transaction_dialog
from views.add_debt import open_add_debt_dialog
from views.settings import open_settings_dialog
from views.pin_lock import build_pin_lock_view


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

    def build_app():
        """Builds the real app UI. Called immediately if PIN lock is off,
        or after a successful PIN entry if it's on."""

        transactions_view = TransactionsView(page)
        debts_view = DebtsView(page)
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

        # Top app bar with a settings icon on the right: manage labels,
        # export data, and toggle the PIN lock.
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

        page.floating_action_button = ft.FloatingActionButton(
            icon=ft.Icons.ADD,
            on_click=handle_fab_click,
        )

        page.controls.clear()
        page.add(
            ft.SafeArea(
                ft.Container(
                    content=body,
                    expand=True,
                )
            )
        )
        page.update()

    # If the PIN lock is enabled, show the unlock screen first and only
    # build the real app once the correct PIN is entered. Off by default,
    # so a fresh install skips straight to the app. If reading the setting
    # fails, fail *open* (skip the lock) rather than stranding the user on
    # a screen they can't get past.
    try:
        pin_enabled = get_setting("pin_enabled", "false") == "true"
        pin_code = get_setting("pin_code") if pin_enabled else None
    except DatabaseError:
        pin_enabled, pin_code = False, None

    if pin_enabled and pin_code:
        def on_unlocked():
            build_app()

        page.appbar = None
        page.navigation_bar = None
        page.floating_action_button = None
        page.add(build_pin_lock_view(page, on_unlocked=on_unlocked))
    else:
        build_app()


ft.run(main)
