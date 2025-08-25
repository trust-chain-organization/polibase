"""Tests for PoliticianRepository V2 (Pydantic-based)"""

from unittest.mock import Mock, patch

import pytest

from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl as PoliticianRepository,
)
from src.models.politician import Politician, PoliticianCreate, PoliticianUpdate


class TestPoliticianRepositoryV2:
    """PoliticianRepository V2のテストクラス"""

    @pytest.fixture
    def mock_db(self):
        """モックデータベースセッションのフィクスチャ"""
        return Mock()

    @pytest.fixture
    def repository(self, mock_db):
        """リポジトリのフィクスチャ"""
        return PoliticianRepository(db=mock_db)

    def test_create_politician_new(self, repository):
        """新規政治家作成のテスト"""
        # モックの設定
        new_politician = Politician(
            id=1,
            name="テスト太郎",
            political_party_id=1,
            position="衆議院議員",
            prefecture="東京都",
            electoral_district="東京1区",
            profile_url="https://example.com/test",
            party_position="幹事長",
        )

        with patch.object(repository, "get_by_name_and_party", return_value=None):
            with patch.object(
                repository, "create_from_model", return_value=new_politician
            ):
                # テスト実行
                politician_data = PoliticianCreate(
                    name="テスト太郎",
                    political_party_id=1,
                    position="衆議院議員",
                    prefecture="東京都",
                    electoral_district="東京1区",
                    profile_url="https://example.com/test",
                    party_position="幹事長",
                )
                result = repository.create_politician(politician_data)

                # アサーション
                assert result is not None
                assert result.id == 1
                assert result.name == "テスト太郎"

    def test_create_politician_existing_no_update(self, repository):
        """既存政治家・更新不要のテスト"""
        # 既存の政治家
        existing = Politician(
            id=1,
            name="テスト太郎",
            political_party_id=1,
            position="衆議院議員",
            prefecture="東京都",
            electoral_district="東京1区",
            profile_url="https://example.com/test",
            party_position="幹事長",
        )

        # モックの設定
        with patch.object(repository, "get_by_name_and_party", return_value=existing):
            # テスト実行
            politician_data = PoliticianCreate(
                name="テスト太郎",
                political_party_id=1,
                position="衆議院議員",
                prefecture="東京都",
                electoral_district="東京1区",
                profile_url="https://example.com/test",
                party_position="幹事長",
            )
            result = repository.create_politician(politician_data)

            # アサーション
            assert result == existing

    def test_bulk_create_politicians(self, repository):
        """一括作成のテスト"""
        # モックの設定
        with patch.object(repository, "find_by_name_and_party") as mock_find:
            with patch.object(repository, "create") as mock_create:
                with patch.object(repository, "update_v2") as mock_update:
                    # 1人目: 新規、2人目: 既存（更新あり）、3人目: エラー
                    mock_find.side_effect = [
                        None,  # 1人目: 新規
                        Politician(
                            id=2,
                            name="更新次郎",
                            political_party_id=1,
                            position="衆議院議員",
                        ),  # 2人目: 既存
                        None,  # 3人目: 新規だがエラー
                    ]

                    mock_create.side_effect = [
                        Politician(id=1, name="新規太郎", political_party_id=1),
                        Exception("Create error"),
                    ]

                    mock_update.return_value = Politician(
                        id=2,
                        name="更新次郎",
                        political_party_id=1,
                        position="参議院議員",
                    )

                    # テストデータ
                    politicians_data = [
                        {"name": "新規太郎", "political_party_id": 1},
                        {
                            "name": "更新次郎",
                            "political_party_id": 1,
                            "position": "参議院議員",
                        },
                        {"name": "エラー三郎", "political_party_id": 1},
                    ]

                    # テスト実行
                    stats = repository.bulk_create_politicians(politicians_data)

                    # アサーション
                    assert len(stats["created"]) == 1
                    assert len(stats["updated"]) == 1
                    assert len(stats["errors"]) == 1

    def test_search_by_name(self, repository):
        """名前での検索のテスト"""
        # モックデータ
        mock_data = [
            {
                "id": 1,
                "name": "山田太郎",
                "political_party_id": 1,
                "party_name": "自由民主党",
                "position": "衆議院議員",
            },
            {
                "id": 2,
                "name": "山田次郎",
                "political_party_id": 2,
                "party_name": "立憲民主党",
                "position": "参議院議員",
            },
        ]

        with patch.object(repository, "fetch_as_dict", return_value=mock_data):
            # テスト実行
            results = repository.search_by_name("山田", threshold=0.5)

            # アサーション
            assert len(results) == 2
            assert all("similarity" in result for result in results)
            assert all("party_name" in result for result in results)

    def test_find_by_name(self, repository):
        """名前での完全一致検索のテスト"""
        # モックデータ
        mock_politicians = [
            Politician(id=1, name="山田太郎", political_party_id=1),
            Politician(id=2, name="山田太郎", political_party_id=2),
        ]

        with patch.object(
            repository, "fetch_all_as_models", return_value=mock_politicians
        ):
            # テスト実行
            results = repository.find_by_name("山田太郎")

            # アサーション
            assert len(results) == 2
            assert all(isinstance(p, Politician) for p in results)
            assert all(p.name == "山田太郎" for p in results)

    def test_update_politician(self, repository):
        """政治家情報更新のテスト"""
        # Mock the update_from_model method which is from TypedRepository
        updated_politician = Politician(
            id=1,
            name="更新太郎",
            political_party_id=1,
            position="参議院議員",
            prefecture="大阪府",
        )

        with patch.object(
            repository, "update_from_model", return_value=updated_politician
        ) as mock_update:
            # テスト実行
            update_data = PoliticianUpdate(position="参議院議員", prefecture="大阪府")
            result = repository.update_politician(1, update_data)

            # アサーション
            assert result is True
            mock_update.assert_called_once_with(1, update_data)

    def test_get_by_party(self, repository):
        """政党別取得のテスト"""
        # モックデータ
        mock_politicians = [
            Politician(id=1, name="議員1", political_party_id=1),
            Politician(id=2, name="議員2", political_party_id=1),
        ]

        with patch.object(
            repository, "fetch_all_as_models", return_value=mock_politicians
        ):
            # テスト実行
            results = repository.get_by_party(1)

            # アサーション
            assert len(results) == 2
            assert all(p.political_party_id == 1 for p in results)
