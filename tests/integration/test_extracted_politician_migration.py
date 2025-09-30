"""Integration tests for extracted politician migration and database schema."""

import pytest

from src.domain.entities.extracted_politician import ExtractedPolitician
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


@pytest.mark.integration
class TestExtractedPoliticianMigration:
    """Test database migrations related to extracted politicians.

    These tests verify:
    1. Politician creation without speaker_id (NULL handling)
    2. Speaker.politician_id nullable constraint
    3. Data integrity after migrations
    """

    @pytest.mark.asyncio
    async def test_politician_creation_without_speaker(
        self, async_session, political_party_repository
    ):
        """Test creating politician without speaker_id.

        Migration 031 made speaker_id nullable in politicians table.
        Migration 032 removed speaker_id from politicians and added
        politician_id to speakers.
        This test verifies politicians can be created without speakers.
        """
        # Ensure a party exists
        from src.domain.entities.political_party import PoliticalParty

        party = PoliticalParty(id=1, name="テスト政党")
        created_party = await political_party_repository.create(party)

        # Create politician without speaker
        politician = Politician(
            name="テスト太郎",
            political_party_id=created_party.id,
            district="東京1区",
            profile_page_url="https://example.com/test",
        )

        # Save to database using repository
        from src.infrastructure.persistence.politician_repository_impl import (
            PoliticianRepositoryImpl,
        )

        politician_repo = PoliticianRepositoryImpl(async_session)
        saved_politician = await politician_repo.create(politician)

        # Assertions
        assert saved_politician is not None
        assert saved_politician.id is not None
        assert saved_politician.name == "テスト太郎"
        assert saved_politician.political_party_id == created_party.id

        # Verify politician was persisted
        await async_session.commit()
        fetched = await politician_repo.get_by_id(saved_politician.id)
        assert fetched is not None
        assert fetched.name == "テスト太郎"

    @pytest.mark.asyncio
    async def test_speaker_with_nullable_politician_id(self, async_session):
        """Test creating speaker without politician_id.

        Migration 032 added politician_id to speakers table.
        This column should be nullable to support speakers
        who haven't been matched to politicians yet.
        """
        # Create speaker without politician_id
        speaker = Speaker(
            name="未知の発言者",
            is_politician=False,
        )

        # Save using repository
        from src.infrastructure.persistence.speaker_repository_impl import (
            SpeakerRepositoryImpl,
        )

        speaker_repo = SpeakerRepositoryImpl(async_session)
        saved_speaker = await speaker_repo.create(speaker)

        # Assertions
        assert saved_speaker is not None
        assert saved_speaker.id is not None
        assert saved_speaker.name == "未知の発言者"
        # politician_id should be None (NULL in database)
        assert (
            not hasattr(saved_speaker, "politician_id")
            or saved_speaker.politician_id is None
        )  # noqa: E501

        # Verify persistence
        await async_session.commit()
        fetched = await speaker_repo.find_by_name("未知の発言者")
        assert fetched is not None

    @pytest.mark.asyncio
    async def test_extracted_to_politician_conversion_flow(
        self, async_session, political_party_repository
    ):
        """Test full conversion flow from extracted_politician to politician.

        This end-to-end test verifies:
        1. ExtractedPolitician can be created with minimal data
        2. Conversion to Politician works without speaker
        3. Speaker creation and linkage is optional
        4. Database constraints are satisfied
        """
        # Setup - Create party
        from src.domain.entities.political_party import PoliticalParty

        party = PoliticalParty(id=1, name="テスト政党")
        created_party = await political_party_repository.create(party)

        # Create ExtractedPolitician
        from src.infrastructure.persistence.extracted_politician_repository_impl import (  # noqa: E501
            ExtractedPoliticianRepositoryImpl,
        )

        extracted_repo = ExtractedPoliticianRepositoryImpl(async_session)
        extracted = ExtractedPolitician(
            name="抽出太郎",
            party_id=created_party.id,
            district="大阪2区",
            profile_url="https://example.com/extracted",
            status="approved",
        )
        saved_extracted = await extracted_repo.create(extracted)
        await async_session.commit()

        # Convert to Politician
        from src.infrastructure.persistence.politician_repository_impl import (
            PoliticianRepositoryImpl,
        )

        politician_repo = PoliticianRepositoryImpl(async_session)
        politician = Politician(
            name=saved_extracted.name,
            political_party_id=saved_extracted.party_id,
            district=saved_extracted.district,
            profile_page_url=saved_extracted.profile_url,
        )
        saved_politician = await politician_repo.create(politician)
        await async_session.commit()

        # Update status
        await extracted_repo.update_status(saved_extracted.id, "converted")
        await async_session.commit()

        # Assertions
        assert saved_politician is not None
        assert saved_politician.name == "抽出太郎"
        assert saved_politician.political_party_id == created_party.id

        # Verify extracted politician status
        fetched_extracted = await extracted_repo.get_by_id(saved_extracted.id)
        assert fetched_extracted is not None
        assert fetched_extracted.status == "converted"

    @pytest.mark.asyncio
    async def test_speaker_politician_linkage_after_conversion(
        self, async_session, political_party_repository
    ):
        """Test speaker-politician linkage using new schema.

        Migration 032 changed the relationship:
        - Old: politicians.speaker_id → speakers.id (1-to-1)
        - New: speakers.politician_id → politicians.id (many-to-1)

        This test verifies the new relationship works correctly.
        """
        # Setup - Create party and politician
        from src.domain.entities.political_party import PoliticalParty
        from src.infrastructure.persistence.politician_repository_impl import (
            PoliticianRepositoryImpl,
        )
        from src.infrastructure.persistence.speaker_repository_impl import (
            SpeakerRepositoryImpl,
        )

        party = PoliticalParty(id=1, name="テスト政党")
        created_party = await political_party_repository.create(party)

        politician_repo = PoliticianRepositoryImpl(async_session)
        politician = Politician(
            name="関連太郎",
            political_party_id=created_party.id,
            district="東京1区",
        )
        saved_politician = await politician_repo.create(politician)
        await async_session.commit()

        # Create speaker linked to politician
        speaker_repo = SpeakerRepositoryImpl(async_session)
        speaker = Speaker(
            name="関連太郎",
            is_politician=True,
        )
        saved_speaker = await speaker_repo.create(speaker)

        # Link speaker to politician using raw SQL
        # (since entity might not support it yet)
        from sqlalchemy import text

        await async_session.execute(
            text(
                "UPDATE speakers SET politician_id = :politician_id "
                "WHERE id = :speaker_id"
            ),
            {"politician_id": saved_politician.id, "speaker_id": saved_speaker.id},
        )
        await async_session.commit()

        # Verify linkage
        result = await async_session.execute(
            text("SELECT politician_id FROM speakers WHERE id = :speaker_id"),
            {"speaker_id": saved_speaker.id},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == saved_politician.id

    @pytest.mark.asyncio
    async def test_multiple_speakers_for_one_politician(
        self, async_session, political_party_repository
    ):
        """Test that multiple speakers can reference the same politician.

        This verifies the many-to-1 relationship from migration 032.
        A politician can have multiple speaker representations
        (e.g., different name variations in minutes).
        """
        # Setup
        from src.domain.entities.political_party import PoliticalParty
        from src.infrastructure.persistence.politician_repository_impl import (
            PoliticianRepositoryImpl,
        )
        from src.infrastructure.persistence.speaker_repository_impl import (
            SpeakerRepositoryImpl,
        )

        party = PoliticalParty(id=1, name="テスト政党")
        created_party = await political_party_repository.create(party)

        politician_repo = PoliticianRepositoryImpl(async_session)
        politician = Politician(
            name="山田太郎",
            political_party_id=created_party.id,
        )
        saved_politician = await politician_repo.create(politician)
        await async_session.commit()

        # Create multiple speakers with name variations
        speaker_repo = SpeakerRepositoryImpl(async_session)
        speaker1 = await speaker_repo.create(
            Speaker(name="山田太郎", is_politician=True)
        )
        speaker2 = await speaker_repo.create(
            Speaker(name="山田　太郎", is_politician=True)  # Different spacing
        )
        speaker3 = await speaker_repo.create(
            Speaker(name="やまだたろう", is_politician=True)  # Hiragana
        )
        await async_session.commit()

        # Link all speakers to same politician
        from sqlalchemy import text

        for speaker in [speaker1, speaker2, speaker3]:
            await async_session.execute(
                text(
                    "UPDATE speakers SET politician_id = :politician_id "
                    "WHERE id = :speaker_id"
                ),
                {"politician_id": saved_politician.id, "speaker_id": speaker.id},
            )
        await async_session.commit()

        # Verify all speakers reference the same politician
        result = await async_session.execute(
            text(
                "SELECT id, name, politician_id FROM speakers "
                "WHERE politician_id = :politician_id"
            ),
            {"politician_id": saved_politician.id},
        )
        rows = result.fetchall()
        assert len(rows) == 3
        assert all(row[2] == saved_politician.id for row in rows)
