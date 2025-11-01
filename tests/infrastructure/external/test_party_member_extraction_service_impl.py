"""Tests for PartyMemberExtractionServiceImpl."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.external.party_member_extraction_service_impl import (
    PartyMemberExtractionServiceImpl,
)


class TestPartyMemberExtractionServiceImpl:
    """Test cases for PartyMemberExtractionServiceImpl."""

    @pytest.mark.asyncio
    async def test_invalid_html_content(self):
        """Test handling of invalid HTML content."""
        # Arrange
        llm_service = MagicMock()
        service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="html_content.*empty"):
            await service.extract_from_html(
                html_content="",
                source_url="https://example.com/invalid",
                party_name="テスト党",
            )

    @pytest.mark.asyncio
    async def test_empty_party_name(self):
        """Test handling of empty party name."""
        # Arrange
        llm_service = MagicMock()
        service = PartyMemberExtractionServiceImpl(llm_service, party_id=1)

        # Act & Assert
        with pytest.raises(ValueError, match="party_name.*empty"):
            await service.extract_from_html(
                html_content="<html><body>test</body></html>",
                source_url="https://example.com/members",
                party_name="",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
