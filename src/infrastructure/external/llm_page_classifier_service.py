"""LLM-based implementation of page classification service."""

import json
import logging

from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.services.interfaces.page_classifier_service import (
    IPageClassifierService,
)
from src.domain.value_objects.page_classification import PageClassification, PageType

logger = logging.getLogger(__name__)


class LLMPageClassifierService(IPageClassifierService):
    """LLM-based implementation of page classification.

    This infrastructure service uses an LLM to classify web pages
    to guide hierarchical navigation strategy.
    """

    def __init__(self, llm_service: ILLMService):
        """Initialize the LLM page classifier.

        Args:
            llm_service: ILLMService instance for making LLM calls
        """
        self._llm_service = llm_service

    async def classify_page(
        self,
        html_content: str,
        current_url: str,
        party_name: str = "",
    ) -> PageClassification:
        """Classify a web page to determine navigation strategy.

        Args:
            html_content: HTML content of the page to classify
            current_url: URL of the current page (for context)
            party_name: Name of the political party (optional, for context)

        Returns:
            PageClassification with type, confidence, and metadata

        Raises:
            ValueError: If html_content or current_url is empty
        """
        if not html_content:
            raise ValueError("HTML content cannot be empty")
        if not current_url:
            raise ValueError("Current URL cannot be empty")

        # Truncate HTML for prompt efficiency (first 3000 characters)
        html_excerpt = html_content[:3000]

        # Get prompt from service
        try:
            prompt_template = self._llm_service.get_prompt("classify_page_type")
            formatted_prompt = prompt_template.format(
                current_url=current_url,
                party_name=party_name or "不明",
                html_excerpt=html_excerpt,
            )
        except Exception as e:
            logger.warning(f"Failed to get prompt template: {e}")
            raise ValueError(
                "Failed to get prompt template for page classification"
            ) from e

        # Call LLM
        try:
            # Access the underlying LLM directly for now
            # TODO: Add generate_structured_output method to ILLMService
            response = await self._llm_service.llm.ainvoke(formatted_prompt)  # type: ignore[attr-defined]

            # Parse response
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Parse LLM response into PageClassification
            classification = self._parse_llm_response(response_text)

            logger.info(
                f"Classified {current_url} as {classification.page_type.value} "
                f"(confidence: {classification.confidence:.2f})"
            )

            return classification

        except Exception as e:
            logger.error(f"Error classifying page: {e}")
            # Return a safe default classification on error
            return PageClassification(
                page_type=PageType.OTHER,
                confidence=0.0,
                reason=f"Failed to classify page: {str(e)}",
                has_child_links=False,
                has_member_info=False,
            )

    def _parse_llm_response(self, response_text: str) -> PageClassification:
        """Parse LLM response into PageClassification object.

        Args:
            response_text: Raw response from LLM

        Returns:
            PageClassification object

        Raises:
            ValueError: If response cannot be parsed
        """
        try:
            # Try to extract JSON from response
            # LLM might wrap JSON in code blocks
            cleaned_text = response_text.strip()
            if "```json" in cleaned_text:
                # Extract JSON from code block
                start = cleaned_text.find("```json") + 7
                end = cleaned_text.find("```", start)
                cleaned_text = cleaned_text[start:end].strip()
            elif "```" in cleaned_text:
                # Generic code block
                start = cleaned_text.find("```") + 3
                end = cleaned_text.find("```", start)
                cleaned_text = cleaned_text[start:end].strip()

            # Parse JSON
            parsed = json.loads(cleaned_text)

            # Extract and validate page_type
            page_type_str = parsed.get("page_type", "other")
            try:
                page_type = PageType(page_type_str)
            except ValueError:
                logger.warning(
                    f"Invalid page_type '{page_type_str}', defaulting to OTHER"
                )
                page_type = PageType.OTHER

            # Build PageClassification
            return PageClassification(
                page_type=page_type,
                confidence=float(parsed.get("confidence", 0.5)),
                reason=str(parsed.get("reason", "No reason provided")),
                has_child_links=bool(parsed.get("has_child_links", False)),
                has_member_info=bool(parsed.get("has_member_info", False)),
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")

            # Fallback: return OTHER classification
            return PageClassification(
                page_type=PageType.OTHER,
                confidence=0.3,
                reason="Failed to parse LLM response",
                has_child_links=False,
                has_member_info=False,
            )
        except ValueError as e:
            logger.error(f"Invalid classification data: {e}")
            return PageClassification(
                page_type=PageType.OTHER,
                confidence=0.0,
                reason=f"Invalid data: {str(e)}",
                has_child_links=False,
                has_member_info=False,
            )
