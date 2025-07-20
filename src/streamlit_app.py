"""Streamlit app for managing meetings"""

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

# Import page components - this is done after initializing logging and Sentry
# which is a necessary pattern for this application
from src.interfaces.web.llm_history_page import manage_llm_history  # noqa: E402
from src.streamlit.pages import (  # noqa: E402
    execute_processes,
    manage_conferences,
    manage_governing_bodies,
    manage_meetings,
    manage_parliamentary_groups,
    manage_political_parties,
    manage_politicians,
)
from src.streamlit.utils import init_session_state  # noqa: E402

# ページ設定
st.set_page_config(page_title="Polibase - 会議管理", page_icon="🏛️", layout="wide")

# セッション状態の初期化
init_session_state()


def main():
    st.title("🏛️ Polibase - 会議管理システム")
    st.markdown("議事録の会議情報（URL、日付）を管理します")

    # タブ作成
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "会議管理",
            "政党管理",
            "会議体管理",
            "開催主体管理",
            "議員団管理",
            "処理実行",
            "政治家管理",
            "LLM履歴",
        ]
    )

    with tab1:
        manage_meetings()

    with tab2:
        manage_political_parties()

    with tab3:
        manage_conferences()

    with tab4:
        manage_governing_bodies()

    with tab5:
        manage_parliamentary_groups()

    with tab6:
        execute_processes()

    with tab7:
        manage_politicians()

    with tab8:
        manage_llm_history()


if __name__ == "__main__":
    main()
