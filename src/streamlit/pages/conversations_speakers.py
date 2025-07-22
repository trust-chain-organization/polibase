"""発言・発言者管理ページ"""

from typing import cast

import pandas as pd

import streamlit as st
from src.common.logging import get_logger
from src.database.speaker_repository import SpeakerRepository

logger = get_logger(__name__)


def manage_conversations_speakers():
    """発言・発言者管理（閲覧専用）"""
    st.header("発言・発言者管理")
    st.markdown("議事録処理で生成された発言と発言者のデータを閲覧します")

    # 発言・発言者管理用のタブを作成
    conversation_tab, speaker_tab = st.tabs(["発言一覧", "発言者一覧"])

    with conversation_tab:
        show_conversations_list()

    with speaker_tab:
        show_speakers_list()


def show_conversations_list():
    """発言一覧を表示"""
    st.subheader("発言一覧")

    # PBI-002で実装予定
    st.info("発言一覧機能は現在開発中です（PBI-002で実装予定）")
    st.markdown(
        """
        ### 実装予定の機能
        - 議事録分割処理で生成された発言レコードの一覧表示
        - 発言内容、発言者名、発言順序、章番号の表示
        - 関連する議事録情報（会議名、開催日）の表示
        - ページネーション機能
        """
    )


def show_speakers_list():
    """発言者一覧を表示"""
    st.subheader("発言者一覧")

    speaker_repo = SpeakerRepository()

    try:
        # 政治家情報を含む発言者データを取得
        speakers_data = speaker_repo.get_speakers_with_politician_info()

        if not speakers_data:
            st.info("発言者データがまだ登録されていません")
            return

        df: pd.DataFrame = pd.DataFrame(speakers_data)

        # 紐付け状況の統計情報を取得
        stats = speaker_repo.get_speaker_politician_stats()

        # 統計情報の表示
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            st.metric("総発言者数", stats["total_speakers"])
        with col2:
            st.metric("政治家", stats["politician_speakers"])
        with col3:
            st.metric("紐付け済み", stats["linked_speakers"])
        with col4:
            st.metric("未紐付け", stats["unlinked_politician_speakers"])
        with col5:
            st.metric("紐付け率", f"{stats['link_rate']:.1f}%")

        # 発言数の統計
        st.markdown("#### 発言数統計")
        col1, col2 = st.columns(2)
        with col1:
            total_conversations = df["conversation_count"].sum()
            st.metric("総発言数", total_conversations)
        with col2:
            avg_conversations = df["conversation_count"].mean()
            st.metric("平均発言数", f"{avg_conversations:.1f}")

        # フィルタリング機能
        st.markdown("### フィルタリング")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # 種別フィルタ
            type_series = cast(pd.Series, df["type"])
            non_null_types = type_series[type_series.notna()]
            # uniqueメソッドを直接使用
            unique_types = cast(pd.Series, non_null_types).unique()
            type_options = ["すべて"] + sorted(unique_types.tolist())
            selected_type = st.selectbox(
                "種別", type_options, key="speaker_type_filter"
            )

        with col2:
            # 紐付け状況フィルタ
            link_options = ["すべて", "紐付け済み", "未紐付け（政治家）", "政治家以外"]
            selected_link_status = st.selectbox(
                "紐付け状況", link_options, key="link_status_filter"
            )

        with col3:
            # 政治家フラグフィルタ
            politician_options = ["すべて", "政治家のみ", "政治家以外"]
            selected_politician = st.selectbox(
                "政治家フラグ", politician_options, key="politician_filter"
            )

        with col4:
            # 名前検索
            search_name = st.text_input(
                "名前検索", placeholder="発言者名を入力", key="speaker_name_search"
            )

        # フィルタリング適用
        filtered_df = df.copy()

        if selected_type != "すべて":
            filtered_df = filtered_df[filtered_df["type"] == selected_type]

        if selected_link_status == "紐付け済み":
            politician_id_series = cast(pd.Series, filtered_df["politician_id"])
            filtered_df = filtered_df[politician_id_series.notna()]
        elif selected_link_status == "未紐付け（政治家）":
            politician_id_series = cast(pd.Series, filtered_df["politician_id"])
            filtered_df = filtered_df[
                (filtered_df["is_politician"]) & (politician_id_series.isna())
            ]
        elif selected_link_status == "政治家以外":
            filtered_df = filtered_df[~filtered_df["is_politician"]]

        if selected_politician == "政治家のみ":
            filtered_df = filtered_df[filtered_df["is_politician"]]
        elif selected_politician == "政治家以外":
            filtered_df = filtered_df[~filtered_df["is_politician"]]

        if search_name:
            name_series = cast(pd.Series, filtered_df["name"])
            name_mask = name_series.astype(str).str.contains(
                search_name, case=False, na=False
            )
            filtered_df = filtered_df[name_mask]

        # ページネーション設定
        st.markdown("### 発言者一覧")
        items_per_page = st.selectbox(
            "表示件数",
            options=[10, 20, 50, 100],
            index=1,
            key="speakers_per_page",
        )

        # ページ番号の計算
        total_items = len(filtered_df)
        total_pages = max(1, (total_items - 1) // items_per_page + 1)

        # ページ選択
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            current_page = st.number_input(
                "ページ",
                min_value=1,
                max_value=total_pages,
                value=1,
                key="speakers_page_number",
            )

        # ページネーション適用
        start_idx = (current_page - 1) * items_per_page
        end_idx = min(start_idx + items_per_page, total_items)
        # DataFrameとして明示的にキャスト
        page_df = cast(pd.DataFrame, filtered_df).iloc[start_idx:end_idx].copy()

        # 表示用のDataFrameを作成
        display_df = page_df.copy()

        # 紐付け状況を視覚的に表示
        def format_link_status(row: pd.Series) -> str:
            if row["is_politician"]:
                if pd.notna(row["politician_id"]):
                    return "✅ 紐付け済み"
                else:
                    return "❌ 未紐付け"
            else:
                return "➖ 対象外"

        display_df["紐付け状況"] = display_df.apply(format_link_status, axis=1)

        # 政治家名を表示（紐付けられている場合）
        display_df["紐付け政治家"] = display_df["politician_name"].fillna("－")

        # 政党名を統合（politiciansテーブルの政党名を優先）
        display_df["政党名（統合）"] = display_df.apply(
            lambda row: row["party_name_from_politician"]
            if pd.notna(row["party_name_from_politician"])
            else row["political_party_name"]
            if pd.notna(row["political_party_name"])
            else "－",
            axis=1,
        )

        # カラム名を日本語に変更
        display_df = display_df.rename(
            columns={
                "name": "発言者名",
                "type": "種別",
                "position": "役職",
                "conversation_count": "発言数",
            }
        )

        # 表示するカラムを選択
        columns_to_display = [
            "発言者名",
            "種別",
            "政党名（統合）",
            "役職",
            "紐付け状況",
            "紐付け政治家",
            "発言数",
        ]

        # データを表示
        st.dataframe(
            display_df[columns_to_display],
            hide_index=True,
            use_container_width=True,
            column_config={
                "発言者名": st.column_config.TextColumn("発言者名", width="medium"),
                "種別": st.column_config.TextColumn("種別", width="small"),
                "政党名（統合）": st.column_config.TextColumn("政党名", width="medium"),
                "役職": st.column_config.TextColumn("役職", width="medium"),
                "紐付け状況": st.column_config.TextColumn("紐付け", width="small"),
                "紐付け政治家": st.column_config.TextColumn("政治家名", width="medium"),
                "発言数": st.column_config.NumberColumn(
                    "発言数", format="%d", width="small"
                ),
            },
        )

        # ページング情報
        st.caption(
            f"表示中: {start_idx + 1}-{end_idx} / 全{total_items}件 "
            f"(ページ {current_page}/{total_pages})"
        )

    except Exception as e:
        logger.error(f"発言者一覧の取得中にエラーが発生しました: {str(e)}")
        st.error(f"データの取得中にエラーが発生しました: {str(e)}")
