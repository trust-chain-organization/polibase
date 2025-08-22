"""Presenter for meeting management in Streamlit.

This module provides the presenter layer for meeting management,
handling UI state and coordinating with repositories.
"""

from typing import Any

import pandas as pd

from src.common.logging import get_logger
from src.domain.entities.meeting import Meeting
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.dto.base import FormStateDTO, WebResponseDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager
from src.seed_generator import SeedGenerator


class MeetingPresenter(CRUDPresenter[list[Meeting]]):
    """Presenter for meeting management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        self.meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
        self.governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
        self.conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
        self.session = SessionManager(namespace="meeting")
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(self.__class__.__name__)

    def _get_or_create_form_state(self) -> FormStateDTO:
        """Get or create form state from session.

        Returns:
            Form state DTO
        """
        state_dict = self.session.get("form_state", {})
        if not state_dict:
            state = FormStateDTO()
            self.session.set("form_state", state.__dict__)
            return state
        return FormStateDTO(**state_dict)

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("form_state", self.form_state.__dict__)

    async def load_data(self) -> list[Meeting]:
        """Load all meetings.

        Returns:
            List of meetings
        """
        return await self.meeting_repo.get_all()

    async def load_meetings_with_filters(
        self, governing_body_id: int | None = None, conference_id: int | None = None
    ) -> list[dict[str, Any]]:
        """Load meetings with optional filters.

        Args:
            governing_body_id: Optional governing body filter
            conference_id: Optional conference filter

        Returns:
            List of meeting dictionaries with additional info
        """
        # Get all meetings
        meetings = await self.meeting_repo.get_all()

        # Convert to dictionaries with additional info
        result = []
        for meeting in meetings:
            # Get conference and governing body info
            conference = await self.conference_repo.get_by_id(meeting.conference_id)
            if conference:
                governing_body = await self.governing_body_repo.get_by_id(
                    conference.governing_body_id
                )

                # Apply filters
                if (
                    governing_body_id
                    and conference.governing_body_id != governing_body_id
                ):
                    continue
                if conference_id and meeting.conference_id != conference_id:
                    continue

                result.append(
                    {
                        "id": meeting.id,
                        "conference_id": meeting.conference_id,
                        "date": meeting.date,
                        "url": meeting.url,
                        "gcs_pdf_uri": meeting.gcs_pdf_uri,
                        "gcs_text_uri": meeting.gcs_text_uri,
                        "conference_name": conference.name,
                        "governing_body_name": governing_body.name
                        if governing_body
                        else "",
                        "governing_body_type": governing_body.type
                        if governing_body
                        else "",
                    }
                )

        return result

    async def get_governing_bodies(self) -> list[dict[str, Any]]:
        """Get all governing bodies.

        Returns:
            List of governing body dictionaries
        """
        bodies = await self.governing_body_repo.get_all()
        return [
            {
                "id": body.id,
                "name": body.name,
                "type": body.type,
                "display_name": f"{body.name} ({body.type})",
            }
            for body in bodies
        ]

    async def get_conferences_by_governing_body(
        self, governing_body_id: int
    ) -> list[dict[str, Any]]:
        """Get conferences for a specific governing body.

        Args:
            governing_body_id: Governing body ID

        Returns:
            List of conference dictionaries
        """
        conferences = await self.conference_repo.get_by_governing_body(
            governing_body_id
        )
        return [
            {
                "id": conf.id,
                "name": conf.name,
                "governing_body_id": conf.governing_body_id,
            }
            for conf in conferences
        ]

    async def create(self, **kwargs: Any) -> WebResponseDTO[Meeting]:
        """Create a new meeting.

        Args:
            **kwargs: Meeting data (conference_id, date, url)

        Returns:
            Response with created meeting
        """
        try:
            # Validate required fields
            required = ["conference_id", "date", "url"]
            is_valid, error_msg = self.validate_input(kwargs, required)
            if not is_valid:
                return WebResponseDTO.error_response(error_msg)

            # Create meeting entity
            meeting = Meeting(
                id=0,  # Will be assigned by repository
                conference_id=kwargs["conference_id"],
                date=kwargs["date"],
                url=kwargs["url"],
            )

            # Save to repository
            created_meeting = await self.meeting_repo.create(meeting)

            return WebResponseDTO.success_response(
                created_meeting, "会議を登録しました"
            )

        except Exception as e:
            self.logger.error(f"Error creating meeting: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"会議の登録に失敗しました: {str(e)}")

    async def read(self, **kwargs: Any) -> Meeting | None:
        """Read a single meeting.

        Args:
            **kwargs: Must include meeting_id

        Returns:
            Meeting entity or None
        """
        meeting_id = kwargs.get("meeting_id")
        if not meeting_id:
            raise ValueError("meeting_id is required")

        return await self.meeting_repo.get_by_id(meeting_id)

    async def update(self, **kwargs: Any) -> WebResponseDTO[Meeting]:
        """Update a meeting.

        Args:
            **kwargs: Meeting data including meeting_id

        Returns:
            Response with updated meeting
        """
        try:
            meeting_id = kwargs.get("meeting_id")
            if not meeting_id:
                return WebResponseDTO.error_response("meeting_id is required")

            # Get existing meeting
            meeting = await self.meeting_repo.get_by_id(meeting_id)
            if not meeting:
                return WebResponseDTO.error_response(
                    f"会議ID {meeting_id} が見つかりません"
                )

            # Update fields
            if "conference_id" in kwargs:
                meeting.conference_id = kwargs["conference_id"]
            if "date" in kwargs:
                meeting.date = kwargs["date"]
            if "url" in kwargs:
                meeting.url = kwargs["url"]

            # Save to repository
            updated_meeting = await self.meeting_repo.update(meeting)

            return WebResponseDTO.success_response(
                updated_meeting, "会議を更新しました"
            )

        except Exception as e:
            self.logger.error(f"Error updating meeting: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"会議の更新に失敗しました: {str(e)}")

    async def delete(self, **kwargs: Any) -> WebResponseDTO[bool]:
        """Delete a meeting.

        Args:
            **kwargs: Must include meeting_id

        Returns:
            Response with success status
        """
        try:
            meeting_id = kwargs.get("meeting_id")
            if not meeting_id:
                return WebResponseDTO.error_response("meeting_id is required")

            success = await self.meeting_repo.delete(meeting_id)

            if success:
                return WebResponseDTO.success_response(True, "会議を削除しました")
            else:
                return WebResponseDTO.error_response("会議の削除に失敗しました")

        except Exception as e:
            self.logger.error(f"Error deleting meeting: {e}", exc_info=True)
            return WebResponseDTO.error_response(f"会議の削除に失敗しました: {str(e)}")

    async def list(self, **kwargs: Any) -> list[Meeting]:
        """List meetings with optional filters.

        Args:
            **kwargs: Can include governing_body_id, conference_id

        Returns:
            List of meetings
        """
        governing_body_id = kwargs.get("governing_body_id")
        conference_id = kwargs.get("conference_id")

        meetings = await self.load_meetings_with_filters(
            governing_body_id, conference_id
        )

        # Convert back to Meeting entities for consistency
        return [
            Meeting(
                id=m["id"],
                conference_id=m["conference_id"],
                date=m["date"],
                url=m["url"],
                gcs_pdf_uri=m.get("gcs_pdf_uri"),
                gcs_text_uri=m.get("gcs_text_uri"),
            )
            for m in meetings
        ]

    def to_dataframe(self, meetings: list[dict[str, Any]]) -> pd.DataFrame:
        """Convert meetings to DataFrame for display.

        Args:
            meetings: List of meeting dictionaries

        Returns:
            DataFrame for display
        """
        if not meetings:
            return pd.DataFrame(
                columns=["ID", "開催日", "開催主体・会議体", "URL", "GCS"]
            )

        df = pd.DataFrame(meetings)

        # Format date
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=False)
        df["開催日"] = df["date"].dt.strftime("%Y年%m月%d日")

        # Format governing body and conference
        df["開催主体・会議体"] = df.apply(
            lambda row: f"{row['governing_body_name']} - {row['conference_name']}",
            axis=1,
        )

        # Check GCS status
        df["GCS"] = df.apply(
            lambda row: "✓"
            if row.get("gcs_pdf_uri") or row.get("gcs_text_uri")
            else "",
            axis=1,
        )

        # Select columns for display
        return df[["id", "開催日", "開催主体・会議体", "url", "GCS"]].rename(
            columns={"id": "ID", "url": "URL"}
        )

    async def generate_seed_file(self) -> WebResponseDTO[str]:
        """Generate seed file for meetings.

        Returns:
            Response with seed file content
        """
        try:
            generator = SeedGenerator()
            content = generator.generate_meetings_seed()

            return WebResponseDTO.success_response(
                content, "SEEDファイルを生成しました"
            )

        except Exception as e:
            self.logger.error(f"Error generating seed file: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"SEEDファイル生成に失敗しました: {str(e)}"
            )

    def set_editing_mode(self, meeting_id: int) -> None:
        """Set form to editing mode for a specific meeting.

        Args:
            meeting_id: ID of the meeting to edit
        """
        self.form_state.set_editing(meeting_id)
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.form_state.reset()
        self._save_form_state()

    def is_editing(self, meeting_id: int | None = None) -> bool:
        """Check if in editing mode.

        Args:
            meeting_id: Optional specific meeting ID to check

        Returns:
            True if in editing mode
        """
        if meeting_id:
            return (
                self.form_state.is_editing and self.form_state.current_id == meeting_id
            )
        return self.form_state.is_editing
