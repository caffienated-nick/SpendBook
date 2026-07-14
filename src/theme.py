import flet as ft

def apply_theme(page: ft.Page):

    page.theme_mode = ft.ThemeMode.SYSTEM

    page.theme = ft.Theme(
        color_scheme_seed=ft.Colors.GREEN
    )

    page.padding = 16