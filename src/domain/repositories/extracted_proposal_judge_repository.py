"""ExtractedProposalJudge repository interface."""

from abc import abstractmethod

from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.repositories.base import BaseRepository


class ExtractedProposalJudgeRepository(BaseRepository[ExtractedProposalJudge]):
    """Repository interface for extracted proposal judges."""

    @abstractmethod
    async def get_pending_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get all pending judges for matching."""
        pass

    @abstractmethod
    async def get_matched_judges(
        self, proposal_id: int | None = None, min_confidence: float | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get matched judges with optional filtering."""
        pass

    @abstractmethod
    async def get_needs_review_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Get judges that need manual review."""
        pass

    @abstractmethod
    async def update_matching_result(
        self,
        judge_id: int,
        politician_id: int | None = None,
        parliamentary_group_id: int | None = None,
        confidence: float | None = None,
        status: str = "pending",
    ) -> ExtractedProposalJudge | None:
        """Update the matching result for a judge."""
        pass

    @abstractmethod
    async def get_by_proposal(self, proposal_id: int) -> list[ExtractedProposalJudge]:
        """Get all extracted judges for a proposal."""
        pass

    @abstractmethod
    async def get_extraction_summary(
        self, proposal_id: int | None = None
    ) -> dict[str, int]:
        """Get summary statistics for extracted judges."""
        pass

    @abstractmethod
    async def bulk_create(
        self, judges: list[ExtractedProposalJudge]
    ) -> list[ExtractedProposalJudge]:
        """Create multiple extracted judges at once."""
        pass

    @abstractmethod
    async def convert_to_proposal_judge(
        self, extracted_judge: ExtractedProposalJudge
    ) -> ProposalJudge:
        """Convert an extracted judge to a ProposalJudge entity."""
        pass

    @abstractmethod
    async def bulk_convert_to_proposal_judges(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Convert all matched judges for a proposal to ProposalJudge entities."""
        pass

    @abstractmethod
    async def get_pending_by_proposal(
        self, proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        """Get pending judges for a specific proposal."""
        pass

    @abstractmethod
    async def get_all_pending(self) -> list[ExtractedProposalJudge]:
        """Get all pending judges."""
        pass

    @abstractmethod
    async def get_matched_by_proposal(
        self, proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        """Get matched judges for a specific proposal."""
        pass

    @abstractmethod
    async def get_all_matched(self) -> list[ExtractedProposalJudge]:
        """Get all matched judges."""
        pass

    @abstractmethod
    async def mark_processed(self, judge_id: int) -> None:
        """Mark a judge as processed."""
        pass
