"""Use case for matching speakers to politicians."""

from src.application.dtos.speaker_dto import SpeakerMatchingDTO
from src.domain.repositories.conversation_repository import ConversationRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.speaker_domain_service import SpeakerDomainService


class MatchSpeakersUseCase:
    """Use case for matching speakers to politicians."""

    def __init__(
        self,
        speaker_repository: SpeakerRepository,
        politician_repository: PoliticianRepository,
        conversation_repository: ConversationRepository,
        speaker_domain_service: SpeakerDomainService,
        llm_service,  # External service interface
    ):
        self.speaker_repo = speaker_repository
        self.politician_repo = politician_repository
        self.conversation_repo = conversation_repository
        self.speaker_service = speaker_domain_service
        self.llm_service = llm_service

    async def execute(
        self,
        use_llm: bool = True,
        speaker_ids: list[int] | None = None,
        limit: int | None = None,
    ) -> list[SpeakerMatchingDTO]:
        """Execute the speaker matching use case."""
        # Get speakers to process
        if speaker_ids:
            speakers = []
            for speaker_id in speaker_ids:
                speaker = await self.speaker_repo.get_by_id(speaker_id)
                if speaker:
                    speakers.append(speaker)
        else:
            # Get all politician speakers
            speakers = await self.speaker_repo.get_politicians()
            if limit:
                speakers = speakers[:limit]

        results = []

        for speaker in speakers:
            # Skip if already linked
            existing_politician = await self.politician_repo.get_by_speaker_id(
                speaker.id
            )
            if existing_politician:
                results.append(
                    SpeakerMatchingDTO(
                        speaker_id=speaker.id,
                        speaker_name=speaker.name,
                        matched_politician_id=existing_politician.id,
                        matched_politician_name=existing_politician.name,
                        confidence_score=1.0,
                        matching_method="existing",
                    )
                )
                continue

            # Try rule-based matching first
            match_result = await self._rule_based_matching(speaker)

            if not match_result and use_llm:
                # Try LLM-based matching
                match_result = await self._llm_based_matching(speaker)

            if match_result:
                results.append(match_result)
            else:
                # No match found
                results.append(
                    SpeakerMatchingDTO(
                        speaker_id=speaker.id,
                        speaker_name=speaker.name,
                        matched_politician_id=None,
                        matched_politician_name=None,
                        confidence_score=0.0,
                        matching_method="none",
                    )
                )

        return results

    async def _rule_based_matching(self, speaker) -> SpeakerMatchingDTO | None:
        """Perform rule-based speaker matching."""
        # Normalize speaker name
        normalized_name = self.speaker_service.normalize_speaker_name(speaker.name)

        # Search for politicians with similar names
        candidates = await self.politician_repo.search_by_name(normalized_name)

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            # Calculate similarity
            score = self.speaker_service.calculate_name_similarity(
                speaker.name, candidate.name
            )

            # Boost score if party matches
            if speaker.political_party_name and candidate.political_party_id:
                # Would need to lookup party name
                score += 0.1

            if score > best_score and score >= 0.8:
                best_match = candidate
                best_score = score

        if best_match:
            return SpeakerMatchingDTO(
                speaker_id=speaker.id,
                speaker_name=speaker.name,
                matched_politician_id=best_match.id,
                matched_politician_name=best_match.name,
                confidence_score=best_score,
                matching_method="rule-based",
            )

        return None

    async def _llm_based_matching(self, speaker) -> SpeakerMatchingDTO | None:
        """Perform LLM-based speaker matching."""
        # Get potential candidates
        candidates = await self.politician_repo.get_all(limit=100)

        if not candidates:
            return None

        # Prepare context for LLM
        context = {
            "speaker_name": speaker.name,
            "speaker_party": speaker.political_party_name,
            "speaker_position": speaker.position,
            "candidates": [
                {
                    "id": c.id,
                    "name": c.name,
                    "party_id": c.political_party_id,
                    "position": c.position,
                }
                for c in candidates
            ],
        }

        # Call LLM service
        match_result = await self.llm_service.match_speaker_to_politician(context)

        if match_result and match_result.get("politician_id"):
            politician = await self.politician_repo.get_by_id(
                match_result["politician_id"]
            )

            if politician:
                return SpeakerMatchingDTO(
                    speaker_id=speaker.id,
                    speaker_name=speaker.name,
                    matched_politician_id=politician.id,
                    matched_politician_name=politician.name,
                    confidence_score=match_result.get("confidence", 0.8),
                    matching_method="llm",
                )

        return None
