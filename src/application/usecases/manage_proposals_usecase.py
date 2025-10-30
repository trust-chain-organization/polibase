"""Use case for managing proposals.

This module provides use cases for proposal management including
listing, creating, updating, and deleting proposals.
"""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities.proposal import Proposal
from src.domain.repositories.proposal_repository import ProposalRepository


@dataclass
class ProposalListInputDto:
    """Input DTO for listing proposals."""

    filter_type: str | None = None  # 'all', 'by_status', 'by_meeting'
    status: str | None = None  # Filter by status (if filter_type='by_status')
    meeting_id: int | None = None  # Filter by meeting (if filter_type='by_meeting')
    order_by: str = "id"


@dataclass
class ProposalStatistics:
    """Statistics for proposals."""

    total: int
    with_detail_url: int
    with_status_url: int
    by_status: dict[str, int]  # Count by status

    @property
    def with_detail_url_percentage(self) -> float:
        """Calculate percentage of proposals with detail URL."""
        if self.total == 0:
            return 0.0
        return (self.with_detail_url / self.total) * 100

    @property
    def with_status_url_percentage(self) -> float:
        """Calculate percentage of proposals with status URL."""
        if self.total == 0:
            return 0.0
        return (self.with_status_url / self.total) * 100


@dataclass
class ProposalListOutputDto:
    """Output DTO for listing proposals."""

    proposals: list[Proposal]
    statistics: ProposalStatistics


@dataclass
class CreateProposalInputDto:
    """Input DTO for creating a proposal."""

    content: str
    status: str | None = None
    detail_url: str | None = None
    status_url: str | None = None
    submission_date: str | None = None
    submitter: str | None = None
    proposal_number: str | None = None
    meeting_id: int | None = None
    summary: str | None = None


@dataclass
class CreateProposalOutputDto:
    """Output DTO for creating a proposal."""

    success: bool
    message: str
    proposal: Proposal | None = None


@dataclass
class UpdateProposalInputDto:
    """Input DTO for updating a proposal."""

    proposal_id: int
    content: str | None = None
    status: str | None = None
    detail_url: str | None = None
    status_url: str | None = None
    submission_date: str | None = None
    submitter: str | None = None
    proposal_number: str | None = None
    meeting_id: int | None = None
    summary: str | None = None


@dataclass
class UpdateProposalOutputDto:
    """Output DTO for updating a proposal."""

    success: bool
    message: str
    proposal: Proposal | None = None


@dataclass
class DeleteProposalInputDto:
    """Input DTO for deleting a proposal."""

    proposal_id: int


@dataclass
class DeleteProposalOutputDto:
    """Output DTO for deleting a proposal."""

    success: bool
    message: str


class ManageProposalsUseCase:
    """Use case for managing proposals."""

    def __init__(self, repository: ProposalRepository):
        """Initialize the use case.

        Args:
            repository: Proposal repository (can be sync or async)
        """
        self.repository = repository
        self.logger = get_logger(self.__class__.__name__)

    async def list_proposals(
        self, input_dto: ProposalListInputDto
    ) -> ProposalListOutputDto:
        """List proposals with optional filtering.

        Args:
            input_dto: Input parameters for listing

        Returns:
            Output DTO with proposals and statistics
        """
        try:
            # Get proposals based on filter
            if input_dto.filter_type == "by_status" and input_dto.status:
                proposals = await self.repository.get_by_status(input_dto.status)
            elif input_dto.filter_type == "by_meeting" and input_dto.meeting_id:
                proposals = await self.repository.get_by_meeting_id(
                    input_dto.meeting_id
                )
            else:
                proposals = await self.repository.get_all()

            # Sort proposals
            if input_dto.order_by == "id":
                proposals.sort(key=lambda p: p.id or 0)
            elif input_dto.order_by == "submission_date":
                proposals.sort(key=lambda p: p.submission_date or "", reverse=True)

            # Calculate statistics
            total = len(proposals)
            with_detail_url = sum(1 for p in proposals if p.detail_url)
            with_status_url = sum(1 for p in proposals if p.status_url)

            # Count by status
            status_counts: dict[str, int] = {}
            for proposal in proposals:
                status = proposal.status or "未設定"
                status_counts[status] = status_counts.get(status, 0) + 1

            statistics = ProposalStatistics(
                total=total,
                with_detail_url=with_detail_url,
                with_status_url=with_status_url,
                by_status=status_counts,
            )

            return ProposalListOutputDto(proposals=proposals, statistics=statistics)

        except Exception as e:
            self.logger.error(f"Error listing proposals: {e}", exc_info=True)
            raise

    async def create_proposal(
        self, input_dto: CreateProposalInputDto
    ) -> CreateProposalOutputDto:
        """Create a new proposal.

        Args:
            input_dto: Input parameters for creating

        Returns:
            Output DTO with result
        """
        try:
            # Check for duplicate proposal_number if provided
            if input_dto.proposal_number:
                existing = await self.repository.get_by_proposal_number(
                    input_dto.proposal_number
                )
                if existing:
                    return CreateProposalOutputDto(
                        success=False,
                        message=(
                            f"議案番号 {input_dto.proposal_number} は既に存在します"
                        ),
                    )

            # Create new proposal entity
            proposal = Proposal(
                content=input_dto.content,
                status=input_dto.status,
                detail_url=input_dto.detail_url,
                status_url=input_dto.status_url,
                submission_date=input_dto.submission_date,
                submitter=input_dto.submitter,
                proposal_number=input_dto.proposal_number,
                meeting_id=input_dto.meeting_id,
                summary=input_dto.summary,
            )

            # Save to repository
            created_proposal = await self.repository.create(proposal)

            return CreateProposalOutputDto(
                success=True, message="議案を作成しました", proposal=created_proposal
            )

        except Exception as e:
            self.logger.error(f"Error creating proposal: {e}", exc_info=True)
            return CreateProposalOutputDto(
                success=False, message=f"作成中にエラーが発生しました: {str(e)}"
            )

    async def update_proposal(
        self, input_dto: UpdateProposalInputDto
    ) -> UpdateProposalOutputDto:
        """Update an existing proposal.

        Args:
            input_dto: Input parameters for updating

        Returns:
            Output DTO with result
        """
        try:
            # Get the proposal
            proposal = await self.repository.get_by_id(input_dto.proposal_id)
            if not proposal:
                return UpdateProposalOutputDto(
                    success=False,
                    message=f"議案ID {input_dto.proposal_id} が見つかりません",
                )

            # Update fields if provided
            if input_dto.content is not None:
                proposal.content = input_dto.content
            if input_dto.status is not None:
                proposal.status = input_dto.status
            if input_dto.detail_url is not None:
                proposal.detail_url = input_dto.detail_url
            if input_dto.status_url is not None:
                proposal.status_url = input_dto.status_url
            if input_dto.submission_date is not None:
                proposal.submission_date = input_dto.submission_date
            if input_dto.submitter is not None:
                proposal.submitter = input_dto.submitter
            if input_dto.proposal_number is not None:
                proposal.proposal_number = input_dto.proposal_number
            if input_dto.meeting_id is not None:
                proposal.meeting_id = input_dto.meeting_id
            if input_dto.summary is not None:
                proposal.summary = input_dto.summary

            # Save updated proposal
            updated_proposal = await self.repository.update(proposal)

            return UpdateProposalOutputDto(
                success=True, message="議案を更新しました", proposal=updated_proposal
            )

        except Exception as e:
            self.logger.error(f"Error updating proposal: {e}", exc_info=True)
            return UpdateProposalOutputDto(
                success=False, message=f"更新中にエラーが発生しました: {str(e)}"
            )

    async def delete_proposal(
        self, input_dto: DeleteProposalInputDto
    ) -> DeleteProposalOutputDto:
        """Delete a proposal.

        Args:
            input_dto: Input parameters for deleting

        Returns:
            Output DTO with result
        """
        try:
            # Check if proposal exists
            proposal = await self.repository.get_by_id(input_dto.proposal_id)
            if not proposal:
                return DeleteProposalOutputDto(
                    success=False,
                    message=f"議案ID {input_dto.proposal_id} が見つかりません",
                )

            # Delete the proposal
            success = await self.repository.delete(input_dto.proposal_id)

            if success:
                return DeleteProposalOutputDto(
                    success=True, message="議案を削除しました"
                )
            else:
                return DeleteProposalOutputDto(
                    success=False, message="削除に失敗しました"
                )

        except Exception as e:
            self.logger.error(f"Error deleting proposal: {e}", exc_info=True)
            return DeleteProposalOutputDto(
                success=False, message=f"削除中にエラーが発生しました: {str(e)}"
            )
