"""LLMベースの議員団メンバー抽出器"""

import logging

from bs4 import BeautifulSoup
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher
from src.party_member_extractor.models import WebPageContent

from .models import ParliamentaryGroupMemberList

logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberExtractor:
    """LLMを使用して議員団メンバー情報を抽出"""

    def __init__(self, llm: ChatGoogleGenerativeAI | None = None):
        if llm is None:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp", temperature=0.1
            )
        else:
            self.llm = llm

        self.extraction_llm = self.llm.with_structured_output(
            ParliamentaryGroupMemberList
        )

    async def extract_from_url(
        self, url: str, parliamentary_group_name: str
    ) -> ParliamentaryGroupMemberList:
        """URLから議員団メンバー情報を抽出"""
        logger.info(f"Extracting parliamentary group members from: {url}")

        # HTMLコンテンツを取得
        async with PartyMemberPageFetcher() as fetcher:
            pages = await fetcher.fetch_all_pages(url, max_pages=1)

        if not pages:
            logger.error(f"Failed to fetch content from {url}")
            return ParliamentaryGroupMemberList(
                members=[],
                parliamentary_group_name=parliamentary_group_name,
                total_count=0,
                source_url=url,
            )

        # 最初のページからメンバー情報を抽出
        return self._extract_members(pages[0], parliamentary_group_name)

    def _extract_members(
        self, page_content: WebPageContent, parliamentary_group_name: str
    ) -> ParliamentaryGroupMemberList:
        """ページコンテンツから議員団メンバーを抽出"""
        # テキストコンテンツのみ抽出
        soup = BeautifulSoup(page_content.html_content, "html.parser")

        # スクリプトとスタイルタグを削除
        for tag in soup(["script", "style"]):
            tag.decompose()

        # 画像のalt属性を保持
        for img in soup.find_all("img", alt=True):
            img.string = f"[画像: {img['alt']}]"

        text_content = soup.get_text(separator="\n", strip=True)

        # 長すぎる場合は切り詰める（トークン制限対策）
        max_length = 50000
        if len(text_content) > max_length:
            text_content = text_content[:max_length] + "\n... (以下省略)"

        prompt = PromptTemplate.from_template("""
あなたは議員団のWebページから所属議員の情報を正確に抽出する専門家です。

以下のWebページから、議員団「{parliamentary_group_name}」に所属する議員の情報を抽出してください。

注意事項：
1. 議員の氏名は敬称（議員、先生、氏、さんなど）を除いて記録
2. 議員団内での役職（団長、幹事長、政調会長など）があれば記録
3. 所属政党名があれば記録
4. 選挙区や地域の情報があれば記録
5. 個人のプロフィールページへのリンクがあれば記録
6. 議員として明確に識別できる人物のみを抽出（職員や秘書は除外）

Webページの内容：
{text_content}

URL: {url}
""")

        try:
            result = self.extraction_llm.invoke(
                prompt.format(
                    parliamentary_group_name=parliamentary_group_name,
                    text_content=text_content,
                    url=page_content.url,
                )
            )

            # 結果を更新
            result.source_url = page_content.url
            result.parliamentary_group_name = parliamentary_group_name

            logger.info(
                f"Successfully extracted {len(result.members)} members "
                f"from {page_content.url}"
            )

            return result

        except Exception as e:
            logger.error(f"Error extracting members: {e}")
            return ParliamentaryGroupMemberList(
                members=[],
                parliamentary_group_name=parliamentary_group_name,
                total_count=0,
                source_url=page_content.url,
            )
