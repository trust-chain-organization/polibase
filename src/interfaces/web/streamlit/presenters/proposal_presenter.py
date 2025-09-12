"""Presenter for proposal management."""

import asyncio
from typing import Any

import pandas as pd

from src.application.usecases.extract_proposal_judges_usecase import (
    ExtractProposalJudgesUseCase,
)
from src.application.usecases.scrape_proposal_usecase import ScrapeProposalUseCase
from src.common.logging import get_logger
from src.config.async_database import get_async_session
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal import Proposal
from src.infrastructure.external.llm_service_factory import LLMServiceFactory
from src.infrastructure.external.proposal_scraper_service import ProposalScraperService
from src.infrastructure.external.web_scraper_service import PlaywrightScraperService
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter

logger = get_logger(__name__)


class ProposalPresenter:
    """Presenter for proposal management."""

    def __init__(self):
        self.proposal_repo = RepositoryAdapter(ProposalRepositoryImpl)
        self.meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
        self.extracted_judge_repo = RepositoryAdapter(
            ExtractedProposalJudgeRepositoryImpl
        )
        self.politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)

    def load_all_proposals(self) -> list[Proposal]:
        """Load all proposals."""
        try:
            return self.proposal_repo.get_all()
        except Exception as e:
            logger.error(f"Failed to load proposals: {e}")
            return []

    def load_proposals_by_meeting(self, meeting_id: int) -> list[Proposal]:
        """Load proposals by meeting ID."""
        try:

            async def _get():
                async with get_async_session() as session:
                    repo = ProposalRepositoryImpl(session)
                    return await repo.get_by_meeting_id(meeting_id)

            return asyncio.run(_get())
        except Exception as e:
            logger.error(f"Failed to load proposals for meeting {meeting_id}: {e}")
            return []

    def load_proposals_by_status(self, status: str) -> list[Proposal]:
        """Load proposals by status."""
        try:

            async def _get():
                async with get_async_session() as session:
                    repo = ProposalRepositoryImpl(session)
                    return await repo.get_by_status(status)

            return asyncio.run(_get())
        except Exception as e:
            logger.error(f"Failed to load proposals with status {status}: {e}")
            return []

    def to_dataframe(self, proposals: list[Proposal]) -> pd.DataFrame | None:
        """Convert proposals to DataFrame."""
        if not proposals:
            return None

        data = []
        for p in proposals:
            # Get meeting name if available
            meeting_name = None
            if p.meeting_id:
                try:
                    meeting = self.meeting_repo.get_by_id(p.meeting_id)
                    if meeting:
                        meeting_name = meeting.meeting_name
                except Exception:
                    pass

            data.append(
                {
                    "ID": p.id,
                    "議案番号": p.proposal_number or "-",
                    "内容": p.content[:50] + "..."
                    if len(p.content) > 50
                    else p.content,
                    "状態": p.status or "-",
                    "提出者": p.submitter or "-",
                    "提出日": p.submission_date or "-",
                    "会議": meeting_name or "-",
                    "URL": "✓" if p.url else "-",
                }
            )

        return pd.DataFrame(data)

    def create_proposal(
        self,
        content: str,
        proposal_number: str | None = None,
        status: str | None = None,
        url: str | None = None,
        submission_date: str | None = None,
        submitter: str | None = None,
        meeting_id: int | None = None,
        summary: str | None = None,
    ) -> tuple[bool, int | None, str | None]:
        """Create a new proposal.

        Returns:
            tuple of (success, proposal_id, error_message)
        """
        try:
            proposal = Proposal(
                content=content,
                proposal_number=proposal_number,
                status=status,
                url=url,
                submission_date=submission_date,
                submitter=submitter,
                meeting_id=meeting_id,
                summary=summary,
            )

            created = self.proposal_repo.save(proposal)
            return True, created.id, None
        except Exception as e:
            error_msg = f"Failed to create proposal: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def update_proposal(
        self,
        proposal_id: int,
        content: str,
        proposal_number: str | None = None,
        status: str | None = None,
        url: str | None = None,
        submission_date: str | None = None,
        submitter: str | None = None,
        meeting_id: int | None = None,
        summary: str | None = None,
    ) -> tuple[bool, str | None]:
        """Update an existing proposal.

        Returns:
            tuple of (success, error_message)
        """
        try:
            proposal = self.proposal_repo.get_by_id(proposal_id)
            if not proposal:
                return False, "議案が見つかりません"

            proposal.content = content
            proposal.proposal_number = proposal_number
            proposal.status = status
            proposal.url = url
            proposal.submission_date = submission_date
            proposal.submitter = submitter
            proposal.meeting_id = meeting_id
            proposal.summary = summary

            self.proposal_repo.update(proposal)
            return True, None
        except Exception as e:
            error_msg = f"Failed to update proposal: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def delete_proposal(self, proposal_id: int) -> tuple[bool, str | None]:
        """Delete a proposal.

        Returns:
            tuple of (success, error_message)
        """
        try:
            self.proposal_repo.delete_by_id(proposal_id)
            return True, None
        except Exception as e:
            error_msg = f"Failed to delete proposal: {str(e)}"
            logger.error(error_msg)
            return False, error_msg

    def scrape_proposal_from_url(
        self, url: str, meeting_id: int | None = None
    ) -> tuple[bool, int | None, str | None]:
        """Scrape proposal from URL.

        Returns:
            tuple of (success, proposal_id, error_message)
        """
        try:

            async def _scrape():
                async with get_async_session() as session:
                    # Initialize services
                    scraper_service = ProposalScraperService()
                    proposal_repo = ProposalRepositoryImpl(session)

                    # Initialize use case
                    use_case = ScrapeProposalUseCase(proposal_repo, scraper_service)

                    # Execute scraping
                    from src.application.dto.scrape_proposal_dto import (
                        ScrapeProposalInputDTO,
                    )

                    input_dto = ScrapeProposalInputDTO(url=url, meeting_id=meeting_id)
                    result = await use_case.execute(input_dto)

                    # Commit transaction
                    await session.commit()

                    return result.proposal_id

            proposal_id = asyncio.run(_scrape())
            return True, proposal_id, None
        except Exception as e:
            error_msg = f"Failed to scrape proposal: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg

    def extract_judges_from_proposal(
        self, proposal_id: int
    ) -> tuple[bool, int, str | None]:
        """Extract judges from proposal.

        Returns:
            tuple of (success, extracted_count, error_message)
        """
        try:

            async def _extract():
                async with get_async_session() as session:
                    # Initialize services
                    scraper_service = PlaywrightScraperService()
                    llm_service = LLMServiceFactory.create_default_service(session)

                    proposal_repo = ProposalRepositoryImpl(session)
                    politician_repo = PoliticianRepositoryImpl(session)
                    extracted_judge_repo = ExtractedProposalJudgeRepositoryImpl(session)
                    proposal_judge_repo = ProposalJudgeRepositoryImpl(session)

                    # Initialize use case
                    use_case = ExtractProposalJudgesUseCase(
                        proposal_repo,
                        politician_repo,
                        extracted_judge_repo,
                        proposal_judge_repo,
                        scraper_service,
                        llm_service,
                    )

                    # Execute extraction
                    result = await use_case.extract_judges(proposal_id)

                    # Commit transaction
                    await session.commit()

                    return result.extracted_count

            count = asyncio.run(_extract())
            return True, count, None
        except Exception as e:
            error_msg = f"Failed to extract judges: {str(e)}"
            logger.error(error_msg)
            return False, 0, error_msg

    def get_extracted_judges_for_proposal(
        self, proposal_id: int
    ) -> list[ExtractedProposalJudge]:
        """Get extracted judges for a proposal."""
        try:

            async def _get():
                async with get_async_session() as session:
                    repo = ExtractedProposalJudgeRepositoryImpl(session)
                    return await repo.get_by_proposal(proposal_id)

            return asyncio.run(_get())
        except Exception as e:
            logger.error(f"Failed to get extracted judges: {e}")
            return []

    def get_all_meetings(self) -> list[Any]:
        """Get all meetings for filter."""
        try:
            return self.meeting_repo.get_all()
        except Exception as e:
            logger.error(f"Failed to load meetings: {e}")
            return []
