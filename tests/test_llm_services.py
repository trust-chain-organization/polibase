"""Tests for the shared LLM service layer"""

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel, Field

from src.services.llm_factory import LLMServiceFactory
from src.services.llm_service import LLMService
from src.services.prompt_loader import PromptLoader


class SampleTestSchema(BaseModel):
    """Test schema for structured output"""

    message: str = Field(description="Test message")
    number: int = Field(description="Test number")


class TestLLMService:
    """Test LLM Service functionality"""

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_initialization_with_api_key(self, mock_llm_class):
        """Test LLM service initialization with API key"""
        service = LLMService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model_name == "gemini-1.5-flash"  # Default model
        assert service.temperature == 0.1

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_initialization_from_env(self, mock_llm_class, monkeypatch):
        """Test LLM service initialization from environment"""
        monkeypatch.setenv("GOOGLE_API_KEY", "env-test-key")
        service = LLMService()
        assert service.api_key == "env-test-key"

    def test_initialization_without_api_key(self, monkeypatch):
        """Test initialization fails without API key"""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        from src.services.llm_errors import LLMAuthenticationError

        with pytest.raises(LLMAuthenticationError, match="Google API key not found"):
            LLMService(api_key=None)

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_lazy_llm_creation(self, mock_llm_class):
        """Test lazy initialization of LLM"""
        service = LLMService(api_key="test-key")
        assert service._llm is None

        # Access llm property
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        llm = service.llm
        assert llm == mock_llm
        mock_llm_class.assert_called_once()

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_get_structured_llm(self, mock_llm_class):
        """Test structured LLM creation"""
        service = LLMService(api_key="test-key")

        # Mock the _llm attribute directly since llm is a property
        mock_llm = MagicMock()
        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured
        service._llm = mock_llm

        result = service.get_structured_llm(SampleTestSchema)

        mock_llm.with_structured_output.assert_called_once_with(SampleTestSchema)
        assert result == mock_structured

        # Test caching
        result2 = service.get_structured_llm(SampleTestSchema)
        assert result2 == mock_structured
        # Should not call again due to caching
        assert mock_llm.with_structured_output.call_count == 1

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_create_fast_instance(self, mock_llm_class, monkeypatch):
        """Test fast instance creation"""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        factory = LLMServiceFactory()
        instance = factory.create_fast()
        assert instance.model_name == "gemini-1.5-flash"
        assert instance.temperature == 0.1

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_create_advanced_instance(self, mock_llm_class, monkeypatch):
        """Test advanced instance creation"""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        factory = LLMServiceFactory()
        instance = factory.create_advanced()
        assert instance.model_name == "gemini-2.0-flash-exp"
        assert instance.temperature == 0.1


class TestPromptLoader:
    """Test Prompt Loader functionality"""

    def test_get_prompt(self):
        """Test getting prompts"""
        loader = PromptLoader()

        prompt = loader.get_prompt("minutes_divide")
        assert prompt is not None

    def test_get_unknown_prompt(self):
        """Test getting unknown prompt raises error"""
        loader = PromptLoader()

        with pytest.raises(KeyError, match="Prompt not found"):
            loader.get_prompt("unknown_prompt")

    def test_list_prompts(self):
        """Test listing available prompts"""
        loader = PromptLoader()

        prompts = loader.list_prompts()
        assert "minutes_divide" in prompts
        assert "speaker_match" in prompts

    def test_get_variables(self):
        """Test getting prompt variables"""
        loader = PromptLoader()

        variables = loader.get_variables("speaker_match")
        assert "speaker_name" in variables
        assert "available_speakers" in variables


class TestLLMServiceFactory:
    """Test LLM Service Factory functionality"""

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_factory_presets(self, mock_llm_class, monkeypatch):
        """Test factory preset configurations"""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        factory = LLMServiceFactory()

        # Test fast preset
        fast = factory.create_fast()
        assert fast.model_name == "gemini-1.5-flash"
        assert fast.temperature == 0.1

        # Test advanced preset
        advanced = factory.create_advanced()
        assert advanced.model_name == "gemini-2.0-flash-exp"
        assert advanced.temperature == 0.1

        # Test creative preset
        creative = factory.create_creative()
        assert creative.temperature == 0.7

        # Test precise preset
        precise = factory.create_precise()
        assert precise.temperature == 0.0

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_custom_service_creation(self, mock_llm_class, monkeypatch):
        """Test creating custom service"""
        monkeypatch.setenv("GOOGLE_API_KEY", "custom-key")
        factory = LLMServiceFactory()

        service = factory.create(
            model_name="custom-model", temperature=0.5, max_tokens=2000
        )

        assert service.model_name == "custom-model"
        assert service.temperature == 0.5
        assert service.max_tokens == 2000


class TestIntegration:
    """Integration tests with mocked API calls"""

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_end_to_end_flow(self, mock_llm_class, monkeypatch):
        """Test end-to-end flow with mocked LLM"""
        monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
        # Setup mock
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        mock_structured.invoke.return_value = SampleTestSchema(
            message="Test successful", number=42
        )

        # Create service
        factory = LLMServiceFactory()
        service = factory.create_fast()

        # Test structured output
        structured_llm = service.get_structured_llm(SampleTestSchema)
        assert structured_llm is not None

        # Test invoke_prompt
        with patch.object(service, "invoke_prompt") as mock_invoke:
            mock_invoke.return_value = SampleTestSchema(message="Test", number=42)

            result = service.invoke_prompt(
                "test_prompt", {"input": "test"}, output_schema=SampleTestSchema
            )

            assert isinstance(result, SampleTestSchema)
            assert result.message == "Test"
            assert result.number == 42
