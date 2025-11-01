"""Integration tests for party member scraping"""

import os
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl as PoliticianRepository,
)
from src.party_member_extractor.extractor import PartyMemberExtractor
from src.party_member_extractor.models import (
    PartyMemberInfo,
    PartyMemberList,
    WebPageContent,
)


class TestPartyMemberIntegration:
    """統合テストクラス"""

    @pytest.mark.skipif(
        os.environ.get("CI") == "true",
        reason="Skip integration test requiring Playwright in CI environment",
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
                page_number=1,
            )
        ]

        # LLMのモック結果
        mock_llm_result = PartyMemberList(
            members=[
                PartyMemberInfo(
                    name="統合太郎",
                    position="衆議院議員",
                    electoral_district="東京1区",
                    prefecture="東京都",
                )
            ],
            total_count=1,
            party_name="統合テスト党",
        )

        # モックの設定
        with patch(
            "src.party_member_extractor.html_fetcher.PartyMemberPageFetcher"
        ) as mock_fetcher:
            mock_fetcher_instance = AsyncMock()
            mock_fetcher_instance.fetch_all_pages.return_value = mock_pages
            mock_fetcher.return_value.__aenter__.return_value = mock_fetcher_instance

            with patch(
                "src.party_member_extractor.extractor.LLMServiceFactory"
            ) as mock_factory:
                mock_service = Mock()
                mock_extraction_llm = Mock()
                mock_extraction_llm.invoke.return_value = mock_llm_result
                mock_service.get_structured_llm.return_value = mock_extraction_llm
                mock_service.invoke_prompt.return_value = mock_llm_result
                mock_factory.return_value.create_advanced.return_value = mock_service

                # エクストラクター作成
                extractor = PartyMemberExtractor()

                # フェッチとエクストラクト実行
                # Note: We're mocking PartyMemberPageFetcher above, so we use the mock
                result = extractor.extract_from_pages(mock_pages, "統合テスト党")

                # アサーション
                assert len(result.members) == 1
                assert result.members[0].name == "統合太郎"
                assert result.members[0].position == "衆議院議員"
                assert result.members[0].prefecture == "東京都"

    @pytest.mark.skip(
        reason="Async repository method needs test refactoring - Issue #437"
    )
    def test_database_integration(self):
        """データベース保存の統合テスト"""
        # テストデータ
        politicians_data = [
            {
                "name": "DB統合太郎",
                "political_party_id": 1,
                "position": "衆議院議員",
                "prefecture": "東京都",
                "electoral_district": "東京1区",
            },
            {
                "name": "DB統合花子",
                "political_party_id": 1,
                "position": "参議院議員",
                "prefecture": "大阪府",
                "electoral_district": "大阪",
                "party_position": "幹事長",
            },
        ]

        # リポジトリのモック
        with patch(
            "src.infrastructure.config.database.get_db_engine"
        ) as mock_get_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_get_engine.return_value = mock_engine
            mock_engine.dispose = Mock()

            # engine.begin() のコンテキストマネージャーをモック
            mock_begin_context = Mock()
            mock_begin_context.__enter__ = Mock(return_value=mock_conn)
            mock_begin_context.__exit__ = Mock(return_value=None)
            mock_engine.begin.return_value = mock_begin_context

            # engine.connect() のコンテキストマネージャーもモック
            mock_connect_context = Mock()
            mock_connect_context.__enter__ = Mock(return_value=mock_conn)
            mock_connect_context.__exit__ = Mock(return_value=None)
            mock_engine.connect.return_value = mock_connect_context

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
                    if not hasattr(execute_side_effect, "insert_count"):
                        execute_side_effect.insert_count = 0
                    execute_side_effect.insert_count += 1
                    return Mock(
                        fetchone=Mock(
                            return_value=Mock(id=execute_side_effect.insert_count)
                        )
                    )
                # UPDATEクエリの場合
                else:
                    return Mock()

            mock_conn.execute = Mock(side_effect=execute_side_effect)

            # リポジトリの各メソッドをモック
            with patch.object(
                PoliticianRepository, "find_by_name_and_party", return_value=None
            ):
                with patch.object(PoliticianRepository, "create") as mock_create:
                    # createメソッドはPoliticianオブジェクトを返す
                    from src.domain.entities.politician import Politician

                    mock_create.side_effect = [
                        Politician(id=1, name="DB統合太郎", political_party_id=1),
                        Politician(id=2, name="DB統合花子", political_party_id=1),
                    ]

                    # リポジトリ実行
                    repo = PoliticianRepository(session=mock_conn)
                    stats = repo.bulk_create_politicians(politicians_data)

                    # アサーション
                    assert len(stats["created"]) == 2
                    assert len(stats["updated"]) == 0
                    assert len(stats["errors"]) == 0

    @pytest.mark.skip(
        reason="Async repository method needs test refactoring - Issue #437"
    )
    def test_duplicate_handling_integration(self):
        """重複処理の統合テスト"""
        # 初回データ
        initial_data = [
            {
                "name": "重複チェック太郎",
                "political_party_id": 1,
                "position": "衆議院議員",
                "prefecture": "東京都",
            }
        ]

        # 2回目データ（一部更新あり）
        update_data = [
            {
                "name": "重複チェック太郎",
                "political_party_id": 1,
                "position": "参議院議員",  # 変更
                "prefecture": "東京都",
                "electoral_district": "東京",  # 追加
            }
        ]

        with patch(
            "src.infrastructure.config.database.get_db_engine"
        ) as mock_get_engine:
            mock_engine = Mock()
            mock_conn = Mock()
            mock_get_engine.return_value = mock_engine
            mock_engine.dispose = Mock()

            # engine.begin() のコンテキストマネージャーをモック
            mock_begin_context = Mock()
            mock_begin_context.__enter__ = Mock(return_value=mock_conn)
            mock_begin_context.__exit__ = Mock(return_value=None)
            mock_engine.begin.return_value = mock_begin_context

            # engine.connect() のコンテキストマネージャーもモック
            mock_connect_context = Mock()
            mock_connect_context.__enter__ = Mock(return_value=mock_conn)
            mock_connect_context.__exit__ = Mock(return_value=None)
            mock_engine.connect.return_value = mock_connect_context

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

            # PoliticianRepositoryのメソッドをモック
            with patch.object(
                PoliticianRepository, "find_by_name_and_party"
            ) as mock_find:
                with patch.object(PoliticianRepository, "create") as mock_create:
                    with patch.object(PoliticianRepository, "update_v2") as mock_update:
                        from src.domain.entities.politician import Politician

                        # 初回: 新規作成
                        mock_find.return_value = None
                        mock_create.return_value = Politician(
                            id=1,
                            name="重複チェック太郎",
                            political_party_id=1,
                        )

                        repo = PoliticianRepository(session=mock_conn)
                        first_stats = repo.bulk_create_politicians(initial_data)

                        # 2回目: 更新
                        existing_politician = Politician(
                            id=1,
                            name="重複チェック太郎",
                            political_party_id=1,
                            prefecture="東京都",
                            electoral_district=None,
                            profile_url=None,
                            party_position=None,
                        )

                        mock_find.return_value = existing_politician
                        mock_update.return_value = Politician(
                            id=1,
                            name="重複チェック太郎",
                            political_party_id=1,
                            electoral_district="東京",
                        )

                        second_stats = repo.bulk_create_politicians(update_data)

                        # アサーション
                        assert len(first_stats["created"]) == 1
                        assert len(second_stats["updated"]) == 1
                        assert len(second_stats["created"]) == 0

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """エラーリカバリーのテスト"""
        # 一部のページでエラーが発生
        mock_pages = [
            WebPageContent(
                url="https://example.com/page1",
                html_content="<html><body><main>Page 1 content</main></body></html>",
                page_number=1,
            ),
            WebPageContent(
                url="https://example.com/page2",
                html_content="<html><body><main>Page 2 content</main></body></html>",
                page_number=2,
            ),
            WebPageContent(
                url="https://example.com/page3",
                html_content="<html><body><main>Page 3 content</main></body></html>",
                page_number=3,
            ),
        ]

        # LLMのモック（2ページ目でエラー）
        with patch(
            "src.party_member_extractor.extractor.LLMServiceFactory"
        ) as mock_factory:
            mock_service = Mock()
            mock_extraction_llm = Mock()

            # Setup mock service attributes
            mock_service.temperature = 0.1
            mock_service.model_name = "test-model"
            mock_service.get_structured_llm.return_value = mock_extraction_llm

            # Mock get_prompt
            mock_prompt = Mock()
            mock_prompt.format.return_value = "Test prompt"
            mock_service.get_prompt.return_value = mock_prompt

            # Setup extraction_llm.invoke to return results with error on 2nd page
            mock_extraction_llm.invoke.side_effect = [
                PartyMemberList(
                    members=[PartyMemberInfo(name="成功太郎", position="衆議院議員")],
                    total_count=1,
                ),
                Exception("LLM Error"),  # エラー
                PartyMemberList(
                    members=[PartyMemberInfo(name="成功花子", position="参議院議員")],
                    total_count=1,
                ),
            ]
            mock_factory.return_value.create_advanced.return_value = mock_service

            extractor = PartyMemberExtractor()
            result = extractor.extract_from_pages(mock_pages, "エラーテスト党")

            # アサーション（エラーページをスキップして続行）
            assert len(result.members) == 2
            assert result.members[0].name == "成功太郎"
            assert result.members[1].name == "成功花子"
