"""Tests for PoliticianRepositoryImpl"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.domain.entities.politician import Politician
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)


class TestPoliticianRepositoryImpl:
    """PoliticianRepositoryImpl のテスト"""

    @pytest.fixture
    def mock_async_session(self):
        """モック非同期セッション"""
        session = AsyncMock(spec=AsyncSession)
        return session

    @pytest.fixture
    def mock_sync_session(self):
        """モック同期セッション"""
        session = Mock(spec=Session)
        return session

    @pytest.fixture
    def async_repository(self, mock_async_session):
        """非同期リポジトリフィクスチャ"""
        return PoliticianRepositoryImpl(mock_async_session)

    @pytest.fixture
    def sync_repository(self, mock_sync_session):
        """同期リポジトリフィクスチャ"""
        return PoliticianRepositoryImpl(mock_sync_session)

    @pytest.mark.asyncio
    async def test_get_by_name_and_party_async(
        self, async_repository, mock_async_session
    ):
        """非同期版のget_by_name_and_partyのテスト"""
        # モックデータの準備
        # Create a mock row that implements both dict access and attributes
        mock_row_data = {
            "id": 1,
            "name": "テスト太郎",
            "speaker_id": 10,
            "political_party_id": 2,
            "position": "衆議院議員",
            "electoral_district": "東京1区",
            "profile_url": "https://example.com/test",
        }
        mock_row = MagicMock()
        mock_row._mapping = mock_row_data
        mock_row.__iter__ = lambda self: iter(mock_row_data.items())
        mock_row.keys = lambda: mock_row_data.keys()
        mock_row.__getitem__ = lambda self, key: mock_row_data[key]

        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_async_session.execute.return_value = mock_result

        # テスト実行
        result = await async_repository.get_by_name_and_party("テスト太郎", 2)

        # 検証
        assert result is not None
        assert result.name == "テスト太郎"
        assert result.political_party_id == 2
        assert result.speaker_id == 10
        assert result.district == "東京1区"
        mock_async_session.execute.assert_called_once()

    def test_find_by_name_and_party_sync(self, sync_repository, mock_sync_session):
        """同期版のfind_by_name_and_partyのテスト（後方互換）"""
        # モックデータの準備
        with patch.object(sync_repository, "legacy_repo") as mock_legacy_repo:
            mock_politician = MagicMock()
            mock_politician.name = "テスト太郎"
            mock_politician.political_party_id = 2
            mock_legacy_repo.fetch_one.return_value = mock_politician

            # テスト実行 (後方互換メソッド)
            result = sync_repository.find_by_name_and_party("テスト太郎", 2)

            # 検証
            assert result is not None
            assert result.name == "テスト太郎"
            assert result.political_party_id == 2
            mock_legacy_repo.fetch_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name_async(self, async_repository, mock_async_session):
        """非同期版のsearch_by_nameのテスト"""

        # モックデータの準備
        # Create mock rows with proper dict implementation
        def create_mock_row(data):
            mock_row = MagicMock()
            mock_row._mapping = data
            mock_row.__iter__ = lambda self: iter(data.items())
            mock_row.keys = lambda: data.keys()
            mock_row.__getitem__ = lambda self, key: data[key]
            return mock_row

        mock_rows = [
            create_mock_row(
                {
                    "id": 1,
                    "name": "テスト太郎",
                    "speaker_id": 10,
                    "political_party_id": 2,
                    "position": "衆議院議員",
                    "electoral_district": "東京1区",
                    "profile_url": "https://example.com/test1",
                }
            ),
            create_mock_row(
                {
                    "id": 2,
                    "name": "テスト次郎",
                    "speaker_id": 11,
                    "political_party_id": 2,
                    "position": "参議院議員",
                    "electoral_district": "東京都",
                    "profile_url": "https://example.com/test2",
                }
            ),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows
        mock_async_session.execute.return_value = mock_result

        # テスト実行
        results = await async_repository.search_by_name("テスト")

        # 検証
        assert len(results) == 2
        assert results[0].name == "テスト太郎"
        assert results[1].name == "テスト次郎"
        mock_async_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_create_new(self, async_repository, mock_async_session):
        """新規作成時のupsertのテスト"""
        # get_by_name_and_partyが何も返さない設定
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_async_session.execute.return_value = mock_result

        # createのモック
        with patch.object(
            async_repository, "create", new_callable=AsyncMock
        ) as mock_create:
            new_politician = Politician(
                name="新規太郎", speaker_id=12, political_party_id=3, id=5
            )
            mock_create.return_value = new_politician

            # テスト実行
            result = await async_repository.upsert(new_politician)

            # 検証
            assert result.name == new_politician.name
            assert result.speaker_id == new_politician.speaker_id
            assert result.political_party_id == new_politician.political_party_id
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_update_existing(self, async_repository, mock_async_session):
        """既存更新時のupsertのテスト"""
        # get_by_name_and_partyが既存を返す設定
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": 10,
            "name": "既存太郎",
            "speaker_id": 13,
            "political_party_id": 4,
            "position": None,
            "electoral_district": None,
            "profile_url": None,
        }
        mock_result = MagicMock()
        mock_result.fetchone.return_value = mock_row
        mock_async_session.execute.return_value = mock_result

        # updateのモック
        with patch.object(
            async_repository, "update", new_callable=AsyncMock
        ) as mock_update:
            updated_politician = Politician(
                name="既存太郎",
                speaker_id=13,
                political_party_id=4,
                position="衆議院議員",
                id=10,
            )
            mock_update.return_value = updated_politician

            # テスト実行
            new_data = Politician(
                name="既存太郎",
                speaker_id=13,
                political_party_id=4,
                position="衆議院議員",
            )
            result = await async_repository.upsert(new_data)

            # 検証
            assert result == updated_politician
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_create_politicians(self, async_repository, mock_async_session):
        """bulk_create_politiciansのテスト"""
        # モックの設定
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # 新規作成のケース
        mock_async_session.execute.return_value = mock_result
        mock_async_session.commit = AsyncMock()

        with patch.object(
            async_repository, "create", new_callable=AsyncMock
        ) as mock_create:
            # createの戻り値設定
            mock_create.return_value = Politician(
                name="バルク太郎", speaker_id=15, political_party_id=5, id=20
            )

            # テストデータ
            politicians_data = [
                {
                    "name": "バルク太郎",
                    "speaker_id": 15,
                    "political_party_id": 5,
                    "position": "衆議院議員",
                }
            ]

            # テスト実行
            result = await async_repository.bulk_create_politicians(politicians_data)

            # 検証
            assert "created" in result
            assert "updated" in result
            assert "errors" in result
            assert len(result["created"]) == 1
            assert len(result["updated"]) == 0
            assert len(result["errors"]) == 0
            mock_async_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_fetch_as_dict(self, async_repository, mock_async_session):
        """fetch_as_dictのテスト"""

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
        mock_async_session.execute.return_value = mock_result

        # テスト実行
        query = "SELECT * FROM politicians"
        results = await async_repository.fetch_as_dict_async(query)

        # 検証
        assert len(results) == 2
        assert results[0]["name"] == "テスト太郎"
        assert results[1]["name"] == "テスト次郎"
        mock_async_session.execute.assert_called_once()

    def test_row_to_entity(self, async_repository):
        """_row_to_entityのテスト"""
        # モックデータの準備
        row_data = {
            "id": 1,
            "name": "変換太郎",
            "speaker_id": 20,
            "political_party_id": 6,
            "position": "参議院議員",
            "prefecture": "大阪府",
            "electoral_district": "大阪1区",
            "profile_url": "https://example.com/convert",
            "party_position": "代表",
        }
        mock_row = MagicMock()
        mock_row._mapping = row_data
        mock_row.__iter__ = lambda self: iter(row_data.items())
        mock_row.keys = lambda: row_data.keys()
        mock_row.__getitem__ = lambda self, key: row_data[key]

        # テスト実行
        result = async_repository._row_to_entity(mock_row)

        # 検証
        assert isinstance(result, Politician)
        assert result.id == 1
        assert result.name == "変換太郎"
        assert result.speaker_id == 20
        assert result.political_party_id == 6
        assert result.position == "参議院議員"
        assert result.district == "大阪1区"  # electoral_district -> district
        assert (
            result.profile_page_url == "https://example.com/convert"
        )  # profile_url -> profile_page_url

    def test_to_model(self, async_repository):
        """_to_modelのテスト"""
        # エンティティの準備
        entity = Politician(
            name="モデル太郎",
            speaker_id=25,
            political_party_id=7,
            position="衆議院議員",
            district="京都1区",
            profile_page_url="https://example.com/model",
            id=30,
        )

        # テスト実行
        result = async_repository._to_model(entity)

        # 検証
        assert result.name == "モデル太郎"
        assert result.speaker_id == 25
        assert result.political_party_id == 7
        assert result.position == "衆議院議員"
        assert result.electoral_district == "京都1区"  # district -> electoral_district
        assert (
            result.profile_url == "https://example.com/model"
        )  # profile_page_url -> profile_url
