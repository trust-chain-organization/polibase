"""Tests for the shared LLM service layer"""

from unittest.mock import MagicMock, patch

import pytest
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field

from src.services import ChainFactory, LLMService, PromptManager


class SampleTestSchema(BaseModel):
    """Test schema for structured output"""

    message: str = Field(description="Test message")
    number: int = Field(description="Test number")


class TestLLMService:
    """Test LLM Service functionality"""

    def test_initialization_with_api_key(self):
        """Test LLM service initialization with API key"""
        service = LLMService(api_key="test-key")
        assert service.api_key == "test-key"
        assert service.model_name == LLMService.DEFAULT_MODELS["fast"]
        assert service.temperature == 0.1

    def test_initialization_from_env(self, monkeypatch):
        """Test LLM service initialization from environment"""
        monkeypatch.setenv("GOOGLE_API_KEY", "env-test-key")
        service = LLMService()
        assert service.api_key == "env-test-key"

    def test_initialization_without_api_key(self, monkeypatch):
        """Test initialization fails without API key"""
        monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
        with pytest.raises(ValueError, match="Google API key not found"):
            LLMService(api_key=None)

    def test_lazy_llm_creation(self):
        """Test lazy initialization of LLM"""
        service = LLMService(api_key="test-key")
        assert service._llm is None

        # Access llm property
        with patch.object(service, "_create_llm") as mock_create:
            mock_llm = MagicMock(spec=ChatGoogleGenerativeAI)
            mock_create.return_value = mock_llm

            llm = service.llm
            assert llm == mock_llm
            mock_create.assert_called_once()

    def test_get_structured_llm(self):
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

    def test_create_fast_instance(self):
        """Test fast instance creation"""
        instance = LLMService.create_fast_instance(api_key="test-key")
        assert instance.model_name == LLMService.DEFAULT_MODELS["fast"]
        assert instance.temperature == 0.1

    def test_create_advanced_instance(self):
        """Test advanced instance creation"""
        # Don't pass temperature as keyword arg since it's handled specially
        instance = LLMService.create_advanced_instance(api_key="test-key")
        assert instance.model_name == LLMService.DEFAULT_MODELS["advanced"]
        assert instance.temperature == 0.1  # Default temperature

        # Test with custom temperature
        instance2 = LLMService(
            model_name=LLMService.DEFAULT_MODELS["advanced"],
            api_key="test-key",
            temperature=0.5,
        )
        assert instance2.temperature == 0.5


class TestPromptManager:
    """Test Prompt Manager functionality"""

    def test_get_prompt(self):
        """Test getting prompts"""
        manager = PromptManager()

        prompt = manager.get_prompt("minutes_divide")
        assert prompt is not None
        assert "議事録" in prompt.messages[0].prompt.template

    def test_get_unknown_prompt(self):
        """Test getting unknown prompt raises error"""
        manager = PromptManager()

        with pytest.raises(ValueError, match="Unknown prompt key"):
            manager.get_prompt("unknown_prompt")

    def test_prompt_caching(self):
        """Test prompt caching"""
        manager = PromptManager()

        prompt1 = manager.get_prompt("minutes_divide")
        prompt2 = manager.get_prompt("minutes_divide")

        # Should be the same object due to caching
        assert prompt1 is prompt2

    def test_create_custom_prompt(self):
        """Test creating custom prompt"""
        manager = PromptManager()

        template = "This is a {test} prompt"
        prompt = manager.create_custom_prompt(template, cache_key="test_prompt")

        assert prompt is not None

        # Test it was cached
        cached_prompt = manager.get_prompt("test_prompt")
        assert cached_prompt is prompt

    def test_singleton_instance(self):
        """Test singleton pattern"""
        instance1 = PromptManager.get_default_instance()
        instance2 = PromptManager.get_default_instance()

        assert instance1 is instance2


class TestChainFactory:
    """Test Chain Factory functionality"""

    @pytest.fixture
    def mock_llm_service(self):
        """Create mock LLM service"""
        service = MagicMock(spec=LLMService)
        service.get_structured_llm.return_value = MagicMock()
        service.llm = MagicMock()
        service.invoke_with_retry.return_value = {"result": "test"}
        return service

    @pytest.fixture
    def mock_prompt_manager(self):
        """Create mock prompt manager"""
        manager = MagicMock(spec=PromptManager)
        manager.get_prompt.return_value = MagicMock()
        manager.get_hub_prompt.return_value = MagicMock()
        return manager

    def test_initialization(self, mock_llm_service, mock_prompt_manager):
        """Test chain factory initialization"""
        factory = ChainFactory(mock_llm_service, mock_prompt_manager)

        assert factory.llm_service == mock_llm_service
        assert factory.prompt_manager == mock_prompt_manager

    def test_create_minutes_divider_chain(self, mock_llm_service, mock_prompt_manager):
        """Test creating minutes divider chain"""
        factory = ChainFactory(mock_llm_service, mock_prompt_manager)

        chain = factory.create_minutes_divider_chain(SampleTestSchema)

        assert chain is not None
        mock_llm_service.get_structured_llm.assert_called_once_with(SampleTestSchema)

    def test_create_speech_divider_chain(self, mock_llm_service, mock_prompt_manager):
        """Test creating speech divider chain"""
        factory = ChainFactory(mock_llm_service, mock_prompt_manager)

        chain = factory.create_speech_divider_chain(SampleTestSchema)

        assert chain is not None
        mock_llm_service.get_structured_llm.assert_called_once_with(SampleTestSchema)

    def test_invoke_with_retry(self, mock_llm_service, mock_prompt_manager):
        """Test invoke with retry"""
        factory = ChainFactory(mock_llm_service, mock_prompt_manager)

        mock_chain = MagicMock()
        input_data = {"test": "data"}

        result = factory.invoke_with_retry(mock_chain, input_data)

        mock_llm_service.invoke_with_retry.assert_called_once_with(
            mock_chain, input_data, 3
        )
        assert result == {"result": "test"}

    def test_create_generic_chain(self, mock_llm_service, mock_prompt_manager):
        """Test creating generic chain"""
        factory = ChainFactory(mock_llm_service, mock_prompt_manager)

        template = "Test {input}"
        chain = factory.create_generic_chain(
            template, output_schema=SampleTestSchema, input_variables=["input"]
        )

        assert chain is not None
        mock_llm_service.get_structured_llm.assert_called_once_with(SampleTestSchema)


class TestIntegration:
    """Integration tests with mocked API calls"""

    @patch("src.services.llm_service.ChatGoogleGenerativeAI")
    def test_end_to_end_flow(self, mock_llm_class):
        """Test end-to-end flow with mocked LLM"""
        # Setup mock
        mock_llm = MagicMock()
        mock_llm_class.return_value = mock_llm

        mock_structured = MagicMock()
        mock_llm.with_structured_output.return_value = mock_structured

        mock_structured.invoke.return_value = SampleTestSchema(
            message="Test successful", number=42
        )

        # Create service
        service = LLMService(api_key="test-key")
        factory = ChainFactory(service)

        # Create and invoke chain
        chain = factory.create_generic_chain(
            "Generate test data", output_schema=SampleTestSchema
        )

        # Mock the chain invocation
        with patch.object(service, "invoke_with_retry") as mock_invoke:
            mock_invoke.return_value = SampleTestSchema(message="Test", number=42)

            result = factory.invoke_with_retry(chain, {})

            assert isinstance(result, SampleTestSchema)
            assert result.message == "Test"
            assert result.number == 42
