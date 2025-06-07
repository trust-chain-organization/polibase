"""Centralized LLM Service for managing LLM operations"""

import logging
import os
from typing import Any, TypeVar

from langchain_core.language_models import BaseChatModel
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMService:
    """Centralized service for LLM operations with consistent configuration
    and error handling"""

    # Default models for different use cases
    DEFAULT_MODELS = {
        "fast": "gemini-1.5-flash",
        "advanced": "gemini-2.0-flash-exp",
        "legacy": "gemini-1.5-flash",
    }

    def __init__(
        self,
        model_name: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        api_key: str | None = None,
    ):
        """
        Initialize LLM Service

        Args:
            model_name: Name of the model to use (defaults to 'fast' model)
            temperature: Temperature for generation (0.0-1.0)
            max_tokens: Maximum tokens to generate
            api_key: Google API key (defaults to environment variable)
        """
        self.model_name = model_name or self.DEFAULT_MODELS["fast"]
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Google API key not found. Set GOOGLE_API_KEY environment variable."
            )

        self._llm = None
        self._structured_llms: dict[str, Any] = {}

    @property
    def llm(self) -> ChatGoogleGenerativeAI:
        """Lazy initialization of LLM"""
        if self._llm is None:
            self._llm = self._create_llm()
        return self._llm

    def _create_llm(self) -> ChatGoogleGenerativeAI:
        """Create LLM instance with configuration"""
        kwargs = {
            "model": self.model_name,
            "temperature": self.temperature,
            "google_api_key": self.api_key,
        }

        if self.max_tokens:
            kwargs["max_tokens"] = self.max_tokens

        return ChatGoogleGenerativeAI(**kwargs)

    def get_structured_llm(self, schema: type[T]) -> BaseChatModel:
        """
        Get LLM configured for structured output

        Args:
            schema: Pydantic model class for structured output

        Returns:
            LLM configured for structured output
        """
        schema_name = schema.__name__

        if schema_name not in self._structured_llms:
            self._structured_llms[schema_name] = self.llm.with_structured_output(schema)

        return self._structured_llms[schema_name]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((Exception,)),
    )
    def invoke_with_retry(
        self, chain: Runnable, input_data: dict[str, Any], max_retries: int = 3
    ) -> Any:
        """
        Invoke a chain with retry logic

        Args:
            chain: The chain to invoke
            input_data: Input data for the chain
            max_retries: Maximum number of retries

        Returns:
            Result from the chain
        """
        try:
            result = chain.invoke(input_data)
            return result
        except Exception as e:
            logger.error(f"Error invoking chain: {e}")
            raise

    def create_simple_chain(
        self,
        prompt_template: str,
        output_schema: type[T] | None = None,
        use_passthrough: bool = True,
    ) -> Runnable:
        """
        Create a simple chain with prompt and optional structured output

        Args:
            prompt_template: Prompt template string
            output_schema: Optional Pydantic model for structured output
            use_passthrough: Whether to use RunnablePassthrough for input

        Returns:
            Configured chain
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)

        # Select appropriate LLM
        if output_schema:
            llm = self.get_structured_llm(output_schema)
        else:
            llm = self.llm

        # Build chain
        if use_passthrough:
            chain = {"input": RunnablePassthrough()} | prompt | llm
        else:
            chain = prompt | llm

        return chain

    def create_json_output_chain(
        self, prompt_template: str, output_schema: type[T]
    ) -> Runnable:
        """
        Create a chain with JSON output parsing

        Args:
            prompt_template: Prompt template string
            output_schema: Pydantic model for output validation

        Returns:
            Configured chain with JSON parsing
        """
        prompt = ChatPromptTemplate.from_template(prompt_template)
        parser = JsonOutputParser(pydantic_object=output_schema)

        chain = prompt | self.llm | parser

        return chain

    @classmethod
    def create_fast_instance(cls, **kwargs) -> "LLMService":
        """Create instance optimized for speed"""
        # Extract temperature to avoid duplicate keyword argument
        temperature = kwargs.pop("temperature", 0.1)
        return cls(
            model_name=cls.DEFAULT_MODELS["fast"], temperature=temperature, **kwargs
        )

    @classmethod
    def create_advanced_instance(cls, **kwargs) -> "LLMService":
        """Create instance for advanced/complex tasks"""
        # Extract temperature to avoid duplicate keyword argument
        temperature = kwargs.pop("temperature", 0.1)
        return cls(
            model_name=cls.DEFAULT_MODELS["advanced"], temperature=temperature, **kwargs
        )

    def validate_api_key(self) -> bool:
        """Validate that API key is set and working"""
        try:
            # Simple test invocation
            test_prompt = ChatPromptTemplate.from_template("Say 'OK'")
            test_chain = test_prompt | self.llm
            test_chain.invoke({})
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False
