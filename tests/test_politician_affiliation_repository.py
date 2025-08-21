"""Tests for politician affiliation repository"""

from datetime import date
from unittest.mock import MagicMock

import pytest


class TestPoliticianAffiliationRepository:
    """Test cases for PoliticianAffiliationRepository"""

    @pytest.fixture
    def repository(self):
        """Create a mock repository instance"""
        return MagicMock()

    def test_upsert_affiliation_new(self, repository):
        """Test creating a new affiliation via upsert"""
        # Setup
        repository.upsert_affiliation.return_value = 1

        # Execute
        result = repository.upsert_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

        # Assert
        assert result == 1
        repository.upsert_affiliation.assert_called_once_with(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

    def test_upsert_affiliation_update_existing(self, repository):
        """Test updating an existing affiliation"""
        # Setup
        repository.upsert_affiliation.return_value = 1

        # Execute
        result = repository.upsert_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",  # Different role
        )

        # Assert
        assert result == 1
        repository.upsert_affiliation.assert_called_once_with(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

    def test_create_affiliation(self, repository):
        """Test creating a new affiliation"""
        # Setup
        repository.create_affiliation.return_value = 1

        # Execute
        result = repository.create_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

        # Assert
        assert result == 1
        repository.create_affiliation.assert_called_once_with(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

    def test_create_affiliation_already_exists(self, repository):
        """Test creating affiliation when it already exists"""
        # Setup
        repository.create_affiliation.return_value = None

        # Execute
        result = repository.create_affiliation(
            politician_id=100,
            conference_id=1,
            start_date=date(2024, 1, 1),
            role="委員長",
        )

        # Assert
        assert result is None  # Returns None when affiliation already exists
        repository.create_affiliation.assert_called_once()

    def test_update_affiliation_role(self, repository):
        """Test updating affiliation role"""
        # Setup
        repository.update_affiliation_role.return_value = True

        # Execute
        result = repository.update_affiliation_role(1, "副委員長")

        # Assert
        assert result is True
        repository.update_affiliation_role.assert_called_once_with(1, "副委員長")

    def test_end_affiliation(self, repository):
        """Test ending an affiliation"""
        # Setup
        repository.end_affiliation.return_value = True

        # Execute
        result = repository.end_affiliation(1, date(2024, 12, 31))

        # Assert
        assert result is True
        repository.end_affiliation.assert_called_once_with(1, date(2024, 12, 31))

    def test_delete_affiliation(self, repository):
        """Test deleting an affiliation"""
        # Setup
        repository.delete_affiliation.return_value = True

        # Execute
        result = repository.delete_affiliation(1)

        # Assert
        assert result is True
        repository.delete_affiliation.assert_called_once_with(1)

    def test_get_affiliations_by_conference(self, repository):
        """Test getting affiliations by conference"""
        # Setup
        mock_data = [
            {
                "id": 1,
                "politician_id": 100,
                "conference_id": 1,
                "start_date": date(2024, 1, 1),
                "end_date": None,
                "role": "委員長",
                "politician_name": "山田太郎",
                "party_name": "自民党",
            }
        ]
        repository.get_affiliations_by_conference.return_value = mock_data

        # Execute
        result = repository.get_affiliations_by_conference(1)

        # Assert
        assert len(result) == 1
        assert result[0]["politician_id"] == 100
        assert result[0]["politician_name"] == "山田太郎"
        assert result[0]["role"] == "委員長"
        assert result[0]["party_name"] == "自民党"
        repository.get_affiliations_by_conference.assert_called_once_with(1)

    def test_get_affiliations_by_politician(self, repository):
        """Test getting affiliations by politician"""
        # Setup
        mock_data = [
            {
                "id": 1,
                "politician_id": 100,
                "conference_id": 1,
                "start_date": date(2024, 1, 1),
                "end_date": None,
                "role": "委員長",
                "conference_name": "本会議",
                "governing_body_name": "国",
            }
        ]
        repository.get_affiliations_by_politician.return_value = mock_data

        # Execute
        result = repository.get_affiliations_by_politician(100)

        # Assert
        assert len(result) == 1
        assert result[0]["politician_id"] == 100
        assert result[0]["conference_name"] == "本会議"
        assert result[0]["role"] == "委員長"
        assert result[0]["governing_body_name"] == "国"
        repository.get_affiliations_by_politician.assert_called_once_with(100)
