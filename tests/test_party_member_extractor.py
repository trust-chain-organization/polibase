"""Tests for Party Member Extractor"""

from unittest.mock import Mock

import pytest

from src.party_member_extractor.extractor import PartyMemberExtractor
from src.party_member_extractor.models import (
    PartyMemberInfo,
    PartyMemberList,
    WebPageContent,
)


class TestPartyMemberExtractor:
    """PartyMemberExtractorのテストクラス"""

    @pytest.fixture
    def mock_llm(self):
        """モックLLMのフィクスチャ"""
        mock = Mock()
        mock.model_name = "test-model"
        mock.temperature = 0.1
        return mock

    @pytest.fixture
    def extractor(self, mock_llm):
        """エクストラクターのフィクスチャ"""
        # PartyMemberExtractorはLLMServiceを使わず、直接ChatGoogleGenerativeAIを使用
        extractor = PartyMemberExtractor(llm=mock_llm)

        # Mock the with_structured_output method
        mock_extraction_llm = Mock()
        mock_llm.with_structured_output.return_value = mock_extraction_llm

        # Store reference for test access
        extractor._mock_extraction_llm = mock_extraction_llm
        return extractor

    @pytest.fixture
    def sample_html(self):
        """サンプルHTMLのフィクスチャ"""
        return """
        <html>
        <body>
            <main>
                <div class="member-list">
                    <div class="member">
                        <h3>山田太郎</h3>
                        <p>衆議院議員</p>
                        <p>東京1区</p>
                        <a href="/profile/yamada">プロフィール</a>
                    </div>
                    <div class="member">
                        <h3>鈴木花子</h3>
                        <p>参議院議員</p>
                        <p>比例代表</p>
                        <p>幹事長</p>
                        <a href="/profile/suzuki">プロフィール</a>
                    </div>
                </div>
            </main>
        </body>
        </html>
        """

    def test_extract_from_pages(self, extractor, mock_llm, sample_html):
        """複数ページからの抽出テスト"""
        # モックLLMの設定 - Use the mock from fixture
        extractor.extraction_llm.invoke.side_effect = [
            PartyMemberList(
                members=[
                    PartyMemberInfo(
                        name="山田太郎",
                        position="衆議院議員",
                        electoral_district="東京1区",
                        prefecture="東京都",
                        profile_url="/profile/yamada",
                    )
                ],
                total_count=1,
                party_name="テスト党",
            ),
            PartyMemberList(
                members=[
                    PartyMemberInfo(
                        name="鈴木花子",
                        position="参議院議員",
                        electoral_district="比例代表",
                        party_position="幹事長",
                        profile_url="/profile/suzuki",
                    )
                ],
                total_count=1,
                party_name="テスト党",
            ),
        ]

        # テストデータ
        pages = [
            WebPageContent(
                url="https://example.com/members/page1",
                html_content=sample_html,
                page_number=1,
            ),
            WebPageContent(
                url="https://example.com/members/page2",
                html_content=sample_html,
                page_number=2,
            ),
        ]

        # テスト実行
        result = extractor.extract_from_pages(pages, "テスト党")

        # アサーション
        assert result.total_count == 2
        assert len(result.members) == 2
        assert result.members[0].name == "山田太郎"
        assert result.members[1].name == "鈴木花子"
        assert result.party_name == "テスト党"

        # 重複がないことを確認
        names = [m.name for m in result.members]
        assert len(names) == len(set(names))

    def test_extract_from_single_page(self, extractor, mock_llm, sample_html):
        """単一ページからの抽出テスト"""
        # モックLLMの設定
        mock_extraction_llm = Mock()
        mock_extraction_llm.invoke.return_value = PartyMemberList(
            members=[
                PartyMemberInfo(
                    name="田中三郎",
                    position="衆議院議員",
                    electoral_district="大阪1区",
                    prefecture="大阪府",
                    profile_url="/profile/tanaka",
                )
            ],
            total_count=1,
            party_name="テスト党",
        )
        extractor.extraction_llm = mock_extraction_llm

        # テストデータ
        page = WebPageContent(
            url="https://example.com/members", html_content=sample_html, page_number=1
        )

        # テスト実行
        result = extractor._extract_from_single_page(page, "テスト党")

        # アサーション
        assert result is not None
        assert len(result.members) == 1
        assert result.members[0].name == "田中三郎"
        # 相対URLが絶対URLに変換されることを確認
        assert result.members[0].profile_url == "https://example.com/profile/tanaka"

    def test_extract_main_content(self, extractor):
        """メインコンテンツ抽出のテスト"""
        html = """
        <html>
        <body>
            <header>ヘッダー</header>
            <nav>ナビゲーション</nav>
            <main>
                <h1>議員一覧</h1>
                <div class="member">山田太郎</div>
            </main>
            <footer>フッター</footer>
        </body>
        </html>
        """

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        # テスト実行
        content = extractor._extract_main_content(soup)

        # アサーション
        assert "議員一覧" in content
        assert "山田太郎" in content
        assert "ヘッダー" not in content  # ヘッダーは除外
        assert "フッター" not in content  # フッターは除外

    def test_clean_text(self, extractor):
        """テキストクリーンアップのテスト"""
        text = """


        山田太郎

        衆議院議員


        東京1区

        """

        # テスト実行
        cleaned = extractor._clean_text(text)

        # アサーション
        lines = cleaned.split("\n")
        assert len(lines) == 3
        assert lines[0] == "山田太郎"
        assert lines[1] == "衆議院議員"
        assert lines[2] == "東京1区"

    def test_get_base_url(self, extractor):
        """ベースURL取得のテスト"""
        test_cases = [
            ("https://example.com/members/page1", "https://example.com/"),
            ("http://test.jp/path/to/page", "http://test.jp/"),
            ("https://sub.domain.com:8080/page", "https://sub.domain.com:8080/"),
        ]

        for url, expected in test_cases:
            assert extractor._get_base_url(url) == expected

    def test_extract_with_error(self, extractor, mock_llm):
        """エラー処理のテスト"""
        # モックLLMがエラーを発生させる
        mock_extraction_llm = Mock()
        mock_extraction_llm.invoke.side_effect = Exception("LLM Error")
        extractor.extraction_llm = mock_extraction_llm

        page = WebPageContent(
            url="https://example.com/members",
            html_content="<html><body>test</body></html>",
            page_number=1,
        )

        # テスト実行
        result = extractor._extract_from_single_page(page, "テスト党")

        # アサーション
        assert result is None

    def test_duplicate_removal(self, extractor, mock_llm):
        """重複除去のテスト"""
        # モックLLMの設定（同じ名前の議員を返す）
        mock_extraction_llm = Mock()
        mock_extraction_llm.invoke.side_effect = [
            PartyMemberList(
                members=[PartyMemberInfo(name="重複太郎", position="衆議院議員")],
                total_count=1,
            ),
            PartyMemberList(
                members=[
                    PartyMemberInfo(name="重複太郎", position="参議院議員"),  # 同じ名前
                    PartyMemberInfo(name="別人次郎", position="衆議院議員"),
                ],
                total_count=2,
            ),
        ]
        extractor.extraction_llm = mock_extraction_llm

        pages = [
            WebPageContent(
                url="https://example.com/1",
                html_content="<html><body>test1</body></html>",
                page_number=1,
            ),
            WebPageContent(
                url="https://example.com/2",
                html_content="<html><body>test2</body></html>",
                page_number=2,
            ),
        ]

        # テスト実行
        result = extractor.extract_from_pages(pages, "テスト党")

        # アサーション
        assert len(result.members) == 2  # 重複を除いて2人
        names = [m.name for m in result.members]
        assert "重複太郎" in names
        assert "別人次郎" in names
