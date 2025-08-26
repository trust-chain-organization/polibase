"""Meeting edit component"""

from datetime import date

import streamlit as st
from src.exceptions import DatabaseError, RecordNotFoundError, UpdateError
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


def edit_meeting():
    """会議編集フォーム"""
    st.subheader("会議編集")

    if not st.session_state.edit_mode or not st.session_state.edit_meeting_id:
        st.info(
            "編集する会議を選択してください（会議一覧タブから編集ボタンをクリック）"
        )
        return

    # Use RepositoryAdapter to handle async methods from sync context
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)

    # 編集対象の会議情報を取得
    meeting = meeting_repo.get_meeting_by_id_with_info(st.session_state.edit_meeting_id)
    if not meeting:
        st.error("会議が見つかりません")
        st.session_state.edit_mode = False
        st.session_state.edit_meeting_id = None
        return

    st.info(f"編集中: {meeting['governing_body_name']} - {meeting['conference_name']}")

    with st.form("edit_meeting_form"):
        # 日付入力
        current_date: date = meeting["date"] if meeting["date"] else date.today()
        meeting_date = st.date_input("開催日", value=current_date)

        # URL入力
        url = st.text_input(
            "会議URL（議事録PDFのURLなど）",
            value=meeting["url"] or "",
            placeholder="https://example.com/minutes.pdf",
        )

        # ボタン
        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("更新")

        with col2:
            cancelled = st.form_submit_button("キャンセル")

        if submitted:
            if not url:
                st.error("URLを入力してください")
            else:
                try:
                    # Update the meeting using the repository

                    meeting_entity = meeting_repo.get_by_id(
                        st.session_state.edit_meeting_id
                    )
                    if meeting_entity:
                        meeting_entity.date = meeting_date
                        meeting_entity.url = url
                        updated_meeting = meeting_repo.update(meeting_entity)
                    else:
                        updated_meeting = None

                    if updated_meeting:
                        st.success("会議を更新しました")
                        st.session_state.edit_mode = False
                        st.session_state.edit_meeting_id = None
                        st.rerun()
                    else:
                        st.error("会議の更新に失敗しました")
                except (UpdateError, RecordNotFoundError, DatabaseError) as e:
                    st.error(f"会議の更新に失敗しました: {str(e)}")
                except Exception as e:
                    st.error(f"予期しないエラーが発生しました: {str(e)}")

        if cancelled:
            st.session_state.edit_mode = False
            st.session_state.edit_meeting_id = None
            st.rerun()

    meeting_repo.close()
