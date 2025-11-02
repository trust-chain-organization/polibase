"""Main layout for BI Dashboard POC.

This module defines the layout structure of the dashboard.
"""

from typing import TYPE_CHECKING

from dash import dcc, html

if TYPE_CHECKING:
    from dash.html import Div


def create_layout() -> html.Div:
    """Create the main dashboard layout.

    Returns:
        html.Div: Dashboard layout component
    """
    return html.Div(
        [
            # Header
            html.Div(
                [
                    html.H1(
                        "Polibase データカバレッジダッシュボード",
                        style={"textAlign": "center", "color": "#2c3e50"},
                    ),
                    html.P(
                        "全国の自治体データ収集状況を可視化",
                        style={"textAlign": "center", "color": "#7f8c8d"},
                    ),
                ],
                style={"padding": "20px"},
            ),
            # Summary Cards
            html.Div(
                id="summary-cards",
                style={
                    "display": "flex",
                    "justifyContent": "space-around",
                    "padding": "20px",
                    "backgroundColor": "#ecf0f1",
                },
            ),
            # Charts Section
            html.Div(
                [
                    # Coverage Pie Chart
                    html.Div(
                        [
                            html.H3("全体カバレッジ率", style={"textAlign": "center"}),
                            dcc.Graph(id="coverage-pie-chart"),
                        ],
                        style={
                            "width": "48%",
                            "display": "inline-block",
                            "padding": "10px",
                        },
                    ),
                    # Coverage by Type Bar Chart
                    html.Div(
                        [
                            html.H3(
                                "組織タイプ別カバレッジ", style={"textAlign": "center"}
                            ),
                            dcc.Graph(id="coverage-by-type-chart"),
                        ],
                        style={
                            "width": "48%",
                            "display": "inline-block",
                            "padding": "10px",
                        },
                    ),
                ],
                style={"padding": "20px"},
            ),
            # Prefecture Coverage Table
            html.Div(
                [
                    html.H3("都道府県別カバレッジ", style={"textAlign": "center"}),
                    html.Div(id="prefecture-table"),
                ],
                style={"padding": "20px"},
            ),
            # Refresh Button
            html.Div(
                [
                    html.Button(
                        "データを更新",
                        id="refresh-button",
                        n_clicks=0,
                        style={
                            "padding": "10px 30px",
                            "fontSize": "16px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "border": "none",
                            "borderRadius": "5px",
                            "cursor": "pointer",
                        },
                    )
                ],
                style={"textAlign": "center", "padding": "20px"},
            ),
            # Hidden div for storing data
            html.Div(id="data-store", style={"display": "none"}),
        ],
        style={
            "fontFamily": "Arial, sans-serif",
            "maxWidth": "1400px",
            "margin": "0 auto",
            "backgroundColor": "#ffffff",
        },
    )


def create_summary_card(title: str, value: str, color: str) -> "Div":
    """Create a summary card component.

    Args:
        title: Card title
        value: Display value
        color: Card background color

    Returns:
        html.Div: Summary card component
    """
    return html.Div(
        [
            html.H4(title, style={"margin": "0", "color": "#2c3e50"}),
            html.H2(value, style={"margin": "10px 0", "color": color}),
        ],
        style={
            "backgroundColor": "white",
            "padding": "20px",
            "borderRadius": "10px",
            "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            "minWidth": "200px",
            "textAlign": "center",
        },
    )
