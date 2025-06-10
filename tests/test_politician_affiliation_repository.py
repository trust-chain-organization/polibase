"""Tests for politician affiliation repository"""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from src.database.politician_affiliation_repository import (
    PoliticianAffiliationRepository,
)


class TestPoliticianAffiliationRepository:
    """Test cases for PoliticianAffiliationRepository"""

    @pytest.fixture
    def mock_connection(self):
        """Create a mock database connection"""
        connection = Mock()
        connection.execute = Mock()
        connection.commit = Mock()
        connection.rollback = Mock()
        return connection

    @pytest.fixture
    @patch("src.database.politician_affiliation_repository.get_db_engine")
    def repository(self, mock_get_engine, mock_connection):
        """Create a repository instance with mocked engine"""
        mock_engine = Mock()
        mock_get_engine.return_value = mock_engine
        repo = PoliticianAffiliationRepository()
        # Inject mock connection
        repo.connection = mock_connection
        return repo

    def test_create_or_update_affiliation_new(self, repository):
        """Test creating a new affiliation"""
        # Setup - simulate no existing affiliation
        mock_select_result = Mock()
        mock_select_result.fetchone.return_value = None

        # Mock insert result
        mock_insert_result = Mock()
        mock_insert_result.fetchone.return_value = Mock(id=1)

        repository.connection.execute.side_effect = [
            mock_select_result,  # SELECT returns None
            mock_insert_result,  # INSERT returns new ID
        ]

        # Execute
        result = repository.create_or_update_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

        # Assert
        assert result["action"] == "created"
        assert result["affiliation_id"] == 1
        assert repository.connection.execute.call_count == 2
        repository.connection.commit.assert_called_once()

    def test_create_or_update_affiliation_update_existing(self, repository):
        """Test updating an existing affiliation"""
        # Setup - simulate existing affiliation
        mock_existing = Mock()
        mock_existing.id = 1
        mock_existing.role = "委員"
        mock_existing.start_date = date(2024, 1, 1)
        mock_existing.end_date = None

        mock_select_result = Mock()
        mock_select_result.fetchone.return_value = mock_existing

        repository.connection.execute.side_effect = [
            mock_select_result,  # SELECT returns existing
            Mock(),  # UPDATE
        ]

        # Execute
        result = repository.create_or_update_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",  # Different role
        )

        # Assert
        assert result["action"] == "updated"
        assert result["affiliation_id"] == 1
        assert repository.connection.execute.call_count == 2
        repository.connection.commit.assert_called_once()

    def test_create_or_update_affiliation_no_change(self, repository):
        """Test when affiliation already exists with same data"""
        # Setup - simulate existing affiliation with same data
        mock_existing = Mock()
        mock_existing.id = 1
        mock_existing.role = "委員長"
        mock_existing.start_date = date(2024, 1, 1)
        mock_existing.end_date = None

        mock_select_result = Mock()
        mock_select_result.fetchone.return_value = mock_existing

        repository.connection.execute.return_value = mock_select_result

        # Execute
        result = repository.create_or_update_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",  # Same role
        )

        # Assert
        assert result["action"] == "no_change"
        assert result["affiliation_id"] == 1
        assert repository.connection.execute.call_count == 1  # Only SELECT
        repository.connection.commit.assert_not_called()

    def test_create_or_update_affiliation_with_end_date(self, repository):
        """Test creating affiliation with end date"""
        # Setup
        mock_select_result = Mock()
        mock_select_result.fetchone.return_value = None

        mock_insert_result = Mock()
        mock_insert_result.fetchone.return_value = Mock(id=1)

        repository.connection.execute.side_effect = [
            mock_select_result,
            mock_insert_result,
        ]

        # Execute
        result = repository.create_or_update_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            role="委員",
        )

        # Assert
        assert result["action"] == "created"
        # Check INSERT parameters include end_date
        insert_call = repository.connection.execute.call_args_list[1]
        params = insert_call[0][1]
        assert params["end_date"] == date(2024, 12, 31)

    def test_create_affiliations_from_matches(self, repository):
        """Test creating multiple affiliations from matches"""
        # Setup
        members = [
            {"id": 1, "matched_politician_id": 100, "extracted_role": "委員長"},
            {"id": 2, "matched_politician_id": 101, "extracted_role": "副委員長"},
            {
                "id": 3,
                "matched_politician_id": 102,
                "extracted_role": None,  # No role
            },
        ]

        # Mock create_or_update_affiliation responses
        with patch.object(repository, "create_or_update_affiliation") as mock_create:
            mock_create.side_effect = [
                {"action": "created", "affiliation_id": 1},
                {"action": "updated", "affiliation_id": 2},
                {"action": "no_change", "affiliation_id": 3},
            ]

            # Execute
            result = repository.create_affiliations_from_matches(
                conference_id=1, members=members, start_date=date(2024, 1, 1)
            )

            # Assert
            assert result["total_processed"] == 3
            assert result["created_count"] == 1
            assert result["updated_count"] == 1
            assert result["no_change_count"] == 1
            assert len(result["details"]) == 3

            # Check calls
            assert mock_create.call_count == 3
            # Check default role for member without role
            third_call = mock_create.call_args_list[2]
            assert third_call[1]["role"] == "委員"

    def test_create_affiliations_from_matches_empty(self, repository):
        """Test creating affiliations with empty member list"""
        # Execute
        result = repository.create_affiliations_from_matches(
            conference_id=1, members=[], start_date=date(2024, 1, 1)
        )

        # Assert
        assert result["total_processed"] == 0
        assert result["created_count"] == 0
        assert result["updated_count"] == 0
        assert result["no_change_count"] == 0
        assert result["details"] == []

    def test_rollback_on_error(self, repository):
        """Test rollback on database error"""
        # Setup
        repository.connection.execute.side_effect = Exception("DB Error")

        # Execute and assert
        with pytest.raises(Exception, match="DB Error"):
            repository.create_or_update_affiliation(
                politician_id=100,
                conference_id=1,
                start_date=date(2024, 1, 1),
                role="委員長",
            )

        repository.connection.rollback.assert_called_once()

    def test_get_affiliations_by_conference(self, repository):
        """Test getting affiliations by conference"""
        # Setup
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = 1
        mock_row.politician_id = 100
        mock_row.politician_name = "山田太郎"
        mock_row.role = "委員長"
        mock_row.start_date = date(2024, 1, 1)
        mock_row.end_date = None

        mock_result.fetchall.return_value = [mock_row]
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_affiliations_by_conference(1)

        # Assert
        assert len(result) == 1
        assert result[0]["politician_id"] == 100
        assert result[0]["politician_name"] == "山田太郎"
        assert result[0]["role"] == "委員長"
