"""Tests for Proposal entity."""

from src.domain.entities.proposal import Proposal


class TestProposal:
    """Test cases for Proposal entity."""

    def test_initialization_with_required_fields(self) -> None:
        """Test entity initialization with required fields only."""
        proposal = Proposal(content="予算案の審議について")

        assert proposal.content == "予算案の審議について"
        assert proposal.status is None
        assert proposal.id is None

    def test_initialization_with_old_fields(self) -> None:
        """Test entity initialization with original fields."""
        proposal = Proposal(
            id=1,
            content="令和6年度予算案の承認について",
            status="審議中",
        )

        assert proposal.id == 1
        assert proposal.content == "令和6年度予算案の承認について"
        assert proposal.status == "審議中"
        # New fields should be None by default
        assert proposal.detail_url is None
        assert proposal.status_url is None
        assert proposal.submission_date is None
        assert proposal.submitter is None
        assert proposal.proposal_number is None
        assert proposal.meeting_id is None
        assert proposal.summary is None

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields including metadata."""
        proposal = Proposal(
            id=1,
            content="令和6年度予算案の承認について",
            status="審議中",
            detail_url="https://example.com/proposal/001",
            status_url="https://example.com/proposal/status/001",
            submission_date="2024-01-15",
            submitter="財務委員会",
            proposal_number="議案第1号",
            meeting_id=100,
            summary="令和6年度の一般会計予算を承認する議案",
        )

        assert proposal.id == 1
        assert proposal.content == "令和6年度予算案の承認について"
        assert proposal.status == "審議中"
        assert proposal.detail_url == "https://example.com/proposal/001"
        assert proposal.status_url == "https://example.com/proposal/status/001"
        assert proposal.submission_date == "2024-01-15"
        assert proposal.submitter == "財務委員会"
        assert proposal.proposal_number == "議案第1号"
        assert proposal.meeting_id == 100
        assert proposal.summary == "令和6年度の一般会計予算を承認する議案"

    def test_str_representation_with_id(self) -> None:
        """Test string representation with ID."""
        proposal = Proposal(
            id=1,
            content="短い内容",
        )

        assert str(proposal) == "Proposal ID:1: 短い内容..."

    def test_str_representation_with_proposal_number(self) -> None:
        """Test string representation with proposal number."""
        proposal = Proposal(
            id=1,
            content="予算案について",
            proposal_number="議案第5号",
        )

        assert str(proposal) == "Proposal 議案第5号: 予算案について..."

    def test_str_representation_long_content(self) -> None:
        """Test string representation with long content."""
        long_content = (
            "これは非常に長い議案内容で、50文字を超えるような詳細な説明が含まれています。"
            "予算の詳細や実施計画などが記載されています。"
        )
        proposal = Proposal(
            id=2,
            content=long_content,
        )

        # Should truncate at 50 characters
        expected = f"Proposal ID:2: {long_content[:50]}..."
        assert str(proposal) == expected

    def test_str_representation_without_id(self) -> None:
        """Test string representation without ID."""
        proposal = Proposal(
            content="議案内容のテスト",
        )

        assert str(proposal) == "Proposal ID:None: 議案内容のテスト..."

    def test_different_status_values(self) -> None:
        """Test with different status values."""
        statuses = ["審議中", "可決", "否決", "継続審議"]

        for status in statuses:
            proposal = Proposal(
                content=f"{status}の議案",
                status=status,
            )
            assert proposal.status == status
            assert proposal.content == f"{status}の議案"

    def test_metadata_fields(self) -> None:
        """Test metadata fields with various values."""
        # Test with detail URL
        proposal_with_detail_url = Proposal(
            content="議案内容",
            detail_url="https://council.example.com/proposals/2024/001",
        )
        assert (
            proposal_with_detail_url.detail_url
            == "https://council.example.com/proposals/2024/001"
        )

        # Test with status URL
        proposal_with_status_url = Proposal(
            content="議案内容",
            status_url="https://council.example.com/proposals/status/001",
        )
        assert (
            proposal_with_status_url.status_url
            == "https://council.example.com/proposals/status/001"
        )

        # Test with submission date
        proposal_with_date = Proposal(
            content="議案内容",
            submission_date="2024-03-15",
        )
        assert proposal_with_date.submission_date == "2024-03-15"

        # Test with submitter
        proposal_with_submitter = Proposal(
            content="議案内容",
            submitter="総務委員会",
        )
        assert proposal_with_submitter.submitter == "総務委員会"

        # Test with meeting ID
        proposal_with_meeting = Proposal(
            content="議案内容",
            meeting_id=42,
        )
        assert proposal_with_meeting.meeting_id == 42

        # Test with summary
        proposal_with_summary = Proposal(
            content="議案内容",
            summary="この議案は地域振興に関する予算配分を定めるものです",
        )
        assert (
            proposal_with_summary.summary
            == "この議案は地域振興に関する予算配分を定めるものです"
        )

    def test_proposal_number_variations(self) -> None:
        """Test various proposal number formats."""
        proposal_numbers = [
            "議案第1号",
            "第123号議案",
            "2024-001",
            "令和6年議案第5号",
        ]

        for number in proposal_numbers:
            proposal = Proposal(
                content="テスト議案",
                proposal_number=number,
            )
            assert proposal.proposal_number == number
