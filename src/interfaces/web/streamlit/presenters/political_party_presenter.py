"""Presenter for political party management in Streamlit.

This module provides the presenter layer for political party management,
handling UI state and coordinating with use cases.
"""

import builtins
from typing import Any

import pandas as pd

from src.application.usecases.manage_political_parties_usecase import (
    GenerateSeedFileOutputDto,
    ManagePoliticalPartiesUseCase,
    PoliticalPartyListInputDto,
    PoliticalPartyListOutputDto,
    UpdatePoliticalPartyUrlInputDto,
    UpdatePoliticalPartyUrlOutputDto,
)
from src.domain.entities.political_party import PoliticalParty
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.dto.base import FormStateDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class PoliticalPartyPresenter(CRUDPresenter[list[PoliticalParty]]):
    """Presenter for political party management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        self.repository = RepositoryAdapter(PoliticalPartyRepositoryImpl)
        # Type: ignore - RepositoryAdapter duck-types as repository protocol
        self.use_case = ManagePoliticalPartiesUseCase(
            self.repository  # type: ignore[arg-type]
        )
        self.session = SessionManager(namespace="political_party")
        self.form_state = self._get_or_create_form_state()

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

    def load_data(self) -> list[PoliticalParty]:
        """Load political parties data.

        Returns:
            List of political parties
        """
        result = self.load_data_filtered("all")
        return result.parties

    def load_data_filtered(
        self, filter_type: str = "all"
    ) -> PoliticalPartyListOutputDto:
        """Load political parties data with filter.

        Args:
            filter_type: Filter type ('all', 'with_url', 'without_url')

        Returns:
            Political party list with statistics
        """
        return self._run_async(self._load_data_filtered_async(filter_type))

    async def _load_data_filtered_async(
        self, filter_type: str = "all"
    ) -> PoliticalPartyListOutputDto:
        """Load political parties data with filter (async implementation)."""
        try:
            input_dto = PoliticalPartyListInputDto(filter_type=filter_type)
            return await self.use_case.list_parties(input_dto)
        except Exception as e:
            self.logger.error(f"Error loading political parties: {e}", exc_info=True)
            raise

    def create(self, **kwargs: Any) -> Any:
        """Create is not supported for political parties (master data)."""
        raise NotImplementedError("政党の作成はサポートされていません")

    def read(self, **kwargs: Any) -> Any:
        """Read a single political party."""
        party_id = kwargs.get("party_id")
        if not party_id:
            raise ValueError("party_id is required")

        party = self.repository.get_by_id(party_id)  # type: ignore[attr-defined]
        if not party:
            raise ValueError(f"政党ID {party_id} が見つかりません")
        return party

    def update(self, **kwargs: Any) -> UpdatePoliticalPartyUrlOutputDto:
        """Update political party URL.

        Args:
            **kwargs: Must include party_id and members_list_url

        Returns:
            Update result DTO
        """
        return self._run_async(self._update_async(**kwargs))

    async def _update_async(self, **kwargs: Any) -> UpdatePoliticalPartyUrlOutputDto:
        """Update political party URL (async implementation)."""
        party_id = kwargs.get("party_id")
        members_list_url = kwargs.get("members_list_url")

        if not party_id:
            raise ValueError("party_id is required")

        input_dto = UpdatePoliticalPartyUrlInputDto(
            party_id=party_id, members_list_url=members_list_url
        )
        return await self.use_case.update_party_url(input_dto)

    def delete(self, **kwargs: Any) -> Any:
        """Delete is not supported for political parties (master data)."""
        raise NotImplementedError("政党の削除はサポートされていません")

    def list(self, **kwargs: Any) -> list[PoliticalParty]:
        """List all political parties.

        Args:
            **kwargs: Can include filter_type

        Returns:
            List of political parties
        """
        filter_type = kwargs.get("filter_type", "all")
        result = self.load_data_filtered(filter_type)
        return result.parties

    def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """Generate seed file for political parties.

        Returns:
            Seed file generation result
        """
        return self.use_case.generate_seed_file()

    def to_dataframe(self, parties: builtins.list[PoliticalParty]) -> pd.DataFrame:
        """Convert political parties to DataFrame for display.

        Args:
            parties: List of political parties

        Returns:
            DataFrame for display
        """
        if not parties:
            # Create empty DataFrame with proper column specification
            return pd.DataFrame({"ID": [], "政党名": [], "議員一覧URL": []})

        data = []
        for party in parties:
            data.append(
                {
                    "ID": party.id,
                    "政党名": party.name,
                    "議員一覧URL": party.members_list_url or "未設定",
                }
            )

        return pd.DataFrame(data)

    def set_editing_mode(self, party_id: int) -> None:
        """Set form to editing mode for a specific party.

        Args:
            party_id: ID of the party to edit
        """
        self.form_state.set_editing(party_id)
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.form_state.reset()
        self._save_form_state()

    def is_editing(self, party_id: int) -> bool:
        """Check if a specific party is being edited.

        Args:
            party_id: ID of the party to check

        Returns:
            True if the party is being edited
        """
        return self.form_state.is_editing and self.form_state.current_id == party_id

    def get_statistics_summary(self, statistics: Any) -> dict[str, str]:
        """Get formatted statistics summary.

        Args:
            statistics: Political party statistics

        Returns:
            Formatted statistics dictionary
        """
        return {
            "全政党数": str(statistics.total),
            "URL設定済み": (
                f"{statistics.with_url} ({statistics.with_url_percentage:.1f}%)"
            ),
            "URL未設定": (
                f"{statistics.without_url} ({statistics.without_url_percentage:.1f}%)"
            ),
        }

    def extract_politicians(
        self, party_id: int, dry_run: bool = False
    ) -> dict[str, Any]:
        """Extract politicians from party members list URL.

        Args:
            party_id: Party ID to extract politicians from
            dry_run: If True, don't save to database

        Returns:
            Dictionary with extraction results:
            - success: Whether extraction succeeded
            - message: Success or error message
            - count: Number of politicians extracted
            - politicians: List of extracted politician DTOs
        """
        import logging

        from src.application.usecases.scrape_politicians_usecase import (
            ScrapePoliticiansInputDTO,
            ScrapePoliticiansUseCase,
        )
        from src.infrastructure.external.web_scraper_service import (
            PlaywrightScraperService,
        )
        from src.infrastructure.persistence import (
            extracted_politician_repository_impl as extracted_repo,
        )

        logger = logging.getLogger(__name__)

        try:
            # Initialize dependencies
            extracted_repo_impl = RepositoryAdapter(
                extracted_repo.ExtractedPoliticianRepositoryImpl
            )
            scraper = PlaywrightScraperService()

            # Create use case
            use_case = ScrapePoliticiansUseCase(
                political_party_repository=self.repository,  # type: ignore[arg-type]
                extracted_politician_repository=extracted_repo_impl,  # type: ignore[arg-type]
                web_scraper_service=scraper,
            )

            # Execute extraction
            request = ScrapePoliticiansInputDTO(
                party_id=party_id, all_parties=False, dry_run=dry_run
            )

            # Run async code synchronously
            # Note: Using _run_async helper inherited from base presenter
            results = self._run_async(use_case.execute(request))

            return {
                "success": True,
                "message": f"✅ {len(results)}人の政治家情報を抽出しました",
                "count": len(results),
                "politicians": results,
            }

        except ValueError as e:
            logger.error(f"Validation error during politician extraction: {e}")
            return {
                "success": False,
                "message": f"❌ エラー: {str(e)}",
                "count": 0,
                "politicians": [],
            }
        except Exception as e:
            logger.error(f"Error during politician extraction: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"❌ 抽出処理中にエラーが発生しました: {str(e)}",
                "count": 0,
                "politicians": [],
            }

    def get_extraction_statistics(self, party_id: int) -> dict[str, int]:
        """Get extraction statistics for a party.

        Args:
            party_id: Party ID

        Returns:
            Dictionary with statistics:
            - total: Total extracted politicians
            - pending: Pending review
            - approved: Approved
            - rejected: Rejected
            - converted: Converted to politicians
        """
        try:
            from src.infrastructure.persistence import (
                extracted_politician_repository_impl as extracted_repo,
            )

            repo = RepositoryAdapter(extracted_repo.ExtractedPoliticianRepositoryImpl)

            # Get all extracted politicians for this party
            # RepositoryAdapter handles async/sync conversion automatically
            all_extracted = repo.get_by_party(party_id)  # type: ignore[attr-defined]

            # Count by status
            total = len(all_extracted)
            pending = sum(1 for p in all_extracted if p.status == "pending")
            approved = sum(1 for p in all_extracted if p.status == "approved")
            rejected = sum(1 for p in all_extracted if p.status == "rejected")

            return {
                "total": total,
                "pending": pending,
                "approved": approved,
                "rejected": rejected,
                "converted": 0,  # Not applicable for party extraction
            }

        except Exception as e:
            # Log error for debugging
            import logging

            logger = logging.getLogger(__name__)
            logger.exception(
                f"Error getting extraction statistics for party {party_id}: {e}"
            )
            # Return zeros on error
            return {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "converted": 0,
            }
