"""Tests for ManageProposalsUseCase."""

from unittest.mock import AsyncMock

import pytest

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
from src.domain.entities.proposal import Proposal


class TestManageProposalsUseCase:
    """Test cases for ManageProposalsUseCase."""

    @pytest.fixture
    def mock_proposal_repository(self):
        """Create mock proposal repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(self, mock_proposal_repository):
        """Create ManageProposalsUseCase instance."""
        return ManageProposalsUseCase(repository=mock_proposal_repository)

    @pytest.mark.asyncio
    async def test_list_proposals_success(self, use_case, mock_proposal_repository):
        """Test listing proposals successfully."""
        # Arrange
        proposals = [
            Proposal(
                id=1,
                content="予算案第1号",
                status="可決",
                detail_url="https://example.com/1",
                proposal_number="議案第1号",
            ),
            Proposal(
                id=2,
                content="予算案第2号",
                status="審議中",
                status_url="https://example.com/status/2",
                proposal_number="議案第2号",
            ),
        ]
        mock_proposal_repository.get_all.return_value = proposals

        input_dto = ProposalListInputDto()

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert isinstance(result, ProposalListOutputDto)
        assert len(result.proposals) == 2
        assert result.statistics.total == 2
        assert result.statistics.with_detail_url == 1
        assert result.statistics.with_status_url == 1
        assert result.statistics.by_status["可決"] == 1
        assert result.statistics.by_status["審議中"] == 1

    @pytest.mark.asyncio
    async def test_list_proposals_filtered_by_status(
        self, use_case, mock_proposal_repository
    ):
        """Test listing proposals filtered by status."""
        # Arrange
        proposals = [
            Proposal(
                id=1, content="予算案第1号", status="可決", proposal_number="議案第1号"
            )
        ]
        mock_proposal_repository.get_by_status.return_value = proposals

        input_dto = ProposalListInputDto(filter_type="by_status", status="可決")

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert len(result.proposals) == 1
        assert result.proposals[0].status == "可決"
        mock_proposal_repository.get_by_status.assert_called_once_with("可決")

    @pytest.mark.asyncio
    async def test_list_proposals_filtered_by_meeting(
        self, use_case, mock_proposal_repository
    ):
        """Test listing proposals filtered by meeting."""
        # Arrange
        proposals = [
            Proposal(
                id=1,
                content="予算案第1号",
                status="可決",
                meeting_id=100,
                proposal_number="議案第1号",
            )
        ]
        mock_proposal_repository.get_by_meeting_id.return_value = proposals

        input_dto = ProposalListInputDto(filter_type="by_meeting", meeting_id=100)

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert len(result.proposals) == 1
        assert result.proposals[0].meeting_id == 100
        mock_proposal_repository.get_by_meeting_id.assert_called_once_with(100)

    @pytest.mark.asyncio
    async def test_list_proposals_sorted_by_submission_date(
        self, use_case, mock_proposal_repository
    ):
        """Test listing proposals sorted by submission date."""
        # Arrange
        proposals = [
            Proposal(
                id=1,
                content="予算案第1号",
                submission_date="2024-01-01",
                proposal_number="議案第1号",
            ),
            Proposal(
                id=2,
                content="予算案第2号",
                submission_date="2024-01-15",
                proposal_number="議案第2号",
            ),
        ]
        mock_proposal_repository.get_all.return_value = proposals

        input_dto = ProposalListInputDto(order_by="submission_date")

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        # Should be sorted by date descending (newest first)
        assert result.proposals[0].submission_date == "2024-01-15"
        assert result.proposals[1].submission_date == "2024-01-01"

    @pytest.mark.asyncio
    async def test_list_proposals_empty(self, use_case, mock_proposal_repository):
        """Test listing proposals when no proposals exist."""
        # Arrange
        mock_proposal_repository.get_all.return_value = []

        input_dto = ProposalListInputDto()

        # Act
        result = await use_case.list_proposals(input_dto)

        # Assert
        assert len(result.proposals) == 0
        assert result.statistics.total == 0
        assert result.statistics.with_detail_url == 0
        assert result.statistics.with_status_url == 0

    @pytest.mark.asyncio
    async def test_create_proposal_success(self, use_case, mock_proposal_repository):
        """Test creating a proposal successfully."""
        # Arrange
        mock_proposal_repository.get_by_proposal_number.return_value = None
        created_proposal = Proposal(
            id=1,
            content="新しい予算案",
            status="提出済み",
            detail_url="https://example.com/new",
            proposal_number="議案第3号",
            meeting_id=100,
        )
        mock_proposal_repository.create.return_value = created_proposal

        input_dto = CreateProposalInputDto(
            content="新しい予算案",
            status="提出済み",
            detail_url="https://example.com/new",
            proposal_number="議案第3号",
            meeting_id=100,
        )

        # Act
        result = await use_case.create_proposal(input_dto)

        # Assert
        assert isinstance(result, CreateProposalOutputDto)
        assert result.success is True
        assert result.proposal is not None
        assert result.proposal.id == 1
        assert "作成しました" in result.message
        mock_proposal_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_proposal_duplicate_number_error(
        self, use_case, mock_proposal_repository
    ):
        """Test creating a proposal with duplicate proposal number."""
        # Arrange
        existing_proposal = Proposal(
            id=1, content="既存の予算案", proposal_number="議案第1号"
        )
        mock_proposal_repository.get_by_proposal_number.return_value = existing_proposal

        input_dto = CreateProposalInputDto(
            content="新しい予算案", proposal_number="議案第1号"
        )

        # Act
        result = await use_case.create_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "既に存在します" in result.message
        mock_proposal_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_proposal_repository_error(
        self, use_case, mock_proposal_repository
    ):
        """Test creating a proposal with repository error."""
        # Arrange
        mock_proposal_repository.get_by_proposal_number.return_value = None
        mock_proposal_repository.create.side_effect = Exception("Database error")

        input_dto = CreateProposalInputDto(content="新しい予算案")

        # Act
        result = await use_case.create_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

    @pytest.mark.asyncio
    async def test_update_proposal_success(self, use_case, mock_proposal_repository):
        """Test updating a proposal successfully."""
        # Arrange
        existing_proposal = Proposal(
            id=1, content="既存の予算案", status="審議中", proposal_number="議案第1号"
        )
        mock_proposal_repository.get_by_id.return_value = existing_proposal

        updated_proposal = Proposal(
            id=1, content="更新された予算案", status="可決", proposal_number="議案第1号"
        )
        mock_proposal_repository.update.return_value = updated_proposal

        input_dto = UpdateProposalInputDto(
            proposal_id=1, content="更新された予算案", status="可決"
        )

        # Act
        result = await use_case.update_proposal(input_dto)

        # Assert
        assert isinstance(result, UpdateProposalOutputDto)
        assert result.success is True
        assert result.proposal is not None
        assert result.proposal.status == "可決"
        assert "更新しました" in result.message
        mock_proposal_repository.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_proposal_not_found(self, use_case, mock_proposal_repository):
        """Test updating a proposal that does not exist."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = None

        input_dto = UpdateProposalInputDto(proposal_id=999, content="存在しない議案")

        # Act
        result = await use_case.update_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message
        mock_proposal_repository.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_proposal_repository_error(
        self, use_case, mock_proposal_repository
    ):
        """Test updating a proposal with repository error."""
        # Arrange
        existing_proposal = Proposal(
            id=1, content="既存の予算案", proposal_number="議案第1号"
        )
        mock_proposal_repository.get_by_id.return_value = existing_proposal
        mock_proposal_repository.update.side_effect = Exception("Database error")

        input_dto = UpdateProposalInputDto(proposal_id=1, content="更新された予算案")

        # Act
        result = await use_case.update_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message

    @pytest.mark.asyncio
    async def test_delete_proposal_success(self, use_case, mock_proposal_repository):
        """Test deleting a proposal successfully."""
        # Arrange
        existing_proposal = Proposal(
            id=1, content="既存の予算案", proposal_number="議案第1号"
        )
        mock_proposal_repository.get_by_id.return_value = existing_proposal
        mock_proposal_repository.delete.return_value = True

        input_dto = DeleteProposalInputDto(proposal_id=1)

        # Act
        result = await use_case.delete_proposal(input_dto)

        # Assert
        assert isinstance(result, DeleteProposalOutputDto)
        assert result.success is True
        assert "削除しました" in result.message
        mock_proposal_repository.delete.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_delete_proposal_not_found(self, use_case, mock_proposal_repository):
        """Test deleting a proposal that does not exist."""
        # Arrange
        mock_proposal_repository.get_by_id.return_value = None

        input_dto = DeleteProposalInputDto(proposal_id=999)

        # Act
        result = await use_case.delete_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "見つかりません" in result.message
        mock_proposal_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_proposal_repository_error(
        self, use_case, mock_proposal_repository
    ):
        """Test deleting a proposal with repository error."""
        # Arrange
        existing_proposal = Proposal(
            id=1, content="既存の予算案", proposal_number="議案第1号"
        )
        mock_proposal_repository.get_by_id.return_value = existing_proposal
        mock_proposal_repository.delete.side_effect = Exception("Database error")

        input_dto = DeleteProposalInputDto(proposal_id=1)

        # Act
        result = await use_case.delete_proposal(input_dto)

        # Assert
        assert result.success is False
        assert "エラーが発生しました" in result.message
        assert "Database error" in result.message
