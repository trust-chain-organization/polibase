"""Message display utilities for Streamlit"""

import streamlit as st


def display_messages():
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
