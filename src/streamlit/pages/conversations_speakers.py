"""発言・発言者管理ページ"""

import streamlit as st


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

    # PBI-003で実装予定
    st.info("発言者一覧機能は現在開発中です（PBI-003で実装予定）")
    st.markdown(
        """
        ### 実装予定の機能
        - 議事録から抽出された発言者レコードの一覧表示
        - 発言者名、種別、政党名、役職の表示
        - 政治家フラグ（is_politician）の状態表示
        - 各発言者の発言数表示
        - 政治家との紐付け状況表示（PBI-004で拡張予定）
        """
    )
