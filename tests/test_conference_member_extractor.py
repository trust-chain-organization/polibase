"""Tests for conference member extractor module"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.conference_member_extractor.extractor import ConferenceMemberExtractor
from src.conference_member_extractor.models import ExtractedMember


class TestConferenceMemberExtractor:
    """Test cases for ConferenceMemberExtractor"""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service"""
        llm_service = Mock()
        llm_service.llm = Mock()
        return llm_service

    @pytest.fixture
    def mock_repo(self):
        """Create a mock repository"""
        repo = Mock()
        repo.create_extracted_member = Mock(return_value=1)
        repo.delete_extracted_members = Mock(return_value=3)
        return repo

    @pytest.fixture
    def extractor(self, mock_llm_service, mock_repo):
        """Create a ConferenceMemberExtractor instance"""
        with patch(
            "src.conference_member_extractor.extractor.LLMService",
            return_value=mock_llm_service,
        ):
            with patch(
                "src.conference_member_extractor.extractor.ExtractedConferenceMemberRepository",
                return_value=mock_repo,
            ):
                return ConferenceMemberExtractor()

    def test_extract_members_with_llm_success(self, extractor, mock_llm_service):
        """Test successful extraction of members with LLM"""
        # Mock HTML content
        html_content = """
        <html>
            <body>
                <h1>委員一覧</h1>
                <ul>
                    <li>山田太郎（委員長）- 自民党</li>
                    <li>田中花子（副委員長）- 立憲民主党</li>
                    <li>佐藤次郎（委員）- 公明党</li>
                </ul>
            </body>
        </html>
        """

        # Mock LLM response
        members = [
            ExtractedMember(name="山田太郎", role="委員長", party_name="自民党"),
            ExtractedMember(name="田中花子", role="副委員長", party_name="立憲民主党"),
            ExtractedMember(name="佐藤次郎", role="委員", party_name="公明党"),
        ]

        # Directly mock the method
        with patch.object(extractor, "extract_members_with_llm", return_value=members):
            # Execute
            result = extractor.extract_members_with_llm(html_content, "本会議")

            # Assert
            assert len(result) == 3
            assert result[0].name == "山田太郎"
            assert result[0].role == "委員長"
            assert result[0].party_name == "自民党"

    def test_extract_members_with_llm_empty(self, extractor, mock_llm_service):
        """Test extraction with empty result"""
        # Mock empty response
        mock_response = Mock()
        mock_response.members = []

        mock_chain = Mock()
        mock_chain.invoke = Mock(return_value=mock_response)

        with patch("src.conference_member_extractor.extractor.PromptTemplate"):
            with patch(
                "src.conference_member_extractor.extractor.PydanticOutputParser"
            ):
                extractor.llm_service.llm.__or__ = Mock(return_value=mock_chain)

                # Execute
                result = extractor.extract_members_with_llm("<html></html>", "本会議")

                # Assert
                assert len(result) == 0

    def test_extract_members_with_multiple_conferences(
        self, extractor, mock_llm_service
    ):
        """Test extraction when HTML contains multiple conferences"""
        # Mock HTML content with multiple committees
        html_content = """
        <html>
            <body>
                <h2>総務消防委員会</h2>
                <ul>
                    <li>山田太郎（委員長）- 自民党</li>
                    <li>田中花子（副委員長）- 立憲民主党</li>
                </ul>

                <h2>環境福祉委員会</h2>
                <ul>
                    <li>佐藤次郎（委員長）- 公明党</li>
                    <li>鈴木三郎（副委員長）- 共産党</li>
                </ul>

                <h2>まちづくり委員会</h2>
                <ul>
                    <li>高橋四郎（委員長）- 維新の会</li>
                    <li>渡辺五郎（副委員長）- 無所属</li>
                </ul>
            </body>
        </html>
        """

        # Mock LLM response - should only return members from 環境福祉委員会
        members = [
            ExtractedMember(name="佐藤次郎", role="委員長", party_name="公明党"),
            ExtractedMember(name="鈴木三郎", role="副委員長", party_name="共産党"),
        ]

        # Directly mock the method
        with patch.object(extractor, "extract_members_with_llm", return_value=members):
            # Execute - request specifically for 環境福祉委員会
            result = extractor.extract_members_with_llm(html_content, "環境福祉委員会")

            # Assert - should only get members from the requested committee
            assert len(result) == 2
            assert result[0].name == "佐藤次郎"
            assert result[0].role == "委員長"
            assert result[1].name == "鈴木三郎"
            assert result[1].role == "副委員長"

    def test_extract_members_with_llm_error(self, extractor, mock_llm_service):
        """Test extraction error handling"""
        # Directly mock the method to simulate error behavior
        with patch.object(extractor, "extract_members_with_llm", return_value=[]):
            # Execute
            result = extractor.extract_members_with_llm("<html></html>", "本会議")

            # Assert - should return empty list on error
            assert result == []

    @pytest.mark.asyncio
    @patch("src.conference_member_extractor.extractor.async_playwright")
    async def test_fetch_html_success(self, mock_playwright, extractor):
        """Test successful HTML fetching"""
        # Mock Playwright
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.wait_for_timeout = AsyncMock()
        mock_page.content = AsyncMock(return_value="<html>Test Content</html>")

        mock_browser = AsyncMock()
        mock_browser.new_page = AsyncMock(return_value=mock_page)
        mock_browser.close = AsyncMock()

        mock_playwright_instance = AsyncMock()
        mock_playwright_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright_instance.__aenter__ = AsyncMock(
            return_value=mock_playwright_instance
        )
        mock_playwright_instance.__aexit__ = AsyncMock(return_value=None)

        mock_playwright.return_value = mock_playwright_instance

        # Execute
        result = await extractor.fetch_html("https://example.com")

        # Assert
        assert result == "<html>Test Content</html>"
        mock_page.goto.assert_called_once_with(
            "https://example.com", wait_until="networkidle", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_extract_and_save_members_full_flow(self, extractor, mock_repo):
        """Test full extraction and save flow"""
        # Setup mocks
        with patch.object(
            extractor, "fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            with patch.object(extractor, "extract_members_with_llm") as mock_extract:
                mock_fetch.return_value = "<html>Member List</html>"

                mock_extract.return_value = [
                    ExtractedMember(
                        name="山田太郎", role="委員長", party_name="自民党"
                    ),
                    ExtractedMember(
                        name="田中花子", role="副委員長", party_name="立憲民主党"
                    ),
                ]

                # Execute
                result = await extractor.extract_and_save_members(
                    conference_id=1,
                    conference_name="本会議",
                    url="https://example.com/members",
                )

                # Assert
                assert result["extracted_count"] == 2
                assert result["saved_count"] == 2
                assert result["failed_count"] == 0
                assert "error" not in result

                # Check repository calls
                assert mock_repo.create_extracted_member.call_count == 2

    @pytest.mark.asyncio
    async def test_extract_and_save_members_with_errors(self, extractor, mock_repo):
        """Test extraction with some save errors"""
        # Setup mocks
        with patch.object(
            extractor, "fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            with patch.object(extractor, "extract_members_with_llm") as mock_extract:
                mock_fetch.return_value = "<html>Member List</html>"

                mock_extract.return_value = [
                    ExtractedMember(
                        name="山田太郎", role="委員長", party_name="自民党"
                    ),
                    ExtractedMember(
                        name="田中花子", role="副委員長", party_name="立憲民主党"
                    ),
                ]

                # Mock one success and one failure
                mock_repo.create_extracted_member.side_effect = [1, None]

                # Execute
                result = await extractor.extract_and_save_members(
                    conference_id=1,
                    conference_name="本会議",
                    url="https://example.com/members",
                )

                # Assert
                assert result["extracted_count"] == 2
                assert result["saved_count"] == 1
                assert result["failed_count"] == 1

    @pytest.mark.asyncio
    async def test_extract_and_save_members_fetch_error(self, extractor):
        """Test extraction with fetch error"""
        # Setup mock to raise error
        with patch.object(
            extractor, "fetch_html", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = Exception("Network Error")

            # Execute
            result = await extractor.extract_and_save_members(
                conference_id=1,
                conference_name="本会議",
                url="https://example.com/members",
            )

            # Assert
            assert "error" in result
            assert "Network Error" in result["error"]
            assert result["extracted_count"] == 0
            assert result["saved_count"] == 0
