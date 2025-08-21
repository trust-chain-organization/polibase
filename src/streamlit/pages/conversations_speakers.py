"""発言・発言者管理ページ"""

from typing import cast

import pandas as pd

import streamlit as st
from src.common.logging import get_logger
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl

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

    conversation_repo = RepositoryAdapter(ConversationRepositoryImpl)

    try:
        # 紐付け統計情報を取得
        stats = conversation_repo.get_speaker_linking_stats()

        # 統計情報の表示
        st.markdown("### 紐付け状況サマリー")
        col1, col2, col3, col4, col5, col6 = st.columns(6)
        with col1:
            st.metric("総発言数", stats["total_conversations"])
        with col2:
            st.metric("Speaker紐付け済", stats["speaker_linked_conversations"])
        with col3:
            st.metric("政治家紐付け済", stats["politician_linked_conversations"])
        with col4:
            st.metric("未紐付け", stats["unlinked_conversations"])
        with col5:
            st.metric("Speaker紐付け率", f"{stats['speaker_link_rate']:.1f}%")
        with col6:
            st.metric("政治家紐付け率", f"{stats['politician_link_rate']:.1f}%")

        # フィルタリング設定
        st.markdown("### フィルタリング")

        # フィルタリング列の作成
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            # 会議体一覧を取得
            conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
            with conference_repo:
                conferences = conference_repo.get_all_conferences()

            # 選択肢を作成
            conference_options = ["すべて"] + [
                f"{conf['name']} ({conf['governing_body_name']})"
                for conf in conferences
            ]
            conference_ids = [None] + [conf["id"] for conf in conferences]

            selected_index = st.selectbox(
                "会議体",
                range(len(conference_options)),
                format_func=lambda x: conference_options[x],
                key="conversation_conference_filter",
            )
            selected_conference_id = conference_ids[selected_index]

        with col2:
            # 選択された会議体に基づいて会議一覧を取得
            meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
            meetings = meeting_repo.get_meetings(
                conference_id=selected_conference_id,
                limit=1000,  # 十分な数の会議を取得
            )

            # 選択肢を作成
            meeting_options = ["すべて"]
            meeting_ids = [None]

            if meetings:
                # 日付でソート（新しい順）
                meetings.sort(
                    key=lambda x: x["date"] if x["date"] else "", reverse=True
                )

                for meeting in meetings:
                    date_str = (
                        meeting["date"].strftime("%Y-%m-%d")
                        if meeting["date"]
                        else "日付なし"
                    )
                    meeting_options.append(f"{date_str} - {meeting['conference_name']}")
                    meeting_ids.append(meeting["id"])

            selected_meeting_index = st.selectbox(
                "議事録（会議）",
                range(len(meeting_options)),
                format_func=lambda x: meeting_options[x],
                key="conversation_meeting_filter",
                disabled=(selected_conference_id is None and len(meetings) == 0),
            )
            selected_meeting_id = meeting_ids[selected_meeting_index]

        with col3:
            items_per_page = st.selectbox(
                "表示件数",
                options=[10, 20, 50, 100],
                index=1,
                key="conversations_per_page",
            )

        # ページ番号の初期化と表示
        if "conversation_page_number" not in st.session_state:
            st.session_state.conversation_page_number = 1

        # フィルタ選択が変更されたらページ番号をリセット
        if "prev_conference_id" not in st.session_state:
            st.session_state.prev_conference_id = selected_conference_id
        if "prev_meeting_id" not in st.session_state:
            st.session_state.prev_meeting_id = selected_meeting_id

        if (
            st.session_state.prev_conference_id != selected_conference_id
            or st.session_state.prev_meeting_id != selected_meeting_id
        ):
            st.session_state.conversation_page_number = 1
            st.session_state.prev_conference_id = selected_conference_id
            st.session_state.prev_meeting_id = selected_meeting_id

        # データ取得
        offset = (st.session_state.conversation_page_number - 1) * items_per_page
        result = conversation_repo.get_conversations_with_pagination(
            limit=items_per_page,
            offset=offset,
            conference_id=selected_conference_id,
            meeting_id=selected_meeting_id,
        )

        conversations = result["conversations"]
        total_items = result["total"]

        if not conversations:
            st.info("発言データがまだ登録されていません")
            return

        # データフレームの作成
        df = pd.DataFrame(conversations)

        # 表示用のDataFrameを作成
        display_df = df.copy()

        # 紐付け状況を視覚的に表示する関数
        def format_link_status(row: pd.Series) -> str:
            if pd.notna(row["politician_id"]):
                return "✅ 完全紐付け"
            elif pd.notna(row["speaker_id"]):
                return "⚠️ Speaker紐付けのみ"
            else:
                return "❌ 未紐付け"

        display_df["紐付け状況"] = display_df.apply(format_link_status, axis=1)

        # 政治家名を表示（紐付けられている場合）
        display_df["紐付け政治家"] = display_df["politician_name"].fillna("－")

        # 政党名を統合（politiciansテーブルの政党名を優先）
        display_df["政党名"] = display_df.apply(
            lambda row: row["politician_party_name"]
            if pd.notna(row["politician_party_name"])
            else row["speaker_party_name"]
            if pd.notna(row["speaker_party_name"])
            else "－",
            axis=1,
        )

        # Speaker種別を追加
        display_df["発言者種別"] = display_df["speaker_type"].fillna("－")

        # カラム名を日本語に変更
        display_df = display_df.rename(
            columns={
                "speaker_name": "発言者名",
                "comment": "発言内容",
                "sequence_number": "発言順序",
                "chapter_number": "章番号",
                "sub_chapter_number": "節番号",
                "meeting_date": "開催日",
                "conference_name": "会議名",
                "governing_body_name": "自治体名",
                "linked_speaker_name": "紐付けSpeaker",
            }
        )

        # 日付のフォーマット
        if "開催日" in display_df.columns:
            date_series = cast(pd.Series, display_df["開催日"])
            display_df["開催日"] = pd.to_datetime(date_series).dt.strftime("%Y-%m-%d")

        # 表示するカラムを選択
        columns_to_display = [
            "発言順序",
            "発言者名",
            "紐付け状況",
            "紐付けSpeaker",
            "紐付け政治家",
            "政党名",
            "発言者種別",
            "発言内容",
            "章番号",
            "節番号",
            "会議名",
            "開催日",
            "自治体名",
        ]

        # 存在するカラムのみを選択
        available_columns = [
            col for col in columns_to_display if col in display_df.columns
        ]

        # ページネーション計算
        total_pages = max(1, (total_items - 1) // items_per_page + 1)

        # ページ選択
        col1, col2, col3 = st.columns([1, 3, 1])
        with col2:
            current_page = st.number_input(
                "ページ",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.conversation_page_number,
                key="conversation_page_input",
            )
            if current_page != st.session_state.conversation_page_number:
                st.session_state.conversation_page_number = current_page
                st.rerun()

        # データを表示
        st.dataframe(
            display_df[available_columns],
            hide_index=True,
            use_container_width=True,
            column_config={
                "発言順序": st.column_config.NumberColumn(
                    "順序", format="%d", width="small"
                ),
                "発言者名": st.column_config.TextColumn("発言者名", width="medium"),
                "紐付け状況": st.column_config.TextColumn("紐付け", width="small"),
                "紐付けSpeaker": st.column_config.TextColumn("Speaker", width="medium"),
                "紐付け政治家": st.column_config.TextColumn("政治家", width="medium"),
                "政党名": st.column_config.TextColumn("政党", width="small"),
                "発言者種別": st.column_config.TextColumn("種別", width="small"),
                "発言内容": st.column_config.TextColumn("発言内容", width="large"),
                "章番号": st.column_config.NumberColumn(
                    "章", format="%d", width="small"
                ),
                "節番号": st.column_config.NumberColumn(
                    "節", format="%d", width="small"
                ),
                "会議名": st.column_config.TextColumn("会議名", width="medium"),
                "開催日": st.column_config.TextColumn("開催日", width="small"),
                "自治体名": st.column_config.TextColumn("自治体名", width="medium"),
            },
        )

        # ページング情報
        start_idx = offset + 1
        end_idx = min(offset + items_per_page, total_items)
        st.caption(
            f"表示中: {start_idx}-{end_idx} / 全{total_items}件 "
            f"(ページ {current_page}/{total_pages})"
        )

    except Exception as e:
        logger.error(f"発言一覧の取得中にエラーが発生しました: {str(e)}")
        st.error(f"データの取得中にエラーが発生しました: {str(e)}")


def show_speakers_list():
    """発言者一覧を表示"""
    st.subheader("発言者一覧")

    speaker_repo = RepositoryAdapter(SpeakerRepositoryImpl)

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
