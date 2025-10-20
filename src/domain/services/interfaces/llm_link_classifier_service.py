"""Interface for LLM-based link classification service."""

from abc import ABC, abstractmethod
from enum import Enum

from pydantic import BaseModel, Field

from src.domain.value_objects.link import Link


class LinkType(str, Enum):
    """Types of links that can be classified."""

    PREFECTURE_LIST = "prefecture_list"  # 都道府県別リスト
    CITY_LIST = "city_list"  # 市区町村別リスト
    MEMBER_LIST = "member_list"  # 議員一覧
    MEMBER_PROFILE = "member_profile"  # 議員個人ページ
    OTHER = "other"  # その他


class LinkClassification(BaseModel):
    """Classification result for a single link."""

    url: str = Field(description="The URL being classified")
    link_type: LinkType = Field(description="Type of link")
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


class ILLMLinkClassifierService(ABC):
    """Interface for LLM-based link classification.

    This interface defines the contract for services that use LLM to classify
    links into different types based on their URL, text, and context.
    """

    @abstractmethod
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

        Raises:
            ValueError: If links list is None
        """
        pass
