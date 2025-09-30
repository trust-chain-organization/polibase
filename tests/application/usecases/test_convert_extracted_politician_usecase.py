"""Tests for ConvertExtractedPoliticianUseCase."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.convert_extracted_politician_dto import (
    ConvertExtractedPoliticianInputDTO,
)
from src.application.usecases.convert_extracted_politician_usecase import (
    ConvertExtractedPoliticianUseCase,
)
from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


class TestConvertExtractedPoliticianUseCase:
    """Test cases for ConvertExtractedPoliticianUseCase."""

    @pytest.fixture
    def mock_extracted_politician_repo(self):
        """Create mock extracted politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_politician_repo(self):
        """Create mock politician repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def mock_speaker_repo(self):
        """Create mock speaker repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def use_case(
        self,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Create ConvertExtractedPoliticianUseCase instance."""
        return ConvertExtractedPoliticianUseCase(
            extracted_politician_repository=mock_extracted_politician_repo,
            politician_repository=mock_politician_repo,
            speaker_repository=mock_speaker_repo,
        )

    @pytest.mark.asyncio
    async def test_convert_approved_politicians(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test converting approved extracted politicians."""
        # Setup
        extracted_politicians = [
            ExtractedPolitician(
                id=1,
                name="山田太郎",
                party_id=1,
                district="東京1区",
                profile_url="https://example.com/yamada",
                status="approved",
            ),
            ExtractedPolitician(
                id=2,
                name="鈴木花子",
                party_id=2,
                district="大阪2区",
                profile_url="https://example.com/suzuki",
                status="approved",
            ),
        ]

        mock_extracted_politician_repo.get_by_status.return_value = (
            extracted_politicians
        )

        # No existing politicians
        mock_politician_repo.get_by_name_and_party.return_value = None

        # Mock speaker creation/retrieval
        mock_speaker_repo.find_by_name.return_value = None
        mock_speaker_repo.create.side_effect = [
            Speaker(id=1, name="山田太郎", is_politician=True),
            Speaker(id=2, name="鈴木花子", is_politician=True),
        ]

        # Mock politician creation
        mock_politician_repo.create.side_effect = [
            Politician(
                id=1,
                name="山田太郎",
                political_party_id=1,
                district="東京1区",
                profile_page_url="https://example.com/yamada",
            ),
            Politician(
                id=2,
                name="鈴木花子",
                political_party_id=2,
                district="大阪2区",
                profile_page_url="https://example.com/suzuki",
            ),
        ]

        # Execute
        result = await use_case.execute(ConvertExtractedPoliticianInputDTO())

        # Assertions
        assert result.total_processed == 2
        assert result.converted_count == 2
        assert result.skipped_count == 0
        assert result.error_count == 0
        assert len(result.converted_politicians) == 2

        # Verify first politician
        assert result.converted_politicians[0].name == "山田太郎"
        assert result.converted_politicians[0].politician_id == 1
        # Speaker-Politician linkage is now on the speaker side
        assert result.converted_politicians[0].party_id == 1

        # Verify status update was called
        assert mock_extracted_politician_repo.update_status.call_count == 2
        mock_extracted_politician_repo.update_status.assert_any_call(1, "converted")
        mock_extracted_politician_repo.update_status.assert_any_call(2, "converted")

    @pytest.mark.asyncio
    async def test_update_existing_politician(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test updating existing politician when converting."""
        # Setup
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京2区",  # Updated district
            profile_url="https://example.com/yamada-new",
            status="approved",
        )

        mock_extracted_politician_repo.get_by_status.return_value = [extracted]

        # Existing politician found
        existing_politician = Politician(
            id=10,
            name="山田太郎",
            political_party_id=1,
            district="東京1区",  # Old district
            profile_page_url="https://example.com/yamada-old",
        )
        mock_politician_repo.get_by_name_and_party.return_value = existing_politician

        # Mock speaker retrieval
        existing_speaker = Speaker(id=5, name="山田太郎", is_politician=True)
        mock_speaker_repo.find_by_name.return_value = existing_speaker

        # Mock politician update
        updated_politician = Politician(
            id=10,
            name="山田太郎",
            political_party_id=1,
            district="東京2区",  # Updated
            profile_page_url="https://example.com/yamada-new",  # Updated
        )
        mock_politician_repo.update.return_value = updated_politician

        # Execute
        result = await use_case.execute(ConvertExtractedPoliticianInputDTO())

        # Assertions
        assert result.total_processed == 1
        assert result.converted_count == 1
        assert result.skipped_count == 0
        assert result.error_count == 0

        # Verify update was called instead of create
        mock_politician_repo.create.assert_not_called()
        mock_politician_repo.update.assert_called_once()

        # Verify the updated values
        updated_arg = mock_politician_repo.update.call_args[0][0]
        assert updated_arg.district == "東京2区"
        assert updated_arg.profile_page_url == "https://example.com/yamada-new"

    @pytest.mark.asyncio
    async def test_dry_run_mode(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test dry run mode doesn't save changes."""
        # Setup
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            status="approved",
        )

        mock_extracted_politician_repo.get_by_status.return_value = [extracted]
        mock_politician_repo.get_by_name_and_party.return_value = None

        # Execute with dry_run=True
        result = await use_case.execute(
            ConvertExtractedPoliticianInputDTO(dry_run=True)
        )

        # Assertions
        assert result.total_processed == 1
        assert result.converted_count == 1  # Simulated conversion

        # Verify no actual changes were made
        mock_speaker_repo.create.assert_not_called()
        mock_politician_repo.create.assert_not_called()
        mock_extracted_politician_repo.update_status.assert_not_called()

    @pytest.mark.asyncio
    async def test_filter_by_party_id(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test filtering by party_id."""
        # Setup
        extracted_politicians = [
            ExtractedPolitician(id=1, name="山田太郎", party_id=1, status="approved"),
            ExtractedPolitician(id=2, name="鈴木花子", party_id=2, status="approved"),
            ExtractedPolitician(id=3, name="佐藤一郎", party_id=1, status="approved"),
        ]

        mock_extracted_politician_repo.get_by_status.return_value = (
            extracted_politicians
        )

        # Mock speaker and politician creation for party_id=1 only
        mock_speaker_repo.find_by_name.return_value = None
        mock_speaker_repo.create.side_effect = [
            Speaker(id=1, name="山田太郎", is_politician=True),
            Speaker(id=3, name="佐藤一郎", is_politician=True),
        ]

        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_politician_repo.create.side_effect = [
            Politician(id=1, name="山田太郎", political_party_id=1),
            Politician(id=3, name="佐藤一郎", political_party_id=1),
        ]

        # Execute with party_id filter
        result = await use_case.execute(ConvertExtractedPoliticianInputDTO(party_id=1))

        # Assertions
        assert result.total_processed == 2  # Only party_id=1 politicians
        assert result.converted_count == 2
        assert all(p.party_id == 1 for p in result.converted_politicians)

    @pytest.mark.asyncio
    async def test_batch_size_limit(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test batch size limiting."""
        # Setup - create more politicians than batch size
        extracted_politicians = [
            ExtractedPolitician(id=i, name=f"政治家{i}", party_id=1, status="approved")
            for i in range(1, 6)  # 5 politicians
        ]

        mock_extracted_politician_repo.get_by_status.return_value = (
            extracted_politicians
        )

        # Mock speaker and politician creation for batch_size=3
        mock_speaker_repo.find_by_name.return_value = None
        mock_speaker_repo.create.side_effect = [
            Speaker(id=i, name=f"政治家{i}", is_politician=True) for i in range(1, 4)
        ]

        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_politician_repo.create.side_effect = [
            Politician(id=i, name=f"政治家{i}", political_party_id=1)
            for i in range(1, 4)
        ]

        # Execute with batch_size=3
        result = await use_case.execute(
            ConvertExtractedPoliticianInputDTO(batch_size=3)
        )

        # Assertions
        assert result.total_processed == 3  # Limited by batch_size
        assert result.converted_count == 3

    @pytest.mark.asyncio
    async def test_handle_conversion_error(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """Test handling errors during conversion."""
        # Setup
        extracted_politicians = [
            ExtractedPolitician(id=1, name="山田太郎", party_id=1, status="approved"),
            ExtractedPolitician(id=2, name="鈴木花子", party_id=2, status="approved"),
        ]

        mock_extracted_politician_repo.get_by_status.return_value = (
            extracted_politicians
        )

        # First speaker creation succeeds, second fails
        mock_speaker_repo.find_by_name.return_value = None
        mock_speaker_repo.create.side_effect = [
            Speaker(id=1, name="山田太郎", is_politician=True),
            Exception("Database error"),
        ]

        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_politician_repo.create.return_value = Politician(
            id=1, name="山田太郎", political_party_id=1
        )

        # Execute
        result = await use_case.execute(ConvertExtractedPoliticianInputDTO())

        # Assertions
        assert result.total_processed == 2
        # Both politicians created despite speaker error
        assert result.converted_count == 2
        # Speaker creation error is handled gracefully
        assert result.error_count == 0
