"""Tests for PoliticianMatchingService."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.domain.exceptions import ExternalServiceException
from src.domain.services.politician_matching_service import (
    PoliticianMatchingService,
)


class TestPoliticianMatchingService:
    """Test cases for PoliticianMatchingService."""

    @pytest.fixture
    def mock_politician_repository(self):
        """Create a mock politician repository."""
        return AsyncMock()

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        mock = MagicMock()
        mock.get_prompt.return_value = MagicMock()
        mock.invoke_with_retry = MagicMock()
        return mock

    @pytest.fixture
    def sample_politicians(self) -> list[dict]:
        """Create sample politicians for testing (as dicts from repository)."""
        return [
            {
                "id": 1,
                "name": "山田太郎",
                "party_name": "テスト党",
                "position": "衆議院議員",
                "prefecture": "東京都",
                "electoral_district": "東京1区",
            },
            {
                "id": 2,
                "name": "佐藤花子",
                "party_name": "テスト党",
                "position": "参議院議員",
                "prefecture": "大阪府",
                "electoral_district": None,
            },
            {
                "id": 3,
                "name": "鈴木一郎",
                "party_name": "サンプル党",
                "position": "衆議院議員",
                "prefecture": "神奈川県",
                "electoral_district": "神奈川3区",
            },
        ]

    @pytest.mark.asyncio
    async def test_exact_match_with_party(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test exact name match with matching party."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party="テスト党"
        )

        # Assert
        # Rule-based matching should succeed with high confidence
        assert result.matched is True
        assert result.confidence >= 0.9
        assert result.politician_id == 1
        assert result.politician_name == "山田太郎"

    @pytest.mark.asyncio
    async def test_match_with_honorific(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test matching with honorific (敬称) in speaker name."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response for honorific matching
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 2,
            "politician_name": "佐藤花子",
            "political_party_name": "テスト党",
            "confidence": 0.95,
            "reason": "敬称を除いた名前が完全一致",
        }

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="佐藤花子議員", speaker_party="テスト党"
        )

        # Assert
        assert result.matched is True
        assert result.politician_id == 2
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_no_match_nonexistent_name(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test no match when name doesn't exist."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response for no match
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": False,
            "politician_id": None,
            "politician_name": None,
            "political_party_name": None,
            "confidence": 0.3,
            "reason": "候補者が見つかりません",
        }

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="存在しない太郎", speaker_party="テスト党"
        )

        # Assert
        assert result.matched is False
        assert result.politician_id is None

    @pytest.mark.asyncio
    async def test_low_confidence_treated_as_no_match(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test that low confidence results are treated as no match."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response with low confidence
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 1,
            "politician_name": "山田太郎",
            "political_party_name": "テスト党",
            "confidence": 0.5,  # Low confidence (< 0.7 threshold)
            "reason": "類似性が低い",
        }

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="山田次郎", speaker_party="テスト党"
        )

        # Assert
        # Low confidence (< 0.7) should be treated as no match
        assert result.matched is False
        assert result.politician_id is None
        assert result.politician_name is None

    @pytest.mark.asyncio
    async def test_empty_politician_list(
        self, mock_llm_service, mock_politician_repository
    ):
        """Test behavior when politician list is empty."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = []

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party="テスト党"
        )

        # Assert
        assert result.matched is False
        assert result.confidence == 0.0
        assert "利用可能な政治家リストが空です" in result.reason

    @pytest.mark.asyncio
    async def test_match_without_party_info(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test matching when party information is not provided."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 1,
            "politician_name": "山田太郎",
            "political_party_name": "テスト党",
            "confidence": 0.85,
            "reason": "名前が一致",
        }

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party=None
        )

        # Assert
        assert result.matched is True
        assert result.politician_id == 1
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_kana_name_variation_matching(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test matching with kana name variations."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM response for kana matching
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 3,
            "politician_name": "鈴木一郎",
            "political_party_name": "サンプル党",
            "confidence": 0.92,
            "reason": "読み仮名が一致",
        }

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="すずきいちろう", speaker_party="サンプル党"
        )

        # Assert
        assert result.matched is True
        assert result.politician_id == 3
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_multiple_candidates_best_match(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test selecting best match when multiple candidates exist."""
        # Arrange
        # Add another politician with similar name
        politicians_with_duplicates = sample_politicians + [
            {
                "id": 4,
                "name": "山田太郎",
                "party_name": "別の党",
                "position": "衆議院議員",
                "prefecture": "北海道",
                "electoral_district": "北海道1区",
            }
        ]
        mock_politician_repository.get_all_for_matching.return_value = (
            politicians_with_duplicates
        )

        # Mock LLM response selecting the correct party
        mock_llm_service.invoke_with_retry.return_value = {
            "matched": True,
            "politician_id": 1,  # Should match the one with correct party
            "politician_name": "山田太郎",
            "political_party_name": "テスト党",
            "confidence": 0.98,
            "reason": "名前と政党が一致",
        }

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act
        result = await service.find_best_match(
            speaker_name="山田太郎", speaker_party="テスト党"
        )

        # Assert
        # Rule-based matching should work for exact match
        assert result.matched is True
        assert result.politician_id == 1  # Should match the correct party
        assert result.confidence >= 0.9

    @pytest.mark.asyncio
    async def test_llm_error_handling(
        self, mock_llm_service, mock_politician_repository, sample_politicians
    ):
        """Test error handling when LLM returns unexpected format."""
        # Arrange
        mock_politician_repository.get_all_for_matching.return_value = (
            sample_politicians
        )

        # Mock LLM to raise an exception
        mock_llm_service.invoke_with_retry.side_effect = ExternalServiceException(
            service_name="LLM",
            operation="politician_matching",
            reason="Test error",
        )

        service = PoliticianMatchingService(
            mock_llm_service, mock_politician_repository
        )

        # Act & Assert
        # Should raise ExternalServiceException
        with pytest.raises(ExternalServiceException):
            # Use a name that won't match rule-based to trigger LLM
            await service.find_best_match(
                speaker_name="存在しない政治家", speaker_party="存在しない党"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
