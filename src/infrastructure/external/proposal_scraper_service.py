"""Implementation of proposal scraping service using LLM for flexible extraction."""

import asyncio
import json
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.infrastructure.interfaces.llm_service import ILLMService
from src.infrastructure.interfaces.proposal_scraper_service import (
    IProposalScraperService,
)


class ProposalScraperService(IProposalScraperService):
    """Service for scraping proposal from Japanese government websites using LLM."""

    def __init__(self, llm_service: ILLMService, headless: bool = True):
        """Initialize the scraper service.

        Args:
            llm_service: LLM service for content extraction
            headless: Whether to run browser in headless mode
        """
        self.llm_service = llm_service
        self.headless = headless

    def is_supported_url(self, url: str) -> bool:
        """Check if the given URL is supported by this scraper.

        Args:
            url: URL to check

        Returns:
            True if the URL appears to be a government/council website
        """
        # Support any government or council domain
        gov_indicators = [
            ".go.jp",  # 国の機関
            ".lg.jp",  # 地方自治体
            "city.",  # 市議会
            "pref.",  # 都道府県
            "town.",  # 町議会
            "vill.",  # 村議会
            "metro.",  # 都議会
            "assembly.",  # 議会
            "council.",  # 議会
            "shugiin",  # 衆議院
            "sangiin",  # 参議院
        ]
        return any(indicator in url.lower() for indicator in gov_indicators)

    async def scrape_proposal(self, url: str) -> dict[str, Any]:
        """Scrape proposal details from a given URL using LLM extraction.

        Args:
            url: URL of the proposal page

        Returns:
            Dictionary containing scraped proposal information

        Raises:
            ValueError: If the URL format is not supported
            RuntimeError: If scraping fails
        """
        if not self.is_supported_url(url):
            raise ValueError(f"Unsupported URL: {url}")

        return await self._scrape_with_llm(url)

    async def _scrape_with_llm(self, url: str) -> dict[str, Any]:
        """Scrape proposal from any government website using LLM.

        Args:
            url: URL of the proposal page

        Returns:
            Dictionary containing scraped proposal information
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="networkidle")
                await asyncio.sleep(1)  # Wait for dynamic content

                # Get the page content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")

                # Get text content from the page
                # Remove script and style elements
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get text content
                text_content = soup.get_text(separator="\n", strip=True)

                # Limit text content to avoid token limits
                max_chars = 10000
                if len(text_content) > max_chars:
                    text_content = text_content[:max_chars] + "..."

                # Use LLM to extract proposal information
                extraction_prompt = f"""以下の政府・議会のウェブページから議案情報を抽出してください。

URL: {url}

ページ内容:
{text_content}

以下の情報を抽出してください（見つからない場合は空文字列または null を返してください）：
1. content: 議案名・法案名（タイトル）
2. proposal_number: 議案番号（例：第210回国会第1号、議第15号など）
3. submission_date: 提出日・上程日・議決日など
   （日付として認識できるもの、例：2023年12月1日、令和5年12月1日）
4. summary: 議案の概要・説明（あれば最初の200文字程度）

JSON形式で返してください。日付はそのまま抽出された文字列で返してください（変換不要）。
"""

                # Call LLM to extract information
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "あなたは日本の政府・議会ウェブサイトから"
                            "情報を抽出する専門家です。"
                        ),
                    },
                    {"role": "user", "content": extraction_prompt},
                ]

                llm_response = self.llm_service.invoke_llm(messages)

                # Parse the LLM response
                try:
                    # Try to parse as JSON
                    extracted_data = json.loads(llm_response)
                except json.JSONDecodeError:
                    # If not valid JSON, try to extract from the text response
                    extracted_data = {
                        "content": "",
                        "proposal_number": None,
                        "submission_date": None,
                        "summary": None,
                    }
                    # Simple fallback extraction from LLM text response
                    if "content:" in llm_response:
                        content_match = (
                            llm_response.split("content:")[1].split("\n")[0].strip()
                        )
                        extracted_data["content"] = content_match.strip('"').strip()

                # Build the proposal data
                proposal_data = {
                    "url": url,
                    "content": extracted_data.get("content", ""),
                    "proposal_number": extracted_data.get("proposal_number"),
                    "submission_date": extracted_data.get("submission_date"),
                    "summary": extracted_data.get("summary"),
                }

                return proposal_data

            except Exception as e:
                raise RuntimeError(
                    f"Failed to scrape proposal from {url}: {str(e)}"
                ) from e
            finally:
                await browser.close()
