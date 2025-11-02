"""Callbacks for BI Dashboard POC.

This module defines interactive callbacks for the dashboard.
"""

from typing import TYPE_CHECKING

import plotly.graph_objects as go
from dash import Input, Output, html
from layouts.main_layout import create_summary_card

from data.data_loader import (
    get_coverage_stats,
    get_prefecture_coverage,
)

if TYPE_CHECKING:
    from dash import Dash


def register_callbacks(app: "Dash") -> None:
    """Register all callbacks for the dashboard.

    Args:
        app: Dash application instance
    """

    @app.callback(
        [
            Output("summary-cards", "children"),
            Output("coverage-pie-chart", "figure"),
            Output("coverage-by-type-chart", "figure"),
            Output("prefecture-table", "children"),
        ],
        [Input("refresh-button", "n_clicks")],
    )
    def update_dashboard(
        n_clicks: int,
    ) -> tuple[list, go.Figure, go.Figure, html.Table]:
        """Update all dashboard components.

        Args:
            n_clicks: Number of times refresh button was clicked

        Returns:
            tuple: Updated components (cards, charts, table)
        """
        # Get data
        stats = get_coverage_stats()
        prefecture_df = get_prefecture_coverage()

        # Create summary cards
        cards = [
            create_summary_card("総自治体数", f"{stats['total']:,}", "#3498db"),
            create_summary_card("データ取得済み", f"{stats['covered']:,}", "#2ecc71"),
            create_summary_card(
                "カバレッジ率",
                f"{stats['coverage_rate']:.1f}%",
                "#e74c3c"
                if stats["coverage_rate"] < 50
                else "#f39c12"
                if stats["coverage_rate"] < 80
                else "#2ecc71",
            ),
        ]

        # Create pie chart
        pie_data = {
            "labels": ["データあり", "データなし"],
            "values": [stats["covered"], stats["total"] - stats["covered"]],
            "colors": ["#2ecc71", "#e74c3c"],
        }
        pie_fig = go.Figure(
            data=[
                go.Pie(
                    labels=pie_data["labels"],
                    values=pie_data["values"],
                    marker={"colors": pie_data["colors"]},
                    hole=0.3,
                    textinfo="label+percent+value",
                )
            ]
        )
        pie_fig.update_layout(showlegend=True, height=400)

        # Create bar chart for coverage by type
        type_data = []
        for org_type, data in stats["by_type"].items():
            type_data.append(
                {
                    "type": org_type,
                    "covered": data["covered"],
                    "not_covered": data["total"] - data["covered"],
                    "coverage_rate": data["coverage_rate"],
                }
            )

        bar_fig = go.Figure()
        bar_fig.add_trace(
            go.Bar(
                name="データあり",
                x=[d["type"] for d in type_data],
                y=[d["covered"] for d in type_data],
                marker_color="#2ecc71",
            )
        )
        bar_fig.add_trace(
            go.Bar(
                name="データなし",
                x=[d["type"] for d in type_data],
                y=[d["not_covered"] for d in type_data],
                marker_color="#e74c3c",
            )
        )
        bar_fig.update_layout(
            barmode="stack",
            height=400,
            xaxis_title="組織タイプ",
            yaxis_title="自治体数",
        )

        # Create prefecture table
        table_header = html.Thead(
            html.Tr(
                [
                    html.Th(
                        "都道府県",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                        },
                    ),
                    html.Th(
                        "総数",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "textAlign": "right",
                        },
                    ),
                    html.Th(
                        "データあり",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "textAlign": "right",
                        },
                    ),
                    html.Th(
                        "カバレッジ率",
                        style={
                            "padding": "10px",
                            "backgroundColor": "#3498db",
                            "color": "white",
                            "textAlign": "right",
                        },
                    ),
                ]
            )
        )

        table_rows = []
        for _, row in prefecture_df.head(10).iterrows():
            bg_color = (
                "#d5f4e6"
                if row["coverage_rate"] >= 80
                else "#fff3cd"
                if row["coverage_rate"] >= 50
                else "#f8d7da"
            )
            table_rows.append(
                html.Tr(
                    [
                        html.Td(row["prefecture"], style={"padding": "10px"}),
                        html.Td(
                            f"{int(row['total']):,}",
                            style={"padding": "10px", "textAlign": "right"},
                        ),
                        html.Td(
                            f"{int(row['covered']):,}",
                            style={"padding": "10px", "textAlign": "right"},
                        ),
                        html.Td(
                            f"{row['coverage_rate']:.1f}%",
                            style={"padding": "10px", "textAlign": "right"},
                        ),
                    ],
                    style={"backgroundColor": bg_color},
                )
            )

        table_body = html.Tbody(table_rows)

        table = html.Table(
            [table_header, table_body],
            style={
                "width": "100%",
                "borderCollapse": "collapse",
                "boxShadow": "0 2px 4px rgba(0,0,0,0.1)",
            },
        )

        return cards, pie_fig, bar_fig, table
