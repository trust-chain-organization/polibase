"""View for political party management in Streamlit.

This module provides the UI layer for political party management,
using the presenter pattern for business logic.
"""

import asyncio

import streamlit as st
from src.interfaces.web.streamlit.presenters.political_party_presenter import (
    PoliticalPartyPresenter,
)
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_political_parties_page():
    """Render the political parties management page."""
    st.title("政党管理")
    st.markdown("政党の議員一覧URLを管理します。")

    # Initialize presenter
    presenter = PoliticalPartyPresenter()

    # Create tabs
    tab1, tab2 = st.tabs(["政党一覧", "SEEDファイル生成"])

    with tab1:
        render_parties_list_tab(presenter)

    with tab2:
        render_seed_generation_tab(presenter)


def render_parties_list_tab(presenter: PoliticalPartyPresenter):
    """Render the parties list tab.

    Args:
        presenter: Political party presenter
    """
    # Filter section
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        filter_options = {
            "すべて": "all",
            "URL設定済み": "with_url",
            "URL未設定": "without_url",
        }
        selected_filter = st.selectbox(
            "表示フィルター", options=list(filter_options.keys()), index=0
        )
        filter_type = filter_options[selected_filter]

    # Load data
    try:
        # Run async function
        result = asyncio.run(presenter.load_data(filter_type))

        # Display statistics
        with col2:
            st.metric("全政党数", result.statistics.total)

        with col3:
            st.metric(
                "URL設定率",
                f"{result.statistics.with_url_percentage:.1f}%",
                f"{result.statistics.with_url}/{result.statistics.total}",
            )

        # Display parties table
        if result.parties:
            st.subheader("政党一覧")

            # Create editable table
            for party in result.parties:
                render_party_row(presenter, party)
        else:
            st.info("表示する政党がありません。")

    except Exception as e:
        handle_ui_error(e, "政党一覧の読み込み")


def render_party_row(presenter: PoliticalPartyPresenter, party):
    """Render a single party row with edit capability.

    Args:
        presenter: Political party presenter
        party: Political party entity
    """
    col1, col2, col3, col4 = st.columns([1, 2, 3, 1])

    with col1:
        st.text(str(party.id))

    with col2:
        st.text(party.name)

    with col3:
        if presenter.is_editing(party.id):
            # Edit mode
            new_url = st.text_input(
                "URL",
                value=party.members_list_url or "",
                key=f"edit_url_{party.id}",
                label_visibility="collapsed",
            )
        else:
            # Display mode
            if party.members_list_url:
                st.markdown(f"[{party.members_list_url}]({party.members_list_url})")
            else:
                st.text("未設定")

    with col4:
        if presenter.is_editing(party.id):
            # Edit mode buttons
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.button("保存", key=f"save_{party.id}"):
                    save_party_url(presenter, party.id, new_url)
            with col_cancel:
                if st.button("キャンセル", key=f"cancel_{party.id}"):
                    presenter.cancel_editing()
                    st.rerun()
        else:
            # Edit button
            if st.button("編集", key=f"edit_{party.id}"):
                presenter.set_editing_mode(party.id)
                st.rerun()


def save_party_url(presenter: PoliticalPartyPresenter, party_id: int, url: str):
    """Save political party URL.

    Args:
        presenter: Political party presenter
        party_id: Party ID
        url: New URL value
    """
    try:
        # Clean up the URL (empty string becomes None)
        url = url.strip() if url else None

        # Update the URL
        result = asyncio.run(presenter.update(party_id=party_id, members_list_url=url))

        if result.success:
            st.success(result.message)
            presenter.cancel_editing()
            st.rerun()
        else:
            st.error(result.message)

    except Exception as e:
        handle_ui_error(e, "URLの更新")


def render_seed_generation_tab(presenter: PoliticalPartyPresenter):
    """Render the seed file generation tab.

    Args:
        presenter: Political party presenter
    """
    st.subheader("SEEDファイル生成")
    st.markdown("""
    現在のデータベースの政党情報からSEEDファイルを生成します。
    生成されたファイルは `database/seeds/` ディレクトリに保存されます。
    """)

    if st.button("SEEDファイルを生成", type="primary"):
        with st.spinner("生成中..."):
            try:
                result = asyncio.run(presenter.generate_seed_file())

                if result.success:
                    st.success(result.message)

                    # Display the generated content
                    if result.content:
                        st.subheader("生成されたSEEDファイル")
                        st.code(result.content, language="sql")

                        # Download button
                        st.download_button(
                            label="ダウンロード",
                            data=result.content,
                            file_name="01_political_parties.sql",
                            mime="text/plain",
                        )
                else:
                    st.error(result.message)

            except Exception as e:
                handle_ui_error(e, "SEEDファイル生成")


# For backward compatibility with existing app.py
def main():
    """Main entry point for the political parties page."""
    render_political_parties_page()


if __name__ == "__main__":
    main()
