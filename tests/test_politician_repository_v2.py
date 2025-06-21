"""Tests for Pydantic-based politician repository"""

import pytest

from src.database.politician_repository_v2 import PoliticianRepositoryV2
from src.models.politician import PoliticianCreate


class TestPoliticianRepositoryV2:
    """Test cases for PoliticianRepositoryV2"""

    @pytest.fixture
    def repo(self):
        """Create a repository instance"""
        repo = PoliticianRepositoryV2()
        yield repo
        repo.close()

    def test_create_politician_with_pydantic_model(self, repo):
        """Test creating a politician using Pydantic model"""
        # First, ensure political party exists
        from src.database.political_party_repository import PoliticalPartyRepository

        party_repo = PoliticalPartyRepository()
        party_repo.create_party_if_not_exists("テスト政党")
        party = party_repo.get_by_name("テスト政党")
        assert party is not None
        party_id = party[0]  # Get party ID

        # Prepare test data
        politician_data = PoliticianCreate(
            name="テスト太郎",
            political_party_id=party_id,
            position="衆議院議員",
            prefecture="東京都",
            electoral_district="東京1区",
            profile_url="https://example.com/test",
            party_position="幹事長",
        )

        # Create politician
        result = repo.create_politician(politician_data)

        # Verify result
        assert result is not None
        assert result.name == "テスト太郎"
        assert result.political_party_id == party_id
        assert result.position == "衆議院議員"
        assert result.prefecture == "東京都"
        assert result.electoral_district == "東京1区"
        assert result.profile_url == "https://example.com/test"
        assert result.party_position == "幹事長"
        assert result.id is not None

        # Clean up
        repo.delete_politician(result.id)
        party_repo.close()

    def test_get_by_id_returns_pydantic_model(self, repo):
        """Test that get_by_id returns a Pydantic model"""
        # First, ensure political party exists
        from src.database.political_party_repository import PoliticalPartyRepository

        party_repo = PoliticalPartyRepository()
        party_repo.create_party_if_not_exists("テスト政党")
        party = party_repo.get_by_name("テスト政党")
        assert party is not None
        party_id = party[0]  # Get party ID

        # Create test politician
        politician_data = PoliticianCreate(
            name="検索テスト太郎",
            political_party_id=party_id,
        )
        created = repo.create_politician(politician_data)
        assert created is not None

        # Fetch by ID
        result = repo.get_by_id(created.id)

        # Verify result is a Pydantic model
        assert result is not None
        assert hasattr(result, "model_dump")  # Pydantic method
        assert result.name == "検索テスト太郎"
        assert result.political_party_id == party_id

        # Clean up
        repo.delete_politician(created.id)
        party_repo.close()

    def test_search_returns_list_of_pydantic_models(self, repo):
        """Test that search returns list of Pydantic models"""
        # First, ensure political parties exist
        from src.database.political_party_repository import PoliticalPartyRepository

        party_repo = PoliticalPartyRepository()
        party_repo.create_party_if_not_exists("テスト政党1")
        party_repo.create_party_if_not_exists("テスト政党2")
        party1 = party_repo.get_by_name("テスト政党1")
        party2 = party_repo.get_by_name("テスト政党2")
        assert party1 is not None and party2 is not None
        party1_id = party1[0]  # Get party ID
        party2_id = party2[0]  # Get party ID

        # Create test politicians
        politicians = [
            PoliticianCreate(name="検索太郎", political_party_id=party1_id),
            PoliticianCreate(name="検索花子", political_party_id=party2_id),
        ]
        created_ids = []
        for p in politicians:
            result = repo.create_politician(p)
            if result:
                created_ids.append(result.id)

        # Search by name pattern
        results = repo.search_by_name("検索")

        # Verify results are Pydantic models
        assert len(results) >= 2
        for result in results:
            if result.name in ["検索太郎", "検索花子"]:
                assert hasattr(result, "model_dump")  # Pydantic method

        # Clean up
        for politician_id in created_ids:
            repo.delete_politician(politician_id)
        party_repo.close()

    def test_update_with_partial_data(self, repo):
        """Test updating politician with partial data"""
        # First, ensure political party exists
        from src.database.political_party_repository import PoliticalPartyRepository

        party_repo = PoliticalPartyRepository()
        party_repo.create_party_if_not_exists("テスト政党")
        party = party_repo.get_by_name("テスト政党")
        assert party is not None
        party_id = party[0]  # Get party ID

        # Create initial politician
        initial_data = PoliticianCreate(
            name="更新テスト太郎",
            political_party_id=party_id,
            position="衆議院議員",
        )
        created = repo.create_politician(initial_data)
        assert created is not None

        # Update only some fields
        from src.models.politician import PoliticianUpdate

        update_data = PoliticianUpdate(
            position="参議院議員",
            electoral_district="比例代表",
        )
        success = repo.update_politician(created.id, update_data)
        assert success is True

        # Verify update
        updated = repo.get_by_id(created.id)
        assert updated is not None
        assert updated.name == "更新テスト太郎"  # Unchanged
        assert updated.political_party_id == party_id  # Unchanged
        assert updated.position == "参議院議員"  # Updated
        assert updated.electoral_district == "比例代表"  # Updated

        # Clean up
        repo.delete_politician(created.id)
        party_repo.close()
