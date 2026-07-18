import flet as ft

from database import DatabaseError


def show_error(page: ft.Page, message: str):
    """
    Show a short-lived error banner at the bottom of the screen. Used
    whenever a database call fails, so the app degrades to 'this one
    action didn't work, try again' instead of crashing outright.
    SnackBar is a DialogControl in this Flet version, same family as
    AlertDialog, so it uses the same show_dialog()/pop_dialog() API.
    """
    page.show_dialog(ft.SnackBar(
        content=ft.Text(message),
        bgcolor=ft.Colors.RED_900,
    ))


def run_safely(page: ft.Page, action, on_success=None, error_prefix="Something went wrong"):
    """
    Runs `action()` (a no-arg callable that touches the database) and
    catches DatabaseError so a single failed write/read shows an error
    banner instead of crashing the whole app. Any *other* exception type
    is re-raised -- we only want to swallow the specific, expected
    "the database call failed" case, not mask real bugs.
    """
    try:
        action()
    except DatabaseError as e:
        show_error(page, f"{error_prefix}: {e}")
        return
    if on_success:
        on_success()


def confirm_delete(page: ft.Page, item_description: str, on_confirm):
    """
    Opens a small confirmation dialog before a destructive delete.
    on_confirm is called with no args if the user taps Delete.
    """

    def do_delete(e):
        page.pop_dialog()
        on_confirm()

    def cancel(e):
        page.pop_dialog()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Delete this entry?"),
        content=ft.Text(f"This will permanently delete {item_description}. This can't be undone."),
        actions=[
            ft.TextButton("Cancel", on_click=cancel),
            ft.TextButton("Delete", style=ft.ButtonStyle(color=ft.Colors.RED_400), on_click=do_delete),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.show_dialog(dialog)
