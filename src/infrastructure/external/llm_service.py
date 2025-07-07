"""LLM service interface and implementation."""

from abc import ABC, abstractmethod

from src.domain.types import (
    LLMExtractResult,
    LLMMatchResult,
    LLMSpeakerMatchContext,
    PoliticianDTO,
)


class ILLMService(ABC):
    """Interface for LLM service."""

    @abstractmethod
    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match speaker to politician using LLM."""
        pass

    @abstractmethod
    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract politician information from HTML using LLM."""
        pass


class GeminiLLMService(ILLMService):
    """Gemini-based implementation of LLM service."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        self.api_key = api_key
        self.model_name = model_name
        # Initialize Gemini client here

    async def match_speaker_to_politician(
        self, context: LLMSpeakerMatchContext
    ) -> LLMMatchResult | None:
        """Match speaker to politician using Gemini."""
        # Implementation would call Gemini API
        # This is a placeholder
        return LLMMatchResult(
            matched=True,
            confidence=0.85,
            reason="Sample match",
            matched_id=1,
            metadata={"politician_name": "Sample Politician"},
        )

    async def extract_party_members(
        self, html_content: str, party_id: int
    ) -> LLMExtractResult:
        """Extract politician information from HTML using Gemini."""
        # Implementation would call Gemini API
        # This is a placeholder
        return LLMExtractResult(
            success=True,
            extracted_data=[
                {
                    "name": "Sample Politician",
                    "furigana": "サンプル セイジカ",
                    "position": "議員",
                    "district": "東京1区",
                }
            ],
            error=None,
            metadata={"party_id": str(party_id)},
        )

    async def match_conference_member(
        self, member_name: str, party_name: str | None, candidates: list[PoliticianDTO]
    ) -> LLMMatchResult | None:
        """Match conference member to politician using Gemini."""
        # Implementation would call Gemini API
        # This is a placeholder
        return LLMMatchResult(
            matched=True,
            confidence=0.9,
            reason="High confidence match",
            matched_id=1,
            metadata={"politician_name": member_name},
        )

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
