"""Main meeting management component"""

import streamlit as st

from .meeting_edit import edit_meeting
from .meeting_form import add_new_meeting
from .meeting_list import show_meetings_list


def manage_meetings():
    """会議管理（一覧・新規登録・編集）"""
    st.header("会議管理")
    st.markdown("議事録の会議情報を管理します")

    # 会議管理用のタブを作成
    meeting_tab1, meeting_tab2, meeting_tab3 = st.tabs(
        ["会議一覧", "新規会議登録", "会議編集"]
    )

    with meeting_tab1:
        show_meetings_list()

    with meeting_tab2:
        add_new_meeting()

    with meeting_tab3:
        edit_meeting()
