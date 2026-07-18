import flet as ft

from database import get_setting


def build_pin_lock_view(page: ft.Page, on_unlocked):
    """
    Returns a full-screen PIN entry control. Calls on_unlocked() once the
    correct PIN is entered. This is intentionally simple -- a 4-8 digit
    PIN check against a value stored in app_settings, not real encryption.
    It's meant to stop a casual glance, not a determined attacker.
    """

    correct_pin = get_setting("pin_code", "")

    entered = {"value": ""}
    dots_row = ft.Row(spacing=10, alignment=ft.MainAxisAlignment.CENTER)
    error_text = ft.Text("", color=ft.Colors.RED_400, size=12)

    def render_dots():
        dots_row.controls = [
            ft.Container(
                width=14, height=14, border_radius=7,
                bgcolor=ft.Colors.GREEN_400 if i < len(entered["value"]) else ft.Colors.GREY_700,
            )
            for i in range(len(correct_pin) or 4)
        ]

    def handle_digit(digit):
        def handler(e):
            if len(entered["value"]) >= len(correct_pin or "0000"):
                return
            entered["value"] += digit
            render_dots()
            error_text.value = ""

            if len(entered["value"]) == len(correct_pin):
                if entered["value"] == correct_pin:
                    on_unlocked()
                    return
                else:
                    error_text.value = "Incorrect PIN, try again."
                    entered["value"] = ""
                    render_dots()

            page.update()
        return handler

    def handle_backspace(e):
        entered["value"] = entered["value"][:-1]
        error_text.value = ""
        render_dots()
        page.update()

    def digit_button(d):
        return ft.ElevatedButton(
            text=d,
            width=64, height=64,
            on_click=handle_digit(d),
        )

    render_dots()

    keypad_rows = [
        ft.Row([digit_button("1"), digit_button("2"), digit_button("3")], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ft.Row([digit_button("4"), digit_button("5"), digit_button("6")], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ft.Row([digit_button("7"), digit_button("8"), digit_button("9")], alignment=ft.MainAxisAlignment.CENTER, spacing=12),
        ft.Row(
            [
                ft.Container(width=64),
                digit_button("0"),
                ft.IconButton(icon=ft.Icons.BACKSPACE_OUTLINED, on_click=handle_backspace),
            ],
            alignment=ft.MainAxisAlignment.CENTER, spacing=12,
        ),
    ]

    return ft.Column(
        [
            ft.Container(height=60),
            ft.Icon(ft.Icons.LOCK_OUTLINE, size=40),
            ft.Text("Enter PIN", size=20, weight=ft.FontWeight.BOLD),
            ft.Container(height=12),
            dots_row,
            error_text,
            ft.Container(height=24),
            *keypad_rows,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=10,
        expand=True,
    )
