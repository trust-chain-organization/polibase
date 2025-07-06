"""LLM service interface and implementation."""

from abc import ABC, abstractmethod
from typing import Any


class ILLMService(ABC):
    """Interface for LLM service."""

    @abstractmethod
    async def match_speaker_to_politician(
        self, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Match speaker to politician using LLM."""
        pass

    @abstractmethod
    async def extract_politicians_from_html(
        self, html_content: str, party_id: int
    ) -> list[dict[str, Any]]:
        """Extract politician information from HTML."""
        pass

    @abstractmethod
    async def match_conference_member(
        self, name: str, party: str, role: str | None = None
    ) -> dict[str, Any] | None:
        """Match conference member to politician."""
        pass

    @abstractmethod
    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches from minutes text."""
        pass


class GeminiLLMService(ILLMService):
    """Gemini-based implementation of LLM service."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        # Initialize Gemini client here

    async def match_speaker_to_politician(
        self, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Match speaker to politician using Gemini."""
        # Implementation would call Gemini API
        # This is a placeholder
        return {
            "politician_id": 1,
            "politician_name": "Sample Politician",
            "confidence": 0.85,
        }

    async def extract_politicians_from_html(
        self, html_content: str, party_id: int
    ) -> list[dict[str, Any]]:
        """Extract politician information from HTML using Gemini."""
        # Implementation would call Gemini API
        # This is a placeholder
        return [
            {
                "name": "Sample Politician",
                "furigana": "サンプル セイジカ",
                "position": "議員",
                "district": "東京1区",
            }
        ]

    async def match_conference_member(
        self, name: str, party: str, role: str | None = None
    ) -> dict[str, Any] | None:
        """Match conference member to politician using Gemini."""
        # Implementation would call Gemini API
        # This is a placeholder
        return {
            "politician_id": 1,
            "politician_name": name,
            "confidence": 0.9,
        }

    async def extract_speeches_from_text(self, text: str) -> list[dict[str, str]]:
        """Extract speeches from minutes text using Gemini."""
        # Implementation would call Gemini API
        # This is a placeholder
        return [
            {
                "speaker": "議長",
                "content": "会議を開始します。",
            },
            {
                "speaker": "山田太郎",
                "content": "議案について説明します。",
            },
        ]
