import flet as ft

from database import get_labels, add_label, delete_label


def open_settings_dialog(page: ft.Page, on_labels_changed):
    """
    Opens a dialog for managing labels: add a new one, or delete an
    existing one. `on_labels_changed` is called after every change so the
    caller can refresh anything that shows a label list/dropdown.
    """

    name_field = ft.TextField(label="Label name", autofocus=True)
    emoji_field = ft.TextField(label="Emoji (optional)", width=100)
    error_text = ft.Text(value="", color=ft.Colors.RED_400, visible=False)

    label_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO, height=220)

    def refresh_list():
        labels = get_labels()
        if not labels:
            label_list.controls = [ft.Text("No labels yet. Add one below.", color=ft.Colors.GREY)]
        else:
            label_list.controls = [_build_label_row(l) for l in labels]
        # Only call update() if this control is already on the page --
        # the very first call happens before show_dialog(), when it isn't yet.
        if label_list.page:
            label_list.update()

    def _build_label_row(label):
        def handle_delete(e, lid=label["id"]):
            delete_label(lid)
            refresh_list()
            on_labels_changed()

        return ft.Row(
            [
                ft.Text(f"{label['emoji'] or ''} {label['name']}", expand=True),
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    icon_size=18,
                    on_click=handle_delete,
                ),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

    def handle_add(e):
        name = (name_field.value or "").strip()
        if not name:
            error_text.value = "Enter a label name."
            error_text.visible = True
            page.update()
            return

        add_label(name=name, emoji=(emoji_field.value or "").strip())
        name_field.value = ""
        emoji_field.value = ""
        error_text.visible = False
        refresh_list()
        on_labels_changed()
        page.update()

    def close_dialog(e=None):
        page.pop_dialog()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Manage Labels"),
        content=ft.Column(
            [
                label_list,
                ft.Divider(),
                ft.Row([name_field, emoji_field], spacing=8),
                error_text,
            ],
            tight=True,
            spacing=12,
            width=320,
        ),
        actions=[
            ft.TextButton("Add", on_click=handle_add),
            ft.FilledButton("Done", on_click=close_dialog),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    refresh_list()
    page.show_dialog(dialog)