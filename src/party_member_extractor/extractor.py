"""LLM-based party member extractor"""

import logging
import re

from bs4 import BeautifulSoup
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import PartyMemberList, WebPageContent

logger = logging.getLogger(__name__)


class PartyMemberExtractor:
    """LLMを使用して政党議員情報を抽出"""

    def __init__(self, llm: ChatGoogleGenerativeAI | None = None):
        if llm is None:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp", temperature=0.1
            )
        else:
            self.llm = llm

        self.extraction_llm = self.llm.with_structured_output(PartyMemberList)

    def extract_from_pages(
        self, pages: list[WebPageContent], party_name: str
    ) -> PartyMemberList:
        """複数ページから議員情報を抽出"""
        all_members = []

        for page in pages:
            logger.info(f"Extracting from page {page.page_number}: {page.url}")
            members = self._extract_from_single_page(page, party_name)

            if members and members.members:
                # 重複チェック
                existing_names = {m.name for m in all_members}
                for member in members.members:
                    if member.name not in existing_names:
                        all_members.append(member)
                        existing_names.add(member.name)

        result = PartyMemberList(
            members=all_members, total_count=len(all_members), party_name=party_name
        )

        logger.info(f"Total extracted members: {len(all_members)}")
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
        prompt = PromptTemplate.from_template("""
あなたは政党の議員一覧ページから議員情報を抽出する専門家です。
以下のHTMLコンテンツから、{party_name}所属の議員情報を抽出してください。

抽出する情報：
- name: 議員の氏名（姓名）
- position: 役職（衆議院議員、参議院議員など）
- electoral_district: 選挙区（例：東京1区、比例北海道）
- prefecture: 都道府県（選挙区から推測可能な場合）
- profile_url: プロフィールページのURL（相対URLの場合は{base_url}を基準に絶対URLに変換）
- party_position: 党内役職（代表、幹事長など）

注意事項：
- 議員でない人物（スタッフ、事務所関係者など）は除外してください
- 氏名は漢字表記を優先し、ふりがなは除外してください
- 選挙区から都道府県を推測できる場合は prefecture に設定してください
- URLは絶対URLに変換してください

HTMLコンテンツ：
{content}
""")

        try:
            result = self.extraction_llm.invoke(
                prompt.format(
                    party_name=party_name,
                    base_url=self._get_base_url(page.url),
                    content=main_content,
                )
            )

            # URLを絶対URLに変換
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
        # メインコンテンツの候補
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
        ]

        for selector in main_selectors:
            main = soup.select_one(selector)
            if main:
                return self._clean_text(main.get_text(separator="\n", strip=True))

        # 見つからない場合はbody全体
        body = soup.find("body")
        if body:
            # ヘッダーとフッターを除外
            for tag in body.find_all(["header", "footer", "nav"]):
                tag.decompose()
            return self._clean_text(body.get_text(separator="\n", strip=True))

        return self._clean_text(soup.get_text(separator="\n", strip=True))

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
