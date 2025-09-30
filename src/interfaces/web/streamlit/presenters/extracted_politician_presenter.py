"""Presenter for extracted politician review functionality."""

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
    UpdateExtractedPoliticianInputDTO,
)
from src.application.usecases.convert_extracted_politician_usecase import (
    ConvertExtractedPoliticianUseCase,
)
from src.application.usecases.review_and_convert_politician_usecase import (
    ReviewAndConvertPoliticianUseCase,
)
from src.application.usecases.review_extracted_politician_usecase import (
    ReviewExtractedPoliticianUseCase,
)
from src.common.logging import get_logger
from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.political_party import PoliticalParty
from src.infrastructure.di.container import Container
from src.interfaces.web.streamlit.presenters.base import BasePresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ExtractedPoliticianPresenter(BasePresenter[list[ExtractedPolitician]]):
    """Presenter for extracted politician review operations."""

    def __init__(
        self,
        container: Container | None = None,
        review_use_case: ReviewExtractedPoliticianUseCase | None = None,
        convert_use_case: ConvertExtractedPoliticianUseCase | None = None,
        review_and_convert_use_case: ReviewAndConvertPoliticianUseCase | None = None,
    ):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
            review_use_case: Use case for reviewing politicians
            convert_use_case: Use case for converting politicians
            review_and_convert_use_case: Use case for review with auto-conversion
        """
        super().__init__(container)

        # Get use cases from container or use provided instances
        if review_use_case is None:
            self.review_use_case = (
                self.container.use_cases.review_extracted_politician_usecase()
            )
        else:
            self.review_use_case = review_use_case

        if convert_use_case is None:
            self.convert_use_case = (
                self.container.use_cases.convert_extracted_politician_usecase()
            )
        else:
            self.convert_use_case = convert_use_case

        if review_and_convert_use_case is None:
            self.review_and_convert_use_case = (
                self.container.use_cases.review_and_convert_politician_usecase()
            )
        else:
            self.review_and_convert_use_case = review_and_convert_use_case

        self.session = SessionManager()
        self.logger = get_logger(__name__)

    def load_data(self) -> list[ExtractedPolitician]:
        """Load all extracted politicians.

        Returns:
            List of all extracted politicians
        """
        try:
            # Use the review use case to get all politicians
            filter_dto = ExtractedPoliticianFilterDTO(limit=10000, offset=0)
            return self._run_async(
                self.review_use_case.get_filtered_politicians(filter_dto)
            )
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
        # Use the review use case to get parties
        return self._run_async(self.review_use_case.get_all_parties())

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
        return self._run_async(
            self.review_use_case.get_filtered_politicians(filter_dto)
        )

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics for extracted politicians.

        Returns:
            Dictionary with statistics
        """
        stats_dto = self._run_async(self.review_use_case.get_statistics())
        return {
            "total": stats_dto.total,
            "pending": stats_dto.pending_count,
            "reviewed": stats_dto.reviewed_count,
            "approved": stats_dto.approved_count,
            "rejected": stats_dto.rejected_count,
            "converted": stats_dto.converted_count,
            "by_party": stats_dto.party_statistics,
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
        try:
            # Create input DTO
            input_dto = ReviewExtractedPoliticianInputDTO(
                politician_id=politician_id,
                action=action,
                reviewer_id=reviewer_id,
            )

            # Use the composite use case for review with auto-conversion
            result = self._run_async(
                self.review_and_convert_use_case.review_with_auto_convert(
                    input_dto, auto_convert=True
                )
            )

            return result.success, result.message

        except Exception as e:
            self.logger.error(f"Error reviewing politician {politician_id}: {e}")
            return False, f"Error: {str(e)}"

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
        try:
            # Create input DTO
            input_dto = BulkReviewInputDTO(
                politician_ids=politician_ids,
                action=action,
                reviewer_id=reviewer_id,
            )

            # Call bulk review use case
            result = self._run_async(self.review_use_case.bulk_review(input_dto))

            return result.successful_count, result.failed_count, result.message

        except Exception as e:
            self.logger.error(f"Error in bulk review: {e}")
            return 0, len(politician_ids), f"Error: {str(e)}"

    def update_politician(
        self,
        politician_id: int,
        name: str,
        party_id: int | None = None,
        district: str | None = None,
        profile_url: str | None = None,
    ) -> tuple[bool, str]:
        """Update an extracted politician's information.

        Args:
            politician_id: ID of the politician to update
            name: New name
            party_id: New party ID
            district: New district
            profile_url: New profile URL

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create input DTO
            input_dto = UpdateExtractedPoliticianInputDTO(
                politician_id=politician_id,
                name=name,
                party_id=party_id,
                district=district,
                profile_url=profile_url,
            )

            # Call update use case
            result = self._run_async(self.review_use_case.update_politician(input_dto))

            return result.success, result.message

        except Exception as e:
            self.logger.error(f"Error updating politician {politician_id}: {e}")
            return False, f"Error: {str(e)}"

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
        try:
            # Create input DTO
            input_dto = ConvertExtractedPoliticianInputDTO(
                party_id=party_id,
                batch_size=batch_size,
                dry_run=dry_run,
            )

            # Call convert use case
            result = self._run_async(self.convert_use_case.execute(input_dto))

            return (
                result.converted_count,
                result.skipped_count,
                result.error_count,
                result.error_messages,
            )

        except Exception as e:
            self.logger.error(f"Error converting politicians: {e}")
            return 0, 0, 1, [f"Error: {str(e)}"]

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
                    "ステータス": status_display,
                    "抽出日時": extracted_date,
                    "レビュー日時": reviewed_date,
                    "プロフィールURL": p.profile_url or "",
                }
            )

        return pd.DataFrame(data)
