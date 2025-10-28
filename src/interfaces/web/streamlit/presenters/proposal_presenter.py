"""Presenter for proposal management in Streamlit.

This module provides the presenter layer for proposal management,
handling UI state and coordinating with use cases.
"""

from typing import Any

import pandas as pd

from src.application.usecases.extract_proposal_judges_usecase import (
    CreateProposalJudgesInputDTO,
    CreateProposalJudgesOutputDTO,
    ExtractProposalJudgesInputDTO,
    ExtractProposalJudgesOutputDTO,
    ExtractProposalJudgesUseCase,
    MatchProposalJudgesInputDTO,
    MatchProposalJudgesOutputDTO,
)
from src.application.usecases.manage_proposals_usecase import (
    CreateProposalInputDto,
    CreateProposalOutputDto,
    DeleteProposalInputDto,
    DeleteProposalOutputDto,
    ManageProposalsUseCase,
    ProposalListInputDto,
    ProposalListOutputDto,
    UpdateProposalInputDto,
    UpdateProposalOutputDto,
)
from src.application.usecases.scrape_proposal_usecase import (
    ScrapeProposalInputDTO,
    ScrapeProposalOutputDTO,
)
from src.domain.entities.extracted_proposal_judge import ExtractedProposalJudge
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.infrastructure.di.container import Container
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.interfaces.web.streamlit.dto.base import FormStateDTO
from src.interfaces.web.streamlit.presenters.base import CRUDPresenter
from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class ProposalPresenter(CRUDPresenter[list[Proposal]]):
    """Presenter for proposal management."""

    def __init__(self, container: Container | None = None):
        """Initialize the presenter.

        Args:
            container: Dependency injection container
        """
        super().__init__(container)
        self.proposal_repository = RepositoryAdapter(ProposalRepositoryImpl)
        self.extracted_judge_repository = RepositoryAdapter(
            ExtractedProposalJudgeRepositoryImpl
        )
        self.judge_repository = RepositoryAdapter(ProposalJudgeRepositoryImpl)

        # Initialize use cases
        self.manage_usecase = ManageProposalsUseCase(
            self.proposal_repository  # type: ignore[arg-type]
        )

        # Session management
        self.session = SessionManager(namespace="proposal")
        self.form_state = self._get_or_create_form_state()

    def _get_or_create_form_state(self) -> FormStateDTO:
        """Get or create form state from session."""
        state_dict = self.session.get("form_state", {})
        if not state_dict:
            state = FormStateDTO()
            self.session.set("form_state", state.__dict__)
            return state
        return FormStateDTO(**state_dict)

    def _save_form_state(self) -> None:
        """Save form state to session."""
        self.session.set("form_state", self.form_state.__dict__)

    def load_data(self) -> list[Proposal]:
        """Load proposals data."""
        result = self.load_data_filtered("all")
        return result.proposals

    def load_data_filtered(
        self,
        filter_type: str = "all",
        status: str | None = None,
        meeting_id: int | None = None,
    ) -> ProposalListOutputDto:
        """Load proposals with filter."""
        return self._run_async(
            self._load_data_filtered_async(filter_type, status, meeting_id)
        )

    async def _load_data_filtered_async(
        self,
        filter_type: str = "all",
        status: str | None = None,
        meeting_id: int | None = None,
    ) -> ProposalListOutputDto:
        """Load proposals with filter (async implementation)."""
        try:
            input_dto = ProposalListInputDto(
                filter_type=filter_type, status=status, meeting_id=meeting_id
            )
            return await self.manage_usecase.list_proposals(input_dto)
        except Exception as e:
            self.logger.error(f"Error loading proposals: {e}", exc_info=True)
            raise

    def create(self, **kwargs: Any) -> CreateProposalOutputDto:
        """Create a new proposal."""
        return self._run_async(self._create_async(**kwargs))

    async def _create_async(self, **kwargs: Any) -> CreateProposalOutputDto:
        """Create a new proposal (async implementation)."""
        input_dto = CreateProposalInputDto(
            content=kwargs["content"],
            status=kwargs.get("status"),
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            submission_date=kwargs.get("submission_date"),
            submitter=kwargs.get("submitter"),
            proposal_number=kwargs.get("proposal_number"),
            meeting_id=kwargs.get("meeting_id"),
            summary=kwargs.get("summary"),
        )
        return await self.manage_usecase.create_proposal(input_dto)

    def update(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal."""
        return self._run_async(self._update_async(**kwargs))

    async def _update_async(self, **kwargs: Any) -> UpdateProposalOutputDto:
        """Update a proposal (async implementation)."""
        input_dto = UpdateProposalInputDto(
            proposal_id=kwargs["proposal_id"],
            content=kwargs.get("content"),
            status=kwargs.get("status"),
            detail_url=kwargs.get("detail_url"),
            status_url=kwargs.get("status_url"),
            submission_date=kwargs.get("submission_date"),
            submitter=kwargs.get("submitter"),
            proposal_number=kwargs.get("proposal_number"),
            meeting_id=kwargs.get("meeting_id"),
            summary=kwargs.get("summary"),
        )
        return await self.manage_usecase.update_proposal(input_dto)

    def delete(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal."""
        return self._run_async(self._delete_async(**kwargs))

    async def _delete_async(self, **kwargs: Any) -> DeleteProposalOutputDto:
        """Delete a proposal (async implementation)."""
        input_dto = DeleteProposalInputDto(proposal_id=kwargs["proposal_id"])
        return await self.manage_usecase.delete_proposal(input_dto)

    def scrape_proposal(
        self, url: str, meeting_id: int | None = None
    ) -> ScrapeProposalOutputDTO:
        """Scrape proposal from URL."""
        return self._run_async(self._scrape_proposal_async(url, meeting_id))

    async def _scrape_proposal_async(
        self, url: str, meeting_id: int | None = None
    ) -> ScrapeProposalOutputDTO:
        """Scrape proposal from URL (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        scrape_usecase = self.container.use_cases.scrape_proposal_usecase()
        input_dto = ScrapeProposalInputDTO(url=url, meeting_id=meeting_id)
        return await scrape_usecase.scrape_and_save(input_dto)

    def extract_judges(
        self, url: str, proposal_id: int | None = None, force: bool = False
    ) -> ExtractProposalJudgesOutputDTO:
        """Extract judges from proposal status URL."""
        return self._run_async(self._extract_judges_async(url, proposal_id, force))

    async def _extract_judges_async(
        self, url: str, proposal_id: int | None = None, force: bool = False
    ) -> ExtractProposalJudgesOutputDTO:
        """Extract judges from proposal status URL (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = ExtractProposalJudgesInputDTO(
            url=url, proposal_id=proposal_id, force=force
        )
        return await extract_usecase.extract_judges(input_dto)

    def match_judges(
        self, proposal_id: int | None = None
    ) -> MatchProposalJudgesOutputDTO:
        """Match extracted judges with politicians."""
        return self._run_async(self._match_judges_async(proposal_id))

    async def _match_judges_async(
        self, proposal_id: int | None = None
    ) -> MatchProposalJudgesOutputDTO:
        """Match extracted judges with politicians (async implementation)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = MatchProposalJudgesInputDTO(proposal_id=proposal_id)
        return await extract_usecase.match_judges(input_dto)

    def create_judges_from_matched(
        self, proposal_id: int | None = None
    ) -> CreateProposalJudgesOutputDTO:
        """Create proposal judges from matched extracted judges."""
        return self._run_async(self._create_judges_from_matched_async(proposal_id))

    async def _create_judges_from_matched_async(
        self, proposal_id: int | None = None
    ) -> CreateProposalJudgesOutputDTO:
        """Create proposal judges from matched extracted judges (async)."""
        if self.container is None:
            raise ValueError("DI container is not initialized")

        extract_usecase: ExtractProposalJudgesUseCase = (
            self.container.use_cases.extract_proposal_judges_usecase()
        )
        input_dto = CreateProposalJudgesInputDTO(proposal_id=proposal_id)
        return await extract_usecase.create_judges(input_dto)

    def load_extracted_judges(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Load extracted judges."""
        return self._run_async(self._load_extracted_judges_async(proposal_id))

    async def _load_extracted_judges_async(
        self, proposal_id: int | None = None
    ) -> list[ExtractedProposalJudge]:
        """Load extracted judges (async implementation)."""
        if proposal_id:
            return await self.extracted_judge_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]
        else:
            return await self.extracted_judge_repository.get_all()  # type: ignore[attr-defined]

    def load_proposal_judges(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Load final proposal judges."""
        return self._run_async(self._load_proposal_judges_async(proposal_id))

    async def _load_proposal_judges_async(
        self, proposal_id: int | None = None
    ) -> list[ProposalJudge]:
        """Load final proposal judges (async implementation)."""
        if proposal_id:
            return await self.judge_repository.get_by_proposal(proposal_id)  # type: ignore[attr-defined]
        else:
            return await self.judge_repository.get_all()  # type: ignore[attr-defined]

    def to_dataframe(self, proposals: list[Proposal]) -> pd.DataFrame:
        """Convert proposals to DataFrame for display."""
        if not proposals:
            return pd.DataFrame(
                {
                    "ID": [],
                    "議案番号": [],
                    "内容": [],
                    "状態": [],
                    "提出者": [],
                    "提出日": [],
                }
            )

        data = []
        for proposal in proposals:
            data.append(
                {
                    "ID": proposal.id,
                    "議案番号": proposal.proposal_number or "未設定",
                    "内容": (
                        proposal.content[:50] + "..."
                        if len(proposal.content) > 50
                        else proposal.content
                    ),
                    "状態": proposal.status or "未設定",
                    "提出者": proposal.submitter or "未設定",
                    "提出日": proposal.submission_date or "未設定",
                }
            )

        return pd.DataFrame(data)

    def extracted_judges_to_dataframe(
        self, judges: list[ExtractedProposalJudge]
    ) -> pd.DataFrame:
        """Convert extracted judges to DataFrame for display."""
        if not judges:
            return pd.DataFrame(
                {
                    "ID": [],
                    "政治家名": [],
                    "議員団名": [],
                    "賛否": [],
                    "信頼度": [],
                    "ステータス": [],
                }
            )

        data = []
        for judge in judges:
            data.append(
                {
                    "ID": judge.id,
                    "政治家名": judge.extracted_politician_name or "未設定",
                    "議員団名": judge.extracted_parliamentary_group_name or "未設定",
                    "賛否": judge.vote or "未設定",
                    "信頼度": (
                        f"{judge.matching_confidence:.2f}"
                        if judge.matching_confidence
                        else "未実施"
                    ),
                    "ステータス": judge.matching_status or "pending",
                }
            )

        return pd.DataFrame(data)

    def proposal_judges_to_dataframe(self, judges: list[ProposalJudge]) -> pd.DataFrame:
        """Convert proposal judges to DataFrame for display."""
        if not judges:
            return pd.DataFrame({"ID": [], "政治家ID": [], "賛否": [], "備考": []})

        data = []
        for judge in judges:
            data.append(
                {
                    "ID": judge.id,
                    "政治家ID": judge.politician_id or "未設定",
                    "賛否": judge.vote or "未設定",
                    "備考": judge.remarks or "",
                }
            )

        return pd.DataFrame(data)

    def set_editing_mode(self, proposal_id: int) -> None:
        """Set form to editing mode."""
        self.form_state.set_editing(proposal_id)
        self._save_form_state()

    def cancel_editing(self) -> None:
        """Cancel editing mode."""
        self.form_state.reset()
        self._save_form_state()

    def is_editing(self, proposal_id: int) -> bool:
        """Check if editing."""
        return self.form_state.is_editing and self.form_state.current_id == proposal_id

    def read(self, **kwargs: Any) -> Proposal | None:
        """Read a single proposal by ID.

        Args:
            **kwargs: Must include proposal_id

        Returns:
            Proposal entity or None if not found
        """
        proposal_id = kwargs.get("proposal_id")
        if not proposal_id:
            raise ValueError("proposal_id is required")

        return self._run_async(
            self.proposal_repository.get_by_id(proposal_id)  # type: ignore[attr-defined]
        )

    def list(self, **kwargs: Any) -> list[Proposal]:
        """List all proposals.

        Args:
            **kwargs: Can include filter_type, status, meeting_id

        Returns:
            List of proposals
        """
        filter_type = kwargs.get("filter_type", "all")
        status = kwargs.get("status")
        meeting_id = kwargs.get("meeting_id")
        result = self.load_data_filtered(filter_type, status, meeting_id)
        return result.proposals
