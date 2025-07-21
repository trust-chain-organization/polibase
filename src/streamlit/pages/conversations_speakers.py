"""発言・発言者管理ページ"""

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
        # 発言者データを発言数と共に取得
        query = """
        SELECT
            s.id,
            s.name,
            s.type,
            s.political_party_name,
            s.position,
            s.is_politician,
            COUNT(c.id) as conversation_count
        FROM speakers s
        LEFT JOIN conversations c ON s.id = c.speaker_id
        GROUP BY s.id, s.name, s.type, s.political_party_name,
                 s.position, s.is_politician
        ORDER BY s.name
        """

        # 生のクエリ結果を取得してdictに変換
        result = speaker_repo.execute_query(query)
        columns = result.keys()
        rows = result.fetchall()

        if not rows:
            st.info("発言者データがまだ登録されていません")
            return

        # 結果をdictのリストに変換
        speakers_data = [dict(zip(columns, row, strict=False)) for row in rows]
        df: pd.DataFrame = pd.DataFrame(speakers_data)

        # 統計情報の表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総発言者数", len(df))
        with col2:
            politicians_count = len(df[df["is_politician"]])
            st.metric("政治家", politicians_count)
        with col3:
            total_conversations = df["conversation_count"].sum()
            st.metric("総発言数", total_conversations)
        with col4:
            avg_conversations = df["conversation_count"].mean()
            st.metric("平均発言数", f"{avg_conversations:.1f}")

        # フィルタリング機能
        st.markdown("### フィルタリング")
        col1, col2, col3 = st.columns(3)

        with col1:
            # 種別フィルタ
            type_series: pd.Series = df["type"]
            non_null_types = type_series[type_series.notna()]
            unique_types = non_null_types.unique()
            type_options = ["すべて"] + sorted(unique_types.tolist())
            selected_type = st.selectbox(
                "種別", type_options, key="speaker_type_filter"
            )

        with col2:
            # 政治家フラグフィルタ
            politician_options = ["すべて", "政治家のみ", "政治家以外"]
            selected_politician = st.selectbox(
                "政治家フラグ", politician_options, key="politician_filter"
            )

        with col3:
            # 名前検索
            search_name = st.text_input(
                "名前検索", placeholder="発言者名を入力", key="speaker_name_search"
            )

        # フィルタリング適用
        filtered_df: pd.DataFrame = df.copy()

        if selected_type != "すべて":
            filtered_df = filtered_df[filtered_df["type"] == selected_type]

        if selected_politician == "政治家のみ":
            filtered_df = filtered_df[filtered_df["is_politician"]]
        elif selected_politician == "政治家以外":
            filtered_df = filtered_df[~filtered_df["is_politician"]]

        if search_name:
            name_series: pd.Series = filtered_df["name"]
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
        page_df = filtered_df.iloc[start_idx:end_idx].copy()

        # 表示用のDataFrameを作成
        display_df = page_df.copy()

        # 政治家フラグを視覚的に表示
        display_df["政治家"] = display_df["is_politician"].apply(
            lambda x: "✓" if x else "✗"
        )

        # カラム名を日本語に変更
        display_df = display_df.rename(
            columns={
                "name": "発言者名",
                "type": "種別",
                "political_party_name": "政党名",
                "position": "役職",
                "conversation_count": "発言数",
            }
        )

        # 表示するカラムを選択
        columns_to_display = [
            "発言者名",
            "種別",
            "政党名",
            "役職",
            "政治家",
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
                "政党名": st.column_config.TextColumn("政党名", width="medium"),
                "役職": st.column_config.TextColumn("役職", width="medium"),
                "政治家": st.column_config.TextColumn("政治家", width="small"),
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
