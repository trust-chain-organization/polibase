"""Tests for Streamlit app components"""

from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd


class TestStreamlitAppComponents:
    """Test cases for Streamlit app components"""

    @patch("src.streamlit.pages.meetings.RepositoryAdapter")
    @patch("src.streamlit.pages.meetings.st")
    def test_show_meetings_list_no_meetings(self, mock_st, mock_repo_class):
        """Test showing meetings list when no meetings exist"""
        # Create separate mocks for each repository type
        mock_meeting_repo = MagicMock()
        mock_gb_repo = MagicMock()
        mock_conf_repo = MagicMock()

        # Set up RepositoryAdapter to return different mocks
        mock_repo_class.side_effect = [mock_meeting_repo, mock_gb_repo, mock_conf_repo]

        # Mock repository methods
        mock_meeting_repo.get_meetings.return_value = []
        mock_gb_repo.get_all.return_value = []  # For governing bodies
        mock_conf_repo.get_all.return_value = []  # For conferences

        # Mock streamlit
        mock_st.columns.return_value = [MagicMock(), MagicMock()]
        mock_st.selectbox.return_value = "すべて"

        # Import and call function
        from src.streamlit.pages.meetings import show_meetings_list

        show_meetings_list()

        # Verify
        mock_st.info.assert_called_with("会議が登録されていません")
        # The function creates 3 repository adapters
        assert mock_repo_class.call_count == 3
        # Each repository adapter should be closed
        mock_meeting_repo.close.assert_called_once()
        mock_gb_repo.close.assert_called_once()
        mock_conf_repo.close.assert_called_once()

    @patch("src.streamlit.pages.meetings.RepositoryAdapter")
    @patch("src.streamlit.pages.meetings.st")
    @patch("src.streamlit.pages.meetings.pd")
    def test_show_meetings_list_with_meetings(self, mock_pd, mock_st, mock_repo_class):
        """Test showing meetings list with meetings"""
        # Create separate mocks for each repository type
        mock_meeting_repo = MagicMock()
        mock_gb_repo = MagicMock()
        mock_conf_repo = MagicMock()

        # Set up RepositoryAdapter to return different mocks
        mock_repo_class.side_effect = [mock_meeting_repo, mock_gb_repo, mock_conf_repo]

        # Mock governing bodies (returns entity objects)
        mock_gb = MagicMock()
        mock_gb.id = 1
        mock_gb.name = "日本国"
        mock_gb.type = "国"
        mock_gb_repo.get_all.return_value = [mock_gb]

        # Mock conferences
        mock_conf = MagicMock()
        mock_conf.id = 1
        mock_conf.name = "本会議"
        mock_conf.governing_body_id = 1
        mock_conf_repo.get_all.return_value = [mock_conf]

        # Mock meetings
        mock_meeting = MagicMock()
        mock_meeting.id = 1
        mock_meeting.date = date(2024, 6, 1)
        mock_meeting.url = "https://example.com/meeting.pdf"
        mock_meeting_repo.get_all.return_value = [mock_meeting]
        mock_meeting_repo.get_meetings.return_value = [
            {
                "id": 1,
                "date": date(2024, 6, 1),
                "url": "https://example.com/meeting.pdf",
                "conference_name": "本会議",
                "governing_body_name": "日本国",
            }
        ]

        # Mock pandas DataFrame with proper column access
        mock_df = MagicMock()
        mock_df.__getitem__ = MagicMock(side_effect=lambda key: mock_df)
        mock_df.dt = MagicMock()
        mock_df.dt.strftime = MagicMock(return_value=pd.Series(["2024年06月01日"]))
        mock_df.sort_values = MagicMock(return_value=mock_df)
        mock_df.iterrows = MagicMock(
            return_value=[
                (
                    0,
                    {
                        "id": 1,
                        "開催日": "2024年06月01日",
                        "開催主体・会議体": "日本国 - 本会議",
                        "url": "https://example.com/meeting.pdf",
                    },
                )
            ]
        )
        mock_pd.DataFrame.return_value = mock_df
        mock_pd.to_datetime.return_value = pd.Series([date(2024, 6, 1)])

        # Mock streamlit columns for the iterrows loop
        mock_col1 = MagicMock()
        mock_col2 = MagicMock()
        mock_col3 = MagicMock()
        # We need 3 calls to columns in show_meetings_list
        mock_st.columns.side_effect = [
            [
                MagicMock(),
                MagicMock(),
            ],  # First call for filter columns (col1, col2 = st.columns(2))
            [
                MagicMock(),
                MagicMock(),
            ],  # Second call for SEED generation (col1, col2 = st.columns([3, 1]))
            [
                mock_col1,
                mock_col2,
                mock_col3,
            ],  # Third call for row display (col1, col2, col3 = st.columns([6, 1, 1]))
        ]
        mock_st.selectbox.side_effect = ["日本国 (国)", "本会議"]
        mock_st.button.return_value = False
        mock_st.markdown = MagicMock()
        mock_st.divider = MagicMock()

        # Import and call function
        from src.streamlit.pages.meetings import show_meetings_list

        show_meetings_list()

        # Verify
        mock_gb_repo.get_all.assert_called()
        # The function creates 3 repository adapters
        assert mock_repo_class.call_count == 3
        # Each repository adapter should be closed
        mock_meeting_repo.close.assert_called_once()
        mock_gb_repo.close.assert_called_once()
        mock_conf_repo.close.assert_called_once()
        # Check that columns were created for display
        assert mock_st.columns.call_count >= 1  # At least for filters

    @patch("src.streamlit.pages.meetings.RepositoryAdapter")
    @patch("src.streamlit.pages.meetings.st")
    def test_add_new_meeting_no_governing_bodies(self, mock_st, mock_repo_class):
        """Test adding new meeting when no governing bodies exist"""
        # Mock repository
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_all.return_value = []  # For governing bodies

        # Import and call function
        from src.streamlit.pages.meetings import add_new_meeting

        add_new_meeting()

        # Verify
        mock_st.error.assert_called_with(
            "開催主体が登録されていません。先にマスターデータを登録してください。"
        )
        # The function creates 3 repository adapters
        assert mock_repo_class.call_count == 3
        # Each repository should be closed
        assert mock_repo.close.call_count == 3

    def test_add_new_meeting_form_display(self):
        """Test that add_new_meeting form displays correctly"""
        with patch("src.streamlit.pages.meetings.RepositoryAdapter") as mock_repo_class:
            with patch("src.streamlit.pages.meetings.st") as mock_st:
                with patch("src.streamlit.pages.meetings.pd") as mock_pd:
                    # Create separate mocks for each repository type
                    mock_meeting_repo = MagicMock()
                    mock_gb_repo = MagicMock()
                    mock_conf_repo = MagicMock()

                    # Set up RepositoryAdapter to return different mocks
                    mock_repo_class.side_effect = [
                        mock_meeting_repo,
                        mock_gb_repo,
                        mock_conf_repo,
                    ]

                    # Mock governing bodies
                    mock_gb = MagicMock()
                    mock_gb.id = 1
                    mock_gb.name = "日本国"
                    mock_gb.type = "国"
                    mock_gb_repo.get_all.return_value = [mock_gb]

                    # Mock conferences
                    mock_conf = MagicMock()
                    mock_conf.id = 1
                    mock_conf.name = "本会議"
                    mock_conf.governing_body_id = 1
                    mock_conf_repo.get_all.return_value = [mock_conf]

                    # Mock pandas DataFrame for expander
                    mock_df = MagicMock()
                    mock_df.__getitem__ = MagicMock(side_effect=lambda key: mock_df)
                    mock_df.unique.return_value = ["日本国"]
                    mock_df.copy.return_value = mock_df
                    mock_df.columns = ["会議体名", "会議体種別"]
                    mock_pd.DataFrame.return_value = mock_df

                    # Mock streamlit components
                    # Now selectboxes are outside form, so they'll be called before form
                    mock_st.selectbox.side_effect = ["日本国 (国)", "本会議"]
                    mock_st.form_submit_button.return_value = False  # No submission
                    mock_st.info = MagicMock()  # Mock info display in form

                    # Mock form and expander contexts
                    mock_st.form.return_value.__enter__ = MagicMock()
                    mock_st.form.return_value.__exit__ = MagicMock()
                    mock_st.expander.return_value.__enter__ = MagicMock()
                    mock_st.expander.return_value.__exit__ = MagicMock()

                    # Import and call function
                    from src.streamlit.pages.meetings import add_new_meeting

                    add_new_meeting()

                    # Verify selectboxes were called
                    assert mock_st.selectbox.call_count >= 2

                    # Verify form components were created
                    mock_st.form.assert_called_once_with("new_meeting_form")
                    mock_st.date_input.assert_called_once()
                    mock_st.text_input.assert_called_once()
                    mock_st.form_submit_button.assert_called_once()
                    # The function creates 3 repository adapters
                    assert mock_repo_class.call_count == 3
                    # Each repository should be closed
                    mock_meeting_repo.close.assert_called_once()
                    mock_gb_repo.close.assert_called_once()
                    mock_conf_repo.close.assert_called_once()

    def test_meeting_repository_integration(self):
        """Test that MeetingRepository is created and closed properly"""
        with patch("src.streamlit.pages.meetings.RepositoryAdapter") as mock_repo_class:
            with patch("src.streamlit.pages.meetings.st") as mock_st:
                with patch("src.streamlit.pages.meetings.pd"):
                    # Mock repository
                    mock_repo = MagicMock()
                    mock_repo_class.return_value = mock_repo
                    mock_repo.get_governing_bodies.return_value = []

                    # Mock streamlit form
                    mock_st.form.return_value.__enter__ = MagicMock()
                    mock_st.form.return_value.__exit__ = MagicMock()

                    # Import and call function
                    from src.streamlit.pages.meetings import add_new_meeting

                    add_new_meeting()

                    # Verify repository lifecycle
                    # The function creates 3 repository adapters (meeting, governing_body, conference)
                    assert mock_repo_class.call_count == 3
                    # Each repository should be closed
                    assert mock_repo.close.call_count == 3

    @patch("src.streamlit.pages.meetings.st")
    def test_edit_meeting_no_selection(self, mock_st):
        """Test edit meeting when no meeting is selected"""
        # Mock session state
        mock_st.session_state.edit_mode = False
        mock_st.session_state.edit_meeting_id = None

        # Import and call function
        from src.streamlit.pages.meetings import edit_meeting

        edit_meeting()

        # Verify
        mock_st.info.assert_called_with(
            "編集する会議を選択してください（会議一覧タブから編集ボタンをクリック）"
        )

    @patch("src.streamlit.pages.meetings.RepositoryAdapter")
    @patch("src.streamlit.pages.meetings.st")
    def test_get_all_conferences_display(self, mock_st, mock_repo_class):
        """Test displaying all conferences"""
        # Mock repository
        mock_repo = MagicMock()
        mock_repo_class.return_value = mock_repo
        mock_repo.get_all_conferences.return_value = [
            {
                "id": 1,
                "name": "本会議",
                "type": "議院",
                "governing_body_id": 1,
                "governing_body_name": "日本国",
                "governing_body_type": "国",
            },
            {
                "id": 2,
                "name": "市議会",
                "type": "地方議会全体",
                "governing_body_id": 2,
                "governing_body_name": "京都市",
                "governing_body_type": "市町村",
            },
        ]

        # Verify that get_all_conferences returns proper format
        conferences = mock_repo.get_all_conferences()
        assert len(conferences) == 2
        assert conferences[0]["governing_body_name"] == "日本国"
        assert conferences[1]["name"] == "市議会"
