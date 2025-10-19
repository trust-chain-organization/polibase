"""Main Streamlit application using Clean Architecture.

This module provides the main entry point for the Streamlit web interface,
following Clean Architecture principles with presenter pattern.
"""

import streamlit as st

# Import new Clean Architecture views
from src.interfaces.web.streamlit.views.conferences_view import (
    render_conferences_page,
)
from src.interfaces.web.streamlit.views.conversations_speakers_view import (
    render_conversations_speakers_page,
)
from src.interfaces.web.streamlit.views.conversations_view import (
    render_conversations_page,
)
from src.interfaces.web.streamlit.views.governing_bodies_view import (
    render_governing_bodies_page,
)
from src.interfaces.web.streamlit.views.meetings_view import render_meetings_page
from src.interfaces.web.streamlit.views.parliamentary_groups_view import (
    render_parliamentary_groups_page,
)
from src.interfaces.web.streamlit.views.political_parties_view import (
    render_political_parties_page,
)
from src.interfaces.web.streamlit.views.politicians_view import render_politicians_page
from src.interfaces.web.streamlit.views.processes_view import render_processes_page

# Legacy pages have been removed (migrated to Clean Architecture)
# Setting to None to maintain compatibility during full migration
manage_conferences = None
manage_governing_bodies = None
manage_politicians = None
manage_parliamentary_groups = None
manage_conversations = None
manage_conversations_speakers = None
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
        # ✅ Migrated to Clean Architecture
        render_conferences_page()
    elif page == "開催主体管理":
        # ✅ Migrated to Clean Architecture
        render_governing_bodies_page()
    elif page == "政治家管理":
        # ✅ Migrated to Clean Architecture
        render_politicians_page()
    elif page == "議員団管理":
        # ✅ Migrated to Clean Architecture
        render_parliamentary_groups_page()
    elif page == "発言レコード一覧":
        # ✅ Migrated to Clean Architecture
        render_conversations_page()
    elif page == "発言・発言者管理":
        # ✅ Migrated to Clean Architecture
        render_conversations_speakers_page()
    elif page == "処理実行":
        # ✅ Migrated to Clean Architecture
        render_processes_page()

    # Footer
    st.sidebar.divider()
    st.sidebar.markdown("""
    ### アーキテクチャ移行状況
    - ✅ 会議管理
    - ✅ 政党管理
    - ✅ 会議体管理
    - ✅ 開催主体管理
    - ✅ 議員団管理
    - ✅ 政治家管理
    - ✅ 発言・発言者管理
    - ✅ 発言レコード一覧
    - ✅ 処理実行
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
    - **会議体管理**: 議会や委員会などの会議体を管理
    - **開催主体管理**: 国、都道府県、市町村などの開催主体を管理
    - **議員団管理**: 議員団・会派の情報を管理
    - **政治家管理**: 政治家の情報を管理
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
        st.metric("移行完了ページ", "9", "✅")

    with col2:
        st.metric("移行中ページ", "0", "✅")

    with col3:
        st.metric("進捗率", "100%", "🎉")


if __name__ == "__main__":
    main()
