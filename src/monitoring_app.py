"""Streamlit monitoring dashboard for data coverage visualization"""

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_folium import st_folium  # type: ignore[import-untyped]

import streamlit as st

# Initialize logging and Sentry before other imports
from src.common.logging import get_logger, setup_logging
from src.config.sentry import init_sentry
from src.config.settings import get_settings

# Initialize settings
settings = get_settings()

# Initialize structured logging with Sentry integration
setup_logging(
    log_level=settings.log_level, json_format=settings.is_production, enable_sentry=True
)

# Initialize Sentry SDK
init_sentry()

# Get logger
logger = get_logger(__name__)

from src.infrastructure.persistence.monitoring_repository_impl import (
    MonitoringRepositoryImpl as MonitoringRepository,  # noqa: E402
)
from src.utils.japan_map import (  # noqa: E402
    create_japan_map,
    create_prefecture_details_card,
)

# ページ設定
st.set_page_config(
    page_title="Polibase - データカバレッジ監視", page_icon="📊", layout="wide"
)

# CSSスタイル
st.markdown(
    """
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .big-font {
        font-size: 32px !important;
        font-weight: bold;
    }
    .medium-font {
        font-size: 20px !important;
    }
</style>
""",
    unsafe_allow_html=True,
)


def main():
    st.title("📊 Polibase データカバレッジ監視ダッシュボード")
    st.markdown("全国の議会情報や議事録情報の入力状況を可視化します")

    # データ更新時刻
    st.sidebar.markdown(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # リポジトリ初期化（デフォルトでセッションベース）
    repo = MonitoringRepository()

    # タブ作成
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📈 全体概要",
            "🗾 日本地図",
            "🏛️ 議会別カバレッジ",
            "📅 時系列分析",
            "🎯 データ充実度詳細",
        ]
    )

    with tab1:
        display_overview_tab(repo)

    with tab2:
        display_japan_map_tab(repo)

    with tab3:
        display_conference_coverage_tab(repo)

    with tab4:
        display_timeline_tab(repo)

    with tab5:
        display_detailed_coverage_tab(repo)


def display_overview_tab(repo: MonitoringRepository):
    """全体概要タブの表示"""
    st.header("📈 全体概要")

    # 主要メトリクスの取得
    metrics = repo.get_overall_metrics()

    # メトリクスの表示（4列）
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="登録議会数",
            value=f"{metrics['total_conferences']:,}",
            delta=f"+{metrics['conferences_with_data']} データあり",
        )

    with col2:
        st.metric(
            label="登録会議数",
            value=f"{metrics['total_meetings']:,}",
            delta=f"{metrics['meetings_coverage']:.1f}% カバー",
        )

    with col3:
        st.metric(
            label="処理済み議事録",
            value=f"{metrics['processed_minutes']:,}",
            delta=f"{metrics['minutes_coverage']:.1f}% 処理済み",
        )

    with col4:
        st.metric(
            label="登録政治家数",
            value=f"{metrics['total_politicians']:,}",
            delta=f"{metrics['active_politicians']} アクティブ",
        )

    # サマリーチャート
    st.subheader("データカバレッジサマリー")

    # カバレッジデータの準備
    coverage_data = pd.DataFrame(
        {
            "カテゴリ": ["議会", "会議", "議事録", "発言者", "政治家"],
            "カバレッジ率": [
                metrics["conferences_coverage"],
                metrics["meetings_coverage"],
                metrics["minutes_coverage"],
                metrics["speakers_coverage"],
                metrics["politicians_coverage"],
            ],
        }
    )

    # 横棒グラフで表示
    fig = px.bar(  # type: ignore[call-overload]
        coverage_data,
        x="カバレッジ率",
        y="カテゴリ",
        orientation="h",
        color="カバレッジ率",
        color_continuous_scale="RdYlGn",
        range_color=[0, 100],
        title="各カテゴリのデータカバレッジ率",
    )

    fig.update_layout(height=400)  # type: ignore[no-untyped-call]
    st.plotly_chart(fig, use_container_width=True)  # type: ignore[no-untyped-call]

    # データ入力進捗
    st.subheader("最近のデータ入力状況")
    recent_activities = repo.get_recent_activities(days=7)

    if not recent_activities.empty:
        st.dataframe(recent_activities, use_container_width=True, hide_index=True)  # type: ignore[call-arg]
    else:
        st.info("過去7日間のデータ入力はありません")


def display_conference_coverage_tab(repo: MonitoringRepository):
    """議会別カバレッジタブの表示"""
    st.header("🏛️ 議会別カバレッジ")

    # フィルタリング
    col1, col2 = st.columns(2)

    with col1:
        governing_body_type = st.selectbox(
            "統治体タイプ", ["すべて", "国", "都道府県", "市町村"], index=0
        )

    with col2:
        min_coverage = st.slider(
            "最小カバレッジ率", min_value=0, max_value=100, value=0, step=10
        )

    # データ取得
    conference_coverage = repo.get_conference_coverage(
        governing_body_type=(
            None if governing_body_type == "すべて" else governing_body_type
        ),
        min_coverage=min_coverage,
    )

    if not conference_coverage.empty:
        # ヒートマップの作成
        st.subheader("議会別データ充実度ヒートマップ")

        # ピボットテーブルの作成
        heatmap_data = conference_coverage.pivot_table(  # type: ignore[attr-defined]
            index="governing_body_name",
            columns="conference_name",
            values="coverage_rate",
            aggfunc="first",
        )

        fig = go.Figure(
            data=go.Heatmap(
                z=heatmap_data.values,
                x=heatmap_data.columns,
                y=heatmap_data.index,
                colorscale="RdYlGn",
                zmid=50,
                text=heatmap_data.values,
                texttemplate="%{text:.0f}%",
                textfont={"size": 10},
                hoverongaps=False,
            )
        )

        fig.update_layout(  # type: ignore[no-untyped-call]
            title="議会別カバレッジ率",
            height=600,
            xaxis_title="議会名",
            yaxis_title="統治体名",
        )

        st.plotly_chart(fig, use_container_width=True)  # type: ignore[attr-defined]  # type: ignore[no-untyped-call]

        # 詳細テーブル
        st.subheader("議会別詳細データ")

        # カラムの表示調整
        display_columns = [
            "governing_body_name",
            "conference_name",
            "total_meetings",
            "processed_meetings",
            "coverage_rate",
            "last_updated",
        ]

        column_config: dict[str, Any] = {
            "governing_body_name": "統治体名",
            "conference_name": "議会名",
            "total_meetings": "総会議数",
            "processed_meetings": "処理済み会議数",
            "coverage_rate": st.column_config.ProgressColumn(
                "カバレッジ率",
                help="データ入力の完了率",
                min_value=0,
                max_value=100,
            ),
            "last_updated": "最終更新日",
        }

        st.dataframe(  # type: ignore[attr-defined]
            conference_coverage[display_columns],
            column_config=column_config,
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("表示するデータがありません")


def display_timeline_tab(repo: MonitoringRepository):
    """時系列分析タブの表示"""
    st.header("📅 時系列分析")

    # 期間選択
    col1, col2 = st.columns(2)

    with col1:
        time_range = st.selectbox(
            "表示期間",
            ["過去7日", "過去30日", "過去3ヶ月", "過去1年", "全期間"],
            index=1,
        )

    with col2:
        data_type = st.selectbox(
            "データタイプ", ["会議数", "議事録数", "発言数", "すべて"], index=3
        )

    # データ取得
    timeline_data = repo.get_timeline_data(time_range, data_type)

    if not timeline_data.empty:
        # 時系列グラフ
        st.subheader("データ入力推移")

        fig = px.line(  # type: ignore[call-overload]
            timeline_data,
            x="date",
            y="count",
            color="data_type",
            title="データ入力数の時系列推移",
            labels={"date": "日付", "count": "件数", "data_type": "データタイプ"},
        )

        fig.update_layout(height=500)  # type: ignore[no-untyped-call]
        st.plotly_chart(fig, use_container_width=True)  # type: ignore[attr-defined]  # type: ignore[no-untyped-call]

        # 累積グラフ
        st.subheader("累積データ数")

        # 累積計算
        timeline_data["cumulative"] = timeline_data.groupby("data_type")[  # type: ignore[attr-defined]
            "count"
        ].cumsum()

        fig_cum = px.area(  # type: ignore[call-overload]
            timeline_data,
            x="date",
            y="cumulative",
            color="data_type",
            title="累積データ数の推移",
            labels={
                "date": "日付",
                "cumulative": "累積件数",
                "data_type": "データタイプ",
            },
        )

        fig_cum.update_layout(height=500)  # type: ignore[no-untyped-call]
        st.plotly_chart(fig_cum, use_container_width=True)  # type: ignore[no-untyped-call]

    else:
        st.info("表示するデータがありません")


def display_detailed_coverage_tab(repo: MonitoringRepository):
    """データ充実度詳細タブの表示"""
    st.header("🎯 データ充実度詳細")

    # カテゴリ選択
    category = st.selectbox(
        "分析カテゴリ", ["政党別", "都道府県別", "委員会タイプ別"], index=0
    )

    if category == "政党別":
        display_party_coverage(repo)
    elif category == "都道府県別":
        display_prefecture_coverage(repo)
    else:
        display_committee_type_coverage(repo)


def display_party_coverage(repo: MonitoringRepository):
    """政党別カバレッジの表示"""
    st.subheader("政党別データカバレッジ")

    party_data = repo.get_party_coverage()

    if not party_data.empty:
        # ドーナツチャート
        fig = px.pie(  # type: ignore[call-overload]
            party_data,
            values="politician_count",
            names="party_name",
            title="政党別政治家数",
            hole=0.4,
        )

        fig.update_traces(textposition="inside", textinfo="percent+label")  # type: ignore[no-untyped-call]
        st.plotly_chart(fig, use_container_width=True)  # type: ignore[attr-defined]

        # 詳細テーブル
        st.dataframe(  # type: ignore[attr-defined]
            party_data,
            column_config={
                "party_name": "政党名",
                "politician_count": "政治家数",
                "active_count": "アクティブ数",
                "coverage_rate": st.column_config.ProgressColumn(
                    "カバレッジ率",
                    min_value=0,
                    max_value=100,
                ),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("政党データがありません")


def display_prefecture_coverage(repo: MonitoringRepository):
    """都道府県別カバレッジの表示"""
    st.subheader("都道府県別データカバレッジ")

    prefecture_data = repo.get_prefecture_coverage()

    if not prefecture_data.empty:
        # 地図表示（簡易版）
        fig = px.bar(  # type: ignore[call-overload]
            prefecture_data.sort_values("coverage_rate", ascending=True),
            y="prefecture_name",
            x="coverage_rate",
            orientation="h",
            color="coverage_rate",
            color_continuous_scale="RdYlGn",
            range_color=[0, 100],
            title="都道府県別カバレッジ率",
        )

        fig.update_layout(height=800)  # type: ignore[no-untyped-call]
        st.plotly_chart(fig, use_container_width=True)  # type: ignore[attr-defined]  # type: ignore[no-untyped-call]

    else:
        st.info("都道府県データがありません")


def display_committee_type_coverage(repo: MonitoringRepository):
    """委員会タイプ別カバレッジの表示"""
    st.subheader("委員会タイプ別データカバレッジ")

    committee_data = repo.get_committee_type_coverage()

    if not committee_data.empty:
        # サンキーダイアグラム
        fig = px.sunburst(  # type: ignore[call-overload]
            committee_data,
            path=["governing_body_type", "committee_type"],
            values="meeting_count",
            title="委員会タイプ別会議数分布",
        )

        fig.update_layout(height=600)  # type: ignore[no-untyped-call]
        st.plotly_chart(fig, use_container_width=True)  # type: ignore[attr-defined]  # type: ignore[no-untyped-call]

    else:
        st.info("委員会データがありません")


def display_japan_map_tab(repo: MonitoringRepository):
    """日本地図タブの表示"""
    st.header("🗾 日本地図でみるデータカバレッジ")

    # データ取得
    prefecture_data = repo.get_prefecture_detailed_coverage()

    if prefecture_data.empty:
        st.warning("都道府県データがありません")
        return

    # 数値型カラムを明示的に変換
    numeric_columns = [
        "conference_count",
        "meetings_count",
        "processed_meetings_count",
        "minutes_count",
        "politicians_count",
        "groups_count",
        "total_value",
    ]
    for col in numeric_columns:
        if col in prefecture_data.columns:
            prefecture_data[col] = pd.to_numeric(prefecture_data[col], errors="coerce")  # type: ignore[assignment]

    # メトリクスの選択
    col1, col2 = st.columns([3, 1])

    with col2:
        st.subheader("表示設定")

        # 表示する指標の選択
        metric_options = {
            "total_value": "総合充実度",
            "meetings_count": "会議数",
            "minutes_count": "議事録数",
            "politicians_count": "議員数",
            "groups_count": "議員団数",
        }

        selected_metric = st.selectbox(
            "表示する指標",
            options=list(metric_options.keys()),
            format_func=lambda x: metric_options[x],
            index=0,
        )

        # データサマリー
        st.markdown("### 📊 データサマリー")

        # 全国平均
        if selected_metric in prefecture_data.columns:
            avg_value = prefecture_data[selected_metric].mean()  # type: ignore[union-attr]
            max_value = prefecture_data[selected_metric].max()  # type: ignore[union-attr]
            min_value = prefecture_data[selected_metric].min()  # type: ignore[union-attr]

            st.metric("全国平均", f"{avg_value:.1f}")
            st.metric("最大値", f"{max_value:.0f}")
            st.metric("最小値", f"{min_value:.0f}")

        # トップ5都道府県
        st.markdown("### 🏆 トップ5")
        top5 = prefecture_data.nlargest(5, selected_metric)[  # type: ignore[union-attr]
            ["prefecture_name", selected_metric]
        ]
        for idx, row in top5.iterrows():  # type: ignore[union-attr]
            st.write(f"{idx + 1}. {row['prefecture_name']}: {row[selected_metric]:.1f}")  # type: ignore[operator]

    with col1:
        # 地図の作成と表示
        m = create_japan_map(
            prefecture_data, value_column=selected_metric, zoom_start=5
        )

        # Foliumマップの表示
        map_data = st_folium(
            m,
            height=600,
            width=None,
            returned_objects=["last_object_clicked"],
            key="japan_map",
        )

        # クリックされた都道府県の詳細表示
        if map_data["last_object_clicked"] is not None:
            clicked_popup = map_data["last_object_clicked"].get("popup")
            if clicked_popup:
                # ポップアップから都道府県名を抽出
                import re

                match = re.search(r"<h4>(.+?)</h4>", clicked_popup)
                if match:
                    prefecture_name = match.group(1)

                    # 該当する都道府県のデータを取得
                    pref_data = prefecture_data[  # type: ignore[index]
                        prefecture_data["prefecture_name"] == prefecture_name
                    ]

                    if not pref_data.empty:  # type: ignore[union-attr]
                        st.markdown("---")
                        st.subheader(f"{prefecture_name}の詳細情報")

                        # 詳細カードの表示
                        st.markdown(
                            create_prefecture_details_card(pref_data.iloc[0]),  # type: ignore[arg-type,union-attr]
                            unsafe_allow_html=True,
                        )

    # データテーブルの表示
    with st.expander("📋 都道府県別詳細データ", expanded=False):
        # カラム名の日本語化
        column_mapping = {
            "prefecture_name": "都道府県",
            "conference_count": "議会数",
            "meetings_count": "会議数",
            "processed_meetings_count": "処理済み会議数",
            "minutes_count": "議事録数",
            "politicians_count": "議員数",
            "groups_count": "議員団数",
            "total_value": "総合充実度 (%)",
        }

        # 表示用のデータフレームを作成
        display_df = prefecture_data.rename(columns=column_mapping)

        # データフレームの表示
        st.dataframe(  # type: ignore[call-arg]
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "総合充実度 (%)": st.column_config.ProgressColumn(
                    "総合充実度 (%)",
                    help="各種指標の総合評価",
                    min_value=0,
                    max_value=100,
                ),
            },
        )

        # CSVダウンロードボタン
        csv = display_df.to_csv(index=False, encoding="utf-8-sig")  # type: ignore[union-attr]
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv,
            file_name=f"prefecture_coverage_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
