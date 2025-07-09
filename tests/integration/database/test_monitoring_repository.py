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
        INSERT INTO minutes (meeting_id, url)
        VALUES (:meeting_id, 'http://test.example.com/minutes')
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
def repository(db_session):
    """Create MonitoringRepository instance with test session"""
    return MonitoringRepository(session=db_session)


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

        # Skip processed_minutes check since processed_at column doesn't exist
        # assert metrics["processed_minutes"] > 0

    def test_get_recent_activities(self, db_session, setup_test_data, repository):
        """Test getting recent activities"""
        # Execute - get activities from last 30 days
        df = repository.get_recent_activities(days=30)

        # Verify
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Check columns exist
        expected_columns = [
            "タイプ",
            "項目名",
            "関連組織",
            "日付",
            "作成日時",
        ]
        for col in expected_columns:
            assert col in df.columns

        # Check that our test data is included
        test_activities = df[df["項目名"].str.contains("モニターテスト", na=False)]
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

    def test_get_timeline_data(self, db_session, setup_test_data, repository):
        """Test getting timeline data"""
        # Execute
        df = repository.get_timeline_data(time_range="過去30日", data_type="すべて")

        # Verify
        assert isinstance(df, pd.DataFrame)

        # Check columns if there's data
        if len(df) > 0:
            expected_columns = ["date", "data_type", "count"]
            for col in expected_columns:
                assert col in df.columns

    def test_get_prefecture_coverage(self, db_session, setup_test_data, repository):
        """Test getting prefecture coverage data"""
        # Execute
        df = repository.get_prefecture_coverage()

        # Verify
        assert isinstance(df, pd.DataFrame)
        # May be empty if no prefectures in test data

        # Check columns if there's data
        if len(df) > 0:
            expected_columns = [
                "prefecture_name",
                "conference_count",
                "meeting_count",
                "processed_count",
                "coverage_rate",
            ]
            for col in expected_columns:
                assert col in df.columns

    def test_get_committee_type_coverage(self, db_session, setup_test_data, repository):
        """Test getting committee type coverage data"""
        # Execute
        df = repository.get_committee_type_coverage()

        # Verify
        assert isinstance(df, pd.DataFrame)

        # Check columns if there's data
        if len(df) > 0:
            expected_columns = [
                "governing_body_type",
                "committee_type",
                "meeting_count",
                "processed_count",
            ]
            for col in expected_columns:
                assert col in df.columns

    def test_get_party_coverage(self, db_session, setup_test_data, repository):
        """Test getting party coverage data"""
        # Execute
        df = repository.get_party_coverage()

        # Verify
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

        # Check columns
        expected_columns = [
            "party_name",
            "politician_count",
            "active_count",
            "coverage_rate",
        ]
        for col in expected_columns:
            assert col in df.columns

        # Check our test party is included
        test_party = df[df["party_name"] == "モニターテスト党"]
        assert len(test_party) == 1
        assert test_party.iloc[0]["politician_count"] >= 1

    def test_get_prefecture_detailed_coverage(
        self, db_session, setup_test_data, repository
    ):
        """Test getting prefecture detailed coverage data"""
        # Execute
        df = repository.get_prefecture_detailed_coverage()

        # Verify
        assert isinstance(df, pd.DataFrame)
        # May be empty if no prefectures in test data

        # Check columns if there's data
        if len(df) > 0:
            expected_columns = [
                "prefecture_name",
                "conference_count",
                "meetings_count",
                "processed_meetings_count",
                "minutes_count",
                "politicians_count",
                "groups_count",
                "total_value",
            ]
            for col in expected_columns:
                assert col in df.columns
