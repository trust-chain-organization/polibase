"""Main Streamlit application using Clean Architecture.

This module provides the main entry point for the Streamlit web interface,
following Clean Architecture principles with presenter pattern.
"""

import streamlit as st

# Import new Clean Architecture views
from src.interfaces.web.streamlit.views.meetings_view import render_meetings_page
from src.interfaces.web.streamlit.views.political_parties_view import (
    render_political_parties_page,
)

# Import legacy pages (to be migrated)
# These will be gradually replaced with Clean Architecture views
try:
    from src.streamlit.pages.conferences import manage_conferences
except ImportError:
    manage_conferences = None

try:
    from src.streamlit.pages.governing_bodies import manage_governing_bodies
except ImportError:
    manage_governing_bodies = None

try:
    from src.streamlit.pages.politicians import manage_politicians
except ImportError:
    manage_politicians = None

try:
    from src.streamlit.pages.parliamentary_groups import manage_parliamentary_groups
except ImportError:
    manage_parliamentary_groups = None

try:
    from src.streamlit.pages.conversations import manage_conversations
except ImportError:
    manage_conversations = None

try:
    from src.streamlit.pages.conversations_speakers import manage_conversations_speakers
except ImportError:
    manage_conversations_speakers = None

try:
    from src.streamlit.pages.processes import execute_processes
except ImportError:
    execute_processes = None


def placeholder_page(title: str):
    """Create a placeholder page for features being migrated.

    Args:
        title: Page title
    """

    def render():
        st.title(title)
        st.info("このページはClean Architectureへの移行中です。")
        st.markdown("""
        ### 移行ステータス
        - 🚧 現在、Clean Architectureパターンへの移行作業中です
        - ✅ 基本機能は引き続き利用可能です
        - 📝 完全移行後、パフォーマンスとメンテナンス性が向上します
        """)

    return render


def main():
    """Main entry point for the Streamlit application."""
    st.set_page_config(
        page_title="Polibase - Political Activity Tracking",
        page_icon="🏛️",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Sidebar navigation
    st.sidebar.title("🏛️ Polibase")
    st.sidebar.markdown("政治活動追跡アプリケーション")
    st.sidebar.divider()

    # Navigation menu
    page = st.sidebar.selectbox(
        "ページ選択",
        [
            "ホーム",
            "会議管理",
            "政党管理",
            "会議体管理",
            "開催主体管理",
            "政治家管理",
            "議員団管理",
            "発言レコード一覧",
            "発言・発言者管理",
            "処理実行",
        ],
    )

    # Route to appropriate page
    if page == "ホーム":
        render_home_page()
    elif page == "会議管理":
        # ✅ Migrated to Clean Architecture
        render_meetings_page()
    elif page == "政党管理":
        # ✅ Migrated to Clean Architecture
        render_political_parties_page()
    elif page == "会議体管理":
        # 🚧 Migration pending - use legacy if available
        if manage_conferences:
            manage_conferences()
        else:
            placeholder_page("会議体管理")()
    elif page == "開催主体管理":
        # 🚧 Migration pending - use legacy if available
        if manage_governing_bodies:
            manage_governing_bodies()
        else:
            placeholder_page("開催主体管理")()
    elif page == "政治家管理":
        # 🚧 Migration pending - use legacy if available
        if manage_politicians:
            manage_politicians()
        else:
            placeholder_page("政治家管理")()
    elif page == "議員団管理":
        # 🚧 Migration pending - use legacy if available
        if manage_parliamentary_groups:
            manage_parliamentary_groups()
        else:
            placeholder_page("議員団管理")()
    elif page == "発言レコード一覧":
        # 🚧 Migration pending - use legacy if available
        if manage_conversations:
            manage_conversations()
        else:
            placeholder_page("発言レコード一覧")()
    elif page == "発言・発言者管理":
        # 🚧 Migration pending - use legacy if available
        if manage_conversations_speakers:
            manage_conversations_speakers()
        else:
            placeholder_page("発言・発言者管理")()
    elif page == "処理実行":
        # 🚧 Migration pending - use legacy if available
        if execute_processes:
            execute_processes()
        else:
            placeholder_page("処理実行")()

    # Footer
    st.sidebar.divider()
    st.sidebar.markdown("""
    ### アーキテクチャ移行状況
    - ✅ 会議管理
    - ✅ 政党管理
    - 🚧 その他のページ（移行中）
    """)
    st.sidebar.caption("© 2024 Polibase - Clean Architecture Edition")


def render_home_page():
    """Render the home page."""
    st.title("🏛️ Polibase")
    st.subheader("政治活動追跡アプリケーション")

    st.markdown("""
    ## Welcome to Polibase

    Polibaseは日本の政治活動を追跡・分析するためのアプリケーションです。

    ### 主な機能

    #### ✅ Clean Architecture対応済み
    - **会議管理**: 議会や委員会の会議情報を管理
    - **政党管理**: 政党情報と議員一覧URLの管理

    #### 🚧 移行作業中
    - **会議体管理**: 議会や委員会などの会議体を管理
    - **開催主体管理**: 国、都道府県、市町村などの開催主体を管理
    - **政治家管理**: 政治家の情報を管理
    - **議員団管理**: 議員団・会派の情報を管理
    - **発言管理**: 会議での発言記録を管理
    - **処理実行**: 各種バッチ処理の実行

    ### アーキテクチャ改善

    現在、Clean Architectureパターンへの移行を進めています：

    - **ドメイン層**: ビジネスエンティティとルール
    - **アプリケーション層**: ユースケースとビジネスロジック
    - **インフラストラクチャ層**: データベースと外部サービス
    - **インターフェース層**: UI（Streamlit）とCLI

    ### 使い方

    左側のサイドバーから管理したい項目を選択してください。
    """)

    # Display architecture diagram
    with st.expander("アーキテクチャ図"):
        st.markdown("""
        ```
        ┌─────────────────────────────────────────────────┐
        │           Interface Layer (Streamlit)            │
        │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
        │  │   View   │ │Presenter │ │   DTO    │        │
        │  └──────────┘ └──────────┘ └──────────┘        │
        └─────────────────────────────────────────────────┘
                              │
        ┌─────────────────────────────────────────────────┐
        │           Application Layer                      │
        │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
        │  │ UseCase  │ │   DTO    │ │ Service  │        │
        │  └──────────┘ └──────────┘ └──────────┘        │
        └─────────────────────────────────────────────────┘
                              │
        ┌─────────────────────────────────────────────────┐
        │             Domain Layer                         │
        │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
        │  │ Entity   │ │Repository│ │  Domain  │        │
        │  │          │ │Interface │ │ Service  │        │
        │  └──────────┘ └──────────┘ └──────────┘        │
        └─────────────────────────────────────────────────┘
                              │
        ┌─────────────────────────────────────────────────┐
        │         Infrastructure Layer                     │
        │  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
        │  │Repository│ │ External │ │    DI    │        │
        │  │   Impl   │ │ Service  │ │Container │        │
        │  └──────────┘ └──────────┘ └──────────┘        │
        └─────────────────────────────────────────────────┘
        ```
        """)

    # Statistics
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("移行完了ページ", "2", "✅")

    with col2:
        st.metric("移行中ページ", "7", "🚧")

    with col3:
        st.metric("進捗率", "22%", "📊")


if __name__ == "__main__":
    main()
