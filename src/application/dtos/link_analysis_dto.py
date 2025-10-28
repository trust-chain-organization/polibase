"""DTOs for link analysis use case."""

from pydantic import BaseModel, Field


class AnalyzeLinksInputDTO(BaseModel):
    """Input DTO for analyzing party page links.

    This DTO represents the input required to analyze links on a party
    member page and classify them.
    """

    html_content: str = Field(description="HTML content of the page")
    current_url: str = Field(description="URL of the current page")
    party_name: str = Field(default="", description="Name of the political party")
    context: str = Field(default="", description="Additional context about the page")
    min_confidence_threshold: float = Field(
        default=0.7, description="Minimum confidence threshold for link classification"
    )


class LinkClassificationDTO(BaseModel):
    """DTO representing a classified link."""

    url: str = Field(description="The classified URL")
    link_type: str = Field(description="Type of the link")
    confidence: float = Field(description="Confidence score (0.0-1.0)")
    reason: str = Field(description="Reason for classification")


class AnalyzeLinksOutputDTO(BaseModel):
    """Output DTO for link analysis results.

    This DTO contains the results of analyzing and classifying links
    from a party member page.
    """

    all_links_count: int = Field(description="Total number of links extracted")
    child_links_count: int = Field(description="Number of child page links")
    classifications: list[LinkClassificationDTO] = Field(
        description="List of classified links"
    )
    summary: dict[str, int] = Field(
        description="Summary count by link type", default_factory=dict
    )
    member_list_urls: list[str] = Field(
        description="URLs classified as member lists", default_factory=list
    )
    profile_urls: list[str] = Field(
        description="URLs classified as individual profiles", default_factory=list
    )
