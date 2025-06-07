"""kaigiroku.netスクレーパーのテスト"""
import asyncio
import os
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.web_scraper.kaigiroku_net_scraper import KaigirokuNetScraper
from src.web_scraper.base_scraper import MinutesData


class TestKaigirokuNetScraper:
    """KaigirokuNetScraperのテストクラス"""
    
    @pytest.fixture
    def scraper(self):
        """テスト用スクレーパーインスタンスを作成"""
        return KaigirokuNetScraper(headless=True)
    
    @pytest.mark.asyncio
    async def test_fetch_minutes_success(self, scraper):
        """正常な議事録取得のテスト"""
        test_url = "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"
        
        # モックページを作成
        mock_page = AsyncMock()
        mock_page.url = test_url
        mock_page.goto = AsyncMock()
        mock_page.content = AsyncMock(return_value="""
            <html>
                <body>
                    <div id="tab-minute-plain">会議録</div>
                    <div id="plain-minute">
                        令和７年１月まちづくり委員会（第１９回）
                        第19回　まちづくり委員会記録（実地視察）
                        ◯令和７年１月23日（木）
                        ◯視察箇所
                        境谷公園
                        大蛇ヶ池公園
                        北鍵屋公園
                    </div>
                </body>
            </html>
        """)
        mock_page.query_selector = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value="令和７年１月まちづくり委員会（第１９回）")
        mock_page.query_selector_all = AsyncMock(return_value=[])
        
        # モックブラウザーを作成
        mock_browser = AsyncMock()
        mock_browser.close = AsyncMock()  # closeメソッドを追加
        mock_browser.new_context = AsyncMock()
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser.new_context.return_value = mock_context
        
        # playwrightのモック
        with patch('src.web_scraper.kaigiroku_net_scraper.async_playwright') as mock_playwright:
            mock_p = AsyncMock()
            mock_p.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_playwright.return_value.__aenter__.return_value = mock_p
            
            # 必要なメソッドをモック
            with patch.object(scraper, '_extract_iframe_content', AsyncMock(return_value=None)):
                with patch.object(scraper, '_wait_for_content', AsyncMock()):
                    with patch.object(scraper.content_extractor, 'extract_title', return_value="まちづくり委員会"):
                        with patch.object(scraper, '_extract_date', AsyncMock(return_value="2025-01-23")):
                            with patch.object(scraper, '_find_pdf_download_url', AsyncMock(return_value=None)):
                                with patch.object(scraper, '_find_text_view_url', AsyncMock(return_value=None)):
                                    # テスト実行
                                    result = await scraper.fetch_minutes(test_url)
            
            # 結果を検証
            assert result is not None
            assert isinstance(result, MinutesData)
            assert result.council_id == "6030"
            assert result.schedule_id == "1"
            assert "まちづくり委員会" in result.content
    
    @pytest.mark.asyncio
    async def test_extract_speakers(self, scraper):
        """発言者抽出のテスト"""
        html_content = """
        <html>
            <body>
                【山田太郎議員】
                これは重要な提案です。
                
                ○鈴木花子委員：
                私も賛成です。
                
                佐藤市長：
                検討させていただきます。
            </body>
        </html>
        """
        
        speakers = await scraper.extract_speakers(html_content)
        
        assert len(speakers) == 3
        assert speakers[0].name == "山田太郎"
        assert "重要な提案" in speakers[0].content
        assert speakers[1].name == "鈴木花子"
        assert speakers[2].name == "佐藤"
    
    @pytest.mark.asyncio
    async def test_parse_japanese_date(self, scraper):
        """日本語日付パースのテスト"""
        # 令和の日付
        date1 = scraper.parse_japanese_date("令和7年1月23日")
        assert date1.year == 2025
        assert date1.month == 1
        assert date1.day == 23
        
        # 平成の日付
        date2 = scraper.parse_japanese_date("平成16年9月22日")
        assert date2.year == 2004
        assert date2.month == 9
        assert date2.day == 22
        
        # 西暦の日付
        date3 = scraper.parse_japanese_date("2024年12月31日")
        assert date3.year == 2024
        assert date3.month == 12
        assert date3.day == 31
    
    @pytest.mark.asyncio
    async def test_extract_minutes_text(self, scraper):
        """議事録テキスト抽出のテスト"""
        html_content = """
        <html>
            <body>
                <button>印刷</button>
                <button>文字拡大</button>
                <div id="plain-minute">
                    <button>文字縮小</button>
                    令和７年１月まちづくり委員会（第１９回）
                    第19回　まちづくり委員会記録（実地視察）
                    ◯令和７年１月23日（木）
                    ◯視察箇所
                    境谷公園
                    大蛇ヶ池公園
                    北鍵屋公園
                    ◯出席委員（13名）
                    委員長　　兵藤しんいち議員
                    副委員長　さくらい泰広議員
                    副委員長　河村　諒議員
                    委員　　　加藤昌洋議員
                    委員　　　富　きくお議員
                    委員　　　山本恵一議員
                    委員　　　中野洋一議員
                    委員　　　くらた共子議員
                    委員　　　とがし　豊議員
                    委員　　　平井良人議員
                    委員　　　増成竜治議員
                    委員　　　天方ひろゆき議員
                    委員　　　繁　隆夫議員
                </div>
            </body>
        </html>
        """
        
        text = await scraper.extract_minutes_text(html_content)
        
        # ボタンテキストが除去されていることを確認
        assert "印刷" not in text
        assert "文字拡大" not in text
        assert "文字縮小" not in text
        
        # 議事録の内容が含まれていることを確認
        assert "まちづくり委員会" in text
        assert "令和７年１月23日" in text
        assert "兵藤しんいち議員" in text


@pytest.mark.skipif(
    os.environ.get('CI') == 'true',
    reason="Skip integration test in CI environment"
)
@pytest.mark.asyncio
async def test_scraper_integration():
    """統合テスト: 実際のURLでスクレーパーをテスト（ネットワーク接続が必要）"""
    scraper = KaigirokuNetScraper(headless=True)
    
    # 小さい議事録でテスト
    url = "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"
    
    try:
        result = await scraper.fetch_minutes(url)
        
        if result:
            print(f"\n--- Minutes Summary ---")
            print(f"Title: {result.title}")
            print(f"Date: {result.date}")
            print(f"Council ID: {result.council_id}")
            print(f"Schedule ID: {result.schedule_id}")
            print(f"Content length: {len(result.content)} characters")
            print(f"Speakers found: {len(result.speakers)}")
            print(f"PDF URL: {result.pdf_url}")
            
            assert result.council_id == "6030"
            assert result.schedule_id == "1"
            assert len(result.content) > 0
            print("\n✅ Integration test passed!")
        else:
            print("\n❌ Failed to fetch minutes")
            
    except Exception as e:
        print(f"\n❌ Integration test failed: {e}")
        raise


if __name__ == "__main__":
    # 統合テストを実行
    asyncio.run(test_scraper_integration())