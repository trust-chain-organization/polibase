"""Session state initialization for Streamlit app"""

import streamlit as st


def init_session_state():
    """セッション状態の初期化"""
    # 基本的なセッション状態
    if "selected_governing_body" not in st.session_state:
        st.session_state.selected_governing_body = None
    if "selected_conference" not in st.session_state:
        st.session_state.selected_conference = None
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False
    if "edit_meeting_id" not in st.session_state:
        st.session_state.edit_meeting_id = None
    if "process_status" not in st.session_state:
        st.session_state.process_status = {}
    if "process_output" not in st.session_state:
        st.session_state.process_output = {}
    if "success_message" not in st.session_state:
        st.session_state.success_message = None
    if "error_message" not in st.session_state:
        st.session_state.error_message = None
    if "message_details" not in st.session_state:
        st.session_state.message_details = None
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "会議一覧"
    if "created_parliamentary_groups" not in st.session_state:
        st.session_state.created_parliamentary_groups = []
