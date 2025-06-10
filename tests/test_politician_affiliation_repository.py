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

    def test_upsert_affiliation_new(self, repository):
        """Test creating a new affiliation via upsert"""
        # Setup - simulate no existing affiliation
        mock_select_result = Mock()
        mock_select_result.fetchone.return_value = None

        repository.connection.execute.return_value = mock_select_result

        # Mock the create_affiliation method that will be called
        with patch.object(
            repository, "create_affiliation", return_value=1
        ) as mock_create:
            # Execute - upsert_affiliation returns just the ID
            result = repository.upsert_affiliation(
                politician_id=100,
                conference_id=1,
                start_date=date(2024, 1, 1),
                role="委員長",
            )

            # Assert
            assert result == 1  # upsert_affiliation returns the ID
            mock_create.assert_called_once_with(
                100, 1, date(2024, 1, 1), None, "委員長"
            )

    def test_upsert_affiliation_update_existing(self, repository):
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
        result = repository.upsert_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",  # Different role
        )

        # Assert
        assert result == 1  # upsert_affiliation returns the existing ID
        assert repository.connection.execute.call_count == 2
        repository.connection.commit.assert_called_once()

    def test_create_affiliation(self, repository):
        """Test creating a new affiliation"""
        # Setup - mock that no existing affiliation exists
        check_result = Mock()
        check_result.fetchone.return_value = None

        # Mock insert result
        insert_result = Mock()
        insert_result.fetchone.return_value = [1]  # Return affiliation ID

        repository.connection.execute.side_effect = [
            check_result,  # Check for existing affiliation
            insert_result,  # Insert new affiliation
        ]

        # Execute
        result = repository.create_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

        # Assert
        assert result == 1
        assert repository.connection.execute.call_count == 2
        repository.connection.commit.assert_called_once()

    def test_create_affiliation_already_exists(self, repository):
        """Test creating affiliation when it already exists"""
        # Setup - mock that affiliation already exists
        check_result = Mock()
        check_result.fetchone.return_value = Mock(id=1)

        repository.connection.execute.return_value = check_result

        # Execute
        result = repository.create_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

        # Assert
        assert result is None  # Returns None when affiliation already exists
        assert repository.connection.execute.call_count == 1  # Only check query
        repository.connection.commit.assert_not_called()

    def test_update_affiliation_role(self, repository):
        """Test updating affiliation role"""
        # Setup
        repository.connection.execute.return_value = Mock()

        # Execute
        result = repository.update_affiliation_role(1, "副委員長")

        # Assert
        assert result is True
        repository.connection.execute.assert_called_once()
        repository.connection.commit.assert_called_once()

    def test_end_affiliation(self, repository):
        """Test ending an affiliation"""
        # Setup
        repository.connection.execute.return_value = Mock()

        # Execute
        result = repository.end_affiliation(1, date(2024, 12, 31))

        # Assert
        assert result is True
        repository.connection.execute.assert_called_once()
        repository.connection.commit.assert_called_once()

    def test_delete_affiliation(self, repository):
        """Test deleting an affiliation"""
        # Setup
        repository.connection.execute.return_value = Mock()

        # Execute
        result = repository.delete_affiliation(1)

        # Assert
        assert result is True
        repository.connection.execute.assert_called_once()
        repository.connection.commit.assert_called_once()

    def test_get_affiliations_by_conference(self, repository):
        """Test getting affiliations by conference"""
        # Setup
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = 1
        mock_row.politician_id = 100
        mock_row.conference_id = 1
        mock_row.start_date = date(2024, 1, 1)
        mock_row.end_date = None
        mock_row.role = "委員長"
        mock_row.politician_name = "山田太郎"
        mock_row.party_name = "自民党"

        # Mock iterator behavior
        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_affiliations_by_conference(1)

        # Assert
        assert len(result) == 1
        assert result[0]["politician_id"] == 100
        assert result[0]["politician_name"] == "山田太郎"
        assert result[0]["role"] == "委員長"
        assert result[0]["party_name"] == "自民党"

    def test_get_affiliations_by_politician(self, repository):
        """Test getting affiliations by politician"""
        # Setup
        mock_result = Mock()
        mock_row = Mock()
        mock_row.id = 1
        mock_row.politician_id = 100
        mock_row.conference_id = 1
        mock_row.start_date = date(2024, 1, 1)
        mock_row.end_date = None
        mock_row.role = "委員長"
        mock_row.conference_name = "本会議"
        mock_row.governing_body_name = "国"

        # Mock iterator behavior
        mock_result.__iter__ = Mock(return_value=iter([mock_row]))
        repository.connection.execute.return_value = mock_result

        # Execute
        result = repository.get_affiliations_by_politician(100)

        # Assert
        assert len(result) == 1
        assert result[0]["politician_id"] == 100
        assert result[0]["conference_name"] == "本会議"
        assert result[0]["role"] == "委員長"
        assert result[0]["governing_body_name"] == "国"
