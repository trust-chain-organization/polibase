"""Link classifier tool for LLM-based classification of page links."""

import json
import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LinkClassification(BaseModel):
    """Classification result for a link."""

    url: str = Field(description="The URL being classified")
    link_type: str = Field(
        description=(
            "Type of link: 'prefecture_list' (都道府県別リスト), "
            "'city_list' (市区町村別リスト), "
            "'member_list' (議員一覧), "
            "'member_profile' (議員個人ページ), "
            "'other' (その他)"
        )
    )
    confidence: float = Field(description="Confidence score (0.0-1.0)", ge=0.0, le=1.0)
    reason: str = Field(description="Reason for classification")


class LinkClassificationResult(BaseModel):
    """Result of classifying multiple links."""

    classifications: list[LinkClassification] = Field(
        description="List of link classifications"
    )
    summary: dict[str, int] = Field(
        description="Summary count by link type",
        default_factory=dict,
    )


class LinkClassifier:
    """Classifies links using LLM to determine their type and relevance."""

    def __init__(self, llm_service: Any):
        """
        Initialize the link classifier.

        Args:
            llm_service: ILLMService instance for making LLM calls
        """
        self.llm_service = llm_service

    async def classify_links(
        self,
        links: list[dict[str, str]],
        party_name: str = "",
        context: str = "",
    ) -> LinkClassificationResult:
        """
        Classify links using LLM.

        Args:
            links: List of link dictionaries with 'url', 'text', etc.
            party_name: Name of the political party (optional context)
            context: Additional context about the page (optional)

        Returns:
            LinkClassificationResult with classifications for each link
        """
        if not links:
            return LinkClassificationResult(classifications=[], summary={})

        # Prepare links for prompt
        links_text = "\n".join(
            [
                (
                    f"{i + 1}. URL: {link['url']}\n"
                    f"   テキスト: {link['text']}\n"
                    f"   タイトル: {link.get('title', '')}"
                )
                for i, link in enumerate(links)
            ]
        )

        # Get prompt from service
        try:
            prompt_template = self.llm_service.get_prompt("classify_page_links")
            formatted_prompt = prompt_template.format(
                links=links_text,
                party_name=party_name or "不明",
                context=context or "コンテキスト情報なし",
            )
        except Exception as e:
            logger.warning(f"Failed to get prompt template: {e}, using fallback")
            formatted_prompt = self._get_fallback_prompt(
                links_text, party_name, context
            )

        # Call LLM
        try:
            response = await self.llm_service.llm.ainvoke(formatted_prompt)

            # Parse response
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            # Try to parse as JSON
            classifications = self._parse_llm_response(response_text, links)

            # Create summary
            summary: dict[str, int] = {}
            for classification in classifications:
                link_type = classification.link_type
                summary[link_type] = summary.get(link_type, 0) + 1

            return LinkClassificationResult(
                classifications=classifications,
                summary=summary,
            )

        except Exception as e:
            logger.error(f"Error classifying links: {e}")
            # Return empty result on error
            return LinkClassificationResult(classifications=[], summary={})

    def _get_fallback_prompt(
        self, links_text: str, party_name: str, context: str
    ) -> str:
        """Generate fallback prompt if template is not available."""
        return f"""あなたは政党ウェブサイトのリンク分類専門家です。
以下のリンクを分析し、それぞれのリンクタイプを判定してください。

政党名: {party_name or "不明"}
コンテキスト: {context or "なし"}

リンク一覧:
{links_text}

各リンクについて、以下の形式でJSON配列として返してください:
[
  {{
    "url": "リンクのURL",
    "link_type": "prefecture_list | city_list | member_list | member_profile | other",
    "confidence": 0.0から1.0の信頼度,
    "reason": "判定理由"
  }}
]

リンクタイプの定義:
- prefecture_list: 都道府県別の議員リスト（例: 「東京都」「大阪府」）
- city_list: 市区町村別の議員リスト（例: 「渋谷区」「横浜市」）
- member_list: 議員一覧ページ（例: 「議員一覧」「メンバー」「所属議員」）
- member_profile: 個別の議員プロフィールページ
- other: その他のページ

必ず全てのリンクについて分類結果を返してください。
"""

    def _parse_llm_response(
        self, response_text: str, original_links: list[dict[str, str]]
    ) -> list[LinkClassification]:
        """
        Parse LLM response into LinkClassification objects.

        Args:
            response_text: Raw response from LLM
            original_links: Original link dictionaries

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
                    classification = LinkClassification(
                        url=item.get("url", ""),
                        link_type=item.get("link_type", "other"),
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
                    url=link["url"],
                    link_type="other",
                    confidence=0.3,
                    reason="Failed to parse LLM response",
                )
                for link in original_links
            ]

    def filter_by_type(
        self,
        result: LinkClassificationResult,
        link_types: list[str],
        min_confidence: float = 0.7,
    ) -> list[str]:
        """
        Filter classified links by type and confidence.

        Args:
            result: LinkClassificationResult to filter
            link_types: List of link types to include
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


@tool
async def classify_child_page_links(
    links: list[dict[str, str]],
    llm_service: Any,
    party_name: str = "",
    context: str = "",
) -> dict[str, Any]:
    """
    Classify child page links using LLM.

    This tool uses an LLM to classify detected links into categories
    such as prefecture lists, city lists, member lists, or individual profiles.

    Args:
        links: List of link dictionaries from detect_child_page_links
        llm_service: ILLMService instance for making LLM calls
        party_name: Name of the political party (optional)
        context: Additional context about the page (optional)

    Returns:
        Dictionary containing:
        - classifications: List of classification results
        - summary: Count by link type
        - member_list_urls: URLs classified as member lists
        - profile_urls: URLs classified as individual profiles
    """
    classifier = LinkClassifier(llm_service)

    result = await classifier.classify_links(
        links, party_name=party_name, context=context
    )

    # Extract specific URL lists
    member_list_urls = classifier.filter_by_type(result, ["member_list"])
    profile_urls = classifier.filter_by_type(result, ["member_profile"])

    return {
        "classifications": [c.model_dump() for c in result.classifications],
        "summary": result.summary,
        "member_list_urls": member_list_urls,
        "profile_urls": profile_urls,
    }
