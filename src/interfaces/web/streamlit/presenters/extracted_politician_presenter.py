"""Presenter for extracted politician review functionality."""

from datetime import datetime
from typing import Any

import pandas as pd

from src.common.logging import get_logger
from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.political_party import PoliticalParty
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
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
        # Start with all politicians
        politicians = self.extracted_politician_repo.get_all()

        # Apply status filter
        if statuses:
            politicians = [p for p in politicians if p.status in statuses]

        # Apply party filter
        if party_id is not None:
            politicians = [p for p in politicians if p.party_id == party_id]

        # Apply date range filter
        if start_date:
            politicians = [
                p
                for p in politicians
                if p.extracted_at and p.extracted_at >= start_date
            ]

        if end_date:
            politicians = [
                p for p in politicians if p.extracted_at and p.extracted_at <= end_date
            ]

        # Apply name search
        if search_name:
            search_term = search_name.lower()
            politicians = [p for p in politicians if search_term in p.name.lower()]

        # Sort by extracted_at descending
        politicians.sort(key=lambda p: p.extracted_at or datetime.min, reverse=True)

        # Apply pagination
        start = offset
        end = start + limit
        return politicians[start:end]

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics for extracted politicians.

        Returns:
            Dictionary with statistics
        """
        # Get status summary
        status_summary = self.extracted_politician_repo.get_summary_by_status()

        # Get all parties for party statistics
        parties = self.party_repo.get_all()
        party_statistics: dict[str, dict[str, int]] = {}

        for party in parties:
            if party.id:
                stats = self.extracted_politician_repo.get_statistics_by_party(party.id)
                if stats["total"] > 0:  # Only include parties with data
                    party_statistics[party.name] = stats

        return {
            "total": sum(status_summary.values()),
            "pending": status_summary.get("pending", 0),
            "reviewed": status_summary.get("reviewed", 0),
            "approved": status_summary.get("approved", 0),
            "rejected": status_summary.get("rejected", 0),
            "converted": status_summary.get("converted", 0),
            "by_party": party_statistics,
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
            # Get the politician
            politician = self.extracted_politician_repo.get_by_id(politician_id)
            if not politician:
                return False, f"Politician with ID {politician_id} not found"

            # Validate action
            if action not in ["approve", "reject", "review"]:
                return False, f"Invalid action: {action}"

            # Determine new status
            status_map = {
                "approve": "approved",
                "reject": "rejected",
                "review": "reviewed",
            }
            new_status = status_map[action]

            # Update status
            updated_politician = self.extracted_politician_repo.update_status(
                politician_id, new_status, reviewer_id
            )

            if updated_politician:
                action_past = {
                    "approve": "approved",
                    "reject": "rejected",
                    "review": "reviewed",
                }
                name = updated_politician.name

                # If approved, automatically convert to Politician
                conversion_message = ""
                if action == "approve":
                    try:
                        # Convert to Politician
                        converted = self._convert_single_politician(updated_politician)
                        if converted:
                            # Update status to converted
                            self.extracted_politician_repo.update_status(
                                politician_id, "converted", reviewer_id
                            )
                            conversion_message = " and converted to politician"
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to auto-convert politician {politician_id}: {e}"
                        )
                        conversion_message = " (auto-conversion failed)"

                msg = f"Successfully {action_past[action]} politician: {name}"
                return True, msg + conversion_message
            else:
                return (
                    False,
                    f"Failed to update status for politician ID {politician_id}",
                )

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
        successful_count = 0
        failed_count = 0

        for politician_id in politician_ids:
            success, _ = self.review_politician(politician_id, action, reviewer_id)
            if success:
                successful_count += 1
            else:
                failed_count += 1

        total_processed = len(politician_ids)
        message = (
            f"Processed {total_processed} politicians: "
            f"{successful_count} succeeded, {failed_count} failed"
        )

        return successful_count, failed_count, message

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
            position: New position
            profile_url: New profile URL
            image_url: New image URL

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get the politician
            politician = self.extracted_politician_repo.get_by_id(politician_id)
            if not politician:
                return False, f"Politician with ID {politician_id} not found"

            # Update fields
            politician.name = name
            politician.party_id = party_id
            politician.district = district
            politician.profile_url = profile_url

            # Save updates
            updated = self.extracted_politician_repo.update(politician)
            if updated:
                return True, f"Successfully updated politician: {name}"
            else:
                return False, f"Failed to update politician ID {politician_id}"

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
        # This is a complex operation that still needs async implementation
        # For now, return a placeholder
        self.logger.warning("Convert operation not yet implemented in sync mode")
        return 0, 0, 0, ["Convert operation not yet implemented in sync mode"]

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

    def _convert_single_politician(self, extracted: ExtractedPolitician) -> bool:
        """Convert a single extracted politician to politician table.

        Args:
            extracted: ExtractedPolitician entity

        Returns:
            True if successful, False otherwise
        """
        try:
            # Check for existing politician
            existing_politician = self.politician_repo.get_by_name_and_party(
                extracted.name, extracted.party_id
            )

            if existing_politician:
                # Update existing politician
                existing_politician.district = (
                    extracted.district or existing_politician.district
                )
                existing_politician.profile_page_url = (
                    extracted.profile_url or existing_politician.profile_page_url
                )
                self.politician_repo.update(existing_politician)
                self.logger.info(f"Updated existing politician: {extracted.name}")
            else:
                # Create new politician without speaker_id
                # (speaker_id will be set later when politician is
                # identified from meeting minutes)
                politician = Politician(
                    name=extracted.name,
                    speaker_id=None,  # No speaker_id from party websites
                    political_party_id=extracted.party_id,
                    district=extracted.district,
                    profile_page_url=extracted.profile_url,
                )
                self.politician_repo.create(politician)
                self.logger.info(
                    f"Created new politician: {extracted.name} (from party website)"
                )

            return True

        except Exception as e:
            self.logger.error(f"Failed to convert politician {extracted.name}: {e}")
            return False

    def _get_or_create_speaker(self, extracted: ExtractedPolitician) -> Speaker | None:
        """Get or create a speaker for the extracted politician.

        Args:
            extracted: ExtractedPolitician entity

        Returns:
            Speaker entity or None if failed
        """
        try:
            # Check for existing speaker
            existing_speakers = self.speaker_repo.find_by_name(extracted.name)
            if existing_speakers:
                return existing_speakers[0]

            # Create new speaker
            speaker = Speaker(
                name=extracted.name,
                position=None,
                party_name=None,
            )
            return self.speaker_repo.create(speaker)
        except Exception as e:
            self.logger.error(f"Failed to get or create speaker: {e}")
            return None
