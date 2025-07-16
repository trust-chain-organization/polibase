"""共通ユーティリティ関数"""

import streamlit as st


def init_session_state() -> None:
    """セッション状態の初期化"""
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


def display_messages() -> None:
    """セッション状態のメッセージを表示"""
    # メッセージクリアフラグをチェック
    if "clear_messages" in st.session_state and st.session_state.clear_messages:
        st.session_state.success_message = None
        st.session_state.error_message = None
        st.session_state.message_details = None
        st.session_state.clear_messages = False
        return

    # 成功メッセージの表示
    if st.session_state.success_message:
        with st.container():
            col1, col2 = st.columns([10, 1])
            with col1:
                st.success(st.session_state.success_message)
            with col2:
                if st.button("✖", key="clear_success", help="メッセージを閉じる"):
                    st.session_state.clear_messages = True
                    st.rerun()

            # 詳細情報があれば表示
            if st.session_state.message_details:
                with st.expander("詳細を表示", expanded=True):
                    st.markdown(st.session_state.message_details)

    # エラーメッセージの表示
    if st.session_state.error_message:
        with st.container():
            col1, col2 = st.columns([10, 1])
            with col1:
                st.error(st.session_state.error_message)
            with col2:
                if st.button("✖", key="clear_error", help="メッセージを閉じる"):
                    st.session_state.clear_messages = True
                    st.rerun()


def set_success_message(message: str, details: str | None = None) -> None:
    """成功メッセージを設定"""
    st.session_state.success_message = message
    st.session_state.message_details = details
    st.session_state.error_message = None


def set_error_message(message: str) -> None:
    """エラーメッセージを設定"""
    st.session_state.error_message = message
    st.session_state.success_message = None
    st.session_state.message_details = None
