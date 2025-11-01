"""Tests for PartyMemberExtractionServiceImpl."""

from __future__ import annotations

import pytest

from src.domain.services.party_member_extraction_service import (
    ExtractedMember,
    MemberExtractionResult,
)
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.party_member_extraction_service_impl import (
    PartyMemberExtractionServiceImpl,
)
from tests.utils.llm_mock import LLMServiceMock


class TestPartyMemberExtractionServiceImpl:
    """Test cases for PartyMemberExtractionServiceImpl."""

    @pytest.fixture
    def sample_html(self) -> str:
        """Create sample HTML content for testing."""
        return """
        <html>
            <body>
                <div class="member">
                    <h3>山田太郎</h3>
                    <p>衆議院議員（東京1区）</p>
                </div>
                <div class="member">
                    <h3>佐藤花子</h3>
                    <p>参議院議員（大阪府）</p>
                </div>
            </body>
        </html>
        """

    @pytest.fixture
    def sample_extraction_response(self) -> list[dict]:
        """Create sample LLM extraction response."""
        return [
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "electoral_district": "東京1区",
                "prefecture": "東京都",
                "profile_url": None,
                "party_position": None,
            },
            {
                "name": "佐藤花子",
                "position": "参議院議員",
                "electoral_district": None,
                "prefecture": "大阪府",
                "profile_url": None,
                "party_position": None,
            },
        ]

    @pytest.mark.asyncio
    async def test_successful_extraction(self, sample_html, sample_extraction_response):
        """Test successful extraction of party members from HTML."""
        # Arrange
        with LLMServiceMock([sample_extraction_response]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act
            result = await service.extract_from_html(
                html_content=sample_html,
                source_url="https://example.com/members",
                party_name="テスト党",
            )

            # Assert
            assert result.extraction_successful is True
            assert len(result.members) == 2
            assert result.source_url == "https://example.com/members"
            assert result.error_message is None

            # Check first member
            assert result.members[0].name == "山田太郎"
            assert result.members[0].position == "衆議院議員"
            assert result.members[0].electoral_district == "東京1区"

    @pytest.mark.asyncio
    async def test_extraction_with_profile_urls(self):
        """Test extraction including profile URLs."""
        # Arrange
        html = """
        <div class="member">
            <a href="/profile/yamada">山田太郎</a>
            <p>幹事長</p>
        </div>
        """

        extraction_response = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "electoral_district": None,
                "prefecture": None,
                "profile_url": "https://example.com/profile/yamada",
                "party_position": "幹事長",
            }
        ]

        with LLMServiceMock([extraction_response]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act
            result = await service.extract_from_html(
                html_content=html,
                source_url="https://example.com/members",
                party_name="テスト党",
            )

            # Assert
            assert result.extraction_successful is True
            assert len(result.members) == 1
            assert result.members[0].profile_url == "https://example.com/profile/yamada"
            assert result.members[0].party_position == "幹事長"

    @pytest.mark.asyncio
    async def test_empty_html_content(self):
        """Test handling of empty HTML content."""
        # Arrange
        with LLMServiceMock([[]]):  # Empty extraction result
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act
            result = await service.extract_from_html(
                html_content="<html><body></body></html>",
                source_url="https://example.com/empty",
                party_name="テスト党",
            )

            # Assert
            assert result.extraction_successful is True
            assert len(result.members) == 0
            assert result.source_url == "https://example.com/empty"

    @pytest.mark.asyncio
    async def test_invalid_html_content(self):
        """Test handling of invalid HTML content."""
        # Arrange
        with LLMServiceMock([[]]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act & Assert
            with pytest.raises(ValueError, match="html_content.*empty"):
                await service.extract_from_html(
                    html_content="",
                    source_url="https://example.com/invalid",
                    party_name="テスト党",
                )

    @pytest.mark.asyncio
    async def test_empty_party_name(self, sample_html):
        """Test handling of empty party name."""
        # Arrange
        with LLMServiceMock([]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act & Assert
            with pytest.raises(ValueError, match="party_name.*empty"):
                await service.extract_from_html(
                    html_content=sample_html,
                    source_url="https://example.com/members",
                    party_name="",
                )

    @pytest.mark.asyncio
    async def test_extraction_with_multiple_pages(self):
        """Test extraction handling pagination information."""
        # Arrange
        html = """
        <div class="members">
            <div>山田太郎</div>
            <div>佐藤花子</div>
            <a href="?page=2">次のページ</a>
        </div>
        """

        extraction_response = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "electoral_district": None,
                "prefecture": None,
                "profile_url": None,
                "party_position": None,
            },
            {
                "name": "佐藤花子",
                "position": "参議院議員",
                "electoral_district": None,
                "prefecture": None,
                "profile_url": None,
                "party_position": None,
            },
        ]

        with LLMServiceMock([extraction_response]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act
            result = await service.extract_from_html(
                html_content=html,
                source_url="https://example.com/members?page=1",
                party_name="テスト党",
            )

            # Assert
            assert result.extraction_successful is True
            assert len(result.members) == 2

    @pytest.mark.asyncio
    async def test_duplicate_member_handling(self):
        """Test handling of duplicate members in extraction."""
        # Arrange
        extraction_response = [
            {
                "name": "山田太郎",
                "position": "衆議院議員",
                "electoral_district": "東京1区",
                "prefecture": "東京都",
                "profile_url": None,
                "party_position": None,
            },
            {
                "name": "山田太郎",  # Duplicate
                "position": "衆議院議員",
                "electoral_district": "東京1区",
                "prefecture": "東京都",
                "profile_url": None,
                "party_position": None,
            },
        ]

        with LLMServiceMock([extraction_response]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act
            result = await service.extract_from_html(
                html_content="<html><body>content</body></html>",
                source_url="https://example.com/members",
                party_name="テスト党",
            )

            # Assert
            # Should extract both (duplicate handling is done at repository level)
            assert result.extraction_successful is True
            assert len(result.members) == 2

    @pytest.mark.asyncio
    async def test_extraction_with_special_characters(self):
        """Test extraction with special characters in names."""
        # Arrange
        html = """
        <div>
            <p>山﨑太郎（やまざきたろう）</p>
            <p>髙橋花子（たかはしはなこ）</p>
        </div>
        """

        extraction_response = [
            {
                "name": "山﨑太郎",  # 特殊文字（﨑）
                "position": "衆議院議員",
                "electoral_district": None,
                "prefecture": None,
                "profile_url": None,
                "party_position": None,
            },
            {
                "name": "髙橋花子",  # 特殊文字（髙）
                "position": "参議院議員",
                "electoral_district": None,
                "prefecture": None,
                "profile_url": None,
                "party_position": None,
            },
        ]

        with LLMServiceMock([extraction_response]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act
            result = await service.extract_from_html(
                html_content=html,
                source_url="https://example.com/members",
                party_name="テスト党",
            )

            # Assert
            assert result.extraction_successful is True
            assert len(result.members) == 2
            assert result.members[0].name == "山﨑太郎"
            assert result.members[1].name == "髙橋花子"

    @pytest.mark.asyncio
    async def test_llm_error_handling(self, sample_html):
        """Test error handling when LLM extraction fails."""
        # Arrange
        with LLMServiceMock(["invalid response"]):  # Invalid response format
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act & Assert
            from src.infrastructure.error_handling.exceptions import (
                ExternalServiceException,
            )

            with pytest.raises(ExternalServiceException):
                await service.extract_from_html(
                    html_content=sample_html,
                    source_url="https://example.com/members",
                    party_name="テスト党",
                )

    @pytest.mark.asyncio
    async def test_extraction_result_data_structure(self, sample_extraction_response):
        """Test the structure of extraction result data."""
        # Arrange
        with LLMServiceMock([sample_extraction_response]):
            llm_service = GeminiLLMService()
            service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

            # Act
            result = await service.extract_from_html(
                html_content="<html><body>content</body></html>",
                source_url="https://example.com/members",
                party_name="テスト党",
            )

            # Assert
            # Verify MemberExtractionResult structure
            assert isinstance(result, MemberExtractionResult)
            assert isinstance(result.members, list)
            assert result.extraction_successful is True
            assert isinstance(result.source_url, str)
            assert result.error_message is None

            # Verify ExtractedMember structure
            for member in result.members:
                assert isinstance(member, ExtractedMember)
                assert isinstance(member.name, str)
                assert member.position is None or isinstance(member.position, str)
                assert member.electoral_district is None or isinstance(
                    member.electoral_district, str
                )
                assert member.prefecture is None or isinstance(member.prefecture, str)
                assert member.profile_url is None or isinstance(member.profile_url, str)
                assert member.party_position is None or isinstance(
                    member.party_position, str
                )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
