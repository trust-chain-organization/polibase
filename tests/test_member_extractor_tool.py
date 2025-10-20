"""Tests for member extractor LangGraph tool."""

from typing import Any

import pytest

from src.domain.services.interfaces.llm_service import ILLMService
from src.infrastructure.external.langgraph_tools.member_extractor_tool import (
    create_member_extractor_tools,
)
from src.party_member_extractor.models import PartyMemberInfo, PartyMemberList


class MockLLMService(ILLMService):
    """Mock LLM service for testing."""

    model_name: str = "mock-model"
    temperature: float = 0.0

    def __init__(self) -> None:
        self.prompt_templates = {
            "party_member_extract": """
            Extract party members from the following content:
            Party: {party_name}
            Base URL: {base_url}
            Content: {content}
            """
        }

    async def set_history_repository(self, repository: Any) -> None:
        """Mock set history repository."""
        pass

    async def get_processing_history(self, processing_id: str) -> Any:
        """Mock get processing history."""
        return None

    async def match_speaker_to_politician(self, context: Any) -> Any:
        """Mock match speaker to politician."""
        return None

    async def extract_speeches_from_text(self, text: str, meeting_info: Any) -> Any:
        """Mock extract speeches."""
        return []

    async def extract_party_members(self, html_content: str, party_name: str) -> Any:
        """Mock extract party members."""
        return []

    async def match_conference_member(
        self, member_name: str, party_name: str | None, candidates: list[Any]
    ) -> Any:
        """Mock match conference member."""
        return None

    def get_prompt(self, prompt_name: str):
        """Return mock prompt template."""

        class MockPrompt:
            def __init__(self, template: str):
                self.template = template

            def format(self, **kwargs: Any) -> str:
                return self.template.format(**kwargs)

        return MockPrompt(self.prompt_templates[prompt_name])

    def get_structured_llm(self, schema: Any):
        """Return mock structured LLM."""

        class MockStructuredLLM:
            def invoke(self, prompt: str):
                # Return mock data based on the prompt
                if "Example Party" in prompt:
                    return PartyMemberList(
                        members=[
                            PartyMemberInfo(
                                name="山田太郎",
                                position="衆議院議員",
                                electoral_district="東京1区",
                                prefecture="東京都",
                                profile_url="https://example.com/yamada",
                                party_position="代表",
                            ),
                            PartyMemberInfo(
                                name="田中花子",
                                position="参議院議員",
                                electoral_district="比例代表",
                                prefecture="神奈川県",
                                profile_url="https://example.com/tanaka",
                                party_position=None,
                            ),
                        ],
                        total_count=2,
                        party_name="Example Party",
                    )
                return PartyMemberList(members=[], total_count=0, party_name="Unknown")

        return MockStructuredLLM()

    def invoke_with_retry(self, chain: Any, inputs: dict[str, Any]) -> Any:
        """Mock invoke with retry."""
        return "Mock response"

    def invoke_llm(self, messages: list[dict[str, str]]) -> str:
        """Mock invoke LLM."""
        return "Mock response"


@pytest.fixture
def mock_llm_service() -> MockLLMService:
    """Create mock LLM service."""
    return MockLLMService()


@pytest.fixture
def sample_html():
    """Create sample HTML for testing."""
    return """
    <html>
        <head><title>党員リスト</title></head>
        <body>
            <main>
                <h1>Example Party 議員一覧</h1>
                <div class="member">
                    <h2>山田太郎</h2>
                    <p>衆議院議員（東京1区）</p>
                    <p>代表</p>
                    <a href="/yamada">プロフィール</a>
                </div>
                <div class="member">
                    <h2>田中花子</h2>
                    <p>参議院議員（比例代表）</p>
                    <a href="/tanaka">プロフィール</a>
                </div>
            </main>
        </body>
    </html>
    """


@pytest.mark.asyncio
async def test_extract_members_from_page_success(
    mock_llm_service: MockLLMService, sample_html: str
) -> None:
    """Test successful member extraction."""
    # Create tools
    tools = create_member_extractor_tools(llm_service=mock_llm_service)
    extract_tool = tools[0]

    # Execute tool
    result = await extract_tool.ainvoke(
        {
            "url": "https://example.com/members",
            "html_content": sample_html,
            "party_name": "Example Party",
        }
    )

    # Verify result
    assert result["success"] is True
    assert result["count"] == 2
    assert result["party_name"] == "Example Party"
    assert len(result["members"]) == 2

    # Verify first member
    member1 = result["members"][0]
    assert member1["name"] == "山田太郎"
    assert member1["position"] == "衆議院議員"
    assert member1["electoral_district"] == "東京1区"
    assert member1["prefecture"] == "東京都"
    assert member1["profile_url"] == "https://example.com/yamada"
    assert member1["party_position"] == "代表"

    # Verify second member
    member2 = result["members"][1]
    assert member2["name"] == "田中花子"
    assert member2["position"] == "参議院議員"
    assert member2["electoral_district"] == "比例代表"
    assert member2["prefecture"] == "神奈川県"
    assert member2["profile_url"] == "https://example.com/tanaka"
    assert member2["party_position"] is None


@pytest.mark.asyncio
async def test_extract_members_from_page_no_members(
    mock_llm_service: MockLLMService,
) -> None:
    """Test extraction when no members are found."""
    # Create tools
    tools = create_member_extractor_tools(llm_service=mock_llm_service)
    extract_tool = tools[0]

    # Execute tool with empty HTML
    result = await extract_tool.ainvoke(
        {
            "url": "https://example.com/empty",
            "html_content": "<html><body></body></html>",
            "party_name": "Unknown Party",
        }
    )

    # Verify result
    assert result["success"] is False
    assert result["count"] == 0
    assert result["party_name"] == "Unknown Party"
    assert len(result["members"]) == 0


@pytest.mark.asyncio
async def test_extract_members_from_page_error_handling(
    mock_llm_service: MockLLMService,
) -> None:
    """Test error handling when extractor's internal LLM raises an error.

    When the extractor's internal _extract_from_single_page catches an error,
    it returns None rather than raising. The tool treats this as "no members found"
    rather than an error. This test verifies that behavior.
    """

    # Create a mock LLM service that raises an error
    class ErrorLLMService(MockLLMService):
        def get_structured_llm(self, schema: Any):  # type: ignore[reportIncompatibleMethodOverride]
            class ErrorLLM:
                def invoke(self, prompt: str):
                    raise ValueError("Test error")

            return ErrorLLM()

    # Create tools with error-raising service
    tools = create_member_extractor_tools(llm_service=ErrorLLMService())
    extract_tool = tools[0]

    # Execute tool
    result = await extract_tool.ainvoke(
        {
            "url": "https://example.com/members",
            "html_content": "<html><body>Test</body></html>",
            "party_name": "Test Party",
        }
    )

    # Verify that internal errors are handled gracefully
    # (extractor catches the error and returns None, which becomes success=False)
    assert result["success"] is False
    assert result["count"] == 0
    assert result["party_name"] == "Test Party"
    # Note: "error" field is NOT present because the extractor handles it internally


@pytest.mark.asyncio
async def test_create_member_extractor_tools_returns_list() -> None:
    """Test that create_member_extractor_tools returns a list of tools."""
    tools = create_member_extractor_tools()
    assert isinstance(tools, list)
    assert len(tools) == 1


@pytest.mark.asyncio
async def test_tool_with_party_id(
    mock_llm_service: MockLLMService, sample_html: str
) -> None:
    """Test tool creation with party_id for history tracking."""
    # Create tools with party_id
    tools = create_member_extractor_tools(llm_service=mock_llm_service, party_id=123)
    extract_tool = tools[0]

    # Execute tool
    result = await extract_tool.ainvoke(
        {
            "url": "https://example.com/members",
            "html_content": sample_html,
            "party_name": "Example Party",
        }
    )

    # Verify result (party_id doesn't affect output, but ensures no errors)
    assert result["success"] is True
    assert result["count"] == 2
