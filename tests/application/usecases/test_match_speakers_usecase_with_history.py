"""Tests for MatchSpeakersUseCase with LLM history recording."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.application.usecases.match_speakers_usecase import MatchSpeakersUseCase
from src.domain.entities import Politician, Speaker
from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.domain.repositories import (
    ConversationRepository,
    PoliticianRepository,
    SpeakerRepository,
)
from src.domain.services import SpeakerDomainService
from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.infrastructure.interfaces.llm_service import ILLMService


class TestMatchSpeakersUseCaseWithHistory:
    """Test cases for MatchSpeakersUseCase with history recording."""

    @pytest.fixture
    def mock_speaker_repo(self) -> AsyncMock:
        """Create mock speaker repository."""
        return AsyncMock(spec=SpeakerRepository)

    @pytest.fixture
    def mock_politician_repo(self) -> AsyncMock:
        """Create mock politician repository."""
        return AsyncMock(spec=PoliticianRepository)

    @pytest.fixture
    def mock_conversation_repo(self) -> AsyncMock:
        """Create mock conversation repository."""
        return AsyncMock(spec=ConversationRepository)

    @pytest.fixture
    def mock_speaker_service(self) -> MagicMock:
        """Create mock speaker domain service."""
        service = MagicMock(spec=SpeakerDomainService)
        service.normalize_speaker_name.return_value = "normalized_name"
        service.calculate_name_similarity.return_value = 0.9
        return service

    @pytest.fixture
    def mock_base_llm_service(self) -> AsyncMock:
        """Create mock base LLM service."""
        service = AsyncMock(spec=ILLMService)
        service.temperature = 0.1
        service.model_name = "gemini-2.0-flash"
        service.match_speaker_to_politician = AsyncMock(
            return_value={
                "matched_id": 1,
                "confidence": 0.95,
                "reason": "High name similarity and matching party affiliation",
            }
        )
        return service

    @pytest.fixture
    def mock_history_repo(self) -> AsyncMock:
        """Create mock history repository."""
        repo = AsyncMock()
        repo.create = AsyncMock(
            return_value=LLMProcessingHistory(
                processing_type=ProcessingType.SPEAKER_MATCHING,
                status=ProcessingStatus.COMPLETED,
                model_name="gemini-2.0-flash",
                model_version="2.0",
                prompt_template="speaker_matching",
                prompt_variables={"speaker_name": "山田太郎"},
                input_reference_type="speaker",
                input_reference_id=1,
                result={"matched_id": 1, "confidence": 0.95},
            )
        )
        return repo

    @pytest.fixture
    def instrumented_llm_service(
        self, mock_base_llm_service: AsyncMock, mock_history_repo: AsyncMock
    ) -> InstrumentedLLMService:
        """Create instrumented LLM service with history recording."""
        return InstrumentedLLMService(
            llm_service=mock_base_llm_service,
            history_repository=mock_history_repo,
            model_name="gemini-2.0-flash",
            model_version="2.0",
        )

    @pytest.fixture
    def use_case(
        self,
        mock_speaker_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_conversation_repo: AsyncMock,
        mock_speaker_service: MagicMock,
        instrumented_llm_service: InstrumentedLLMService,
    ) -> MatchSpeakersUseCase:
        """Create MatchSpeakersUseCase with all dependencies."""
        return MatchSpeakersUseCase(
            speaker_repository=mock_speaker_repo,
            politician_repository=mock_politician_repo,
            conversation_repository=mock_conversation_repo,
            speaker_domain_service=mock_speaker_service,
            llm_service=instrumented_llm_service,
        )

    @pytest.mark.asyncio
    async def test_llm_matching_records_history(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_history_repo: AsyncMock,
    ):
        """Test that LLM-based matching records history."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="山田太郎",
            political_party_name="自民党",
            position="議員",
        )

        politician = Politician(
            id=1,
            name="山田太郎",
            speaker_id=1,
            political_party_id=1,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.get_by_speaker_id.return_value = None
        mock_politician_repo.search_by_name.return_value = []  # No rule-based match
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id == 1
        assert result.confidence_score == 0.95
        assert result.matching_method == "llm"
        assert (
            result.matching_reason
            == "High name similarity and matching party affiliation"
        )

        # Verify history was recorded
        mock_history_repo.create.assert_called_once()
        history_call = mock_history_repo.create.call_args[0][0]
        assert history_call.processing_type == ProcessingType.SPEAKER_MATCHING
        assert history_call.status == ProcessingStatus.COMPLETED
        assert history_call.model_name == "gemini-2.0-flash"

    @pytest.mark.asyncio
    async def test_rule_based_matching_no_history(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_history_repo: AsyncMock,
    ):
        """Test that rule-based matching doesn't record LLM history."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="山田太郎",
            political_party_name="自民党",
        )

        politician = Politician(
            id=1,
            name="山田太郎",
            speaker_id=1,
            political_party_id=1,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.get_by_speaker_id.return_value = None
        mock_politician_repo.search_by_name.return_value = [
            politician
        ]  # Rule-based match found

        # Act
        results = await use_case.execute(use_llm=False)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id == 1
        assert result.matching_method == "rule-based"

        # Verify history was NOT recorded (rule-based doesn't use LLM)
        mock_history_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_input_reference_called(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        instrumented_llm_service: InstrumentedLLMService,
    ):
        """Test that set_input_reference is called when LLM matching is used."""
        # Arrange
        speaker = Speaker(
            id=123,
            name="佐藤花子",
            political_party_name="立憲民主党",
        )

        politician = Politician(
            id=456,
            name="佐藤花子",
            speaker_id=123,
            political_party_id=2,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.get_by_speaker_id.return_value = None
        mock_politician_repo.search_by_name.return_value = []  # No rule-based match
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        # Spy on set_input_reference
        with patch.object(
            instrumented_llm_service, "set_input_reference"
        ) as mock_set_ref:
            # Act
            await use_case.execute(use_llm=True)

            # Assert
            mock_set_ref.assert_called_once_with(
                reference_type="speaker",
                reference_id=123,
            )

    @pytest.mark.asyncio
    async def test_matching_with_no_candidates(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_history_repo: AsyncMock,
    ):
        """Test matching when no politician candidates are available."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="新人議員",
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.get_by_speaker_id.return_value = None
        mock_politician_repo.search_by_name.return_value = []
        mock_politician_repo.get_all.return_value = []  # No candidates

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id is None
        assert result.confidence_score == 0.0
        assert result.matching_method == "none"
        assert result.matching_reason == "No matching politician found"

        # Verify history was NOT recorded (no LLM call made)
        mock_history_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_history_recording_failure_doesnt_break_matching(
        self,
        use_case: MatchSpeakersUseCase,
        mock_speaker_repo: AsyncMock,
        mock_politician_repo: AsyncMock,
        mock_history_repo: AsyncMock,
    ):
        """Test that history recording failure doesn't break the matching process."""
        # Arrange
        speaker = Speaker(
            id=1,
            name="エラーテスト議員",
        )

        politician = Politician(
            id=1,
            name="エラーテスト議員",
            speaker_id=1,
        )

        mock_speaker_repo.get_politicians.return_value = [speaker]
        mock_politician_repo.get_by_speaker_id.return_value = None
        mock_politician_repo.search_by_name.return_value = []
        mock_politician_repo.get_all.return_value = [politician]
        mock_politician_repo.get_by_id.return_value = politician

        # Make history recording fail
        mock_history_repo.create.side_effect = Exception("Database error")

        # Act
        results = await use_case.execute(use_llm=True)

        # Assert - matching should still succeed
        assert len(results) == 1
        result = results[0]
        assert result.speaker_id == 1
        assert result.matched_politician_id == 1
        assert result.confidence_score == 0.95
        assert result.matching_method == "llm"
