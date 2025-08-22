"""Presenter for conference management in Streamlit.

This module provides the presenter layer for conference management,
handling UI state and coordinating with repositories.
"""

from typing import Any

import pandas as pd

from src.common.logging import get_logger
from src.domain.entities.conference import Conference
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.dto.base import FormStateDTO, WebResponseDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager
from src.seed_generator import SeedGenerator


class ConferencePresenter(CRUDPresenter[list[Conference]]):
    """Presenter for conference management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        self.conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
        self.governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
        self.session = SessionManager(namespace="conference")
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

    async def load_data(self) -> list[Conference]:
        """Load all conferences.

        Returns:
            List of conferences
        """
        return await self.conference_repo.get_all()

    async def load_conferences_with_governing_bodies(self) -> list[dict[str, Any]]:
        """Load conferences with governing body information.

        Returns:
            List of conference dictionaries with additional info
        """
        conferences = await self.conference_repo.get_all()
        result = []

        for conf in conferences:
            governing_body = await self.governing_body_repo.get_by_id(
                conf.governing_body_id
            )

            result.append(
                {
                    "id": conf.id,
                    "name": conf.name,
                    "governing_body_id": conf.governing_body_id,
                    "governing_body_name": governing_body.name
                    if governing_body
                    else "",
                    "governing_body_type": governing_body.type
                    if governing_body
                    else "",
                    "members_introduction_url": conf.members_introduction_url,
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

    async def create(self, **kwargs: Any) -> WebResponseDTO[Conference]:
        """Create a new conference.

        Args:
            **kwargs: Conference data (name, governing_body_id,
                members_introduction_url)

        Returns:
            Response with created conference
        """
        try:
            # Validate required fields
            required = ["name", "governing_body_id"]
            is_valid, error_msg = self.validate_input(kwargs, required)
            if not is_valid:
                return WebResponseDTO.error_response(error_msg)

            # Create conference entity
            conference = Conference(
                id=0,  # Will be assigned by repository
                name=kwargs["name"],
                governing_body_id=kwargs["governing_body_id"],
                members_introduction_url=kwargs.get("members_introduction_url"),
            )

            # Save to repository
            created_conference = await self.conference_repo.create(conference)

            return WebResponseDTO.success_response(
                created_conference, "会議体を登録しました"
            )

        except Exception as e:
            self.logger.error(f"Error creating conference: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"会議体の登録に失敗しました: {str(e)}"
            )

    async def read(self, **kwargs: Any) -> Conference | None:
        """Read a single conference.

        Args:
            **kwargs: Must include conference_id

        Returns:
            Conference entity or None
        """
        conference_id = kwargs.get("conference_id")
        if not conference_id:
            raise ValueError("conference_id is required")

        return await self.conference_repo.get_by_id(conference_id)

    async def update(self, **kwargs: Any) -> WebResponseDTO[Conference]:
        """Update a conference.

        Args:
            **kwargs: Conference data including conference_id

        Returns:
            Response with updated conference
        """
        try:
            conference_id = kwargs.get("conference_id")
            if not conference_id:
                return WebResponseDTO.error_response("conference_id is required")

            # Get existing conference
            conference = await self.conference_repo.get_by_id(conference_id)
            if not conference:
                return WebResponseDTO.error_response(
                    f"会議体ID {conference_id} が見つかりません"
                )

            # Update fields
            if "name" in kwargs:
                conference.name = kwargs["name"]
            if "governing_body_id" in kwargs:
                conference.governing_body_id = kwargs["governing_body_id"]
            if "members_introduction_url" in kwargs:
                conference.members_introduction_url = kwargs["members_introduction_url"]

            # Save to repository
            updated_conference = await self.conference_repo.update(conference)

            return WebResponseDTO.success_response(
                updated_conference, "会議体を更新しました"
            )

        except Exception as e:
            self.logger.error(f"Error updating conference: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"会議体の更新に失敗しました: {str(e)}"
            )

    async def delete(self, **kwargs: Any) -> WebResponseDTO[bool]:
        """Delete a conference.

        Args:
            **kwargs: Must include conference_id

        Returns:
            Response with success status
        """
        try:
            conference_id = kwargs.get("conference_id")
            if not conference_id:
                return WebResponseDTO.error_response("conference_id is required")

            success = await self.conference_repo.delete(conference_id)

            if success:
                return WebResponseDTO.success_response(True, "会議体を削除しました")
            else:
                return WebResponseDTO.error_response("会議体の削除に失敗しました")

        except Exception as e:
            self.logger.error(f"Error deleting conference: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"会議体の削除に失敗しました: {str(e)}"
            )

    async def list(self, **kwargs: Any) -> list[Conference]:
        """List conferences with optional filters.

        Args:
            **kwargs: Can include governing_body_id

        Returns:
            List of conferences
        """
        governing_body_id = kwargs.get("governing_body_id")

        if governing_body_id:
            return await self.conference_repo.get_by_governing_body(governing_body_id)
        else:
            return await self.conference_repo.get_all()

    def to_dataframe(self, conferences: list[dict[str, Any]]) -> pd.DataFrame:
        """Convert conferences to DataFrame for display.

        Args:
            conferences: List of conference dictionaries

        Returns:
            DataFrame for display
        """
        if not conferences:
            return pd.DataFrame(columns=["ID", "会議体名", "開催主体", "議員紹介URL"])

        data = []
        for conf in conferences:
            data.append(
                {
                    "ID": conf["id"],
                    "会議体名": conf["name"],
                    "開催主体": (
                        f"{conf['governing_body_name']} ({conf['governing_body_type']})"
                    ),
                    "議員紹介URL": conf.get("members_introduction_url") or "未設定",
                }
            )

        return pd.DataFrame(data)

    async def generate_seed_file(self) -> WebResponseDTO[str]:
        """Generate seed file for conferences.

        Returns:
            Response with seed file content
        """
        try:
            generator = SeedGenerator()
            content = generator.generate_conferences_seed()

            return WebResponseDTO.success_response(
                content, "SEEDファイルを生成しました"
            )

        except Exception as e:
            self.logger.error(f"Error generating seed file: {e}", exc_info=True)
            return WebResponseDTO.error_response(
                f"SEEDファイル生成に失敗しました: {str(e)}"
            )

    def set_editing_mode(self, conference_id: int) -> None:
        """Set form to editing mode for a specific conference.

        Args:
            conference_id: ID of the conference to edit
        """
        self.form_state.set_editing(conference_id)
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.form_state.reset()
        self._save_form_state()

    def is_editing(self, conference_id: int | None = None) -> bool:
        """Check if in editing mode.

        Args:
            conference_id: Optional specific conference ID to check

        Returns:
            True if in editing mode
        """
        if conference_id:
            return (
                self.form_state.is_editing
                and self.form_state.current_id == conference_id
            )
        return self.form_state.is_editing

    def get_statistics(self, conferences: list[dict[str, Any]]) -> dict[str, Any]:
        """Get statistics about conferences.

        Args:
            conferences: List of conference dictionaries

        Returns:
            Statistics dictionary
        """
        total = len(conferences)
        with_url = sum(1 for c in conferences if c.get("members_introduction_url"))
        without_url = total - with_url

        return {
            "total": total,
            "with_url": with_url,
            "without_url": without_url,
            "with_url_percentage": (with_url / total * 100) if total > 0 else 0,
        }
