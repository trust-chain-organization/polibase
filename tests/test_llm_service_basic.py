"""Basic tests for LLMService without mocks"""

import os

import pytest

from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.infrastructure.external.prompt_loader import PromptLoader
from src.services.llm_factory import LLMServiceFactory


class TestLLMServiceBasic:
    """Basic tests for LLMService"""

    def test_factory_creates_service(self):
        """Test that factory creates service instances correctly"""
        # Set dummy API key for testing
        os.environ["GOOGLE_API_KEY"] = "test-key"

        factory = LLMServiceFactory()

        # Test different presets
        fast_service = factory.create_fast()
        assert isinstance(fast_service, InstrumentedLLMService)
        assert fast_service.model_name == "gemini-1.5-flash"

        advanced_service = factory.create_advanced()
        assert isinstance(advanced_service, InstrumentedLLMService)
        assert advanced_service.model_name == "gemini-2.0-flash-exp"

    def test_prompt_loader(self):
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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
