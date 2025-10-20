"""LangGraph node for page classification."""

import logging
from collections.abc import Awaitable, Callable

from src.domain.services.interfaces.page_classifier_service import (
    IPageClassifierService,
)
from src.infrastructure.external.langgraph_state_adapter import (
    LangGraphPartyScrapingStateOptional,
)

logger = logging.getLogger(__name__)


def create_page_classifier_node(
    page_classifier: IPageClassifierService,
) -> Callable[
    [LangGraphPartyScrapingStateOptional],
    Awaitable[LangGraphPartyScrapingStateOptional],
]:
    """Create a LangGraph node for page classification.

    This factory function creates a node that classifies page HTML content
    to determine the next action. HTML content must be present in state.

    Args:
        page_classifier: Service for classifying page types

    Returns:
        LangGraph node function that classifies pages
    """

    async def classify_page_node(
        state: LangGraphPartyScrapingStateOptional,
    ) -> LangGraphPartyScrapingStateOptional:
        """Classify the current page and update state.

        This node:
        1. Reads HTML content from state (must be fetched by a prior node)
        2. Classifies the page type (index_page, member_list_page, other)
        3. Stores classification result in state metadata

        Args:
            state: Current LangGraph state (must include html_content)

        Returns:
            Updated state with classification metadata
        """
        current_url = state.get("current_url")
        party_name = state.get("party_name", "")
        html_content = state.get("html_content")

        if not current_url:
            logger.error("No current_url in state, cannot classify")
            # Store error in state metadata
            state["classification"] = {
                "page_type": "other",
                "confidence": 0.0,
                "reason": "No current URL available",
                "has_child_links": False,
                "has_member_info": False,
            }
            return state

        if not html_content:
            logger.warning(f"No HTML content in state for {current_url}")
            state["classification"] = {
                "page_type": "other",
                "confidence": 0.0,
                "reason": "No HTML content available",
                "has_child_links": False,
                "has_member_info": False,
            }
            return state

        try:
            logger.info(f"Classifying page: {current_url}")

            # Classify the page
            classification = await page_classifier.classify_page(
                html_content=html_content,
                current_url=current_url,
                party_name=party_name,
            )

            # Store classification in state as dict
            state["classification"] = {
                "page_type": classification.page_type.value,
                "confidence": classification.confidence,
                "reason": classification.reason,
                "has_child_links": classification.has_child_links,
                "has_member_info": classification.has_member_info,
            }

            logger.info(
                f"Classification result: {classification.page_type.value} "
                f"(confidence: {classification.confidence:.2f})"
            )

            return state

        except Exception as e:
            logger.error(f"Error classifying page {current_url}: {e}", exc_info=True)

            # Store error in state
            state["classification"] = {
                "page_type": "other",
                "confidence": 0.0,
                "reason": f"Classification error: {str(e)}",
                "has_child_links": False,
                "has_member_info": False,
            }

            return state

    return classify_page_node
