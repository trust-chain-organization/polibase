"""View for meeting management in Streamlit.

This module provides the UI layer for meeting management,
using the presenter pattern for business logic.
"""

import asyncio
from datetime import date
from typing import Any

import streamlit as st
from src.interfaces.web.streamlit.presenters.meeting_presenter import MeetingPresenter
from src.interfaces.web.streamlit.utils.error_handler import handle_ui_error


def render_meetings_page():
    """Render the meetings management page."""
    st.title("会議管理")
    st.markdown("会議情報の登録・編集・削除を行います。")

    # Initialize presenter
    presenter = MeetingPresenter()

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["会議一覧", "新規登録", "SEEDファイル生成"])

    with tab1:
        render_meetings_list_tab(presenter)

    with tab2:
        render_new_meeting_tab(presenter)

    with tab3:
        render_seed_generation_tab(presenter)


def render_meetings_list_tab(presenter: MeetingPresenter):
    """Render the meetings list tab.

    Args:
        presenter: Meeting presenter
    """
    st.subheader("会議一覧")

    # Filter section
    col1, col2, col3 = st.columns([2, 2, 1])

    # Load governing bodies for filter
    try:
        governing_bodies = presenter.get_governing_bodies()

        with col1:
            gb_options = ["すべて"] + [gb["display_name"] for gb in governing_bodies]
            selected_gb = st.selectbox("開催主体", options=gb_options, index=0)

        # Get selected governing body ID
        selected_gb_id = None
        if selected_gb != "すべて":
            for gb in governing_bodies:
                if gb["display_name"] == selected_gb:
                    selected_gb_id = gb["id"]
                    break

        # Load conferences based on governing body
        conferences = []
        if selected_gb_id:
            conferences = presenter.get_conferences_by_governing_body(selected_gb_id)

        with col2:
            if conferences:
                conf_options = ["すべて"] + [conf["name"] for conf in conferences]
                selected_conf = st.selectbox("会議体", options=conf_options, index=0)

                # Get selected conference ID
                selected_conf_id = None
                if selected_conf != "すべて":
                    for conf in conferences:
                        if conf["name"] == selected_conf:
                            selected_conf_id = conf["id"]
                            break
            else:
                st.selectbox("会議体", options=["すべて"], disabled=True)
                selected_conf_id = None

        with col3:
            if st.button("検索", type="primary"):
                st.rerun()

        # Load and display meetings
        meetings = presenter.load_meetings_with_filters(
            selected_gb_id, selected_conf_id
        )

        if meetings:
            # Convert to DataFrame for display
            df = presenter.to_dataframe(meetings)

            # Display as table with actions
            for idx, (_, row) in enumerate(df.iterrows()):
                render_meeting_row(presenter, row, meetings[idx])
        else:
            st.info("表示する会議がありません。")

    except Exception as e:
        handle_ui_error(e, "会議一覧の読み込み")


def render_meeting_row(
    presenter: MeetingPresenter, display_row: Any, meeting_data: dict[str, Any]
):
    """Render a single meeting row with actions.

    Args:
        presenter: Meeting presenter
        display_row: DataFrame row for display
        meeting_data: Original meeting data dictionary
    """
    col1, col2, col3, col4, col5, col6 = st.columns([1, 2, 3, 3, 1, 2])

    with col1:
        st.text(str(display_row["ID"]))

    with col2:
        st.text(display_row["開催日"])

    with col3:
        st.text(display_row["開催主体・会議体"])

    with col4:
        if display_row["URL"]:
            st.markdown(f"[{display_row['URL'][:50]}...]({display_row['URL']})")
        else:
            st.text("URLなし")

    with col5:
        st.text(display_row["GCS"])

    with col6:
        col_edit, col_delete = st.columns(2)

        with col_edit:
            if st.button("編集", key=f"edit_{display_row['ID']}"):
                presenter.set_editing_mode(display_row["ID"])
                st.rerun()

        with col_delete:
            if st.button("削除", key=f"delete_{display_row['ID']}", type="secondary"):
                if st.checkbox(
                    "本当に削除しますか？", key=f"confirm_delete_{display_row['ID']}"
                ):
                    delete_meeting(presenter, display_row["ID"])

    # Show edit form if this meeting is being edited
    if presenter.is_editing(display_row["ID"]):
        render_edit_form(presenter, meeting_data)


def render_edit_form(presenter: MeetingPresenter, meeting_data: dict[str, Any]):
    """Render the edit form for a meeting.

    Args:
        presenter: Meeting presenter
        meeting_data: Meeting data dictionary
    """
    with st.form(f"edit_form_{meeting_data['id']}"):
        st.subheader("会議を編集")

        # Load governing bodies and conferences for dropdowns
        governing_bodies = presenter.get_governing_bodies()

        # Find current governing body
        current_gb_id = None
        for gb in governing_bodies:
            conferences = presenter.get_conferences_by_governing_body(gb["id"])
            if any(c["id"] == meeting_data["conference_id"] for c in conferences):
                current_gb_id = gb["id"]
                break

        # Governing body selection
        gb_index = 0
        if current_gb_id:
            for i, gb in enumerate(governing_bodies):
                if gb["id"] == current_gb_id:
                    gb_index = i
                    break

        selected_gb = st.selectbox(
            "開催主体",
            options=governing_bodies,
            format_func=lambda x: x["display_name"],
            index=gb_index,
        )

        # Conference selection based on governing body
        conferences = presenter.get_conferences_by_governing_body(selected_gb["id"])

        conf_index = 0
        for i, conf in enumerate(conferences):
            if conf["id"] == meeting_data["conference_id"]:
                conf_index = i
                break

        selected_conf = st.selectbox(
            "会議体",
            options=conferences,
            format_func=lambda x: x["name"],
            index=conf_index,
        )

        # Date input
        meeting_date = st.date_input(
            "開催日",
            value=meeting_data["date"] if meeting_data["date"] else date.today(),
        )

        # URL input
        url = st.text_input("URL", value=meeting_data["url"] or "")

        # Form buttons
        col1, col2 = st.columns(2)

        with col1:
            if st.form_submit_button("更新", type="primary"):
                update_meeting(
                    presenter,
                    meeting_data["id"],
                    selected_conf["id"],
                    meeting_date,
                    url,
                )

        with col2:
            if st.form_submit_button("キャンセル"):
                presenter.cancel_editing()
                st.rerun()


def render_new_meeting_tab(presenter: MeetingPresenter):
    """Render the new meeting registration tab.

    Args:
        presenter: Meeting presenter
    """
    st.subheader("新規会議登録")

    with st.form("new_meeting_form"):
        # Load governing bodies
        governing_bodies = presenter.get_governing_bodies()

        if not governing_bodies:
            st.error("開催主体が登録されていません。")
            return

        # Governing body selection
        selected_gb = st.selectbox(
            "開催主体",
            options=governing_bodies,
            format_func=lambda x: x["display_name"],
        )

        # Conference selection based on governing body
        conferences = []
        if selected_gb:
            conferences = presenter.get_conferences_by_governing_body(selected_gb["id"])

        if not conferences:
            st.error("選択した開催主体に会議体が登録されていません。")
            selected_conf = None
        else:
            selected_conf = st.selectbox(
                "会議体", options=conferences, format_func=lambda x: x["name"]
            )

        # Date input
        meeting_date = st.date_input("開催日", value=date.today())

        # URL input
        url = st.text_input("URL", placeholder="https://example.com/meeting/...")

        # Submit button
        if st.form_submit_button("登録", type="primary"):
            if selected_conf and url:
                create_meeting(presenter, selected_conf["id"], meeting_date, url)
            else:
                st.error("すべての必須フィールドを入力してください。")


def render_seed_generation_tab(presenter: MeetingPresenter):
    """Render the seed file generation tab.

    Args:
        presenter: Meeting presenter
    """
    st.subheader("SEEDファイル生成")
    st.markdown("""
    現在のデータベースの会議情報からSEEDファイルを生成します。
    生成されたファイルは `database/seeds/` ディレクトリに保存されます。
    """)

    if st.button("SEEDファイルを生成", type="primary"):
        with st.spinner("生成中..."):
            try:
                result = presenter.generate_seed_file()

                if result.success:
                    st.success(result.message)

                    # Display the generated content
                    if result.data:
                        st.subheader("生成されたSEEDファイル")
                        st.code(result.data, language="sql")

                        # Download button
                        st.download_button(
                            label="ダウンロード",
                            data=result.data,
                            file_name="03_meetings.sql",
                            mime="text/plain",
                        )
                else:
                    st.error(result.message)

            except Exception as e:
                handle_ui_error(e, "SEEDファイル生成")


def create_meeting(
    presenter: MeetingPresenter, conference_id: int, meeting_date: date, url: str
):
    """Create a new meeting.

    Args:
        presenter: Meeting presenter
        conference_id: Conference ID
        meeting_date: Meeting date
        url: Meeting URL
    """
    try:
        result = asyncio.run(
            presenter.create(conference_id=conference_id, date=meeting_date, url=url)
        )

        if result.success:
            st.success(result.message)
            st.balloons()
            # Clear form by rerunning
            st.rerun()
        else:
            st.error(result.message)

    except Exception as e:
        handle_ui_error(e, "会議の登録")


def update_meeting(
    presenter: MeetingPresenter,
    meeting_id: int,
    conference_id: int,
    meeting_date: date,
    url: str,
):
    """Update an existing meeting.

    Args:
        presenter: Meeting presenter
        meeting_id: Meeting ID
        conference_id: Conference ID
        meeting_date: Meeting date
        url: Meeting URL
    """
    try:
        result = asyncio.run(
            presenter.update(
                meeting_id=meeting_id,
                conference_id=conference_id,
                date=meeting_date,
                url=url,
            )
        )

        if result.success:
            st.success(result.message)
            presenter.cancel_editing()
            st.rerun()
        else:
            st.error(result.message)

    except Exception as e:
        handle_ui_error(e, "会議の更新")


def delete_meeting(presenter: MeetingPresenter, meeting_id: int):
    """Delete a meeting.

    Args:
        presenter: Meeting presenter
        meeting_id: Meeting ID
    """
    try:
        result = asyncio.run(presenter.delete(meeting_id=meeting_id))

        if result.success:
            st.success(result.message)
            st.rerun()
        else:
            st.error(result.message)

    except Exception as e:
        handle_ui_error(e, "会議の削除")


# For backward compatibility with existing app.py
def main():
    """Main entry point for the meetings page."""
    render_meetings_page()


if __name__ == "__main__":
    main()
