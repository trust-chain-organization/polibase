"""Presenter for parliamentary group member review functionality."""

from datetime import date, datetime
from typing import Any

import pandas as pd

from src.application.usecases.create_parliamentary_group_memberships_usecase import (
    CreateParliamentaryGroupMembershipsUseCase,
)
from src.application.usecases.match_parliamentary_group_members_usecase import (
    MatchParliamentaryGroupMembersUseCase,
)
from src.common.logging import get_logger
from src.domain.entities.extracted_parliamentary_group_member import (
    ExtractedParliamentaryGroupMember,
)
from src.domain.entities.parliamentary_group import ParliamentaryGroup
from src.domain.entities.politician import Politician
from src.domain.services.parliamentary_group_member_matching_service import (
    ParliamentaryGroupMemberMatchingService,
)
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.di.container import Container
from src.infrastructure.external.llm_service import GeminiLLMService
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


class ParliamentaryGroupMemberPresenter(
    BasePresenter[list[ExtractedParliamentaryGroupMember]]
):
    """Presenter for parliamentary group member review operations."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)

        # Initialize repositories
        self.extracted_member_repo = RepositoryAdapter(
            ExtractedParliamentaryGroupMemberRepositoryImpl
        )
        self.membership_repo = RepositoryAdapter(
            ParliamentaryGroupMembershipRepositoryImpl
        )
        self.parliamentary_group_repo = RepositoryAdapter(
            ParliamentaryGroupRepositoryImpl
        )
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)

        # Initialize LLM service
        self.llm_service = GeminiLLMService()

        # Initialize speaker service
        self.speaker_service = SpeakerDomainService()

        # Initialize matching service
        self.matching_service = ParliamentaryGroupMemberMatchingService(
            politician_repository=self.politician_repo,  # type: ignore
            llm_service=self.llm_service,
            speaker_service=self.speaker_service,
        )

        # Initialize use cases
        self.match_usecase = MatchParliamentaryGroupMembersUseCase(
            member_repository=self.extracted_member_repo,  # type: ignore
            matching_service=self.matching_service,
        )

        self.create_memberships_usecase = CreateParliamentaryGroupMembershipsUseCase(
            member_repository=self.extracted_member_repo,  # type: ignore
            membership_repository=self.membership_repo,  # type: ignore
        )

        self.session = SessionManager()
        self.logger = get_logger(__name__)

    def load_data(self) -> list[ExtractedParliamentaryGroupMember]:
        """Load all extracted members.

        Returns:
            List of all extracted members
        """
        try:
            # Get all parliamentary groups
            groups = self.parliamentary_group_repo.get_all()
            all_members = []
            for group in groups:
                if group.id:
                    members = self.extracted_member_repo.get_by_parliamentary_group(
                        group.id
                    )
                    all_members.extend(members)
            return all_members
        except Exception as e:
            self.logger.error(f"Failed to load extracted members: {e}")
            return []

    def get_all_parliamentary_groups(self) -> list[ParliamentaryGroup]:
        """Get all parliamentary groups.

        Returns:
            List of parliamentary groups
        """
        try:
            return self.parliamentary_group_repo.get_all()
        except Exception as e:
            self.logger.error(f"Failed to get parliamentary groups: {e}")
            return []

    def get_filtered_extracted_members(
        self,
        parliamentary_group_id: int | None = None,
        statuses: list[str] | None = None,
        search_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExtractedParliamentaryGroupMember]:
        """Get filtered extracted members.

        Args:
            parliamentary_group_id: Parliamentary group ID to filter by
            statuses: List of statuses to filter by
            search_name: Name search term
            limit: Maximum number of records
            offset: Number of records to skip

        Returns:
            List of filtered extracted members
        """
        try:
            # Get members by parliamentary group
            if parliamentary_group_id:
                members = self.extracted_member_repo.get_by_parliamentary_group(
                    parliamentary_group_id
                )
            else:
                members = self.load_data()

            # Apply filters
            if statuses:
                members = [m for m in members if m.matching_status in statuses]

            if search_name:
                members = [
                    m
                    for m in members
                    if search_name.lower() in m.extracted_name.lower()
                ]

            # Apply pagination
            return members[offset : offset + limit]

        except Exception as e:
            self.logger.error(f"Failed to filter extracted members: {e}")
            return []

    def get_statistics(
        self, parliamentary_group_id: int | None = None
    ) -> dict[str, Any]:
        """Get statistics for extracted members.

        Args:
            parliamentary_group_id: Optional parliamentary group ID to filter

        Returns:
            Dictionary with statistics
        """
        try:
            summary = self.extracted_member_repo.get_extraction_summary(
                parliamentary_group_id
            )
            return summary
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {
                "total": 0,
                "pending": 0,
                "matched": 0,
                "needs_review": 0,
                "no_match": 0,
            }

    def review_extracted_member(
        self,
        member_id: int,
        action: str,
        politician_id: int | None = None,
        confidence: float | None = None,
    ) -> tuple[bool, str]:
        """Review a single extracted member.

        Args:
            member_id: ID of the member to review
            action: Review action ('approve', 'reject', 'match')
            politician_id: ID of politician to match (for 'match' action)
            confidence: Confidence score (for 'match' action)

        Returns:
            Tuple of (success, message)
        """
        try:
            # Get member
            member = self.extracted_member_repo.get_by_id(member_id)
            if not member:
                return False, "メンバーが見つかりません"

            if action == "approve":
                # Approve matched member (status: matched)
                if member.matching_status != "matched":
                    return False, "マッチ済みのメンバーのみ承認できます"

                status = "matched"
                matched_at = datetime.now()

            elif action == "reject":
                # Reject member (status: no_match)
                status = "no_match"
                politician_id = None
                confidence = None
                matched_at = None

            elif action == "match":
                # Manual match
                if not politician_id or confidence is None:
                    return False, "政治家IDと信頼度が必要です"

                status = "matched"
                matched_at = datetime.now()

            else:
                return False, f"不明なアクション: {action}"

            # Update matching result
            self.extracted_member_repo.update_matching_result(
                member_id=member_id,
                politician_id=politician_id,
                confidence=confidence,
                status=status,
                matched_at=matched_at,
            )

            action_label = {
                "approve": "承認",
                "reject": "却下",
                "match": "マッチング",
            }.get(action, action)

            return True, f"{member.extracted_name} を{action_label}しました"

        except Exception as e:
            self.logger.error(f"Error reviewing member {member_id}: {e}")
            return False, f"エラー: {str(e)}"

    def bulk_review(self, member_ids: list[int], action: str) -> tuple[int, int, str]:
        """Bulk review members.

        Args:
            member_ids: List of member IDs to review
            action: Review action ('approve', 'reject')

        Returns:
            Tuple of (successful_count, failed_count, message)
        """
        successful_count = 0
        failed_count = 0

        for member_id in member_ids:
            success, _ = self.review_extracted_member(member_id, action)
            if success:
                successful_count += 1
            else:
                failed_count += 1

        action_label = {"approve": "承認", "reject": "却下"}.get(action, action)
        message = (
            f"{action_label}完了: 成功 {successful_count}件、失敗 {failed_count}件"
        )

        return successful_count, failed_count, message

    def create_memberships(
        self,
        parliamentary_group_id: int | None = None,
        min_confidence: float = 0.7,
        start_date: date | None = None,
    ) -> tuple[int, int, list[dict[str, Any]]]:
        """Create memberships from matched members.

        Args:
            parliamentary_group_id: Parliamentary group ID (None for all)
            min_confidence: Minimum confidence threshold
            start_date: Membership start date

        Returns:
            Tuple of (created_count, skipped_count, created_memberships)
        """
        try:
            result = self._run_async(
                self.create_memberships_usecase.execute(
                    parliamentary_group_id=parliamentary_group_id,
                    min_confidence=min_confidence,
                    start_date=start_date,
                )
            )

            # Extract values with proper types
            created_count_raw = result["created_count"]
            skipped_count_raw = result["skipped_count"]
            created_memberships_raw = result["created_memberships"]

            # Type narrowing
            created_count = (
                created_count_raw if isinstance(created_count_raw, int) else 0
            )
            skipped_count = (
                skipped_count_raw if isinstance(skipped_count_raw, int) else 0
            )

            # Convert to list of dicts with Any values
            created_memberships: list[dict[str, Any]] = []
            if isinstance(created_memberships_raw, list):
                created_memberships = [dict(m) for m in created_memberships_raw]

            return (created_count, skipped_count, created_memberships)

        except Exception as e:
            self.logger.error(f"Error creating memberships: {e}")
            return 0, 0, []

    def rematch_members(
        self, parliamentary_group_id: int | None = None
    ) -> tuple[int, int, str]:
        """Re-run matching for pending members.

        Args:
            parliamentary_group_id: Parliamentary group ID (None for all)

        Returns:
            Tuple of (matched_count, total_count, message)
        """
        try:
            results = self._run_async(
                self.match_usecase.execute(parliamentary_group_id)
            )

            matched_count = sum(1 for r in results if r["status"] == "matched")
            total_count = len(results)

            message = f"マッチング完了: {matched_count}/{total_count}件がマッチしました"
            return matched_count, total_count, message

        except Exception as e:
            self.logger.error(f"Error re-matching members: {e}")
            return 0, 0, f"エラー: {str(e)}"

    def get_politician_by_id(self, politician_id: int) -> Politician | None:
        """Get politician by ID.

        Args:
            politician_id: Politician ID

        Returns:
            Politician or None if not found
        """
        try:
            return self.politician_repo.get_by_id(politician_id)
        except Exception as e:
            self.logger.error(f"Failed to get politician {politician_id}: {e}")
            return None

    def search_politicians(
        self, name: str, party_id: int | None = None
    ) -> list[Politician]:
        """Search politicians by name and optionally party.

        Args:
            name: Politician name (partial match)
            party_id: Optional party ID filter

        Returns:
            List of matching politicians
        """
        try:
            # Get all politicians
            all_politicians = self.politician_repo.get_all()

            # Filter by name
            politicians = [p for p in all_politicians if name.lower() in p.name.lower()]

            # Filter by party if specified
            if party_id:
                politicians = [
                    p for p in politicians if p.political_party_id == party_id
                ]

            return politicians

        except Exception as e:
            self.logger.error(f"Failed to search politicians: {e}")
            return []

    def to_dataframe(
        self,
        members: list[ExtractedParliamentaryGroupMember],
        parliamentary_groups: list[ParliamentaryGroup] | None = None,
    ) -> pd.DataFrame | None:
        """Convert extracted members to DataFrame.

        Args:
            members: List of extracted members
            parliamentary_groups: List of parliamentary groups for mapping

        Returns:
            DataFrame with member data or None if empty
        """
        if not members:
            return None

        # Create parliamentary group map
        group_map = {}
        if parliamentary_groups:
            group_map = {g.id: g.name for g in parliamentary_groups if g.id}

        # Convert to dictionary list
        data = []
        for m in members:
            group_name = (
                group_map.get(m.parliamentary_group_id, "不明")
                if m.parliamentary_group_id
                else "不明"
            )

            # Format dates
            extracted_date = (
                m.extracted_at.strftime("%Y-%m-%d %H:%M") if m.extracted_at else ""
            )
            matched_date = (
                m.matched_at.strftime("%Y-%m-%d %H:%M") if m.matched_at else ""
            )

            # Format status for display
            status_display = {
                "pending": "⏳ 未処理",
                "matched": "✅ マッチ済み",
                "needs_review": "⚠️ 要確認",
                "no_match": "❌ マッチなし",
            }.get(m.matching_status, m.matching_status)

            # Get politician name if matched
            politician_name = "-"
            if m.matched_politician_id:
                politician = self.get_politician_by_id(m.matched_politician_id)
                if politician:
                    politician_name = politician.name

            data.append(
                {
                    "ID": m.id,
                    "名前": m.extracted_name,
                    "役職": m.extracted_role or "-",
                    "政党": m.extracted_party_name or "-",
                    "選挙区": m.extracted_district or "-",
                    "議員団": group_name,
                    "ステータス": status_display,
                    "マッチした政治家": politician_name,
                    "信頼度": (
                        f"{m.matching_confidence:.2f}"
                        if m.matching_confidence is not None
                        else "-"
                    ),
                    "抽出日時": extracted_date,
                    "マッチ日時": matched_date,
                }
            )

        return pd.DataFrame(data)

    def handle_action(self, action: str, **kwargs: Any) -> Any:
        """Handle user actions.

        Args:
            action: The action to perform
            **kwargs: Additional parameters for the action

        Returns:
            Result of the action
        """
        if action == "review":
            return self.review_extracted_member(
                kwargs.get("member_id", 0),
                kwargs.get("review_action", ""),
                kwargs.get("politician_id"),
                kwargs.get("confidence"),
            )
        elif action == "bulk_review":
            return self.bulk_review(
                kwargs.get("member_ids", []), kwargs.get("review_action", "")
            )
        elif action == "create_memberships":
            return self.create_memberships(
                kwargs.get("parliamentary_group_id"),
                kwargs.get("min_confidence", 0.7),
                kwargs.get("start_date"),
            )
        elif action == "rematch":
            return self.rematch_members(kwargs.get("parliamentary_group_id"))
        else:
            raise ValueError(f"Unknown action: {action}")
