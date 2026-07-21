import flet as ft

from database import (
    get_summary_totals, get_spending_by_label, get_daily_totals,
    get_transaction_stats, get_period_comparison,
    get_stats_window_days, set_stats_window_days,
    DatabaseError,
)


WINDOW_OPTIONS = [7, 30, 90]


class StatsView(ft.Column):
    """
    Stats screen: income/expense summary (with a period-over-period
    comparison), transaction-level stats (count, averages, largest
    single transactions), a spend-by-label breakdown, and a 14-day daily
    trend chart.

    The summary/label-breakdown window (7/30/90 days) is user-selectable
    and persisted via database.py's app_settings, rather than a fixed
    30 days -- different shops want different lookback periods.

    The daily trend is a vertical grouped bar chart (income/expense bars
    side by side per day) inside a horizontally scrollable row, so it's
    never cut off regardless of screen width. An earlier version tried
    overlapping the two bars using a Stack with pixel widths computed
    from page.width; that didn't render correctly on a real device, so
    this uses fixed-size Containers in a bottom-aligned Column instead --
    a simpler, more standard Flet layout. (This chart's own window
    stays fixed at 14 days -- a daily bar chart gets unreadably dense
    much past that on a phone screen.)
    """

    def __init__(self, page: ft.Page):
        super().__init__()

        self.page_ref = page
        self.expand = True
        self.scroll = ft.ScrollMode.AUTO

        self.window_days = get_stats_window_days()

        self.income_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600)
        self.expense_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.net_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD)
        self.comparison_text = ft.Text("", size=12)

        self.window_dropdown = ft.Dropdown(
            value=str(self.window_days),
            options=[ft.dropdown.Option(key=str(d), text=f"{d} days") for d in WINDOW_OPTIONS],
            dense=True,
            width=110,
            on_select=self._handle_window_change,
        )

        self.count_text = ft.Text("0", size=16, weight=ft.FontWeight.BOLD)
        self.avg_income_text = ft.Text("₹0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600)
        self.avg_expense_text = ft.Text("₹0", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.max_income_text = ft.Text("₹0", size=13, color=ft.Colors.GREEN_600)
        self.max_expense_text = ft.Text("₹0", size=13, color=ft.Colors.RED_400)

        self.label_breakdown = ft.Column(spacing=10)
        self.daily_trend = ft.Column(spacing=10)

        self.controls = [
            ft.Row(
                [
                    ft.Text("Statistics", size=24, weight=ft.FontWeight.BOLD, expand=True),
                    self.window_dropdown,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),

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
            self.comparison_text,

            ft.Divider(),

            ft.Text("Activity", size=16, weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    ft.Column(
                        [ft.Text("Transactions", size=12, color=ft.Colors.GREY), self.count_text],
                        spacing=0, expand=True,
                    ),
                    ft.Column(
                        [ft.Text("Avg. income", size=12, color=ft.Colors.GREY), self.avg_income_text],
                        spacing=0, expand=True,
                    ),
                    ft.Column(
                        [ft.Text("Avg. expense", size=12, color=ft.Colors.GREY), self.avg_expense_text],
                        spacing=0, expand=True,
                    ),
                ],
            ),
            ft.Row(
                [
                    ft.Column(
                        [ft.Text("Largest income", size=11, color=ft.Colors.GREY), self.max_income_text],
                        spacing=0, expand=True,
                    ),
                    ft.Column(
                        [ft.Text("Largest expense", size=11, color=ft.Colors.GREY), self.max_expense_text],
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

    def _handle_window_change(self, e):
        try:
            self.window_days = int(self.window_dropdown.value)
        except (TypeError, ValueError):
            return
        set_stats_window_days(self.window_days)
        self.refresh()

    def refresh(self):
        days = self.window_days
        try:
            income, expense = get_summary_totals(days=days)
            tx_stats = get_transaction_stats(days=days)
            current_net, previous_net, pct_change = get_period_comparison(days=days)
        except DatabaseError as e:
            self.controls = [ft.Text(f"Couldn't load stats: {e}", color=ft.Colors.RED_400)]
            self.update()
            return

        net = income - expense

        self.income_text.value = f"₹{income:,.0f}"
        self.expense_text.value = f"₹{expense:,.0f}"
        self.net_text.value = f"₹{net:,.0f}"
        self.net_text.color = ft.Colors.GREEN_600 if net >= 0 else ft.Colors.RED_400

        self._render_comparison(pct_change, previous_net, days)

        self.count_text.value = str(tx_stats["count"])
        self.avg_income_text.value = f"₹{tx_stats['avg_income']:,.0f}"
        self.avg_expense_text.value = f"₹{tx_stats['avg_expense']:,.0f}"
        self.max_income_text.value = f"₹{tx_stats['max_income']:,.0f}"
        self.max_expense_text.value = f"₹{tx_stats['max_expense']:,.0f}"

        self._render_label_breakdown(days)
        self._render_daily_trend()

        self.update()

    def _render_comparison(self, pct_change, previous_net, days):
        if pct_change is None:
            # No activity in the previous period to compare against --
            # showing a meaningless "infinite %" would be worse than
            # just omitting the comparison.
            self.comparison_text.value = ""
            return

        arrow = "▲" if pct_change >= 0 else "▼"
        color = ft.Colors.GREEN_600 if pct_change >= 0 else ft.Colors.RED_400
        self.comparison_text.value = f"{arrow} {abs(pct_change):,.0f}% vs previous {days} days"
        self.comparison_text.color = color

    def _render_label_breakdown(self, days: int):
        try:
            rows = get_spending_by_label(days=days)
        except DatabaseError as e:
            self.label_breakdown.controls = [ft.Text(f"Couldn't load: {e}", color=ft.Colors.RED_400)]
            return

        if not rows:
            self.label_breakdown.controls = [ft.Text(f"No expenses yet in the last {days} days.", color=ft.Colors.GREY)]
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
                                ft.Row(
                                    [
                                        ft.Container(width=10, height=10, border_radius=5, bgcolor=r["label_color"] or ft.Colors.GREY_500),
                                        ft.Text(r["label_name"], size=13),
                                    ],
                                    spacing=6,
                                ),
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

        # Vertical grouped bar chart: each day gets a small column with an
        # income bar and an expense bar side by side, growing up from a
        # shared baseline, height proportional to value.
        #
        # The whole chart sits in a horizontally scrollable Row so it's
        # never cut off regardless of screen width or how many days are
        # shown.
        chart_area_height = 140
        bar_max_height = 110
        bar_width = 10

        day_columns = []
        for d in days:
            income_h = max((d["income"] / max_val) * bar_max_height, 2) if d["income"] else 2
            expense_h = max((d["expense"] / max_val) * bar_max_height, 2) if d["expense"] else 2
            label = d["day"][5:]  # MM-DD, short enough for a phone chart

            day_columns.append(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Container(
                                    width=bar_width, height=income_h,
                                    border_radius=3, bgcolor=ft.Colors.GREEN_600,
                                ),
                                ft.Container(
                                    width=bar_width, height=expense_h,
                                    border_radius=3, bgcolor=ft.Colors.RED_300,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.END,
                            spacing=3,
                            height=bar_max_height,
                        ),
                        ft.Text(label, size=9, color=ft.Colors.GREY),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                    width=44,
                )
            )

        self.daily_trend.controls = [
            ft.Container(
                height=chart_area_height,
                content=ft.Row(
                    day_columns,
                    scroll=ft.ScrollMode.AUTO,
                    spacing=6,
                    vertical_alignment=ft.CrossAxisAlignment.END,
                ),
            )
        ]