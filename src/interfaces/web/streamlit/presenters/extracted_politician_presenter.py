"""Presenter for extracted politician review functionality."""

import asyncio
from datetime import datetime
from typing import Any

import pandas as pd

from src.application.dtos.convert_extracted_politician_dto import (
    ConvertExtractedPoliticianInputDTO,
)
from src.application.dtos.review_extracted_politician_dto import (
    BulkReviewInputDTO,
    ExtractedPoliticianFilterDTO,
    ReviewExtractedPoliticianInputDTO,
)
from src.application.usecases.convert_extracted_politician_usecase import (
    ConvertExtractedPoliticianUseCase,
)
from src.application.usecases.review_extracted_politician_usecase import (
    ReviewExtractedPoliticianUseCase,
)
from src.common.logging import get_logger
from src.config.async_database import async_db
from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.political_party import PoliticalParty
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.extracted_politician_repository_impl import (
    ExtractedPoliticianRepositoryImpl,
)
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl,
)
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ExtractedPoliticianPresenter(BasePresenter[list[ExtractedPolitician]]):
    """Presenter for extracted politician review operations."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter."""
        super().__init__(container)

        # Wrap repositories with adapter for sync access
        self.extracted_politician_repo = RepositoryAdapter(
            ExtractedPoliticianRepositoryImpl
        )
        self.party_repo = RepositoryAdapter(PoliticalPartyRepositoryImpl)
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
        self.speaker_repo = RepositoryAdapter(SpeakerRepositoryImpl)

        # Note: Use cases are not initialized here because they need async repositories
        # They will be created on demand in _run_async_use_case method

        self.session = SessionManager()
        self.logger = get_logger(__name__)

    def load_data(self) -> list[ExtractedPolitician]:
        """Load all extracted politicians."""
        try:
            # RepositoryAdapter already handles async-to-sync conversion
            return self.extracted_politician_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to load extracted politicians: {e}")
            return []

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions.

        Args:
            action: The action to perform
            **kwargs: Additional parameters for the action

        Returns:
            Result of the action
        """
        if action == "review":
            return self.review_politician(
                kwargs.get("politician_id", 0),
                kwargs.get("action", ""),
                kwargs.get("reviewer_id", 1),
            )
        elif action == "bulk_review":
            return self.bulk_review(
                kwargs.get("politician_ids", []),
                kwargs.get("action", ""),
                kwargs.get("reviewer_id", 1),
            )
        elif action == "convert":
            return self.convert_approved_politicians(
                kwargs.get("party_id"),
                kwargs.get("batch_size", 100),
                kwargs.get("dry_run", False),
            )
        else:
            raise ValueError(f"Unknown action: {action}")

    def get_all_parties(self) -> list[PoliticalParty]:
        """Get all political parties.

        Returns:
            List of political parties
        """
        # RepositoryAdapter already handles async-to-sync conversion
        return self.party_repo.get_all()

    def get_filtered_politicians(
        self,
        statuses: list[str] | None = None,
        party_id: int | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        search_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExtractedPolitician]:
        """Get filtered extracted politicians.

        Args:
            statuses: List of statuses to filter by
            party_id: Party ID to filter by
            start_date: Start date for extraction date filter
            end_date: End date for extraction date filter
            search_name: Name search term
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of filtered extracted politicians
        """
        filter_dto = ExtractedPoliticianFilterDTO(
            statuses=statuses,
            party_id=party_id,
            start_date=start_date,
            end_date=end_date,
            search_name=search_name,
            limit=limit,
            offset=offset,
        )
        return self._run_async_with_use_case(
            "review", "get_filtered_politicians", filter_dto
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics for extracted politicians.

        Returns:
            Dictionary with statistics
        """
        stats = self._run_async_with_use_case("review", "get_statistics")
        return {
            "total": stats.total,
            "pending": stats.pending_count,
            "reviewed": stats.reviewed_count,
            "approved": stats.approved_count,
            "rejected": stats.rejected_count,
            "converted": stats.converted_count,
            "by_party": stats.party_statistics,
        }

    def review_politician(
        self, politician_id: int, action: str, reviewer_id: int = 1
    ) -> tuple[bool, str]:
        """Review a single politician.

        Args:
            politician_id: ID of the politician to review
            action: Review action ('approve', 'reject', 'review')
            reviewer_id: ID of the reviewer

        Returns:
            Tuple of (success, message)
        """
        input_dto = ReviewExtractedPoliticianInputDTO(
            politician_id=politician_id, action=action, reviewer_id=reviewer_id
        )
        result = self._run_async_with_use_case("review", "review_politician", input_dto)
        return result.success, result.message

    def bulk_review(
        self, politician_ids: list[int], action: str, reviewer_id: int = 1
    ) -> tuple[int, int, str]:
        """Bulk review politicians.

        Args:
            politician_ids: List of politician IDs to review
            action: Review action ('approve', 'reject', 'review')
            reviewer_id: ID of the reviewer

        Returns:
            Tuple of (successful_count, failed_count, message)
        """
        input_dto = BulkReviewInputDTO(
            politician_ids=politician_ids, action=action, reviewer_id=reviewer_id
        )
        result = self._run_async_with_use_case("review", "bulk_review", input_dto)
        return result.successful_count, result.failed_count, result.message

    def convert_approved_politicians(
        self, party_id: int | None = None, batch_size: int = 100, dry_run: bool = False
    ) -> tuple[int, int, int, list[str]]:
        """Convert approved politicians to politicians table.

        Args:
            party_id: Optional party ID to filter
            batch_size: Number of records to process
            dry_run: Whether to perform dry run

        Returns:
            Tuple of (converted_count, skipped_count, error_count, error_messages)
        """
        input_dto = ConvertExtractedPoliticianInputDTO(
            party_id=party_id, batch_size=batch_size, dry_run=dry_run
        )
        result = self._run_async_with_use_case("convert", "execute", input_dto)
        return (
            result.converted_count,
            result.skipped_count,
            result.error_count,
            result.error_messages,
        )

    def to_dataframe(
        self,
        politicians: list[ExtractedPolitician],
        parties: list[PoliticalParty] | None = None,
    ) -> pd.DataFrame | None:
        """Convert extracted politicians to DataFrame.

        Args:
            politicians: List of extracted politicians
            parties: List of political parties for mapping

        Returns:
            DataFrame with politician data or None if empty
        """
        if not politicians:
            return None

        # Create party map
        party_map = {}
        if parties:
            party_map = {p.id: p.name for p in parties if p.id}

        # Convert to dictionary list
        data = []
        for p in politicians:
            party_name = party_map.get(p.party_id, "無所属") if p.party_id else "無所属"

            # Format dates
            extracted_date = (
                p.extracted_at.strftime("%Y-%m-%d %H:%M") if p.extracted_at else ""
            )
            reviewed_date = (
                p.reviewed_at.strftime("%Y-%m-%d %H:%M") if p.reviewed_at else ""
            )

            # Format status for display
            status_display = {
                "pending": "⏳ 未レビュー",
                "reviewed": "👀 レビュー済み",
                "approved": "✅ 承認済み",
                "rejected": "❌ 却下",
                "converted": "✔️ 変換済み",
            }.get(p.status, p.status)

            data.append(
                {
                    "ID": p.id,
                    "名前": p.name,
                    "政党": party_name,
                    "選挙区": p.district or "",
                    "役職": p.position or "",
                    "ステータス": status_display,
                    "抽出日時": extracted_date,
                    "レビュー日時": reviewed_date,
                    "プロフィールURL": p.profile_url or "",
                    "画像URL": p.image_url or "",
                }
            )

        return pd.DataFrame(data)

    def _run_async_with_use_case(
        self, use_case_type: str, method_name: str, *args: Any, **kwargs: Any
    ) -> Any:
        """Run async use case method in sync context.

        Args:
            use_case_type: Type of use case ('review' or 'convert')
            method_name: Name of the method to call
            *args: Positional arguments for the method
            **kwargs: Keyword arguments for the method

        Returns:
            Result of the use case method
        """

        async def async_wrapper():
            async with async_db.get_session() as session:
                # Create repository implementations with the session
                extracted_politician_repo = ExtractedPoliticianRepositoryImpl(session)
                party_repo = PoliticalPartyRepositoryImpl(session)

                if use_case_type == "review":
                    use_case = ReviewExtractedPoliticianUseCase(
                        extracted_politician_repo, party_repo
                    )
                    method = getattr(use_case, method_name)
                    return await method(*args, **kwargs)
                elif use_case_type == "convert":
                    politician_repo = PoliticianRepositoryImpl(session)
                    speaker_repo = SpeakerRepositoryImpl(session)
                    use_case = ConvertExtractedPoliticianUseCase(
                        extracted_politician_repo, politician_repo, speaker_repo
                    )
                    method = getattr(use_case, method_name)
                    return await method(*args, **kwargs)
                else:
                    raise ValueError(f"Unknown use case type: {use_case_type}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(async_wrapper())
        finally:
            loop.close()
