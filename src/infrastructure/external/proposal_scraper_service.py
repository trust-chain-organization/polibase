"""Implementation of proposal scraping service."""

import asyncio
import re
from typing import Any

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

from src.infrastructure.interfaces.proposal_scraper_service import (
    IProposalScraperService,
)


class ProposalScraperService(IProposalScraperService):
    """Service for scraping proposal from Japanese government websites."""

    def __init__(self, headless: bool = True):
        """Initialize the scraper service.

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless

    def is_supported_url(self, url: str) -> bool:
        """Check if the given URL is supported by this scraper.

        Args:
            url: URL to check

        Returns:
            True if the URL is supported, False otherwise
        """
        supported_domains = [
            "shugiin.go.jp",  # 衆議院
            "city.kyoto.lg.jp",  # 京都市議会
            "city.kyoto.jp",  # 京都市議会（別ドメイン）
        ]
        return any(domain in url for domain in supported_domains)

    async def scrape_proposal(self, url: str) -> dict[str, Any]:
        """Scrape proposal details from a given URL.

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

        if "shugiin.go.jp" in url:
            return await self._scrape_shugiin_proposal(url)
        elif "city.kyoto" in url:
            return await self._scrape_kyoto_proposal(url)
        else:
            raise ValueError(f"No scraper implementation for URL: {url}")

    async def _scrape_shugiin_proposal(self, url: str) -> dict[str, Any]:
        """Scrape proposal from the House of Representatives website.

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

                # Extract proposal information
                proposal_data = {
                    "url": url,
                    "content": "",
                    "proposal_number": "",
                    "submission_date": None,
                    "summary": "",
                }

                # Extract proposal number and title
                # 衆議院のページでは通常、議案番号と議案名が一緒に表示される
                title_element = soup.find("h1") or soup.find("h2")
                if title_element:
                    title_text = title_element.get_text(strip=True)
                    # 議案番号を抽出（例: 第210回国会 第1号）
                    number_match = re.search(r"第?\d+回?国会\s*第?\d+号?", title_text)
                    if number_match:
                        proposal_data["proposal_number"] = number_match.group()
                        # 議案番号を除いた部分を議案名とする
                        proposal_data["content"] = title_text.replace(
                            number_match.group(), ""
                        ).strip()
                    else:
                        proposal_data["content"] = title_text

                # Extract submission date
                date_patterns = [
                    r"提出日[:：]\s*(\d{4}年\d{1,2}月\d{1,2}日)",
                    r"(\d{4}年\d{1,2}月\d{1,2}日)\s*提出",
                    r"令和(\d+)年(\d{1,2})月(\d{1,2})日",
                ]
                for pattern in date_patterns:
                    date_match = re.search(pattern, content)
                    if date_match:
                        # Convert Japanese date to ISO format
                        date_str = (
                            date_match.group(1)
                            if "令和" not in pattern
                            else date_match.group(0)
                        )
                        proposal_data["submission_date"] = (
                            self._convert_japanese_date_to_iso(date_str)
                        )
                        break

                # Extract summary if available
                summary_element = soup.find("div", class_="summary") or soup.find(
                    "div", id="summary"
                )
                if summary_element:
                    proposal_data["summary"] = summary_element.get_text(strip=True)

                return proposal_data

            except Exception as e:
                raise RuntimeError(
                    f"Failed to scrape Shugiin proposal: {str(e)}"
                ) from e
            finally:
                await browser.close()

    async def _scrape_kyoto_proposal(self, url: str) -> dict[str, Any]:
        """Scrape proposal from Kyoto City Council website.

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

                # Extract proposal information
                proposal_data = {
                    "url": url,
                    "content": "",
                    "proposal_number": "",
                    "submission_date": None,
                    "summary": "",
                }

                # Kyoto city council specific extraction logic
                # Look for proposal title
                title_element = (
                    soup.find("h1")
                    or soup.find("h2")
                    or soup.find("div", class_="title")
                )
                if title_element:
                    proposal_data["content"] = title_element.get_text(strip=True)

                # Extract proposal number (京都市議会では議案番号の形式が異なる)
                number_patterns = [
                    r"議第(\d+)号",
                    r"市会議案第(\d+)号",
                    r"(\d+)号議案",
                ]
                for pattern in number_patterns:
                    number_match = re.search(pattern, content)
                    if number_match:
                        proposal_data["proposal_number"] = number_match.group()
                        break

                # Extract date (京都市議会の日付形式)
                date_patterns = [
                    r"(\d{4})年(\d{1,2})月(\d{1,2})日",
                    r"令和(\d+)年(\d{1,2})月(\d{1,2})日",
                    r"平成(\d+)年(\d{1,2})月(\d{1,2})日",
                ]
                for pattern in date_patterns:
                    date_match = re.search(pattern, content)
                    if date_match:
                        if "令和" in pattern:
                            year = 2018 + int(date_match.group(1))
                            month = date_match.group(2).zfill(2)
                            day = date_match.group(3).zfill(2)
                            proposal_data["submission_date"] = f"{year}-{month}-{day}"
                        elif "平成" in pattern:
                            year = 1988 + int(date_match.group(1))
                            month = date_match.group(2).zfill(2)
                            day = date_match.group(3).zfill(2)
                            proposal_data["submission_date"] = f"{year}-{month}-{day}"
                        else:
                            year = date_match.group(1)
                            month = date_match.group(2).zfill(2)
                            day = date_match.group(3).zfill(2)
                            proposal_data["submission_date"] = f"{year}-{month}-{day}"
                        break

                # Look for summary or description sections
                summary_sections = soup.find_all(
                    ["div", "section"], class_=re.compile(r"(summary|description|概要)")
                )
                if summary_sections:
                    proposal_data["summary"] = summary_sections[0].get_text(strip=True)[
                        :500
                    ]  # Limit to 500 chars

                return proposal_data

            except Exception as e:
                raise RuntimeError(f"Failed to scrape Kyoto proposal: {str(e)}") from e
            finally:
                await browser.close()

    def _convert_japanese_date_to_iso(self, date_str: str) -> str:
        """Convert Japanese date format to ISO format.

        Args:
            date_str: Japanese date string (e.g., "2023年12月1日")

        Returns:
            ISO format date string (e.g., "2023-12-01")
        """
        try:
            # Handle different Japanese date formats
            if "令和" in date_str:
                # Handle 令和元年 (Reiwa 1st year)
                if "令和元年" in date_str:
                    match = re.search(r"令和元年(\d{1,2})月(\d{1,2})日", date_str)
                    if match:
                        year = 2019
                        month = match.group(1).zfill(2)
                        day = match.group(2).zfill(2)
                        return f"{year}-{month}-{day}"
                else:
                    match = re.search(r"令和(\d+)年(\d{1,2})月(\d{1,2})日", date_str)
                    if match:
                        year = 2018 + int(match.group(1))
                        month = match.group(2).zfill(2)
                        day = match.group(3).zfill(2)
                        return f"{year}-{month}-{day}"
            elif "平成" in date_str:
                # Handle 平成元年 (Heisei 1st year)
                if "平成元年" in date_str:
                    match = re.search(r"平成元年(\d{1,2})月(\d{1,2})日", date_str)
                    if match:
                        year = 1989
                        month = match.group(1).zfill(2)
                        day = match.group(2).zfill(2)
                        return f"{year}-{month}-{day}"
                else:
                    match = re.search(r"平成(\d+)年(\d{1,2})月(\d{1,2})日", date_str)
                    if match:
                        year = 1988 + int(match.group(1))
                        month = match.group(2).zfill(2)
                        day = match.group(3).zfill(2)
                        return f"{year}-{month}-{day}"
            else:
                # Standard format: 2023年12月1日
                match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
                if match:
                    year = match.group(1)
                    month = match.group(2).zfill(2)
                    day = match.group(3).zfill(2)
                    return f"{year}-{month}-{day}"
        except Exception:
            pass

        return date_str  # Return original if conversion fails
