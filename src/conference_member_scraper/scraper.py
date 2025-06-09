"""Conference member scraper implementation"""

import asyncio
import logging
from datetime import date
from typing import Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from playwright.async_api import async_playwright

from src.conference_member_scraper.models import ConferenceMember, ConferenceMemberList
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ConferenceMemberScraper:
    """会議体メンバー情報をスクレイピングするクラス"""

    def __init__(self):
        self.llm_service = LLMService()

    async def fetch_html(self, url: str) -> str:
        """URLからHTMLを取得"""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2000)  # 動的コンテンツの読み込み待機
                content = await page.content()
                return content
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
                raise
            finally:
                await browser.close()

    def extract_members_with_llm(
        self, html_content: str, conference_name: str
    ) -> list[ConferenceMember]:
        """LLMを使用してHTMLから議員情報を抽出"""
        # パーサーの設定
        parser = PydanticOutputParser(pydantic_object=list[ConferenceMember])

        # プロンプトテンプレート
        prompt = PromptTemplate(
            template="""以下のHTMLから{conference_name}の議員メンバー情報を抽出してください。

HTMLコンテンツ:
{html_content}

抽出する情報:
1. 議員名（フルネーム）
2. 役職（議長、副議長、委員長、副委員長、委員など）
3. 所属政党名（わかる場合）
4. 就任日（わかる場合）
5. その他の重要な情報

注意事項:
- 議員名は姓名を正確に抽出してください
- 役職がない場合は「委員」としてください
- 議長、副議長、委員長などの役職者は必ず役職を明記してください
- 複数の役職がある場合は主要な役職を選択してください

{format_instructions}""",
            input_variables=["html_content", "conference_name"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        # LLMチェーンの実行
        chain = prompt | self.llm_service.get_llm() | parser

        try:
            # HTMLが長すぎる場合は切り詰める
            max_length = 50000
            if len(html_content) > max_length:
                html_content = html_content[:max_length] + "..."

            members = chain.invoke(
                {"html_content": html_content, "conference_name": conference_name}
            )
            return members
        except Exception as e:
            logger.error(f"Error extracting members with LLM: {e}")
            return []

    async def scrape_conference_members(
        self, conference_id: int, conference_name: str, url: str
    ) -> ConferenceMemberList:
        """会議体メンバー情報をスクレイピング"""
        logger.info(f"Scraping members from {url} for conference {conference_name}")

        try:
            # HTMLを取得
            html_content = await self.fetch_html(url)

            # LLMで議員情報を抽出
            members = self.extract_members_with_llm(html_content, conference_name)

            # 結果を構築
            member_list = ConferenceMemberList(
                conference_id=conference_id,
                conference_name=conference_name,
                url=url,
                members=members,
            )

            logger.info(f"Successfully extracted {len(members)} members")
            return member_list

        except Exception as e:
            logger.error(f"Error scraping conference members: {e}")
            # エラー時は空のリストを返す
            return ConferenceMemberList(
                conference_id=conference_id,
                conference_name=conference_name,
                url=url,
                members=[],
            )