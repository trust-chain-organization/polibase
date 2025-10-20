"""LLM-based implementation of link classification service."""

import json
import logging

from src.domain.services.interfaces.llm_link_classifier_service import (
    ILLMLinkClassifierService,
    LinkClassification,
    LinkClassificationResult,
    LinkType,
)
from src.domain.services.interfaces.llm_service import ILLMService
from src.domain.value_objects.link import Link

logger = logging.getLogger(__name__)


class LLMLinkClassifierService(ILLMLinkClassifierService):
    """LLM-based implementation of link classification.

    This infrastructure service uses an LLM to classify links into different
    types. It implements the ILLMLinkClassifierService interface.
    """

    def __init__(self, llm_service: ILLMService):
        """Initialize the LLM link classifier.

        Args:
            llm_service: ILLMService instance for making LLM calls
        """
        self._llm_service = llm_service

    async def classify_links(
        self,
        links: list[Link],
        party_name: str = "",
        context: str = "",
    ) -> LinkClassificationResult:
        """Classify links using LLM.

        Args:
            links: List of Link value objects to classify
            party_name: Name of the political party (optional context)
            context: Additional context about the page (optional)

        Returns:
            LinkClassificationResult with classifications and summary
        """
        if not links:
            return LinkClassificationResult(classifications=[], summary={})

        # Prepare links for prompt
        links_text = "\n".join(
            [
                (
                    f"{i + 1}. URL: {link.url}\n"
                    f"   テキスト: {link.text}\n"
                    f"   タイトル: {link.title}"
                )
                for i, link in enumerate(links)
            ]
        )

        # Get prompt from service
        try:
            prompt_template = self._llm_service.get_prompt("classify_page_links")
            formatted_prompt = prompt_template.format(
                links=links_text,
                party_name=party_name or "不明",
                context=context or "コンテキスト情報なし",
            )
        except Exception as e:
            logger.warning(f"Failed to get prompt template: {e}")
            raise ValueError(
                "Failed to get prompt template for link classification"
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

            # Try to parse as JSON
            classifications = self._parse_llm_response(response_text, links)

            # Create summary
            summary: dict[str, int] = {}
            for classification in classifications:
                link_type = classification.link_type.value
                summary[link_type] = summary.get(link_type, 0) + 1

            return LinkClassificationResult(
                classifications=classifications,
                summary=summary,
            )

        except Exception as e:
            logger.error(f"Error classifying links: {e}")
            # Return empty result on error
            return LinkClassificationResult(classifications=[], summary={})

    def _parse_llm_response(
        self, response_text: str, original_links: list[Link]
    ) -> list[LinkClassification]:
        """Parse LLM response into LinkClassification objects.

        Args:
            response_text: Raw response from LLM
            original_links: Original link objects

        Returns:
            List of LinkClassification objects
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

            # Convert to LinkClassification objects
            classifications: list[LinkClassification] = []
            for item in parsed:
                try:
                    # Parse link_type as enum
                    link_type_str = item.get("link_type", "other")
                    try:
                        link_type = LinkType(link_type_str)
                    except ValueError:
                        logger.warning(
                            f"Invalid link_type '{link_type_str}', using OTHER"
                        )
                        link_type = LinkType.OTHER

                    classification = LinkClassification(
                        url=item.get("url", ""),
                        link_type=link_type,
                        confidence=float(item.get("confidence", 0.5)),
                        reason=item.get("reason", ""),
                    )
                    classifications.append(classification)
                except Exception as e:
                    logger.warning(f"Failed to parse classification item: {e}")
                    continue

            return classifications

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.debug(f"Response text: {response_text}")

            # Fallback: create basic classifications
            return [
                LinkClassification(
                    url=link.url,
                    link_type=LinkType.OTHER,
                    confidence=0.3,
                    reason="Failed to parse LLM response",
                )
                for link in original_links
            ]

    def filter_by_type(
        self,
        result: LinkClassificationResult,
        link_types: list[LinkType],
        min_confidence: float = 0.7,
    ) -> list[str]:
        """Filter classified links by type and confidence.

        Args:
            result: LinkClassificationResult to filter
            link_types: List of LinkType enums to include
            min_confidence: Minimum confidence threshold

        Returns:
            List of URLs matching the criteria
        """
        filtered_urls: list[str] = []

        for classification in result.classifications:
            if (
                classification.link_type in link_types
                and classification.confidence >= min_confidence
            ):
                filtered_urls.append(classification.url)

        return filtered_urls
