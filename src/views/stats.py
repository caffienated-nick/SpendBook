import flet as ft

from database import get_summary_totals, get_spending_by_label, get_daily_totals, DatabaseError


class StatsView(ft.Column):
    """
    Stats screen: a 30-day income/expense summary, a spend-by-label
    breakdown, and a 14-day daily trend.

    Bar widths are computed from the real screen width (page.width) at
    render time rather than a hardcoded pixel value -- the previous
    version used a fixed 260px bar width, which left a visible empty gap
    on narrower screens or larger system font scales (anything that
    changes the actual available width without changing the hardcoded
    number). This also avoids nesting flex-based `expand` inside a Stack,
    a layout combination not otherwise used/proven elsewhere in this app.
    """

    def __init__(self, page: ft.Page):
        super().__init__()

        self.page_ref = page
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO

        self.income_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600)
        self.expense_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.net_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD)

        self.label_breakdown = ft.Column(spacing=10)
        self.daily_trend = ft.Column(spacing=10)

        self.controls = [
            ft.Text("Statistics", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Last 30 days", size=12, color=ft.Colors.GREY),

            ft.Row(
                [
                    ft.Column(
                        [ft.Text("Income", size=12, color=ft.Colors.GREY), self.income_text],
                        spacing=0, expand=True,
                    ),
                    ft.Column(
                        [ft.Text("Expense", size=12, color=ft.Colors.GREY), self.expense_text],
                        spacing=0, expand=True,
                    ),
                    ft.Column(
                        [ft.Text("Net", size=12, color=ft.Colors.GREY), self.net_text],
                        spacing=0, expand=True,
                    ),
                ],
            ),

            ft.Divider(),

            ft.Text("Spending by label", size=16, weight=ft.FontWeight.BOLD),
            self.label_breakdown,

            ft.Divider(),

            ft.Row(
                [
                    ft.Text("Last 14 days", size=16, weight=ft.FontWeight.BOLD, expand=True),
                    ft.Row(
                        [
                            ft.Container(width=10, height=10, border_radius=2, bgcolor=ft.Colors.RED_300),
                            ft.Text("expense", size=11, color=ft.Colors.GREY),
                            ft.Container(width=10, height=10, border_radius=2, bgcolor=ft.Colors.GREEN_600),
                            ft.Text("income", size=11, color=ft.Colors.GREY),
                        ],
                        spacing=4,
                    ),
                ],
            ),
            self.daily_trend,
        ]

    def did_mount(self):
        self.refresh()

    def _bar_width(self) -> float:
        """
        The real available width for a bar: page width minus the app's
        16px horizontal padding (set in theme.py) on each side, minus
        space for the day label / left margin. Falls back to a
        reasonable default if page.width isn't available yet (can be
        None very early in the render lifecycle).
        """
        total = self.page_ref.width or 390
        return max(total - 32 - 56, 80)  # 32 = page padding, 56 = label column + spacing

    def refresh(self):
        try:
            income, expense = get_summary_totals(days=30)
        except DatabaseError as e:
            self.controls = [ft.Text(f"Couldn't load stats: {e}", color=ft.Colors.RED_400)]
            self.update()
            return

        net = income - expense

        self.income_text.value = f"₹{income:,.0f}"
        self.expense_text.value = f"₹{expense:,.0f}"
        self.net_text.value = f"₹{net:,.0f}"
        self.net_text.color = ft.Colors.GREEN_600 if net >= 0 else ft.Colors.RED_400

        self._render_label_breakdown()
        self._render_daily_trend()

        self.update()

    def _render_label_breakdown(self):
        try:
            rows = get_spending_by_label(days=30)
        except DatabaseError as e:
            self.label_breakdown.controls = [ft.Text(f"Couldn't load: {e}", color=ft.Colors.RED_400)]
            return

        if not rows:
            self.label_breakdown.controls = [ft.Text("No expenses yet in the last 30 days.", color=ft.Colors.GREY)]
            return

        # Full bar width here (label breakdown bars aren't preceded by a
        # day-label column like the daily trend is).
        full_width = max((self.page_ref.width or 390) - 32, 100)

        max_total = max(r["total"] for r in rows) or 1
        controls = []
        for r in rows:
            fraction = r["total"] / max_total
            controls.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Text(f"{r['label_emoji']} {r['label_name']}", size=13),
                                ft.Text(f"₹{r['total']:,.0f}", size=13, weight=ft.FontWeight.BOLD),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Stack(
                            [
                                ft.Container(height=8, border_radius=4, bgcolor=ft.Colors.GREY_800, width=full_width),
                                ft.Container(
                                    height=8, border_radius=4, bgcolor=ft.Colors.ORANGE_400,
                                    width=max(fraction * full_width, 8),
                                ),
                            ],
                        ),
                    ],
                    spacing=4,
                )
            )
        self.label_breakdown.controls = controls

    def _render_daily_trend(self):
        try:
            days = get_daily_totals(days=14)
        except DatabaseError as e:
            self.daily_trend.controls = [ft.Text(f"Couldn't load: {e}", color=ft.Colors.RED_400)]
            return

        max_val = max((d["income"] for d in days), default=0)
        max_val = max(max_val, max((d["expense"] for d in days), default=0), 1)

        bar_width = self._bar_width()
        bar_height = 18

        controls = []
        for d in days:
            income_frac = d["income"] / max_val
            expense_frac = d["expense"] / max_val
            label = d["day"][5:]  # MM-DD, short enough for a phone row

            # Overlapping bar: expense drawn as a full-height background
            # bar, income drawn as a shorter bar on top of it (both
            # anchored to the same scale) -- so a glance shows whether
            # that day's income covered its expense, instead of two
            # separate thin bars that were hard to compare side by side.
            controls.append(
                ft.Row(
                    [
                        ft.Text(label, size=11, color=ft.Colors.GREY, width=44),
                        ft.Stack(
                            [
                                ft.Container(height=bar_height, border_radius=4, bgcolor=ft.Colors.GREY_900, width=bar_width),
                                ft.Container(
                                    height=bar_height, border_radius=4, bgcolor=ft.Colors.RED_300,
                                    width=max(expense_frac * bar_width, 4),
                                ),
                                ft.Container(
                                    top=bar_height * 0.22,
                                    content=ft.Container(
                                        height=bar_height * 0.56, border_radius=3, bgcolor=ft.Colors.GREEN_600,
                                        width=max(income_frac * bar_width, 4),
                                    ),
                                ),
                            ],
                        ),
                    ],
                    spacing=6,
                )
            )
        self.daily_trend.controls = controls