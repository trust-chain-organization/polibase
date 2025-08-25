"""View for conversations and speakers management."""

import streamlit as st


def render_conversations_speakers_page():
    """Render the conversations and speakers management page."""
    st.header("発言・発言者管理")
    st.markdown("発言記録と発言者の情報を管理します")

    # Create tabs
    tabs = st.tabs(["発言者一覧", "発言マッチング", "統計情報"])

    with tabs[0]:
        render_speakers_list_tab()

    with tabs[1]:
        render_matching_tab()

    with tabs[2]:
        render_statistics_tab()


def render_speakers_list_tab():
    """Render the speakers list tab."""
    st.subheader("発言者一覧")

    # Placeholder for speaker list
    st.info("発言者リストの表示機能は実装中です")

    # Sample data display
    st.markdown("""
    ### 機能概要
    - 発言者の一覧表示
    - 政治家とのマッチング状況
    - 発言回数の統計
    """)


def render_matching_tab():
    """Render the matching tab."""
    st.subheader("発言マッチング")

    st.markdown("""
    ### LLMによる発言者マッチング

    発言者と政治家のマッチングを行います。
    """)

    if st.button("マッチング実行", type="primary"):
        with st.spinner("マッチング処理を実行中..."):
            st.info("マッチング機能は実装中です")


def render_statistics_tab():
    """Render the statistics tab."""
    st.subheader("統計情報")

    # Statistics placeholders
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("総発言者数", "0名")

    with col2:
        st.metric("マッチング済み", "0名")

    with col3:
        st.metric("マッチング率", "0%")

    st.markdown("""
    ### 詳細統計
    - 会議別発言者数
    - 政党別発言数
    - 時系列発言推移
    """)


def main():
    """Main function for testing."""
    render_conversations_speakers_page()


if __name__ == "__main__":
    main()
