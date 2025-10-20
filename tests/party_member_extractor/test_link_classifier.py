"""Tests for link classifier tool."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.party_member_extractor.tools.link_classifier import (
    LinkClassification,
    LinkClassificationResult,
    LinkClassifier,
)


class TestLinkClassifier:
    """Test cases for LinkClassifier class."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service."""
        mock_service = MagicMock()

        # Mock the get_prompt method
        mock_prompt = MagicMock()
        mock_prompt.format = MagicMock(
            return_value="Mocked prompt with {links}, {party_name}, {context}"
        )
        mock_service.get_prompt = MagicMock(return_value=mock_prompt)

        # Mock the LLM call
        mock_service.llm = MagicMock()
        mock_service.llm.ainvoke = AsyncMock()

        return mock_service

    @pytest.fixture
    def sample_links(self):
        """Sample links for testing."""
        return [
            {
                "url": "https://example.com/members/tokyo",
                "text": "東京都",
                "title": "Tokyo Members",
            },
            {
                "url": "https://example.com/members/osaka",
                "text": "大阪府",
                "title": "Osaka Members",
            },
            {
                "url": "https://example.com/members",
                "text": "議員一覧",
                "title": "All Members",
            },
        ]

    @pytest.mark.asyncio
    async def test_classify_links_success(self, mock_llm_service, sample_links):
        """Test successful link classification."""
        # Mock LLM response
        mock_response = MagicMock()
        mock_response.content = """
        [
            {
                "url": "https://example.com/members/tokyo",
                "link_type": "prefecture_list",
                "confidence": 0.95,
                "reason": "Contains prefecture name Tokyo"
            },
            {
                "url": "https://example.com/members/osaka",
                "link_type": "prefecture_list",
                "confidence": 0.95,
                "reason": "Contains prefecture name Osaka"
            },
            {
                "url": "https://example.com/members",
                "link_type": "member_list",
                "confidence": 0.9,
                "reason": "Contains keyword 'members' and '議員一覧'"
            }
        ]
        """
        mock_llm_service.llm.ainvoke.return_value = mock_response

        classifier = LinkClassifier(mock_llm_service)
        result = await classifier.classify_links(
            sample_links, party_name="Test Party", context="Member page"
        )

        # Verify result structure
        assert isinstance(result, LinkClassificationResult)
        assert len(result.classifications) == 3

        # Verify classifications
        assert result.classifications[0].link_type == "prefecture_list"
        assert result.classifications[0].confidence == 0.95
        assert result.classifications[1].link_type == "prefecture_list"
        assert result.classifications[2].link_type == "member_list"

        # Verify summary
        assert result.summary["prefecture_list"] == 2
        assert result.summary["member_list"] == 1

    @pytest.mark.asyncio
    async def test_classify_links_with_json_code_block(
        self, mock_llm_service, sample_links
    ):
        """Test classification when LLM returns JSON in code block."""
        # Mock LLM response with code block
        mock_response = MagicMock()
        mock_response.content = """
        ```json
        [
            {
                "url": "https://example.com/members/tokyo",
                "link_type": "prefecture_list",
                "confidence": 0.95,
                "reason": "Tokyo prefecture"
            }
        ]
        ```
        """
        mock_llm_service.llm.ainvoke.return_value = mock_response

        classifier = LinkClassifier(mock_llm_service)
        result = await classifier.classify_links([sample_links[0]])

        assert len(result.classifications) == 1
        assert result.classifications[0].link_type == "prefecture_list"

    @pytest.mark.asyncio
    async def test_classify_links_empty_list(self, mock_llm_service):
        """Test classification with empty link list."""
        classifier = LinkClassifier(mock_llm_service)
        result = await classifier.classify_links([])

        assert len(result.classifications) == 0
        assert result.summary == {}

    @pytest.mark.asyncio
    async def test_classify_links_invalid_json_response(
        self, mock_llm_service, sample_links
    ):
        """Test handling of invalid JSON response from LLM."""
        # Mock invalid JSON response
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"
        mock_llm_service.llm.ainvoke.return_value = mock_response

        classifier = LinkClassifier(mock_llm_service)
        result = await classifier.classify_links(sample_links)

        # Should return fallback classifications
        assert len(result.classifications) == len(sample_links)
        # All should be marked as "other" with low confidence
        for classification in result.classifications:
            assert classification.link_type == "other"
            assert classification.confidence == 0.3

    @pytest.mark.asyncio
    async def test_classify_links_llm_error(self, mock_llm_service, sample_links):
        """Test handling of LLM service error."""
        # Mock LLM error
        mock_llm_service.llm.ainvoke.side_effect = Exception("LLM service error")

        classifier = LinkClassifier(mock_llm_service)
        result = await classifier.classify_links(sample_links)

        # Should return empty result on error
        assert len(result.classifications) == 0
        assert result.summary == {}

    @pytest.mark.asyncio
    async def test_classify_links_prompt_not_available(
        self, mock_llm_service, sample_links
    ):
        """Test classification when prompt template is not available."""
        # Mock prompt error
        mock_llm_service.get_prompt.side_effect = KeyError("Prompt not found")

        # Mock LLM response for fallback prompt
        mock_response = MagicMock()
        mock_response.content = """
        [
            {
                "url": "https://example.com/members",
                "link_type": "member_list",
                "confidence": 0.8,
                "reason": "Fallback classification"
            }
        ]
        """
        mock_llm_service.llm.ainvoke.return_value = mock_response

        classifier = LinkClassifier(mock_llm_service)
        result = await classifier.classify_links([sample_links[2]])

        # Should use fallback prompt and still work
        assert len(result.classifications) == 1
        assert result.classifications[0].link_type == "member_list"

    def test_filter_by_type_basic(self):
        """Test filtering by link type."""
        # Create a sample result
        classifications = [
            LinkClassification(
                url="https://example.com/tokyo",
                link_type="prefecture_list",
                confidence=0.9,
                reason="Tokyo",
            ),
            LinkClassification(
                url="https://example.com/osaka",
                link_type="prefecture_list",
                confidence=0.85,
                reason="Osaka",
            ),
            LinkClassification(
                url="https://example.com/members",
                link_type="member_list",
                confidence=0.95,
                reason="Members",
            ),
            LinkClassification(
                url="https://example.com/about",
                link_type="other",
                confidence=0.6,
                reason="Other",
            ),
        ]
        result = LinkClassificationResult(
            classifications=classifications,
            summary={"prefecture_list": 2, "member_list": 1, "other": 1},
        )

        mock_llm_service = MagicMock()
        classifier = LinkClassifier(mock_llm_service)

        # Filter for prefecture lists
        prefecture_urls = classifier.filter_by_type(result, ["prefecture_list"])
        assert len(prefecture_urls) == 2
        assert "https://example.com/tokyo" in prefecture_urls
        assert "https://example.com/osaka" in prefecture_urls

        # Filter for member lists
        member_urls = classifier.filter_by_type(result, ["member_list"])
        assert len(member_urls) == 1
        assert "https://example.com/members" in member_urls

    def test_filter_by_type_with_confidence_threshold(self):
        """Test filtering with confidence threshold."""
        classifications = [
            LinkClassification(
                url="https://example.com/high",
                link_type="member_list",
                confidence=0.95,
                reason="High confidence",
            ),
            LinkClassification(
                url="https://example.com/medium",
                link_type="member_list",
                confidence=0.75,
                reason="Medium confidence",
            ),
            LinkClassification(
                url="https://example.com/low",
                link_type="member_list",
                confidence=0.5,
                reason="Low confidence",
            ),
        ]
        result = LinkClassificationResult(
            classifications=classifications, summary={"member_list": 3}
        )

        mock_llm_service = MagicMock()
        classifier = LinkClassifier(mock_llm_service)

        # Filter with high threshold
        high_confidence_urls = classifier.filter_by_type(
            result, ["member_list"], min_confidence=0.8
        )
        assert len(high_confidence_urls) == 1
        assert "https://example.com/high" in high_confidence_urls

        # Filter with medium threshold
        medium_confidence_urls = classifier.filter_by_type(
            result, ["member_list"], min_confidence=0.7
        )
        assert len(medium_confidence_urls) == 2

    def test_filter_by_type_multiple_types(self):
        """Test filtering for multiple link types."""
        classifications = [
            LinkClassification(
                url="https://example.com/tokyo",
                link_type="prefecture_list",
                confidence=0.9,
                reason="Tokyo",
            ),
            LinkClassification(
                url="https://example.com/members",
                link_type="member_list",
                confidence=0.95,
                reason="Members",
            ),
            LinkClassification(
                url="https://example.com/about",
                link_type="other",
                confidence=0.8,
                reason="Other",
            ),
        ]
        result = LinkClassificationResult(
            classifications=classifications,
            summary={"prefecture_list": 1, "member_list": 1, "other": 1},
        )

        mock_llm_service = MagicMock()
        classifier = LinkClassifier(mock_llm_service)

        # Filter for both prefecture and member lists
        filtered_urls = classifier.filter_by_type(
            result, ["prefecture_list", "member_list"]
        )
        assert len(filtered_urls) == 2
        assert "https://example.com/tokyo" in filtered_urls
        assert "https://example.com/members" in filtered_urls


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
