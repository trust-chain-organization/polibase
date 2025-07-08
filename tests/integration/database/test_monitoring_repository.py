"""Integration tests for MonitoringRepository"""

import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config.database import DATABASE_URL
from src.database.monitoring_repository import MonitoringRepository

# Skip all tests in this module if running in CI environment
pytestmark = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Integration tests require database connection not available in CI",
)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing with transaction rollback"""
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def setup_test_data(db_session):
    """Set up test data for monitoring"""
    # Ensure we have a governing body
    gb_check = db_session.execute(text("SELECT id FROM governing_bodies WHERE id = 1"))
    if not gb_check.scalar():
        db_session.execute(
            text("""
            INSERT INTO governing_bodies (id, name, type)
            VALUES (1, 'テスト市', '市区町村')
            """)
        )
        db_session.commit()

    # Insert test conference
    conf_result = db_session.execute(
        text("""
        INSERT INTO conferences (governing_body_id, name, type)
        VALUES (1, 'モニターテスト議会', '地方議会全体')
        RETURNING id
        """)
    )
    conference_id = conf_result.scalar()

    # Insert test meeting
    meeting_result = db_session.execute(
        text("""
        INSERT INTO meetings (conference_id, name, date, url)
        VALUES (:conf_id, 'モニターテスト会議', CURRENT_DATE, 'http://test.example.com')
        RETURNING id
        """),
        {"conf_id": conference_id},
    )
    meeting_id = meeting_result.scalar()

    # Insert test minutes
    minutes_result = db_session.execute(
        text("""
        INSERT INTO minutes (meeting_id, title, content, processed_at)
        VALUES (:meeting_id, 'テスト議事録', 'テスト内容', CURRENT_TIMESTAMP)
        RETURNING id
        """),
        {"meeting_id": meeting_id},
    )
    minutes_id = minutes_result.scalar()

    # Insert test speaker
    speaker_result = db_session.execute(
        text("""
        INSERT INTO speakers (name, type, is_politician)
        VALUES ('モニターテスト議員', '議員', true)
        RETURNING id
        """)
    )
    speaker_id = speaker_result.scalar()

    # Insert test political party
    party_result = db_session.execute(
        text("""
        INSERT INTO political_parties (name)
        VALUES ('モニターテスト党')
        RETURNING id
        """)
    )
    party_id = party_result.scalar()

    # Insert test politician
    politician_result = db_session.execute(
        text("""
        INSERT INTO politicians (name, political_party_id, speaker_id)
        VALUES ('モニターテスト議員', :party_id, :speaker_id)
        RETURNING id
        """),
        {"party_id": party_id, "speaker_id": speaker_id},
    )
    politician_id = politician_result.scalar()

    db_session.commit()

    return {
        "conference_id": conference_id,
        "meeting_id": meeting_id,
        "minutes_id": minutes_id,
        "speaker_id": speaker_id,
        "politician_id": politician_id,
        "party_id": party_id,
    }


@pytest.fixture
def repository():
    """Create MonitoringRepository instance"""
    return MonitoringRepository()


class TestMonitoringRepository:
    """Test cases for MonitoringRepository"""

    def test_get_overall_metrics(self, db_session, setup_test_data, repository):
        """Test getting overall metrics"""
        # Execute
        metrics = repository.get_overall_metrics()

        # Verify
        assert isinstance(metrics, dict)

        # Check basic keys exist
        assert "total_conferences" in metrics
        assert "conferences_with_data" in metrics
        assert "conferences_coverage" in metrics
        assert "total_meetings" in metrics
        assert "meetings_with_minutes" in metrics
        assert "meetings_coverage" in metrics
        assert "total_minutes" in metrics
        assert "processed_minutes" in metrics
        assert "minutes_coverage" in metrics
        assert "total_speakers" in metrics
        assert "linked_speakers" in metrics
        assert "speakers_coverage" in metrics
        assert "total_politicians" in metrics
        assert "active_politicians" in metrics
        assert "politicians_coverage" in metrics

        # Check values are reasonable
        assert metrics["total_conferences"] > 0
        assert metrics["total_meetings"] > 0
        assert metrics["total_minutes"] > 0
        assert metrics["total_speakers"] > 0
        assert metrics["total_politicians"] > 0

        # Check coverage percentages
        assert 0 <= metrics["conferences_coverage"] <= 100
        assert 0 <= metrics["meetings_coverage"] <= 100
        assert 0 <= metrics["minutes_coverage"] <= 100
        assert 0 <= metrics["speakers_coverage"] <= 100
        assert 0 <= metrics["politicians_coverage"] <= 100

    def test_get_recent_activities(self, db_session, setup_test_data, repository):
        """Test getting recent activities"""
        # Execute - get activities from last 30 days
        df = repository.get_recent_activities(days=30)

        # Verify
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Check columns exist
        expected_columns = [
            "activity_type",
            "item_name",
            "activity_date",
            "conference_name",
        ]
        for col in expected_columns:
            assert col in df.columns

        # Check that our test data is included
        test_activities = df[df["item_name"].str.contains("モニターテスト", na=False)]
        assert len(test_activities) > 0

    def test_get_conference_coverage(self, db_session, setup_test_data, repository):
        """Test getting conference coverage data"""
        # Execute
        df = repository.get_conference_coverage()

        # Verify
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Check columns
        expected_columns = [
            "conference_id",
            "conference_name",
            "governing_body_name",
            "total_meetings",
            "processed_meetings",
            "coverage_rate",
        ]
        for col in expected_columns:
            assert col in df.columns

        # Check our test conference is included
        test_conf = df[df["conference_name"] == "モニターテスト議会"]
        assert len(test_conf) == 1
        assert test_conf.iloc[0]["total_meetings"] >= 1

    def test_get_time_series_data(self, db_session, setup_test_data, repository):
        """Test getting time series data"""
        # Execute
        df = repository.get_time_series_data(months=12)

        # Verify
        assert isinstance(df, pd.DataFrame)

        # Check columns
        expected_columns = ["month", "new_meetings", "new_minutes", "new_politicians"]
        for col in expected_columns:
            assert col in df.columns

        # Should have data for current month
        current_month = pd.Timestamp.now().strftime("%Y-%m")
        current_month_data = df[df["month"] == current_month]
        if len(current_month_data) > 0:
            assert current_month_data.iloc[0]["new_meetings"] >= 1

    def test_get_governing_body_statistics(
        self, db_session, setup_test_data, repository
    ):
        """Test getting governing body statistics"""
        # Execute
        df = repository.get_governing_body_statistics()

        # Verify
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Check columns
        expected_columns = [
            "governing_body_id",
            "governing_body_name",
            "type",
            "total_conferences",
            "total_meetings",
            "total_minutes",
            "total_politicians",
        ]
        for col in expected_columns:
            assert col in df.columns

        # Check our test governing body is included
        test_gb = df[df["governing_body_name"] == "テスト市"]
        assert len(test_gb) >= 1
        assert test_gb.iloc[0]["total_conferences"] >= 1

    def test_get_politician_activity_summary(
        self, db_session, setup_test_data, repository
    ):
        """Test getting politician activity summary"""
        # Execute
        df = repository.get_politician_activity_summary(limit=100)

        # Verify
        assert isinstance(df, pd.DataFrame)

        # Check columns if there's data
        if len(df) > 0:
            expected_columns = [
                "politician_id",
                "politician_name",
                "party_name",
                "total_conversations",
                "first_activity",
                "last_activity",
            ]
            for col in expected_columns:
                assert col in df.columns

    def test_get_party_statistics(self, db_session, setup_test_data, repository):
        """Test getting party statistics"""
        # Execute
        df = repository.get_party_statistics()

        # Verify
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Check columns
        expected_columns = [
            "party_id",
            "party_name",
            "total_politicians",
            "active_politicians",
            "total_conversations",
        ]
        for col in expected_columns:
            assert col in df.columns

        # Check our test party is included
        test_party = df[df["party_name"] == "モニターテスト党"]
        assert len(test_party) == 1
        assert test_party.iloc[0]["total_politicians"] >= 1

    def test_get_monthly_processing_stats(
        self, db_session, setup_test_data, repository
    ):
        """Test getting monthly processing statistics"""
        # Execute
        df = repository.get_monthly_processing_stats()

        # Verify
        assert isinstance(df, pd.DataFrame)

        # Check columns if there's data
        if len(df) > 0:
            expected_columns = [
                "month",
                "minutes_processed",
                "conversations_extracted",
                "speakers_linked",
            ]
            for col in expected_columns:
                assert col in df.columns
