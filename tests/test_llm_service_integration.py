"""Integration tests for LLMService and its usage across the system"""

import pytest
from pydantic import BaseModel
from pytest import MonkeyPatch  # Add the import for type annotation

from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.party_member_extractor.models import PartyMemberInfo, PartyMemberList
from src.services.llm_errors import LLMError, LLMRateLimitError
from src.services.llm_factory import LLMServiceFactory
from src.services.llm_service import LLMService
from src.services.prompt_loader import PromptLoader
from src.test_utils.llm_mock import LLMServiceMock, mock_llm_service


class TestLLMService:
    """Test LLMService functionality"""

    def test_factory_creates_service(self, monkeypatch: MonkeyPatch) -> None:
        """Test that factory creates service instances correctly"""
        # Set dummy API key for testing
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        factory = LLMServiceFactory()

        # Test different presets
        fast_service = factory.create_fast()
        assert isinstance(fast_service, InstrumentedLLMService)
        assert fast_service.model_name == "gemini-1.5-flash"

        advanced_service = factory.create_advanced()
        assert isinstance(advanced_service, InstrumentedLLMService)
        assert advanced_service.model_name == "gemini-2.0-flash-exp"

        creative_service = factory.create_creative()
        assert isinstance(creative_service, InstrumentedLLMService)
        assert creative_service.temperature == 0.7

        precise_service = factory.create_precise()
        assert isinstance(precise_service, InstrumentedLLMService)
        assert precise_service.temperature == 0.0

    def test_prompt_loader(self) -> None:
        """Test prompt loader functionality"""
        loader = PromptLoader()

        # Test loading prompts
        prompts = loader.list_prompts()
        assert len(prompts) > 0
        assert "minutes_divide" in prompts
        assert "speaker_match" in prompts
        assert "party_member_extract" in prompts

        # Test getting prompt
        prompt = loader.get_prompt("speaker_match")
        assert prompt is not None

        # Test prompt variables
        variables = loader.get_variables("speaker_match")
        assert "speaker_name" in variables
        assert "available_speakers" in variables

    def test_llm_service_with_mock(self, monkeypatch: MonkeyPatch) -> None:
        """Test LLMService with mock"""
        # Set dummy API key for testing
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        with LLMServiceMock([{"matched": True, "speaker_id": 123, "confidence": 0.9}]):
            factory = LLMServiceFactory()
            service = factory.create_fast()

            # Verify service was created
            assert service is not None
            assert hasattr(service, "model_name")

    def test_error_handling(self) -> None:
        """Test error handling in LLMService"""
        # Test error types - this can be tested independently
        rate_limit_error = LLMRateLimitError("Rate limit exceeded")
        assert isinstance(rate_limit_error, LLMError)

        generic_error = LLMError("Some other error")
        assert isinstance(generic_error, LLMError)
        assert not isinstance(generic_error, LLMRateLimitError)


class TestLLMServiceIntegration:
    """Test LLMService integration with other components"""

    @mock_llm_service(
        [
            PartyMemberList(
                members=[
                    PartyMemberInfo(
                        name="田中太郎",
                        position="衆議院議員",
                        electoral_district="東京1区",
                    )
                ],
                total_count=1,
                party_name="テスト党",
            )
        ]
    )
    def test_party_member_extractor_integration(self) -> None:
        """Test PartyMemberExtractor with LLMService"""
        from src.party_member_extractor.extractor import PartyMemberExtractor
        from src.party_member_extractor.models import WebPageContent

        extractor = PartyMemberExtractor()

        # Test extraction
        page = WebPageContent(
            url="https://example.com",
            html_content="<html><body>田中太郎 衆議院議員</body></html>",
            page_number=1,
        )

        result = extractor._extract_from_single_page(page, "テスト党")  # type: ignore[reportPrivateUsage]
        assert result is not None
        assert len(result.members) == 1
        assert result.members[0].name == "田中太郎"

    def test_minutes_divider_integration(self, monkeypatch: MonkeyPatch) -> None:
        """Test MinutesDivider with LLMService"""
        # Set dummy API key for testing
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        with LLMServiceMock(
            [
                {
                    "section_info_list": [
                        {"chapter_number": 1, "keyword": "開会"},
                        {"chapter_number": 2, "keyword": "議事"},
                    ]
                }
            ]
        ):
            from src.minutes_divide_processor.minutes_divider import MinutesDivider

            divider = MinutesDivider()

            # Test section divide
            result = divider.section_divide_run("議事録テキスト")
            assert result is not None
            assert len(result.section_info_list) == 2

    @pytest.mark.skip(
        reason="Legacy test - SpeakerMatchingService requires llm_service and "
        "speaker_repository in constructor"
    )
    def test_speaker_matching_service_integration(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test SpeakerMatchingService with LLMService"""
        # Set dummy API key for testing
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        with LLMServiceMock(
            [
                {
                    "matched": True,
                    "speaker_id": 456,
                    "speaker_name": "山田花子",
                    "confidence": 0.95,
                    "reason": "完全一致",
                }
            ]
        ):
            from src.domain.services.speaker_matching_service import (
                SpeakerMatchingService,
            )

            service = SpeakerMatchingService()
            assert service.llm_service is not None

    @pytest.mark.skip(
        reason="Legacy test - PoliticianMatchingService requires llm_service and "
        "politician_repository in constructor"
    )
    def test_politician_matching_service_integration(
        self, monkeypatch: MonkeyPatch
    ) -> None:
        """Test PoliticianMatchingService with LLMService"""
        # Set dummy API key for testing
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")

        with LLMServiceMock(
            [
                {
                    "matched": True,
                    "politician_id": 789,
                    "politician_name": "鈴木一郎",
                    "political_party_name": "サンプル党",
                    "confidence": 0.85,
                    "reason": "表記ゆれだが同一人物",
                }
            ]
        ):
            from src.domain.services.politician_matching_service import (
                PoliticianMatchingService,
            )

            service = PoliticianMatchingService()
            assert service.llm_service is not None


class TestMockFramework:
    """Test the LLM mock framework itself"""

    def test_mock_llm_basic(self) -> None:
        """Test basic mock LLM functionality"""
        from src.test_utils.llm_mock import MockLLM

        mock = MockLLM(["Response 1", "Response 2"])

        # Test first response
        result = mock.invoke("test input")
        assert "Response 1" in result.content

        # Test second response
        result = mock.invoke("another input")
        assert "Response 2" in result.content

        # Test call history
        assert len(mock.call_history) == 2
        assert mock.call_history[0]["input"] == "test input"

    def test_mock_structured_llm(self) -> None:
        """Test mock structured LLM"""
        from src.test_utils.llm_mock import MockLLM

        class TestModel(BaseModel):
            name: str
            value: int

        mock = MockLLM([{"name": "test", "value": 42}])
        structured = mock.with_structured_output(TestModel)

        result = structured.invoke("test")
        assert isinstance(result, TestModel)
        assert result.name == "test"
        assert result.value == 42

    def test_llm_service_mock_context(self) -> None:
        """Test LLMServiceMock context manager"""
        with LLMServiceMock(["mocked response"]) as mock:
            service = LLMService()
            chain = service.create_simple_chain("Test prompt: {input}")
            result = chain.invoke({"input": "test"})

            assert mock.call_count == 1
            assert "mocked response" in str(result)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
