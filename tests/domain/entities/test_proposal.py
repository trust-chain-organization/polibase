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

    def test_initialization_with_all_fields(self) -> None:
        """Test entity initialization with all fields."""
        proposal = Proposal(
            id=1,
            content="令和6年度予算案の承認について",
            status="審議中",
        )

        assert proposal.id == 1
        assert proposal.content == "令和6年度予算案の承認について"
        assert proposal.status == "審議中"

    def test_str_representation_short_content(self) -> None:
        """Test string representation with short content."""
        proposal = Proposal(
            id=1,
            content="短い内容",
        )

        assert str(proposal) == "Proposal 1: 短い内容..."

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
        expected = f"Proposal 2: {long_content[:50]}..."
        assert str(proposal) == expected

    def test_str_representation_without_id(self) -> None:
        """Test string representation without ID."""
        proposal = Proposal(
            content="議案内容のテスト",
        )

        assert str(proposal) == "Proposal None: 議案内容のテスト..."

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
