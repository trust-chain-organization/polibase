"""LLM-based party member extractor"""

import logging
import re
from typing import cast

from bs4 import BeautifulSoup, Tag

from ..infrastructure.interfaces.llm_service import ILLMService
from ..infrastructure.persistence.llm_history_helper import SyncLLMHistoryHelper
from ..services.llm_factory import LLMServiceFactory
from .models import PartyMemberInfo, PartyMemberList, WebPageContent

logger = logging.getLogger(__name__)


class PartyMemberExtractor:
    """LLMを使用して政党議員情報を抽出"""

    def __init__(
        self, llm_service: ILLMService | None = None, party_id: int | None = None
    ):
        """
        Initialize PartyMemberExtractor

        Args:
            llm_service: LLMService instance (creates default if not provided)
            party_id: ID of the party being processed (for history tracking)
        """
        if llm_service is None:
            factory = LLMServiceFactory()
            llm_service = cast(ILLMService, factory.create_advanced())

        self.llm_service: ILLMService = llm_service
        self.extraction_llm = self.llm_service.get_structured_llm(PartyMemberList)
        self.party_id = party_id
        self.history_helper = SyncLLMHistoryHelper()

    def extract_from_pages(
        self, pages: list[WebPageContent], party_name: str
    ) -> PartyMemberList:
        """複数ページから議員情報を抽出"""
        all_members: list[PartyMemberInfo] = []

        logger.info(f"Starting extraction from {len(pages)} pages for {party_name}")

        for page in pages:
            logger.info(f"Extracting from page {page.page_number}: {page.url}")
            members = self._extract_from_single_page(page, party_name)

            if members and members.members:
                member_count = len(members.members)
                logger.info(
                    f"Extracted {member_count} members from page {page.page_number}"
                )
                # 重複チェック
                existing_names: set[str] = {m.name for m in all_members}
                new_members_count = 0
                for member in members.members:
                    if member.name not in existing_names:
                        all_members.append(member)
                        existing_names.add(member.name)
                        new_members_count += 1
                        logger.debug(f"Added member: {member.name}")
                if new_members_count < member_count:
                    skipped = member_count - new_members_count
                    logger.info(f"Skipped {skipped} duplicate members")
            else:
                logger.warning(f"No members extracted from page {page.page_number}")

        result = PartyMemberList(
            members=all_members, total_count=len(all_members), party_name=party_name
        )

        logger.info(f"Total extracted members: {len(all_members)}")
        if all_members:
            logger.info(
                f"Members: {', '.join([m.name for m in all_members[:10]])}"
                + (
                    f"... and {len(all_members) - 10} more"
                    if len(all_members) > 10
                    else ""
                )
            )
        return result

    def _extract_from_single_page(
        self, page: WebPageContent, party_name: str
    ) -> PartyMemberList | None:
        """単一ページから議員情報を抽出"""
        # HTMLをテキストに変換（構造を保持）
        soup = BeautifulSoup(page.html_content, "html.parser")

        # スクリプトとスタイルを削除
        for script in soup(["script", "style"]):
            script.decompose()

        # メインコンテンツを抽出
        main_content = self._extract_main_content(soup)

        if not main_content:
            logger.warning(f"No main content found in {page.url}")
            return None

        # LLMで抽出
        try:
            # Get prompt and format it
            prompt = self.llm_service.get_prompt("party_member_extract")
            formatted_prompt = prompt.format(
                party_name=party_name,
                base_url=self._get_base_url(page.url),
                content=main_content,
            )

            # Record history before extraction if party_id is available
            if self.party_id is not None:
                self._record_extraction_to_history(
                    party_name=party_name,
                    page_url=page.url,
                    content_length=len(main_content),
                    status="started",
                )

            # Extract using LLM
            raw_result = self.extraction_llm.invoke(formatted_prompt)
            result = cast(PartyMemberList, raw_result)

            # Record successful extraction
            if self.party_id is not None and result:
                self._record_extraction_to_history(
                    party_name=party_name,
                    page_url=page.url,
                    content_length=len(main_content),
                    status="completed",
                    members_count=len(result.members) if result.members else 0,
                )

            # URLを絶寞URLに変換
            base_url = self._get_base_url(page.url)
            for member in result.members:
                if member.profile_url and not member.profile_url.startswith("http"):
                    member.profile_url = base_url + member.profile_url.lstrip("/")

            return result

        except Exception as e:
            logger.error(f"Error extracting from page: {e}")
            return None

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """メインコンテンツを抽出"""
        # メインコンテンツの候補（より幅広いセレクタを追加）
        main_selectors = [
            "main",
            '[role="main"]',
            "#main",
            "#content",
            ".main-content",
            ".content",
            "article",
            ".member-list",
            ".members",
            "#members",
            ".container",  # 一般的なコンテナ
            ".wrapper",  # ラッパー要素
            "#wrapper",
            ".page-content",
            ".site-content",
        ]

        for selector in main_selectors:
            main = soup.select_one(selector)
            if main:
                content = self._clean_text(main.get_text(separator="\n", strip=True))
                # コンテンツが短すぎる場合はスキップ
                if len(content) > 500:  # 最低500文字以上
                    content_len = len(content)
                    logger.info(
                        f"Found main content with '{selector}': {content_len} chars"
                    )
                    return content

        # 見つからない場合はbody全体
        body = soup.find("body")
        if body and isinstance(body, Tag):
            # ヘッダーとフッターを除外
            for tag in body.find_all(["header", "footer", "nav", "aside"]):
                if isinstance(tag, Tag):
                    tag.decompose()
            content = self._clean_text(body.get_text(separator="\n", strip=True))
            logger.info(f"Using entire body content, length: {len(content)}")
            return content

        content = self._clean_text(soup.get_text(separator="\n", strip=True))
        logger.info(f"Using full page content, length: {len(content)}")
        return content

    def _clean_text(self, text: str) -> str:
        """テキストをクリーンアップ"""
        # 複数の空行を1つに
        text = re.sub(r"\n\s*\n+", "\n\n", text)
        # 行頭行末の空白を削除
        lines = [line.strip() for line in text.split("\n")]
        # 空行でない行だけを残す
        lines = [line for line in lines if line]
        return "\n".join(lines)

    def _get_base_url(self, url: str) -> str:
        """URLからベースURLを取得"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}/"

    def _record_extraction_to_history(
        self,
        party_name: str,
        page_url: str,
        content_length: int,
        status: str,
        members_count: int = 0,
    ) -> None:
        """Record extraction to LLM history"""
        try:
            # Use the sync helper to record history
            if status == "started":
                # For now, we'll just log it
                logger.debug(
                    f"Starting extraction for {party_name} from {page_url} "
                    f"(content_length: {content_length})"
                )
            elif status == "completed":
                # Record using the history helper's new method
                self.history_helper.record_politician_extraction(
                    party_name=party_name,
                    page_url=page_url,
                    extracted_count=members_count,
                    party_id=self.party_id,
                    model_name=getattr(
                        self.llm_service, "model_name", "gemini-2.0-flash-exp"
                    ),
                    prompt_template="party_member_extract",
                )
                logger.debug(
                    f"Completed extraction for {party_name}: {members_count} members"
                )
        except Exception as e:
            logger.error(f"Failed to record extraction history: {e}")
