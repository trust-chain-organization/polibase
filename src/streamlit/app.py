"""Streamlit app with URL-based routing using st.navigation"""

import streamlit as st

# Initialize logging and Sentry before other imports
from src.common.logging import setup_logging
from src.config.sentry import init_sentry
from src.config.settings import get_settings

# Initialize settings
settings = get_settings()

# Initialize structured logging with Sentry integration
setup_logging(
    log_level=settings.log_level, json_format=settings.is_production, enable_sentry=True
)

# Initialize Sentry SDK
init_sentry()

# Import page functions - this is done after initializing logging and Sentry
# which is a necessary pattern for this application
from src.interfaces.web.llm_history_page import manage_llm_history  # noqa: E402
from src.streamlit.pages import (  # noqa: E402
    execute_processes,
    manage_conferences,
    manage_conversations,
    manage_conversations_speakers,
    manage_governing_bodies,
    manage_meetings,
    manage_parliamentary_groups,
    manage_political_parties,
    manage_politicians,
)
from src.streamlit.utils import init_session_state  # noqa: E402


def home_page():
    """ホームページの表示"""
    st.title("🏛️ Polibase - 会議管理システム")
    st.markdown("議事録の会議情報（URL、日付）を管理します")

    st.subheader("📍 機能一覧")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 🗓️ [会議管理](/meetings)
        議事録の会議情報（URL、日付）を管理

        ### 🏛️ [政党管理](/parties)
        政党情報と政党員リストURLの管理

        ### 🏢 [会議体管理](/conferences)
        議会や委員会などの会議体情報を管理

        ### 🏛️ [開催主体管理](/governing-bodies)
        国・都道府県・市町村などの管理
        """)

    with col2:
        st.markdown("""
        ### 👥 [議員団管理](/parliamentary-groups)
        議員団（会派）情報の管理

        ### ⚙️ [処理実行](/processes)
        議事録処理やスクレイピングの実行

        ### 👤 [政治家管理](/politicians)
        政治家情報の検索・編集・管理

        ### 💬 [発言・発言者管理](/conversations-speakers)
        議事録処理で生成された発言と発言者データの閲覧

        ### 📊 [LLM履歴](/llm-history)
        LLM処理履歴の確認と検索

        """)


def main():
    """メインエントリーポイント"""
    # ページ設定
    st.set_page_config(page_title="Polibase - 会議管理", page_icon="🏛️", layout="wide")

    # セッション状態の初期化
    init_session_state()

    # ページ定義
    pages = [
        st.Page(home_page, title="ホーム", url_path="/", icon="🏠"),
        st.Page(manage_meetings, title="会議管理", url_path="meetings", icon="🗓️"),
        st.Page(
            manage_political_parties, title="政党管理", url_path="parties", icon="🏛️"
        ),
        st.Page(
            manage_conferences, title="会議体管理", url_path="conferences", icon="🏢"
        ),
        st.Page(
            manage_governing_bodies,
            title="開催主体管理",
            url_path="governing-bodies",
            icon="🏛️",
        ),
        st.Page(
            manage_parliamentary_groups,
            title="議員団管理",
            url_path="parliamentary-groups",
            icon="👥",
        ),
        st.Page(execute_processes, title="処理実行", url_path="processes", icon="⚙️"),
        st.Page(
            manage_politicians, title="政治家管理", url_path="politicians", icon="👤"
        ),
        st.Page(
            manage_conversations_speakers,
            title="発言・発言者管理",
            url_path="conversations-speakers",
            icon="💬",
        ),
        st.Page(manage_llm_history, title="LLM履歴", url_path="llm-history", icon="📊"),
    ]

    # ナビゲーション設定
    nav = st.navigation(pages)
    nav.run()


if __name__ == "__main__":
    main()
