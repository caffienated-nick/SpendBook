import flet as ft

from database import get_summary_totals, get_spending_by_label, get_daily_totals


class StatsView(ft.Column):
    """
    Stats screen: a 30-day income/expense summary, a spend-by-label
    breakdown (as simple proportional bars -- no chart library needed),
    and a 14-day daily trend list.
    """

    def __init__(self):
        super().__init__()

        self.expand = True
        self.scroll = ft.ScrollMode.AUTO

        self.income_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.GREEN_600)
        self.expense_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.RED_400)
        self.net_text = ft.Text("₹0", size=20, weight=ft.FontWeight.BOLD)

        self.label_breakdown = ft.Column(spacing=10)
        self.daily_trend = ft.Column(spacing=6)

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

            ft.Text("Last 14 days", size=16, weight=ft.FontWeight.BOLD),
            self.daily_trend,
        ]

    def did_mount(self):
        self.refresh()

    def refresh(self):
        income, expense = get_summary_totals(days=30)
        net = income - expense

        self.income_text.value = f"₹{income:,.0f}"
        self.expense_text.value = f"₹{expense:,.0f}"
        self.net_text.value = f"₹{net:,.0f}"
        self.net_text.color = ft.Colors.GREEN_600 if net >= 0 else ft.Colors.RED_400

        self._render_label_breakdown()
        self._render_daily_trend()

        self.update()

    def _render_label_breakdown(self):
        rows = get_spending_by_label(days=30)
        if not rows:
            self.label_breakdown.controls = [ft.Text("No expenses yet in the last 30 days.", color=ft.Colors.GREY)]
            return

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
                                ft.Container(height=8, border_radius=4, bgcolor=ft.Colors.GREY_800),
                                ft.Container(
                                    height=8,
                                    border_radius=4,
                                    bgcolor=ft.Colors.ORANGE_400,
                                    width=fraction * 260,
                                ),
                            ],
                        ),
                    ],
                    spacing=4,
                )
            )
        self.label_breakdown.controls = controls

    def _render_daily_trend(self):
        days = get_daily_totals(days=14)
        max_val = max((d["income"] for d in days), default=0)
        max_val = max(max_val, max((d["expense"] for d in days), default=0), 1)

        controls = []
        for d in days:
            income_frac = d["income"] / max_val
            expense_frac = d["expense"] / max_val
            label = d["day"][5:]  # MM-DD, short enough for a phone row
            controls.append(
                ft.Row(
                    [
                        ft.Text(label, size=11, color=ft.Colors.GREY, width=44),
                        ft.Container(
                            height=6, border_radius=3, bgcolor=ft.Colors.GREEN_600,
                            width=max(income_frac * 100, 2),
                        ),
                        ft.Container(
                            height=6, border_radius=3, bgcolor=ft.Colors.RED_400,
                            width=max(expense_frac * 100, 2),
                        ),
                    ],
                    spacing=6,
                )
            )
        self.daily_trend.controls = controls
