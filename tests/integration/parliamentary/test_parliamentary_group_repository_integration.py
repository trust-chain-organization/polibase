"""Integration tests for parliamentary group repositories"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.infrastructure.config.database import DATABASE_URL
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl as ParliamentaryGroupMembershipRepository,  # noqa: E501
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl as ParliamentaryGroupRepository,
)


@pytest.fixture(scope="function")
def db_session():
    """Create a database session for testing with transaction rollback"""
    engine = create_engine(DATABASE_URL)

    # Check if parliamentary_groups table exists
    with engine.connect() as temp_conn:
        result = temp_conn.execute(
            text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'parliamentary_groups'
            )
            """)
        )
        if not result.scalar():
            pytest.fail(
                "Parliamentary groups tables not found. "
                "Database migrations must be applied before running integration tests. "
                "Run: psql -f "
                "database/migrations/008_create_parliamentary_groups_tables.sql"
            )

    # Now create the actual test connection
    connection = engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    # Clean up any existing test data before yielding
    try:
        # Delete in correct order to respect foreign key constraints
        session.execute(
            text("DELETE FROM parliamentary_group_memberships WHERE id > 0")
        )
        session.execute(text("DELETE FROM parliamentary_groups WHERE id > 0"))
        session.execute(text("DELETE FROM politician_affiliations WHERE id > 0"))
        session.execute(text("DELETE FROM politicians WHERE name LIKE 'テスト議員%'"))
        session.execute(text("DELETE FROM speakers WHERE name LIKE 'テスト議員%'"))
        session.execute(
            text("DELETE FROM political_parties WHERE name LIKE 'テスト党%'")
        )
        session.execute(text("DELETE FROM conferences WHERE name LIKE 'テスト%'"))
        session.commit()
    except Exception:
        # If cleanup fails, still continue with test
        session.rollback()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
    engine.dispose()


@pytest.fixture
def setup_test_data(db_session):
    """Set up test data for parliamentary groups"""
    # First check if governing body exists, if not create one
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
    result = db_session.execute(
        text("""
        INSERT INTO conferences (governing_body_id, name, type)
        VALUES (1, 'テスト市議会', '地方議会全体')
        RETURNING id
        """)
    )
    conference_id = result.scalar()

    # Verify conference was created
    if not conference_id:
        pytest.fail("Failed to create test conference")

    # Debug: Check what conference_id we got
    print(f"DEBUG: Created conference with ID: {conference_id}")

    # Insert test political parties
    party_result1 = db_session.execute(
        text("INSERT INTO political_parties (name) VALUES ('テスト党A') RETURNING id")
    )
    party_id1 = party_result1.scalar()

    party_result2 = db_session.execute(
        text("INSERT INTO political_parties (name) VALUES ('テスト党B') RETURNING id")
    )
    party_id2 = party_result2.scalar()

    # Insert test speakers first (required for politicians)
    speaker_result1 = db_session.execute(
        text(
            "INSERT INTO speakers (name, type, is_politician) "
            "VALUES ('テスト議員1', '議員', true) RETURNING id"
        )
    )
    speaker_id1 = speaker_result1.scalar()

    speaker_result2 = db_session.execute(
        text(
            "INSERT INTO speakers (name, type, is_politician) "
            "VALUES ('テスト議員2', '議員', true) RETURNING id"
        )
    )
    speaker_id2 = speaker_result2.scalar()

    speaker_result3 = db_session.execute(
        text(
            "INSERT INTO speakers (name, type, is_politician) "
            "VALUES ('テスト議員3', '議員', true) RETURNING id"
        )
    )
    speaker_id3 = speaker_result3.scalar()

    # Insert test politicians (without speaker_id - removed in migration 032)
    politician_result1 = db_session.execute(
        text("""
        INSERT INTO politicians (name, political_party_id)
        VALUES ('テスト議員1', :party_id)
        RETURNING id
        """),
        {"party_id": party_id1},
    )
    politician_id1 = politician_result1.scalar()

    politician_result2 = db_session.execute(
        text("""
        INSERT INTO politicians (name, political_party_id)
        VALUES ('テスト議員2', :party_id)
        RETURNING id
        """),
        {"party_id": party_id2},
    )
    politician_id2 = politician_result2.scalar()

    politician_result3 = db_session.execute(
        text("""
        INSERT INTO politicians (name, political_party_id)
        VALUES ('テスト議員3', :party_id)
        RETURNING id
        """),
        {"party_id": party_id1},
    )
    politician_id3 = politician_result3.scalar()

    # Link speakers to politicians (new relationship from migration 032)
    db_session.execute(
        text(
            "UPDATE speakers SET politician_id = :politician_id WHERE id = :speaker_id"
        ),
        {"politician_id": politician_id1, "speaker_id": speaker_id1},
    )
    db_session.execute(
        text(
            "UPDATE speakers SET politician_id = :politician_id WHERE id = :speaker_id"
        ),
        {"politician_id": politician_id2, "speaker_id": speaker_id2},
    )
    db_session.execute(
        text(
            "UPDATE speakers SET politician_id = :politician_id WHERE id = :speaker_id"
        ),
        {"politician_id": politician_id3, "speaker_id": speaker_id3},
    )

    db_session.commit()

    return {
        "conference_id": conference_id,
        "party_ids": [party_id1, party_id2],
        "politician_ids": [politician_id1, politician_id2, politician_id3],
    }


class TestParliamentaryGroupRepositoryIntegration:
    """Integration tests for ParliamentaryGroupRepository"""

    def test_create_parliamentary_group(self, db_session, setup_test_data):
        """Test creating a parliamentary group"""
        repo = ParliamentaryGroupRepository(session=db_session)

        # Create a parliamentary group
        group = repo.create_parliamentary_group(
            name="テスト会派",
            conference_id=setup_test_data["conference_id"],
            url="http://test-group.example.com",
            description="テスト用の会派です",
            is_active=True,
        )

        # Verify the created group
        assert group["name"] == "テスト会派"
        assert group["conference_id"] == setup_test_data["conference_id"]
        assert group["url"] == "http://test-group.example.com"
        assert group["description"] == "テスト用の会派です"
        assert group["is_active"] is True
        assert "id" in group
        assert "created_at" in group

    def test_get_parliamentary_group_by_id(self, db_session, setup_test_data):
        """Test retrieving a parliamentary group by ID"""
        repo = ParliamentaryGroupRepository(session=db_session)

        # Create a group
        created_group = repo.create_parliamentary_group(
            name="取得テスト会派",
            conference_id=setup_test_data["conference_id"],
        )

        # Retrieve by ID
        retrieved_group = repo.get_parliamentary_group_by_id(created_group["id"])

        assert retrieved_group is not None
        assert retrieved_group["id"] == created_group["id"]
        assert retrieved_group["name"] == "取得テスト会派"
        assert "conference_name" in retrieved_group  # Join field

        # Test non-existent ID
        non_existent = repo.get_parliamentary_group_by_id(99999)
        assert non_existent is None

    def test_get_parliamentary_groups_by_conference(self, db_session, setup_test_data):
        """Test retrieving parliamentary groups by conference"""
        repo = ParliamentaryGroupRepository(session=db_session)
        conference_id = setup_test_data["conference_id"]

        # Create multiple groups
        repo.create_parliamentary_group("会派A", conference_id, is_active=True)
        repo.create_parliamentary_group("会派B", conference_id, is_active=True)
        repo.create_parliamentary_group("会派C（解散）", conference_id, is_active=False)

        # Get active groups only
        active_groups = repo.get_parliamentary_groups_by_conference(
            conference_id, active_only=True
        )
        assert len(active_groups) == 2
        assert all(g["is_active"] for g in active_groups)

        # Get all groups
        all_groups = repo.get_parliamentary_groups_by_conference(
            conference_id, active_only=False
        )
        assert len(all_groups) == 3
        assert any(not g["is_active"] for g in all_groups)

    def test_search_parliamentary_groups(self, db_session, setup_test_data):
        """Test searching parliamentary groups"""
        repo = ParliamentaryGroupRepository(session=db_session)
        conference_id = setup_test_data["conference_id"]

        # Create test groups
        repo.create_parliamentary_group("自由民主党会派", conference_id)
        repo.create_parliamentary_group("立憲民主党会派", conference_id)
        repo.create_parliamentary_group("公明党会派", conference_id)

        # Search by name
        results = repo.search_parliamentary_groups(name="民主")
        assert len(results) == 2
        assert all("民主" in g["name"] for g in results)

        # Search by conference
        results = repo.search_parliamentary_groups(conference_id=conference_id)
        assert len(results) >= 3

        # Combined search
        results = repo.search_parliamentary_groups(
            name="立憲", conference_id=conference_id
        )
        assert len(results) == 1
        assert results[0]["name"] == "立憲民主党会派"

    def test_update_parliamentary_group(self, db_session, setup_test_data):
        """Test updating parliamentary group information"""
        repo = ParliamentaryGroupRepository(session=db_session)

        # Create a group
        group = repo.create_parliamentary_group(
            name="更新前会派",
            conference_id=setup_test_data["conference_id"],
            description="更新前の説明",
        )

        # Update the group
        success = repo.update_parliamentary_group(
            group_id=group["id"],
            name="更新後会派",
            description="更新後の説明",
            url="http://updated.example.com",
        )
        assert success is True

        # Verify the update
        updated = repo.get_parliamentary_group_by_id(group["id"])
        assert updated["name"] == "更新後会派"
        assert updated["description"] == "更新後の説明"
        assert updated["url"] == "http://updated.example.com"

        # Test partial update
        success = repo.update_parliamentary_group(
            group_id=group["id"],
            is_active=False,
        )
        assert success is True

        updated = repo.get_parliamentary_group_by_id(group["id"])
        assert updated["is_active"] is False
        assert updated["name"] == "更新後会派"  # Unchanged


@pytest.fixture
def setup_membership_group(db_session, setup_test_data):
    """Create a parliamentary group for membership tests"""
    group_repo = ParliamentaryGroupRepository(session=db_session)
    # Ensure we have a valid conference_id from setup_test_data
    conference_id = setup_test_data["conference_id"]
    if not conference_id:
        pytest.fail("No conference_id available from setup_test_data")

    # Debug: Print conference_id
    print(f"DEBUG: Using conference_id: {conference_id} for membership group")

    group = group_repo.create_parliamentary_group(
        name="メンバーシップテスト会派",
        conference_id=conference_id,
    )
    return group


class TestParliamentaryGroupMembershipRepositoryIntegration:
    """Integration tests for ParliamentaryGroupMembershipRepository"""

    def test_add_membership(self, db_session, setup_test_data, setup_membership_group):
        """Test adding a membership"""
        repo = ParliamentaryGroupMembershipRepository(session=db_session)

        membership = repo.add_membership(
            politician_id=setup_test_data["politician_ids"][0],
            parliamentary_group_id=setup_membership_group["id"],
            start_date=date(2024, 1, 1),
            role="会長",
        )

        assert membership["politician_id"] == setup_test_data["politician_ids"][0]
        assert membership["parliamentary_group_id"] == setup_membership_group["id"]
        assert membership["start_date"] == date(2024, 1, 1)
        assert membership["end_date"] is None
        assert membership["role"] == "会長"
        assert "id" in membership

    def test_get_current_members(
        self, db_session, setup_test_data, setup_membership_group
    ):
        """Test getting current members of a group"""
        repo = ParliamentaryGroupMembershipRepository(session=db_session)

        # Add current members
        repo.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 1, 1),
            role="会長",
        )
        repo.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date(2024, 1, 15),
        )

        # Add past member
        repo.add_membership(
            setup_test_data["politician_ids"][2],
            setup_membership_group["id"],
            date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Get current members
        current_members = repo.get_current_members(setup_membership_group["id"])

        assert len(current_members) == 2
        assert all(m["end_date"] is None for m in current_members)
        assert "politician_name" in current_members[0]  # Join field
        assert "party_name" in current_members[0]  # Join field

        # Check roles
        leader = [m for m in current_members if m["role"] == "会長"]
        assert len(leader) == 1

    def test_get_member_history(
        self, db_session, setup_test_data, setup_membership_group
    ):
        """Test getting member history"""
        repo = ParliamentaryGroupMembershipRepository(session=db_session)

        # Add members with history
        repo.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 1, 1),
        )
        repo.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Get all history
        all_history = repo.get_member_history(
            setup_membership_group["id"], include_past=True
        )
        assert len(all_history) == 2

        # Get current only
        current_only = repo.get_member_history(
            setup_membership_group["id"], include_past=False
        )
        assert len(current_only) == 1
        assert current_only[0]["politician_id"] == setup_test_data["politician_ids"][0]

    def test_get_politician_groups(
        self, db_session, setup_test_data, setup_membership_group
    ):
        """Test getting groups a politician belongs to"""
        repo = ParliamentaryGroupMembershipRepository(session=db_session)
        group_repo = ParliamentaryGroupRepository(session=db_session)

        # Create another group
        another_group = group_repo.create_parliamentary_group(
            name="別の会派",
            conference_id=setup_test_data["conference_id"],
        )

        politician_id = setup_test_data["politician_ids"][0]

        # Add memberships
        repo.add_membership(
            politician_id,
            setup_membership_group["id"],
            date(2024, 1, 1),
        )
        repo.add_membership(
            politician_id,
            another_group["id"],
            date(2023, 1, 1),
            end_date=date(2023, 12, 31),
        )

        # Get current groups
        current_groups = repo.get_politician_groups(politician_id, current_only=True)
        assert len(current_groups) == 1
        assert current_groups[0]["group_name"] == "メンバーシップテスト会派"

        # Get all groups
        all_groups = repo.get_politician_groups(politician_id, current_only=False)
        assert len(all_groups) == 2
        assert "conference_name" in all_groups[0]  # Join field

    def test_end_membership(self, db_session, setup_test_data, setup_membership_group):
        """Test ending a membership"""
        repo = ParliamentaryGroupMembershipRepository(session=db_session)

        # Add membership
        politician_id = setup_test_data["politician_ids"][0]
        repo.add_membership(
            politician_id,
            setup_membership_group["id"],
            date(2024, 1, 1),
        )

        # End membership
        success = repo.end_membership(
            politician_id,
            setup_membership_group["id"],
            date(2024, 6, 30),
        )
        assert success is True

        # Verify membership ended
        current_members = repo.get_current_members(setup_membership_group["id"])
        assert len(current_members) == 0

        # Check history shows ended membership
        history = repo.get_member_history(setup_membership_group["id"])
        assert len(history) == 1
        assert history[0]["end_date"] == date(2024, 6, 30)

    def test_get_group_members_at_date(
        self, db_session, setup_test_data, setup_membership_group
    ):
        """Test getting group members at a specific date"""
        repo = ParliamentaryGroupMembershipRepository(session=db_session)

        # Add members with different periods
        repo.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2023, 1, 1),
            end_date=date(2023, 6, 30),
        )
        repo.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date(2023, 4, 1),
            end_date=date(2023, 12, 31),
        )
        repo.add_membership(
            setup_test_data["politician_ids"][2],
            setup_membership_group["id"],
            date(2023, 7, 1),
        )

        # Check members at different dates
        members_jan = repo.get_group_members_at_date(
            setup_membership_group["id"], date(2023, 1, 15)
        )
        assert len(members_jan) == 1  # Only politician 0

        members_may = repo.get_group_members_at_date(
            setup_membership_group["id"], date(2023, 5, 15)
        )
        assert len(members_may) == 2  # Politicians 0 and 1

        members_aug = repo.get_group_members_at_date(
            setup_membership_group["id"], date(2023, 8, 15)
        )
        assert len(members_aug) == 2  # Politicians 1 and 2

        members_now = repo.get_group_members_at_date(
            setup_membership_group["id"], date.today()
        )
        assert len(members_now) == 1  # Only politician 2 (no end date)

    def test_membership_constraints(
        self, db_session, setup_test_data, setup_membership_group
    ):
        """Test database constraints and edge cases"""
        repo = ParliamentaryGroupMembershipRepository(session=db_session)

        # Add a membership
        repo.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 1, 1),
        )

        # Try to add duplicate active membership
        # (should succeed - business logic should prevent)
        # This tests that the repository doesn't enforce uniqueness at DB level
        duplicate = repo.add_membership(
            setup_test_data["politician_ids"][0],
            setup_membership_group["id"],
            date(2024, 2, 1),
        )
        assert duplicate["id"] is not None

        # Test with future dates
        future_membership = repo.add_membership(
            setup_test_data["politician_ids"][1],
            setup_membership_group["id"],
            date.today() + timedelta(days=30),
        )
        assert future_membership["start_date"] > date.today()
