"""Tests for PoliticianRepository"""

from unittest.mock import Mock, patch

import pytest

from src.database.politician_repository import PoliticianRepository


class TestPoliticianRepository:
    """PoliticianRepositoryのテストクラス"""

    @pytest.fixture
    def mock_engine(self):
        """モックエンジンのフィクスチャ"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_engine):
        """リポジトリのフィクスチャ"""
        with patch("src.config.database.get_db_engine", return_value=mock_engine):
            repo = PoliticianRepository()
            repo._engine = mock_engine
            return repo

    def test_create_politician_new(self, repository, mock_engine):
        """新規政治家作成のテスト"""
        # モックの設定
        mock_conn = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.begin.return_value = mock_context

        # 既存レコードなし
        mock_conn.execute.side_effect = [
            Mock(fetchone=Mock(return_value=None)),  # 既存チェック
            Mock(fetchone=Mock(return_value=Mock(id=1))),  # INSERT結果
        ]

        # テスト実行
        result = repository.create_politician(
            name="テスト太郎",
            political_party_id=1,
            position="衆議院議員",
            prefecture="東京都",
            electoral_district="東京1区",
            profile_url="https://example.com/test",
            party_position="幹事長",
        )

        # アサーション
        assert result == 1
        assert mock_conn.execute.call_count == 2

    def test_create_politician_existing_no_update(self, repository, mock_engine):
        """既存政治家・更新不要のテスト"""
        # モックの設定
        mock_conn = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.begin.return_value = mock_context

        # 既存レコードあり（同じ内容）
        existing = Mock(
            id=1,
            position="衆議院議員",
            prefecture="東京都",
            electoral_district="東京1区",
            profile_url="https://example.com/test",
            party_position="幹事長",
        )
        mock_conn.execute.return_value.fetchone.return_value = existing

        # テスト実行
        result = repository.create_politician(
            name="テスト太郎",
            political_party_id=1,
            position="衆議院議員",
            prefecture="東京都",
            electoral_district="東京1区",
            profile_url="https://example.com/test",
            party_position="幹事長",
        )

        # アサーション
        assert result == 1
        assert mock_conn.execute.call_count == 1  # SELECTのみ
        assert not mock_conn.commit.called  # 更新なし

    def test_create_politician_existing_with_update(self, repository, mock_engine):
        """既存政治家・更新ありのテスト"""
        # モックの設定
        mock_conn = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.begin.return_value = mock_context

        # 既存レコードあり（異なる内容）
        existing = Mock(
            id=1,
            position="衆議院議員",
            prefecture="東京都",
            electoral_district="東京1区",
            profile_url="https://example.com/old",
            party_position=None,
        )
        mock_conn.execute.side_effect = [
            Mock(fetchone=Mock(return_value=existing)),  # 既存チェック
            Mock(),  # UPDATE実行
        ]

        # テスト実行
        result = repository.create_politician(
            name="テスト太郎",
            political_party_id=1,
            position="参議院議員",  # 変更
            prefecture="神奈川県",  # 変更
            electoral_district="神奈川1区",  # 変更
            profile_url="https://example.com/new",  # 変更
            party_position="代表",  # 変更
        )

        # アサーション
        assert result == 1
        assert mock_conn.execute.call_count == 2  # SELECT + UPDATE

    def test_create_politician_error(self, repository, mock_engine):
        """エラー処理のテスト"""
        # モックの設定
        mock_conn = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.begin.return_value = mock_context
        mock_conn.execute.side_effect = Exception("Database error")

        # テスト実行（エラーが発生することを期待）
        with pytest.raises(Exception, match="Database error"):
            repository.create_politician(name="テスト太郎", political_party_id=1)

    def test_bulk_create_politicians(self, repository, mock_engine):
        """一括作成のテスト"""
        # create_politicianをモック化
        with patch.object(repository, "create_politician") as mock_create:
            # 1人目: 新規作成、2人目: 更新、3人目: エラー
            mock_create.side_effect = [1, 2, None]

            # existsメソッドをモック
            with patch.object(repository, "exists") as mock_exists:
                # 1人目: 既存なし、2人目: 既存あり、3人目: 既存なし
                mock_exists.side_effect = [False, True, False]

                # テストデータ
                politicians_data = [
                    {"name": "新規太郎", "political_party_id": 1},
                    {"name": "更新次郎", "political_party_id": 1},
                    {"name": "エラー三郎", "political_party_id": 1},
                ]

                # テスト実行
                stats = repository.bulk_create_politicians(politicians_data)

                # アサーション
                assert len(stats["created"]) == 1
                assert len(stats["updated"]) == 1
                assert len(stats["errors"]) == 1
                assert stats["created"] == [1]
                assert stats["updated"] == [2]
                assert stats["errors"] == ["エラー三郎"]

    def test_get_politicians_by_party(self, repository, mock_engine):
        """政党別政治家取得のテスト"""
        # モックの設定
        mock_conn = Mock()
        mock_context = Mock()
        mock_context.__enter__ = Mock(return_value=mock_conn)
        mock_context.__exit__ = Mock(return_value=None)
        mock_engine.connect.return_value = mock_context

        # モックデータ
        mock_rows = [
            {
                "id": 1,
                "name": "テスト太郎",
                "position": "衆議院議員",
                "prefecture": "東京都",
                "electoral_district": "東京1区",
                "profile_url": "https://example.com/test1",
            },
            {
                "id": 2,
                "name": "テスト次郎",
                "position": "参議院議員",
                "prefecture": "大阪府",
                "electoral_district": "大阪",
                "profile_url": "https://example.com/test2",
            },
        ]

        # fetch_as_dictメソッドを直接モック
        with patch.object(repository, "fetch_as_dict", return_value=mock_rows):
            # テスト実行
            result = repository.get_politicians_by_party(1)

        # アサーション
        assert len(result) == 2
        assert result[0]["name"] == "テスト太郎"
        assert result[1]["name"] == "テスト次郎"

    def test_update_politician(self, repository, mock_engine):
        """政治家情報更新のテスト"""
        # updateメソッドをモック
        with patch.object(repository, "update") as mock_update:
            mock_update.return_value = 1

            # テスト実行
            result = repository.update_politician(
                politician_id=1,
                name="更新太郎",
                position="参議院議員",
                invalid_field="無効なフィールド",  # 無視される
            )

            # アサーション
            assert result is True
            mock_update.assert_called_once_with(
                table="politicians",
                data={"name": "更新太郎", "position": "参議院議員"},
                where={"id": 1},
            )
