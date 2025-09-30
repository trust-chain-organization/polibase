"""Tests for ReviewAndConvertPoliticianUseCase integration."""

from unittest.mock import AsyncMock

import pytest

from src.application.dtos.review_extracted_politician_dto import (
    ReviewExtractedPoliticianInputDTO,
)
from src.application.usecases.convert_extracted_politician_usecase import (
    ConvertExtractedPoliticianUseCase,
)
from src.application.usecases.review_and_convert_politician_usecase import (
    ReviewAndConvertPoliticianUseCase,
)
from src.application.usecases.review_extracted_politician_usecase import (
    ReviewExtractedPoliticianUseCase,
)
from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


class TestReviewAndConvertPoliticianUseCase:
    """Test cases for ReviewAndConvertPoliticianUseCase integration."""

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
    def mock_party_repo(self):
        """Create mock party repository."""
        repo = AsyncMock()
        return repo

    @pytest.fixture
    def review_use_case(self, mock_extracted_politician_repo, mock_party_repo):
        """Create ReviewExtractedPoliticianUseCase instance."""
        return ReviewExtractedPoliticianUseCase(
            mock_extracted_politician_repo, mock_party_repo
        )

    @pytest.fixture
    def convert_use_case(
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

    @pytest.fixture
    def use_case(
        self,
        review_use_case,
        convert_use_case,
        mock_extracted_politician_repo,
    ):
        """Create ReviewAndConvertPoliticianUseCase instance."""
        return ReviewAndConvertPoliticianUseCase(
            review_use_case=review_use_case,
            convert_use_case=convert_use_case,
            extracted_politician_repository=mock_extracted_politician_repo,
        )

    @pytest.mark.asyncio
    async def test_approval_to_politician_conversion_flow(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """承認から政治家作成までの完全なフローをテスト.

        End-to-Endテスト:
        1. ExtractedPoliticianを作成
        2. 承認処理
        3. 自動変換の確認
        4. Politicianテーブルへの保存確認
        5. ステータス更新の確認
        """
        # Setup - ExtractedPolitician
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            profile_url="https://example.com/yamada",
            status="pending",
        )

        # Mock for review step
        mock_extracted_politician_repo.get_by_id.return_value = extracted
        approved_politician = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            profile_url="https://example.com/yamada",
            status="approved",
        )
        mock_extracted_politician_repo.update_status.return_value = approved_politician

        # Mock for conversion step
        mock_extracted_politician_repo.get_by_status.return_value = [
            approved_politician
        ]
        mock_politician_repo.get_by_name_and_party.return_value = None
        mock_speaker_repo.find_by_name.return_value = None

        # Mock speaker and politician creation
        created_speaker = Speaker(id=1, name="山田太郎", is_politician=True)
        mock_speaker_repo.create.return_value = created_speaker

        created_politician = Politician(
            id=1,
            name="山田太郎",
            political_party_id=1,
            district="東京1区",
            profile_page_url="https://example.com/yamada",
        )
        mock_politician_repo.create.return_value = created_politician

        # Execute - Review with auto-conversion
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="approve", reviewer_id=1
        )
        result = await use_case.review_with_auto_convert(request, auto_convert=True)

        # Assertions
        assert result.success is True
        assert result.politician_id == 1
        assert result.new_status == "approved"
        assert "converted to politician" in result.message

        # Verify status update was called for both review and conversion
        assert mock_extracted_politician_repo.update_status.call_count >= 1
        # Review step calls update_status with reviewer_id
        mock_extracted_politician_repo.update_status.assert_any_call(1, "approved", 1)

        # Verify politician creation
        mock_politician_repo.create.assert_called_once()
        mock_speaker_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_conversion_failure_handling(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """変換失敗時のエラーハンドリング.

        エラーケーステスト:
        1. 変換エラーをモック
        2. 承認処理実行
        3. エラーメッセージの確認
        4. ステータスが'approved'のままであることを確認
        """
        # Setup
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            status="pending",
        )

        # Mock for review step (succeeds)
        mock_extracted_politician_repo.get_by_id.return_value = extracted
        approved_politician = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京1区",
            status="approved",
        )
        mock_extracted_politician_repo.update_status.return_value = approved_politician

        # Mock for conversion step (fails)
        mock_extracted_politician_repo.get_by_status.side_effect = Exception(
            "Database connection error"
        )

        # Execute
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="approve", reviewer_id=1
        )
        result = await use_case.review_with_auto_convert(request, auto_convert=True)

        # Assertions
        assert result.success is True  # Review succeeded
        assert result.new_status == "approved"
        assert "auto-conversion failed" in result.message

        # Verify status was updated to approved (not converted)
        mock_extracted_politician_repo.update_status.assert_called_with(
            1, "approved", 1
        )

        # Verify politician creation was not completed
        mock_politician_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_duplicate_politician_handling(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """重複政治家の処理.

        重複チェックテスト:
        1. 既存の政治家を作成
        2. 同名・同政党のExtractedPoliticianを承認
        3. 更新処理の確認
        4. 重複作成されていないことを確認
        """
        # Setup - Extracted politician
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京2区",  # Updated district
            profile_url="https://example.com/yamada-new",
            status="pending",
        )

        # Mock for review step
        mock_extracted_politician_repo.get_by_id.return_value = extracted
        approved_politician = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            district="東京2区",
            profile_url="https://example.com/yamada-new",
            status="approved",
        )
        mock_extracted_politician_repo.update_status.return_value = approved_politician

        # Mock for conversion step - existing politician found
        mock_extracted_politician_repo.get_by_status.return_value = [
            approved_politician
        ]
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
            district="東京2区",
            profile_page_url="https://example.com/yamada-new",
        )
        mock_politician_repo.update.return_value = updated_politician

        # Execute
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="approve", reviewer_id=1
        )
        result = await use_case.review_with_auto_convert(request, auto_convert=True)

        # Assertions
        assert result.success is True
        assert "converted to politician" in result.message

        # Verify update was called instead of create
        mock_politician_repo.create.assert_not_called()
        mock_politician_repo.update.assert_called_once()

        # Verify the updated values
        updated_arg = mock_politician_repo.update.call_args[0][0]
        assert updated_arg.district == "東京2区"
        assert updated_arg.profile_page_url == "https://example.com/yamada-new"

    @pytest.mark.asyncio
    async def test_auto_convert_disabled(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
        mock_speaker_repo,
    ):
        """自動変換が無効な場合のテスト.

        承認のみで変換しない:
        1. auto_convert=Falseで承認
        2. 承認は成功
        3. 変換は実行されない
        """
        # Setup
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            status="pending",
        )

        mock_extracted_politician_repo.get_by_id.return_value = extracted
        approved_politician = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            status="approved",
        )
        mock_extracted_politician_repo.update_status.return_value = approved_politician

        # Execute with auto_convert=False
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="approve", reviewer_id=1
        )
        result = await use_case.review_with_auto_convert(request, auto_convert=False)

        # Assertions
        assert result.success is True
        assert result.new_status == "approved"
        assert "converted" not in result.message

        # Verify conversion was not attempted
        mock_extracted_politician_repo.get_by_status.assert_not_called()
        mock_politician_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_reject_does_not_convert(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
    ):
        """拒否時は変換しないことを確認.

        拒否の場合:
        1. actionが'reject'
        2. 拒否は成功
        3. 変換は実行されない
        """
        # Setup
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            status="pending",
        )

        mock_extracted_politician_repo.get_by_id.return_value = extracted
        rejected_politician = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=1,
            status="rejected",
        )
        mock_extracted_politician_repo.update_status.return_value = rejected_politician

        # Execute with reject action
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="reject", reviewer_id=1
        )
        result = await use_case.review_with_auto_convert(request, auto_convert=True)

        # Assertions
        assert result.success is True
        assert result.new_status == "rejected"
        assert "converted" not in result.message

        # Verify conversion was not attempted
        mock_extracted_politician_repo.get_by_status.assert_not_called()
        mock_politician_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_missing_party_id_handling(
        self,
        use_case,
        mock_extracted_politician_repo,
    ):
        """party_idが欠落している場合のハンドリング.

        エラーケース:
        1. party_idがNoneの政治家を承認
        2. 承認は成功
        3. 変換はスキップされる
        """
        # Setup
        extracted = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=None,  # Missing party_id
            status="pending",
        )

        mock_extracted_politician_repo.get_by_id.return_value = extracted
        approved_politician = ExtractedPolitician(
            id=1,
            name="山田太郎",
            party_id=None,
            status="approved",
        )
        mock_extracted_politician_repo.update_status.return_value = approved_politician

        # Execute
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=1, action="approve", reviewer_id=1
        )
        result = await use_case.review_with_auto_convert(request, auto_convert=True)

        # Assertions
        assert result.success is True
        assert result.new_status == "approved"
        assert "auto-conversion skipped: no party" in result.message

    @pytest.mark.asyncio
    async def test_review_failure_prevents_conversion(
        self,
        use_case,
        mock_extracted_politician_repo,
        mock_politician_repo,
    ):
        """承認失敗時は変換を実行しない.

        エラーケース:
        1. 承認処理が失敗
        2. 変換は実行されない
        """
        # Setup - Politician not found
        mock_extracted_politician_repo.get_by_id.return_value = None

        # Execute
        request = ReviewExtractedPoliticianInputDTO(
            politician_id=999, action="approve", reviewer_id=1
        )
        result = await use_case.review_with_auto_convert(request, auto_convert=True)

        # Assertions
        assert result.success is False
        assert "not found" in result.message

        # Verify conversion was not attempted
        mock_extracted_politician_repo.get_by_status.assert_not_called()
        mock_politician_repo.create.assert_not_called()
