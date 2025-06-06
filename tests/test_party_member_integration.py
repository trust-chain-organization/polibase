"""Integration tests for party member scraping"""
import os
import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.party_member_extractor.models import PartyMemberInfo, PartyMemberList, WebPageContent
from src.party_member_extractor.extractor import PartyMemberExtractor
from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher
from src.database.politician_repository import PoliticianRepository


class TestPartyMemberIntegration:
    """統合テストクラス"""
    
    @pytest.mark.skipif(
        os.environ.get('CI') == 'true',
        reason="Skip integration test requiring Playwright in CI environment"
    )
    @pytest.mark.asyncio
    async def test_full_scraping_flow(self):
        """完全なスクレイピングフローのテスト"""
        # HTMLフェッチャーのモック
        mock_pages = [
            WebPageContent(
                url="https://example.com/members/page1",
                html_content="""
                <html><body>
                    <main>
                        <div class="member">
                            <h3>統合太郎</h3>
                            <p>衆議院議員</p>
                            <p>東京1区</p>
                        </div>
                    </main>
                </body></html>
                """,
                page_number=1
            )
        ]
        
        # LLMのモック結果
        mock_llm_result = PartyMemberList(
            members=[
                PartyMemberInfo(
                    name="統合太郎",
                    position="衆議院議員",
                    electoral_district="東京1区",
                    prefecture="東京都"
                )
            ],
            total_count=1,
            party_name="統合テスト党"
        )
        
        # モックの設定
        with patch('src.party_member_extractor.html_fetcher.PartyMemberPageFetcher') as MockFetcher:
            mock_fetcher_instance = AsyncMock()
            mock_fetcher_instance.fetch_all_pages.return_value = mock_pages
            MockFetcher.return_value.__aenter__.return_value = mock_fetcher_instance
            
            with patch('src.party_member_extractor.extractor.ChatGoogleGenerativeAI') as MockLLM:
                mock_llm = Mock()
                mock_extraction_llm = Mock()
                mock_extraction_llm.invoke.return_value = mock_llm_result
                mock_llm.with_structured_output.return_value = mock_extraction_llm
                MockLLM.return_value = mock_llm
                
                # エクストラクター作成
                extractor = PartyMemberExtractor()
                
                # フェッチとエクストラクト実行
                async with PartyMemberPageFetcher() as fetcher:
                    pages = await fetcher.fetch_all_pages("https://example.com/members")
                    result = extractor.extract_from_pages(pages, "統合テスト党")
                
                # アサーション
                assert len(result.members) == 1
                assert result.members[0].name == "統合太郎"
                assert result.members[0].position == "衆議院議員"
                assert result.members[0].prefecture == "東京都"
    
    def test_database_integration(self):
        """データベース保存の統合テスト"""
        # テストデータ
        politicians_data = [
            {
                'name': 'DB統合太郎',
                'political_party_id': 1,
                'position': '衆議院議員',
                'prefecture': '東京都',
                'electoral_district': '東京1区'
            },
            {
                'name': 'DB統合花子',
                'political_party_id': 1,
                'position': '参議院議員',
                'prefecture': '大阪府',
                'electoral_district': '大阪',
                'party_position': '幹事長'
            }
        ]
        
        # リポジトリのモック
        with patch('src.database.politician_repository.get_db_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_get_engine.return_value = mock_engine
            mock_engine.dispose = Mock()
            mock_context = Mock()
            mock_context.__enter__ = Mock(return_value=mock_conn)
            mock_context.__exit__ = Mock(return_value=None)
            mock_engine.connect.return_value = mock_context
            
            # commitとrollbackメソッドを追加
            mock_conn.commit = Mock()
            mock_conn.rollback = Mock()
            
            # 既存チェックは全てなし
            mock_conn.execute.return_value.fetchone.return_value = None
            
            # executorメソッドのモック設定を改善
            def execute_side_effect(query, params=None):
                # SELECTクエリの場合（既存チェック）
                if "SELECT" in str(query):
                    return Mock(fetchone=Mock(return_value=None))
                # INSERTクエリの場合
                elif "INSERT" in str(query):
                    # 呼び出し回数に応じてIDを返す
                    if not hasattr(execute_side_effect, 'insert_count'):
                        execute_side_effect.insert_count = 0
                    execute_side_effect.insert_count += 1
                    return Mock(fetchone=Mock(return_value=Mock(id=execute_side_effect.insert_count)))
                # UPDATEクエリの場合
                else:
                    return Mock()
            
            mock_conn.execute = Mock(side_effect=execute_side_effect)
            
            # リポジトリ実行
            repo = PoliticianRepository()
            stats = repo.bulk_create_politicians(politicians_data)
            
            # アサーション
            assert len(stats['created']) == 2
            assert len(stats['updated']) == 0
            assert len(stats['errors']) == 0
    
    def test_duplicate_handling_integration(self):
        """重複処理の統合テスト"""
        # 初回データ
        initial_data = [
            {
                'name': '重複チェック太郎',
                'political_party_id': 1,
                'position': '衆議院議員',
                'prefecture': '東京都'
            }
        ]
        
        # 2回目データ（一部更新あり）
        update_data = [
            {
                'name': '重複チェック太郎',
                'political_party_id': 1,
                'position': '参議院議員',  # 変更
                'prefecture': '東京都',
                'electoral_district': '東京'  # 追加
            }
        ]
        
        with patch('src.database.politician_repository.get_db_engine') as mock_get_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_get_engine.return_value = mock_engine
            mock_engine.dispose = Mock()
            mock_context = Mock()
            mock_context.__enter__ = Mock(return_value=mock_conn)
            mock_context.__exit__ = Mock(return_value=None)
            mock_engine.connect.return_value = mock_context
            
            # commitとrollbackメソッドを追加
            mock_conn.commit = Mock()
            mock_conn.rollback = Mock()
            
            # 初回用のexecuteモック
            call_count = [0]
            
            def execute_side_effect_initial(query, params=None):
                call_count[0] += 1
                # SELECTクエリの場合（既存チェック）
                if "SELECT" in str(query):
                    return Mock(fetchone=Mock(return_value=None))  # 既存なし
                # INSERTクエリの場合
                elif "INSERT" in str(query):
                    return Mock(fetchone=Mock(return_value=Mock(id=1)))
                else:
                    return Mock()
            
            mock_conn.execute = Mock(side_effect=execute_side_effect_initial)
            
            repo = PoliticianRepository()
            first_stats = repo.bulk_create_politicians(initial_data)
            
            # 2回目: 更新
            existing_record = Mock(
                id=1,
                position='衆議院議員',
                prefecture='東京都',
                electoral_district=None,
                profile_url=None,
                party_position=None
            )
            
            def execute_side_effect_update(query, params=None):
                # SELECTクエリの場合（既存チェック）
                if "SELECT" in str(query):
                    return Mock(fetchone=Mock(return_value=existing_record))  # 既存あり
                # UPDATEクエリの場合
                elif "UPDATE" in str(query):
                    return Mock()
                else:
                    return Mock()
            
            mock_conn.execute = Mock(side_effect=execute_side_effect_update)
            
            second_stats = repo.bulk_create_politicians(update_data)
            
            # アサーション
            assert len(first_stats['created']) == 1
            assert len(second_stats['updated']) == 1
            assert len(second_stats['created']) == 0
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """エラーリカバリーのテスト"""
        # 一部のページでエラーが発生
        mock_pages = [
            WebPageContent(
                url="https://example.com/page1",
                html_content="<html><body><main>Page 1 content</main></body></html>",
                page_number=1
            ),
            WebPageContent(
                url="https://example.com/page2",
                html_content="<html><body><main>Page 2 content</main></body></html>",
                page_number=2
            ),
            WebPageContent(
                url="https://example.com/page3",
                html_content="<html><body><main>Page 3 content</main></body></html>",
                page_number=3
            )
        ]
        
        # LLMのモック（2ページ目でエラー）
        with patch('src.party_member_extractor.extractor.ChatGoogleGenerativeAI') as MockLLM:
            mock_llm = Mock()
            mock_extraction_llm = Mock()
            mock_extraction_llm.invoke.side_effect = [
                PartyMemberList(
                    members=[PartyMemberInfo(name="成功太郎", position="衆議院議員")],
                    total_count=1
                ),
                Exception("LLM Error"),  # エラー
                PartyMemberList(
                    members=[PartyMemberInfo(name="成功花子", position="参議院議員")],
                    total_count=1
                )
            ]
            mock_llm.with_structured_output.return_value = mock_extraction_llm
            MockLLM.return_value = mock_llm
            
            extractor = PartyMemberExtractor()
            result = extractor.extract_from_pages(mock_pages, "エラーテスト党")
            
            # アサーション（エラーページをスキップして続行）
            assert len(result.members) == 2
            assert result.members[0].name == "成功太郎"
            assert result.members[1].name == "成功花子"