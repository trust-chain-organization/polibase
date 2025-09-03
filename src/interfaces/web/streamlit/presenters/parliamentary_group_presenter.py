"""Presenter for parliamentary group management."""

from datetime import date
from typing import Any

import pandas as pd

from src.application.usecases.manage_parliamentary_groups_usecase import (
    CreateParliamentaryGroupInputDto,
    DeleteParliamentaryGroupInputDto,
    ExtractMembersInputDto,
    ManageParliamentaryGroupsUseCase,
    ParliamentaryGroupListInputDto,
    UpdateParliamentaryGroupInputDto,
)
from src.common.logging import get_logger
from src.domain.entities import Conference, ParliamentaryGroup
from src.infrastructure.di.container import Container
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ParliamentaryGroupPresenter(BasePresenter[list[ParliamentaryGroup]]):
    """Presenter for parliamentary group management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)
        # Initialize repositories and use case
        self.parliamentary_group_repo = RepositoryAdapter(
            ParliamentaryGroupRepositoryImpl
        )
        self.conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
        self.membership_repo = RepositoryAdapter(
            ParliamentaryGroupMembershipRepositoryImpl
        )
        self.extracted_member_repo = RepositoryAdapter(
            ExtractedParliamentaryGroupMemberRepositoryImpl
        )
        self.llm_service = GeminiLLMService()

        # Initialize use case with all required dependencies
        self.use_case = ManageParliamentaryGroupsUseCase(
            parliamentary_group_repository=self.parliamentary_group_repo,
            politician_repository=self.politician_repo,
            membership_repository=self.membership_repo,
            llm_service=self.llm_service,
            extracted_member_repository=self.extracted_member_repo,
        )
        self.session = SessionManager()
        self.form_state = self._get_or_create_form_state()
        self.logger = get_logger(__name__)

    def _get_or_create_form_state(self) -> dict[str, Any]:
        """Get or create form state in session."""
        default_state = {
            "editing_mode": None,
            "editing_id": None,
            "conference_filter": "すべて",
            "created_parliamentary_groups": [],
        }
        return self.session.get_or_create(
            "parliamentary_group_form_state", default_state
        )

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("parliamentary_group_form_state", self.form_state)

    def load_data(self) -> list[ParliamentaryGroup]:
        """Load all parliamentary groups."""
        try:
            result = self.use_case.list_parliamentary_groups(
                ParliamentaryGroupListInputDto()
            )
            return result.parliamentary_groups
        except Exception as e:
            self.logger.error(f"Failed to load parliamentary groups: {e}")
            return []

    def load_parliamentary_groups_with_filters(
        self, conference_id: int | None = None, active_only: bool = False
    ) -> list[ParliamentaryGroup]:
        """Load parliamentary groups with filters."""
        try:
            result = self.use_case.list_parliamentary_groups(
                ParliamentaryGroupListInputDto(
                    conference_id=conference_id, active_only=active_only
                )
            )
            return result.parliamentary_groups
        except Exception as e:
            self.logger.error(f"Failed to load parliamentary groups with filters: {e}")
            return []

    def get_all_conferences(self) -> list[Conference]:
        """Get all conferences."""
        try:
            return self.conference_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get conferences: {e}")
            return []

    def create(
        self,
        name: str,
        conference_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> tuple[bool, ParliamentaryGroup | None, str | None]:
        """Create a new parliamentary group."""
        try:
            result = self.use_case.create_parliamentary_group(
                CreateParliamentaryGroupInputDto(
                    name=name,
                    conference_id=conference_id,
                    url=url,
                    description=description,
                    is_active=is_active,
                )
            )
            if result.success:
                return True, result.parliamentary_group, None
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to create parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def update(
        self,
        id: int,
        name: str,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> tuple[bool, str | None]:
        """Update an existing parliamentary group."""
        try:
            result = self.use_case.update_parliamentary_group(
                UpdateParliamentaryGroupInputDto(
                    id=id,
                    name=name,
                    url=url,
                    description=description,
                    is_active=is_active,
                )
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to update parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def delete(self, id: int) -> tuple[bool, str | None]:
        """Delete a parliamentary group."""
        try:
            result = self.use_case.delete_parliamentary_group(
                DeleteParliamentaryGroupInputDto(id=id)
            )
            if result.success:
                return True, None
            else:
                return False, result.error_message
        except Exception as e:
            error_msg = f"Failed to delete parliamentary group: {e}"
            self.logger.error(error_msg)
            return False, error_msg

    def extract_members(
        self,
        parliamentary_group_id: int,
        url: str,
        confidence_threshold: float = 0.7,
        start_date: date | None = None,
        dry_run: bool = True,
    ) -> tuple[bool, Any, str | None]:
        """Extract members from parliamentary group URL."""
        try:
            result = self.use_case.extract_members(
                ExtractMembersInputDto(
                    parliamentary_group_id=parliamentary_group_id,
                    url=url,
                    confidence_threshold=confidence_threshold,
                    start_date=start_date,
                    dry_run=dry_run,
                )
            )
            if result.success:
                return True, result, None
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to extract members: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def generate_seed_file(self) -> tuple[bool, str | None, str | None]:
        """Generate seed file for parliamentary groups."""
        try:
            result = self.use_case.generate_seed_file()
            if result.success:
                return True, result.seed_content, result.file_path
            else:
                return False, None, result.error_message
        except Exception as e:
            error_msg = f"Failed to generate seed file: {e}"
            self.logger.error(error_msg)
            return False, None, error_msg

    def to_dataframe(
        self,
        parliamentary_groups: list[ParliamentaryGroup],
        conferences: list[Conference],
    ) -> pd.DataFrame | None:
        """Convert parliamentary groups to DataFrame."""
        if not parliamentary_groups:
            return None

        df_data = []
        for group in parliamentary_groups:
            # Find conference name
            conf = next((c for c in conferences if c.id == group.conference_id), None)
            conf_name = f"{conf.name}" if conf else "不明"

            df_data.append(
                {
                    "ID": group.id,
                    "議員団名": group.name,
                    "会議体": conf_name,
                    "URL": group.url or "未設定",
                    "説明": group.description or "",
                    "状態": "活動中" if group.is_active else "非活動",
                    "作成日": group.created_at,
                }
            )
        return pd.DataFrame(df_data)

    def get_member_counts(
        self, parliamentary_groups: list[ParliamentaryGroup]
    ) -> pd.DataFrame | None:
        """Get member counts for parliamentary groups."""
        # TODO: Implement when membership repository is available
        if not parliamentary_groups:
            return None

        member_counts = []
        for group in parliamentary_groups:
            member_counts.append(
                {
                    "議員団名": group.name,
                    "現在のメンバー数": 0,  # Placeholder
                }
            )
        return pd.DataFrame(member_counts)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions."""
        if action == "list":
            return self.load_parliamentary_groups_with_filters(
                kwargs.get("conference_id"), kwargs.get("active_only", False)
            )
        elif action == "create":
            return self.create(
                kwargs.get("name", ""),
                kwargs.get("conference_id", 0),
                kwargs.get("url"),
                kwargs.get("description"),
                kwargs.get("is_active", True),
            )
        elif action == "update":
            return self.update(
                kwargs.get("id", 0),
                kwargs.get("name", ""),
                kwargs.get("url"),
                kwargs.get("description"),
                kwargs.get("is_active", True),
            )
        elif action == "delete":
            return self.delete(kwargs.get("id", 0))
        elif action == "extract_members":
            return self.extract_members(
                kwargs.get("parliamentary_group_id", 0),
                kwargs.get("url", ""),
                kwargs.get("confidence_threshold", 0.7),
                kwargs.get("start_date"),
                kwargs.get("dry_run", True),
            )
        elif action == "generate_seed":
            return self.generate_seed_file()
        else:
            raise ValueError(f"Unknown action: {action}")

    def add_created_group(
        self, group: ParliamentaryGroup, conference_name: str
    ) -> None:
        """Add a created group to the session state."""
        created_group = {
            "id": group.id,
            "name": group.name,
            "conference_id": group.conference_id,
            "conference_name": conference_name,
            "url": group.url or "",
            "description": group.description or "",
            "is_active": group.is_active,
            "created_at": group.created_at,
        }
        self.form_state["created_parliamentary_groups"].append(created_group)
        self._save_form_state()

    def remove_created_group(self, index: int) -> None:
        """Remove a created group from the session state."""
        if 0 <= index < len(self.form_state["created_parliamentary_groups"]):
            self.form_state["created_parliamentary_groups"].pop(index)
            self._save_form_state()

    def get_created_groups(self) -> list[dict[str, Any]]:
        """Get created groups from the session state."""
        return self.form_state.get("created_parliamentary_groups", [])

    def get_extracted_members(self, parliamentary_group_id: int) -> list[Any]:
        """Get extracted members for a parliamentary group from database."""
        try:
            import asyncio

            members = asyncio.run(
                self.extracted_member_repo.get_by_parliamentary_group(
                    parliamentary_group_id
                )
            )
            return members
        except Exception as e:
            self.logger.error(f"Failed to get extracted members: {e}")
            return []

    def get_extraction_summary(self, parliamentary_group_id: int) -> dict[str, int]:
        """Get extraction summary for a parliamentary group."""
        try:
            import asyncio

            summary = asyncio.run(
                self.extracted_member_repo.get_extraction_summary(
                    parliamentary_group_id
                )
            )
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get extraction summary: {e}")
            return {
                "total": 0,
                "pending": 0,
                "matched": 0,
                "no_match": 0,
                "needs_review": 0,
            }
