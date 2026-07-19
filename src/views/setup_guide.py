import flet as ft

from database import get_setting, set_setting, get_labels, DatabaseError


SETUP_GUIDE_SEEN_KEY = "setup_guide_seen"


def maybe_show_setup_guide(page: ft.Page, on_finished):
    """
    Shows a short first-run welcome dialog exactly once -- tracked via a
    row in app_settings, so it survives app restarts but never nags again
    after the first dismissal. Safe to call on every launch; it's a no-op
    once the flag is set.
    """
    try:
        already_seen = get_setting(SETUP_GUIDE_SEEN_KEY, "false") == "true"
    except DatabaseError:
        # If we can't even read the flag, don't block the user with a
        # guide they can't dismiss cleanly -- just skip it silently.
        return

    if already_seen:
        return

    def mark_seen_and_close(e=None):
        try:
            set_setting(SETUP_GUIDE_SEEN_KEY, "true")
        except DatabaseError:
            pass  # not critical enough to interrupt the user over
        page.pop_dialog()
        on_finished()

    def open_settings_now(e):
        mark_seen_and_close()
        from views.settings import open_settings_dialog
        open_settings_dialog(page, on_labels_changed=on_finished)

    has_labels = False
    try:
        has_labels = len(get_labels()) > 0
    except DatabaseError:
        pass

    steps = [
        ft.Row(
            [ft.Icon(ft.Icons.LABEL_OUTLINE, size=18), ft.Text(
                "Add a few labels (Food, Sales, Rent...) from Settings -- "
                "none are pre-loaded, so transactions need at least one "
                "label to categorize against.",
                size=13, expand=True,
            )],
            spacing=8,
        ),
        ft.Row(
            [ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=18), ft.Text(
                "Tap the + button to add income or expense entries. "
                "Tap any entry afterward to edit it.",
                size=13, expand=True,
            )],
            spacing=8,
        ),
        ft.Row(
            [ft.Icon(ft.Icons.HANDSHAKE_OUTLINED, size=18), ft.Text(
                "Use the Dues tab to track customer credit (udhaar) and "
                "money owed to suppliers, separate from daily transactions.",
                size=13, expand=True,
            )],
            spacing=8,
        ),
        ft.Row(
            [ft.Icon(ft.Icons.INSIGHTS, size=18), ft.Text(
                "The Stats tab fills in once you have a few transactions "
                "logged -- income/expense trends and spending by label.",
                size=13, expand=True,
            )],
            spacing=8,
        ),
    ]

    actions = [ft.TextButton("Skip", on_click=mark_seen_and_close)]
    if not has_labels:
        actions.append(ft.FilledButton("Add labels now", on_click=open_settings_now))
    else:
        actions.append(ft.FilledButton("Got it", on_click=mark_seen_and_close))

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Welcome to SpendBook"),
        content=ft.Container(
            width=280,
            content=ft.Column(steps, spacing=14, tight=True),
        ),
        actions=actions,
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.show_dialog(dialog)
