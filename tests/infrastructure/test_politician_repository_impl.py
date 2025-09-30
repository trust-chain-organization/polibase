"""Tests for PoliticianRepositoryImpl"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from src.domain.entities.politician import Politician
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_sync_impl import (
    PoliticianRepositorySyncImpl,
)


class TestPoliticianRepositoryImpl:
    """PoliticianRepositoryImpl のテスト"""

    @pytest.fixture
    def mock_sync_session(self):
        """モック同期セッション"""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def sync_repository(self, mock_sync_session):
        """同期リポジトリフィクスチャ"""
        return PoliticianRepositorySyncImpl(mock_sync_session)

    @pytest.fixture
    def async_repository(self):
        """非同期リポジトリフィクスチャ"""
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_async_session = MagicMock(spec=AsyncSession)
        return PoliticianRepositoryImpl(mock_async_session)

    def test_find_by_name_and_party_sync(self, sync_repository, mock_sync_session):
        """同期版のfind_by_name_and_partyのテスト"""
        # モックデータの準備
        mock_row = MagicMock()
        mock_row.name = "テスト太郎"
        mock_row.political_party_id = 2
        mock_row.id = 1
        mock_row.furigana = None
        mock_row.position = None
        mock_row.prefecture = None
        mock_row.electoral_district = None
        mock_row.profile_url = None
        mock_row.party_position = None
        mock_row._mapping = {
            "id": 1,
            "name": "テスト太郎",
            "political_party_id": 2,
            "furigana": None,
            "position": None,
            "prefecture": None,
            "electoral_district": None,
            "profile_url": None,
            "party_position": None,
        }

        mock_result = MagicMock()
        mock_result.first.return_value = mock_row
        mock_sync_session.execute.return_value = mock_result

        # テスト実行 (同期メソッド)
        result = sync_repository.find_by_name_and_party("テスト太郎", 2)

        # 検証
        assert result is not None
        assert result["name"] == "テスト太郎"
        assert result["political_party_id"] == 2
        mock_sync_session.execute.assert_called_once()

    def test_search_by_name_sync(self, sync_repository, mock_sync_session):
        """同期版のsearch_by_nameのテスト"""

        # モックデータの準備
        def create_dict_row(data):
            mock_row = MagicMock()
            mock_row._mapping = data
            for key, value in data.items():
                setattr(mock_row, key, value)
            return mock_row

        mock_rows = [
            create_dict_row({"id": 1, "name": "テスト太郎", "political_party_id": 2}),
            create_dict_row({"id": 2, "name": "テスト次郎", "political_party_id": 2}),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_sync_session.execute.return_value = mock_result

        # テスト実行
        results = sync_repository.search_by_name_sync("テスト")

        # 検証
        assert len(results) == 2
        assert results[0]["name"] == "テスト太郎"
        assert results[1]["name"] == "テスト次郎"
        mock_sync_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_create_new(self):
        """新規作成時のupsertのテスト"""
        from sqlalchemy.ext.asyncio import AsyncSession

        # Create async session mock
        mock_async_session = MagicMock(spec=AsyncSession)

        # Create async repository
        async_repository = PoliticianRepositoryImpl(mock_async_session)

        # Mock get_by_name_and_party to return None (not found)
        with patch.object(async_repository, "get_by_name_and_party", return_value=None):
            # Mock create to return the new politician
            new_politician = Politician(
                name="新規太郎", furigana="しんきたろう", political_party_id=3, id=5
            )
            with patch.object(async_repository, "create", return_value=new_politician):
                # テスト実行
                result = await async_repository.upsert(new_politician)

                # 検証
                assert result.name == new_politician.name
                assert result.furigana == new_politician.furigana
                assert result.political_party_id == new_politician.political_party_id

    @pytest.mark.asyncio
    async def test_upsert_update_existing(self):
        """既存更新時のupsertのテスト"""
        from sqlalchemy.ext.asyncio import AsyncSession

        # Create async session mock
        mock_async_session = MagicMock(spec=AsyncSession)

        # Create async repository
        async_repository = PoliticianRepositoryImpl(mock_async_session)

        # Mock get_by_name_and_party to return existing politician
        existing_politician = Politician(
            name="既存太郎",
            furigana="きそんたろう",
            political_party_id=4,
            id=10,
        )
        with patch.object(
            async_repository, "get_by_name_and_party", return_value=existing_politician
        ):
            # Mock update to return updated politician
            updated_politician = Politician(
                name="既存太郎",
                furigana="きそんたろう",
                political_party_id=4,
                id=10,
            )
            with patch.object(
                async_repository, "update", return_value=updated_politician
            ):
                # テスト実行
                new_data = Politician(
                    name="既存太郮",
                    furigana="きそんたろう",
                    political_party_id=4,
                )
                result = await async_repository.upsert(new_data)

                # 検証
                assert result == updated_politician

    def test_bulk_create_politicians_sync(self, sync_repository, mock_sync_session):
        """bulk_create_politicians_syncのテスト"""
        # テストデータ
        politicians_data = [
            {
                "name": "バルク太郎",
                "furigana": "ばるくたろう",
                "political_party_id": 5,
                "position": "衆議院議員",
            }
        ]

        # Mock find_by_name_and_party to return None (not exists)
        with patch.object(sync_repository, "find_by_name_and_party", return_value=None):
            # Mock the insert operation
            mock_row = MagicMock()
            mock_row._mapping = {
                "id": 20,
                "name": "バルク太郎",
                "furigana": "ばるくたろう",
                "political_party_id": 5,
                "position": "衆議院議員",
            }
            mock_result = MagicMock()
            mock_result.first.return_value = mock_row
            mock_sync_session.execute.return_value = mock_result

            # Mock the commit
            mock_sync_session.commit = MagicMock()

            # テスト実行
            result = sync_repository.bulk_create_politicians_sync(politicians_data)

            # 検証
            assert "created" in result
            assert "updated" in result
            assert "errors" in result
            assert len(result["created"]) == 1
            assert result["created"][0]["name"] == "バルク太郎"
            assert len(result["updated"]) == 0
            assert len(result["errors"]) == 0
            mock_sync_session.execute.assert_called()
            mock_sync_session.commit.assert_called()

    def test_fetch_as_dict_sync(self, sync_repository, mock_sync_session):
        """fetch_as_dict_syncのテスト"""

        # モックデータの準備
        # Create mock rows with proper dict implementation
        def create_dict_row(data):
            mock_row = MagicMock()
            mock_row._mapping = data
            mock_row.__iter__ = lambda self: iter(data.items())
            mock_row.keys = lambda: data.keys()
            mock_row.__getitem__ = lambda self, key: data[key]
            return mock_row

        mock_rows = [
            create_dict_row({"id": 1, "name": "テスト太郎", "party_name": "テスト党"}),
            create_dict_row({"id": 2, "name": "テスト次郎", "party_name": "テスト党"}),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_sync_session.execute.return_value = mock_result

        # テスト実行
        query = "SELECT * FROM politicians"
        results = sync_repository.fetch_as_dict_sync(query)

        # 検証
        assert len(results) == 2
        assert results[0]["name"] == "テスト太郎"
        assert results[1]["name"] == "テスト次郎"
        mock_sync_session.execute.assert_called_once()

    def test_row_to_entity(self, async_repository):
        """_row_to_entityのテスト"""
        # モックデータの準備 - Ensure proper Row-like object
        row_data = {
            "id": 1,
            "name": "変換太郎",
            "furigana": "へんかんたろう",
            "political_party_id": 6,
            "position": "参議院議員",
            "prefecture": "大阪府",
            "electoral_district": "大阪1区",
            "profile_url": "https://example.com/convert",
            "party_position": "代表",
        }

        # Create a proper mock that behaves like a SQLAlchemy Row
        mock_row = MagicMock()
        # Set up _mapping attribute
        mock_row._mapping = row_data
        # Set up attribute access for legacy compatibility
        for key, value in row_data.items():
            setattr(mock_row, key, value)

        # テスト実行
        result = async_repository._row_to_entity(mock_row)

        # 検証
        assert isinstance(result, Politician)
        assert result.id == 1
        assert result.name == "変換太郎"
        assert result.furigana == "へんかんたろう"
        assert result.political_party_id == 6
        assert result.district == "大阪1区"  # electoral_district -> district
        assert (
            result.profile_page_url == "https://example.com/convert"
        )  # profile_url -> profile_page_url

    def test_to_model(self, async_repository):
        """_to_modelのテスト"""
        # エンティティの準備
        entity = Politician(
            name="モデル太郎",
            furigana="もでるたろう",
            political_party_id=7,
            district="京都1区",
            profile_page_url="https://example.com/model",
            id=30,
        )

        # テスト実行
        result = async_repository._to_model(entity)

        # 検証
        assert result.name == "モデル太郎"
        assert result.furigana == "もでるたろう"
        assert result.political_party_id == 7
        assert result.electoral_district == "京都1区"  # district -> electoral_district
        assert (
            result.profile_url == "https://example.com/model"
        )  # profile_page_url -> profile_url
