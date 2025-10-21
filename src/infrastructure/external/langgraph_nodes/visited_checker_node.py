"""LangGraph node for visited URL checking and depth enforcement.

This module provides infrastructure layer components that integrate the domain
entity's visited URL checking logic with the LangGraph workflow framework.
"""

import logging

from langchain_core.messages import HumanMessage

from src.domain.entities.party_scraping_state import PartyScrapingState
from src.infrastructure.external.langgraph_state_adapter import (
    LangGraphPartyScrapingStateOptional,
    domain_to_langgraph_state,
    langgraph_to_domain_state,
)

logger = logging.getLogger(__name__)


def check_visited_and_depth(
    state: LangGraphPartyScrapingStateOptional,
) -> LangGraphPartyScrapingStateOptional:
    """LangGraph node: Check if current URL is visited and enforce depth limits.

    This is a thin adapter that converts between LangGraph state and domain state,
    delegating all business logic to the domain entity.

    Args:
        state: LangGraph state containing current_url, visited_urls, depth, etc.

    Returns:
        Updated LangGraph state with:
            - visited_urls: Updated with current URL if new
            - messages: Updated with status message
            - should_skip: Boolean flag indicating if processing should be skipped
            - skip_reason: Reason for skipping (if applicable)

    Example:
        >>> from langgraph.graph import StateGraph
        >>> workflow = StateGraph(state_schema)
        >>> workflow.add_node("check_visited", check_visited_and_depth)
        >>> workflow.add_edge("fetch_page", "check_visited")
    """
    # Convert to domain state
    domain_state = langgraph_to_domain_state(state)

    # Get current state values
    current_url = state.get("current_url", "")
    messages = list(state.get("messages", []))

    # Initialize flags
    should_skip = False
    skip_reason = None

    try:
        # Delegate to domain entity for business logic
        if domain_state.has_visited(current_url):
            should_skip = True
            skip_reason = "already_visited"
            normalized_url = PartyScrapingState.normalize_url(current_url)
            logger.info(
                f"URL already visited (infinite loop prevented): {normalized_url}"
            )
            messages.append(
                HumanMessage(
                    content=f"⚠️ Skipping already visited URL: {normalized_url}"
                )
            )
        elif domain_state.depth > domain_state.max_depth:
            should_skip = True
            skip_reason = "max_depth_exceeded"
            normalized_url = PartyScrapingState.normalize_url(current_url)
            logger.info(
                f"Max depth {domain_state.max_depth} exceeded at depth "
                f"{domain_state.depth}: {normalized_url}"
            )
            messages.append(
                HumanMessage(
                    content=(
                        f"⚠️ Max depth {domain_state.max_depth} exceeded at "
                        f"depth {domain_state.depth}, skipping: {normalized_url}"
                    )
                )
            )
        else:
            # Mark as visited using domain logic
            domain_state.mark_visited(current_url)
            normalized_url = PartyScrapingState.normalize_url(current_url)
            logger.info(
                f"Processing URL at depth {domain_state.depth}/"
                f"{domain_state.max_depth}: {normalized_url}"
            )
            messages.append(
                HumanMessage(
                    content=(
                        f"✓ Processing URL at depth {domain_state.depth}/"
                        f"{domain_state.max_depth}: {normalized_url}"
                    )
                )
            )

    except ValueError as e:
        # Handle invalid URLs
        should_skip = True
        skip_reason = "invalid_url"
        error_msg = f"Invalid URL: {current_url} - {e}"
        logger.error(error_msg)
        messages.append(HumanMessage(content=f"❌ {error_msg}"))

    # Convert back to LangGraph state
    lg_state = domain_to_langgraph_state(domain_state)

    # Return updated state with framework-specific fields
    return {
        **lg_state,
        "messages": messages,
        "should_skip": should_skip,
        "skip_reason": skip_reason,
    }


def add_pending_url_with_checks(
    state: LangGraphPartyScrapingStateOptional, url: str, depth: int
) -> LangGraphPartyScrapingStateOptional:
    """Add a URL to pending queue with visited and depth checks.

    This helper function delegates to the domain entity for URL validation
    and visited checking.

    Args:
        state: LangGraph state dict
        url: URL to add to pending queue
        depth: Depth level for this URL

    Returns:
        Updated state with URL added to pending_urls if checks pass

    Raises:
        ValueError: If depth is negative or URL is invalid
    """
    if depth < 0:
        raise ValueError(f"Depth cannot be negative: {depth}")

    # Convert to domain state
    domain_state = langgraph_to_domain_state(state)
    messages = list(state.get("messages", []))

    try:
        # Use domain entity's business logic
        was_added = domain_state.add_pending_url(url, depth)

        if was_added:
            normalized_url = PartyScrapingState.normalize_url(url)
            logger.info(
                f"Added URL to pending queue at depth {depth}: {normalized_url}"
            )
            messages.append(
                HumanMessage(
                    content=f"➕ Added to queue (depth {depth}): {normalized_url}"
                )
            )
        else:
            # URL was skipped (already visited or exceeds depth)
            normalized_url = PartyScrapingState.normalize_url(url)
            logger.debug(f"Skipping URL (visited or exceeds depth): {normalized_url}")

    except ValueError as e:
        error_msg = f"Failed to add URL '{url}': {e}"
        logger.error(error_msg)
        messages.append(HumanMessage(content=f"❌ {error_msg}"))

    # Convert back to LangGraph state
    lg_state = domain_to_langgraph_state(domain_state)

    return {**lg_state, "messages": messages}
