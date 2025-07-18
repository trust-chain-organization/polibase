"""Tests for LLM service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.types import LLMSpeakerMatchContext
from src.infrastructure.external.llm_service import GeminiLLMService


class TestGeminiLLMService:
    """Test cases for GeminiLLMService."""

    @pytest.fixture
    def service(self):
        """Create LLM service instance."""
        with patch(
            "src.infrastructure.external.llm_service.ChatGoogleGenerativeAI"
        ) as mock_llm:
            mock_llm.return_value = MagicMock()
            return GeminiLLMService(api_key="test-key", model_name="gemini-2.0-flash")

    @pytest.mark.asyncio
    async def test_match_speaker_to_politician(self, service):
        """Test speaker to politician matching."""
        # Setup
        context = LLMSpeakerMatchContext(
            speaker_name="山田太郎",
            normalized_name="山田太郎",
            party_affiliation="自民党",
            position="議長",
            meeting_date="2023-01-01",
            candidates=[
                {
                    "id": "1",
                    "name": "山田太郎",
                    "party_name": "自民党",
                    "position": "衆議院議員",
                    "district": "東京1区",
                },
                {
                    "id": "2",
                    "name": "山田次郎",
                    "party_name": "立憲民主党",
                    "position": "参議院議員",
                    "district": "比例区",
                },
            ],
        )

        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = """
        {
            "matched": true,
            "confidence": 0.95,
            "reason": "Name and party affiliation match exactly",
            "matched_id": 1
        }
        """

        # Mock the chain.ainvoke call
        with patch.object(service._llm, "ainvoke"):
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)

            with patch(
                "langchain_core.prompts.ChatPromptTemplate.from_template"
            ) as mock_template:
                mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

                # Execute
                result = await service.match_speaker_to_politician(context)

        # Verify
        assert result is not None
        assert result["matched"] is True
        assert result["confidence"] > 0.0
        assert result["confidence"] <= 1.0
        assert result["reason"] is not None
        assert result["matched_id"] is not None
        assert result["metadata"] is not None

    @pytest.mark.asyncio
    async def test_extract_party_members(self, service):
        """Test party member extraction from HTML."""
        # Setup
        html_content = """
        <div class="member-list">
            <div class="member">
                <h3>山田太郎</h3>
                <p>やまだ たろう</p>
                <p>衆議院議員・東京1区</p>
            </div>
            <div class="member">
                <h3>鈴木花子</h3>
                <p>すずき はなこ</p>
                <p>参議院議員・比例区</p>
            </div>
        </div>
        """

        # Mock the LLM response
        mock_response = MagicMock()
        mock_response.content = """
        {
            "success": true,
            "extracted_data": [
                {
                    "name": "山田太郎",
                    "furigana": "ヤマダ タロウ",
                    "position": "衆議院議員",
                    "district": "東京1区"
                },
                {
                    "name": "鈴木花子",
                    "furigana": "スズキ ハナコ",
                    "position": "参議院議員",
                    "district": "比例区"
                }
            ],
            "error": null
        }
        """

        # Mock the chain.ainvoke call
        with patch.object(service._llm, "ainvoke"):
            mock_chain = MagicMock()
            mock_chain.ainvoke = AsyncMock(return_value=mock_response)

            with patch(
                "langchain_core.prompts.ChatPromptTemplate.from_template"
            ) as mock_template:
                mock_template.return_value.__or__ = MagicMock(return_value=mock_chain)

                # Execute
                result = await service.extract_party_members(html_content, party_id=1)

        # Verify
        assert result["success"] is True
        assert result["error"] is None
        assert result["extracted_data"] is not None
        assert len(result["extracted_data"]) > 0

        # Check first extracted member
        first_member = result["extracted_data"][0]
        assert "name" in first_member
        assert first_member["name"] is not None

        # Check metadata
        assert result["metadata"] is not None
        assert result["metadata"].get("party_id") == "1"

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test service initialization with different parameters."""
        with patch(
            "src.infrastructure.external.llm_service.ChatGoogleGenerativeAI"
        ) as mock_llm:
            mock_llm.return_value = MagicMock()

            # Test with default model
            service1 = GeminiLLMService(api_key="key1")
            assert service1.api_key == "key1"
            assert service1.model_name == "gemini-2.0-flash"

            # Test with custom model
            service2 = GeminiLLMService(api_key="key2", model_name="gemini-1.5-pro")
            assert service2.api_key == "key2"
            assert service2.model_name == "gemini-1.5-pro"

            # Test with another model variant
            service3 = GeminiLLMService(api_key="key3", model_name="gemini-1.5-flash")
            assert service3.api_key == "key3"
            assert service3.model_name == "gemini-1.5-flash"
