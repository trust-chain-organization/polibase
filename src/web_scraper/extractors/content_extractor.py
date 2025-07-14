"""HTML parsing and content extraction"""

import logging
import re

from bs4 import BeautifulSoup, Tag


class ContentExtractor:
    """HTMLコンテンツ抽出器"""

    # 議事録コンテンツのセレクタ
    CONTENT_SELECTORS = [
        "#plain-minute",
        "#outputframe-minute",
        ".minute-content",
        ".meeting-record",
        ".minute-body",
        "#minute-body",
        ".info-txt",  # kaigiroku.net特有のクラス
        'div[id*="minute"]',
        'div[class*="minute"]',
        ".content-main",
        "#content-main",
        "main",
        "article",
        ".document-content",
        "#document-content",
    ]

    # 削除すべき要素のタグ
    REMOVE_TAGS = ["script", "style", "noscript", "button", "header", "footer", "nav"]

    # 無視すべきテキストパターン
    IGNORE_TEXTS = {
        "印刷",
        "文字拡大",
        "文字縮小",
        "ダウンロード",
        "PDF",
        "トップページ",
        "ホーム",
        "戻る",
        "次へ",
        "前へ",
    }

    # 議事録として有効なキーワード
    VALID_KEYWORDS = {
        "議",
        "委員",
        "市長",
        "町長",
        "村長",
        "知事",
        "局長",
        "部長",
        "課長",
        "答弁",
        "質問",
        "会議",
        "記録",
        "令和",
        "平成",
        "審議",
        "説明",
        "議事",
        "本会議",
        "委員会",
        "定例会",
        "臨時会",
        "協議",
    }

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    def extract_content(self, html_content: str) -> str:
        """HTMLから議事録コンテンツを抽出

        Args:
            html_content: HTML文字列

        Returns:
            抽出されたテキストコンテンツ
        """
        soup = BeautifulSoup(html_content, "html.parser")

        # まず特定のセレクタでコンテンツを探す
        content = self._extract_by_selectors(soup)

        if content and self._is_valid_content(content):
            return content

        # セレクタで見つからない場合は全体から抽出
        content = self._extract_from_body(soup)

        if not content or not self._is_valid_content(content):
            self.logger.warning("No valid content found, extracting all text")
            content = self._extract_all_text(soup)

        return content

    def _extract_by_selectors(self, soup: BeautifulSoup) -> str:
        """セレクタを使用してコンテンツを抽出"""
        for selector in self.CONTENT_SELECTORS:
            elements = self._find_elements(soup, selector)

            for element in elements:
                # 不要な要素を削除
                self._clean_element(element)

                # テキストを抽出
                text = self._extract_text_from_element(element)

                if text and len(text) > 50:  # 最小限のコンテンツがあれば返す
                    self.logger.info(
                        f"Found content with selector {selector}, length: {len(text)}"
                    )
                    return text

        return ""

    def _find_elements(self, soup: BeautifulSoup, selector: str) -> list[Tag]:
        """セレクタに一致する要素を検索"""
        elements: list[Tag] = []

        if selector.startswith("#"):
            # IDセレクタ
            element = soup.find(id=selector[1:])
            if element and isinstance(element, Tag):
                elements = [element]
        elif selector.startswith("."):
            # クラスセレクタ
            found_elements = soup.find_all(class_=re.compile(selector[1:]))
            elements = [el for el in found_elements if isinstance(el, Tag)]
        elif "[" in selector:
            # 属性セレクタ
            found_elements = soup.select(selector)
            elements = [el for el in found_elements if isinstance(el, Tag)]
        else:
            # タグセレクタ
            element = soup.find(selector)
            if element and isinstance(element, Tag):
                elements = [element]

        return elements

    def _clean_element(self, element: Tag):
        """要素から不要なタグを削除"""
        for tag in self.REMOVE_TAGS:
            for item in element.find_all(tag):
                item.decompose()

    def _extract_text_from_element(self, element: Tag) -> str:
        """要素からテキストを抽出して整形"""
        # テキストを抽出
        text = element.get_text(separator="\n", strip=True)

        # 行ごとに処理
        lines = text.split("\n")
        cleaned_lines: list[str] = []

        for line in lines:
            line = line.strip()
            if self._is_valid_line(line):
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _is_valid_line(self, line: str) -> bool:
        """有効な行かどうかチェック"""
        if not line:
            return False

        # 無視すべきテキストかチェック
        for ignore_text in self.IGNORE_TEXTS:
            if line == ignore_text or (
                line.startswith("「") and line.endswith("」ボタン")
            ):
                return False

        return True

    def _extract_from_body(self, soup: BeautifulSoup) -> str:
        """body要素全体から議事録コンテンツを抽出"""
        body = soup.find("body")
        if not body or not isinstance(body, Tag):
            return ""

        # 不要な要素を削除
        self._clean_element(body)

        # テーブル内のテキストも含めて抽出
        text = body.get_text(separator="\n", strip=True)

        # 議事録っぽいコンテンツだけを抽出
        lines = text.split("\n")
        content_lines: list[str] = []

        for line in lines:
            line = line.strip()
            if self._is_minutes_content(line):
                content_lines.append(line)

        return "\n".join(content_lines)

    def _is_minutes_content(self, line: str) -> bool:
        """議事録のコンテンツかどうかチェック"""
        if not line:
            return False

        # 無視すべきテキストかチェック
        if not self._is_valid_line(line):
            return False

        # キーワードが含まれているか、または十分な長さがあるか
        for keyword in self.VALID_KEYWORDS:
            if keyword in line:
                return True

        # 長い行は議事録の可能性が高い
        return len(line) > 20

    def _extract_all_text(self, soup: BeautifulSoup) -> str:
        """全てのテキストを抽出（最終手段）"""
        # 不要な要素を削除
        for tag in self.REMOVE_TAGS:
            for item in soup.find_all(tag):
                item.decompose()

        return soup.get_text(separator="\n", strip=True)

    def _is_valid_content(self, content: str) -> bool:
        """有効なコンテンツかチェック"""
        if not content or len(content.strip()) < 100:
            return False

        # 議事録のキーワードが含まれているかチェック
        keyword_count = sum(1 for keyword in self.VALID_KEYWORDS if keyword in content)

        return keyword_count >= 3

    def extract_title(self, soup: BeautifulSoup) -> str:
        """ページタイトルを抽出"""
        # タイトル要素のセレクタ
        title_selectors = [
            "h1.minute-title",
            "h2.minute-title",
            ".title-area",
            "h1",
            "h2",
            "title",
        ]

        for selector in title_selectors:
            elements = self._find_elements(soup, selector)
            for element in elements:
                title = element.get_text(strip=True)
                if title and len(title) > 5:
                    return title

        # フォールバック
        title_tag = soup.find("title")
        if title_tag:
            return title_tag.get_text(strip=True)

        return "議事録"

    def extract_metadata(self, soup: BeautifulSoup) -> dict[str, str]:
        """メタデータを抽出"""
        metadata: dict[str, str] = {}

        # metaタグから情報を抽出
        for meta in soup.find_all("meta"):
            if isinstance(meta, Tag):
                name = meta.get("name", "")
                content = meta.get("content", "")
                if (
                    name
                    and content
                    and isinstance(name, str)
                    and isinstance(content, str)
                ):
                    metadata[name] = content

        # その他の情報を抽出
        # 例: 会議名、開催場所など
        info_elements = soup.find_all(class_=re.compile("info|detail|meta"))
        for element in info_elements:
            if isinstance(element, Tag):
                text = element.get_text(strip=True)
                if "会議" in text or "場所" in text or "出席" in text:
                    lines = text.split("\n")
                    for line in lines:
                        if "：" in line:
                            key, value = line.split("：", 1)
                            metadata[key.strip()] = value.strip()

        return metadata
