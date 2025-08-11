"""発言レコード一覧ページ"""

from typing import Any

import streamlit as st
from src.database.conversation_repository import ConversationRepository
from src.database.meeting_repository import MeetingRepository


def manage_conversations():
    """発言レコード一覧管理"""
    st.header("発言レコード一覧")
    st.markdown("議事録分割処理で生成された発言レコードを一覧表示します")

    # リポジトリの初期化
    meeting_repo = MeetingRepository()
    conversation_repo = ConversationRepository()

    # フィルター設定
    col1, col2, col3 = st.columns(3)

    with col1:
        # 開催主体フィルター
        governing_bodies = meeting_repo.get_governing_bodies()
        gb_options = ["すべて"] + [
            f"{gb['name']} ({gb['type']})" for gb in governing_bodies
        ]
        gb_selected = st.selectbox("開催主体", gb_options, key="conv_gb")

        if gb_selected != "すべて":
            # 選択されたオプションから対応するgoverning_bodyを探す
            selected_gb = None
            for gb in governing_bodies:
                if f"{gb['name']} ({gb['type']})" == gb_selected:
                    selected_gb = gb
                    break
            conferences = meeting_repo.get_conferences_by_governing_body(
                selected_gb["id"] if selected_gb else 0
            )
        else:
            conferences = meeting_repo.get_all_conferences()

    with col2:
        # 会議体フィルター
        selected_conf_id: int | None = None
        conf_selected = "すべて"  # デフォルト値を設定
        if conferences:
            conf_options = ["すべて"] + [conf["name"] for conf in conferences]
            conf_selected = st.selectbox("会議体", conf_options, key="conv_conf")

            if conf_selected != "すべて":
                # 選択されたオプションから対応するconferenceを探す
                for conf in conferences:
                    if conf["name"] == conf_selected:
                        selected_conf_id = conf["id"]
                        break

            # 会議体が選択されている場合、その会議一覧を取得
            if selected_conf_id:
                meetings = meeting_repo.get_meetings(conference_id=selected_conf_id)
            else:
                meetings = []
        else:
            meetings = []

    with col3:
        # 会議フィルター
        selected_meeting_id: int | None = None
        meeting_selected = "すべて"  # デフォルト値を設定
        if meetings:
            meeting_options = ["すべて"] + [
                f"{m['date'].strftime('%Y年%m月%d日')} - {m['conference_name']}"
                for m in meetings
            ]
            meeting_selected = st.selectbox("会議", meeting_options, key="conv_meeting")

            if meeting_selected != "すべて":
                # 選択されたオプションから対応するmeetingを探す
                for _i, m in enumerate(meetings):
                    if (
                        f"{m['date'].strftime('%Y年%m月%d日')} - {m['conference_name']}"
                        == meeting_selected
                    ):
                        selected_meeting_id = m["id"]
                        break

    # ページネーション設定
    col1, col2 = st.columns([1, 3])
    with col1:
        items_per_page = st.selectbox(
            "表示件数", [10, 20, 50, 100], index=1, key="conv_items_per_page"
        )

    # 現在のページ番号（セッション状態で管理）
    if "conv_current_page" not in st.session_state:
        st.session_state.conv_current_page = 1

    # フィルター条件が変更された場合、ページを1に戻す
    filter_key = f"{gb_selected}_{conf_selected}_{meeting_selected}"
    if "conv_last_filter" not in st.session_state:
        st.session_state.conv_last_filter = filter_key
    elif st.session_state.conv_last_filter != filter_key:
        st.session_state.conv_current_page = 1
        st.session_state.conv_last_filter = filter_key

    # データ取得
    offset = (st.session_state.conv_current_page - 1) * items_per_page
    result = conversation_repo.get_conversations_with_pagination(
        limit=items_per_page,
        offset=offset,
        conference_id=selected_conf_id,
        meeting_id=selected_meeting_id,
    )

    conversations = result["conversations"]
    total_count = result["total"]
    total_pages = max(1, (total_count + items_per_page - 1) // items_per_page)

    # 統計情報表示
    st.markdown("### 📊 統計情報")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("総発言数", f"{total_count:,}")

    # speaker_idが設定されているレコードの数を計算
    linked_count = sum(1 for c in conversations if c["speaker_id"] is not None)
    unlinked_count = len(conversations) - linked_count

    with col2:
        st.metric("現在ページの発言数", f"{len(conversations):,}")

    with col3:
        st.metric("発言者紐付け済み", f"{linked_count:,}")

    with col4:
        st.metric("発言者未紐付け", f"{unlinked_count:,}")

    st.markdown("---")

    # 発言レコード一覧表示
    if conversations:
        st.markdown("### 📝 発言レコード一覧")

        # 表示範囲の計算
        start_index = offset + 1
        end_index = min(offset + items_per_page, total_count)
        st.info(f"表示中: {start_index}-{end_index} / 全{total_count}件")

        # ページネーションコントロール
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("◀ 前へ", disabled=st.session_state.conv_current_page <= 1):
                st.session_state.conv_current_page -= 1
                st.rerun()

        with col2:
            st.write(f"ページ {st.session_state.conv_current_page} / {total_pages}")

        with col3:
            # ページ番号の直接入力
            new_page = st.number_input(
                "ページ番号",
                min_value=1,
                max_value=total_pages,
                value=st.session_state.conv_current_page,
                key="conv_page_input",
            )
            if new_page != st.session_state.conv_current_page:
                st.session_state.conv_current_page = new_page
                st.rerun()

        with col5:
            if st.button(
                "次へ ▶", disabled=st.session_state.conv_current_page >= total_pages
            ):
                st.session_state.conv_current_page += 1
                st.rerun()

        # 章ごとにグループ化して表示
        from itertools import groupby

        # 章番号でグループ化（None値は"その他"として扱う）
        def get_chapter_key(conv: dict[str, Any]) -> tuple[Any, Any]:
            if conv["chapter_number"] is None:
                return ("その他", None)
            else:
                return (conv["chapter_number"], conv.get("sub_chapter_number"))

        grouped_conversations = []
        for key, group in groupby(conversations, key=get_chapter_key):
            grouped_conversations.append((key, list(group)))

        # グループごとに表示
        for (chapter_num, sub_chapter_num), group_convs in grouped_conversations:
            # 章のヘッダー
            if chapter_num == "その他":
                chapter_title = "📌 章番号なしの発言"
            else:
                if sub_chapter_num:
                    chapter_title = f"📖 第{chapter_num}章-{sub_chapter_num}"
                else:
                    chapter_title = f"📖 第{chapter_num}章"

            # 展開/折りたたみ可能なエクスパンダーで表示
            with st.expander(
                f"{chapter_title} （{len(group_convs)}件の発言）", expanded=True
            ):
                for conv in group_convs:
                    with st.container():
                        col1, col2 = st.columns([3, 1])

                        with col1:
                            # 発言者情報
                            speaker_display = conv["speaker_name"] or "発言者不明"
                            if conv["speaker_id"]:
                                if conv["linked_speaker_name"]:
                                    speaker_display = (
                                        f"{speaker_display} → "
                                        f"{conv['linked_speaker_name']} "
                                        f"(ID: {conv['speaker_id']})"
                                    )
                                else:
                                    speaker_display = (
                                        f"{speaker_display} "
                                        f"(Speaker ID: {conv['speaker_id']})"
                                    )
                            else:
                                speaker_display = f"{speaker_display} (未紐付け)"

                            st.markdown(f"**👤 {speaker_display}**")

                            # 発言内容（最大300文字で表示）
                            comment = conv["comment"]
                            if len(comment) > 300:
                                comment_display = comment[:300] + "..."
                            else:
                                comment_display = comment

                            st.text_area(
                                "発言内容",
                                value=comment_display,
                                height=100,
                                disabled=True,
                                key=f"comment_{conv['id']}",
                            )

                        with col2:
                            # メタ情報
                            st.markdown("**📋 詳細情報**")
                            st.markdown(f"ID: {conv['id']}")
                            st.markdown(f"発言順序: {conv['sequence_number']}")
                            if conv["chapter_number"]:
                                chapter_info = f"章: {conv['chapter_number']}"
                                if conv["sub_chapter_number"]:
                                    chapter_info += f"-{conv['sub_chapter_number']}"
                                st.markdown(chapter_info)

                            # 会議情報
                            st.markdown("**🏛️ 会議情報**")
                            if conv["meeting_date"]:
                                meeting_date_str = conv["meeting_date"].strftime(
                                    "%Y年%m月%d日"
                                )
                                st.markdown(f"開催日: {meeting_date_str}")
                            if conv["governing_body_name"]:
                                st.markdown(
                                    f"{conv['governing_body_name']} "
                                    f"({conv['governing_body_type']})"
                                )
                            if conv["conference_name"]:
                                st.markdown(f"会議体: {conv['conference_name']}")

                        st.divider()

        # ページネーションコントロール（下部）
        st.info(f"表示中: {start_index}-{end_index} / 全{total_count}件")

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button(
                "◀ 前へ",
                key="prev_bottom",
                disabled=st.session_state.conv_current_page <= 1,
            ):
                st.session_state.conv_current_page -= 1
                st.rerun()

        with col2:
            st.write(
                f"ページ {st.session_state.conv_current_page} / {total_pages}",
                unsafe_allow_html=True,
            )

        with col3:
            if st.button(
                "次へ ▶",
                key="next_bottom",
                disabled=st.session_state.conv_current_page >= total_pages,
            ):
                st.session_state.conv_current_page += 1
                st.rerun()

    else:
        st.info("発言レコードが登録されていません")

    # リポジトリのクローズ
    meeting_repo.close()
    conversation_repo.close()
