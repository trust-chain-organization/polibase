"""Use case for managing conference members."""

from datetime import date
from typing import Any, Protocol

from src.application.dtos.conference_dto import (
    ConferenceMemberMatchingDTO,
    CreateAffiliationDTO,
    ExtractedConferenceMemberDTO,
)
from src.domain.repositories.conference_repository import ConferenceRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.conference_domain_service import ConferenceDomainService
from src.infrastructure.interfaces.llm_service import ILLMService
from src.infrastructure.interfaces.web_scraper_service import IWebScraperService


# Protocol for external repositories
class ExtractedMemberEntity:
    """Minimal entity for extracted member."""

    id: int
    name: str
    conference_id: int
    party_affiliation: str | None
    role: str | None
    matching_status: str
    matched_politician_id: int | None
    confidence_score: float | None


class ExtractedMemberRepository(Protocol):
    """Protocol for extracted member repository."""

    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedMemberEntity]:
        """Get extracted members by conference."""
        ...

    async def get_pending_by_conference(
        self, conference_id: int
    ) -> list[ExtractedMemberEntity]:
        """Get pending extracted members by conference."""
        ...

    async def get_all_pending(self) -> list[ExtractedMemberEntity]:
        """Get all pending extracted members."""
        ...

    async def get_by_conference_and_status(
        self, conference_id: int, status: str | None
    ) -> list[ExtractedMemberEntity]:
        """Get extracted members by conference and status."""
        ...

    async def get_by_status(self, status: str | None) -> list[ExtractedMemberEntity]:
        """Get extracted members by status."""
        ...

    async def create(
        self, member: ExtractedConferenceMemberDTO
    ) -> ExtractedMemberEntity:
        """Create extracted member."""
        ...

    async def update(
        self, member_id: int, data: dict[str, Any]
    ) -> ExtractedMemberEntity:
        """Update extracted member."""
        ...

    async def update_matching_status(
        self,
        member_id: int,
        status: str,
        matched_politician_id: int | None,
        confidence_score: float,
    ) -> None:
        """Update member matching status."""
        ...

    async def mark_processed(self, member_id: int) -> None:
        """Mark member as processed."""
        ...


class AffiliationEntity:
    """Minimal entity for affiliation."""

    id: int
    politician_id: int
    conference_id: int
    start_date: date
    end_date: date | None
    role: str | None


class AffiliationRepository(Protocol):
    """Protocol for affiliation repository."""

    async def create(self, affiliation: CreateAffiliationDTO) -> AffiliationEntity:
        """Create affiliation."""
        ...

    async def get_by_politician_and_conference(
        self, politician_id: int, conference_id: int
    ) -> list[AffiliationEntity]:
        """Get affiliations by politician and conference."""
        ...


class ManageConferenceMembersUseCase:
    """Use case for managing conference members."""

    def __init__(
        self,
        conference_repository: ConferenceRepository,
        politician_repository: PoliticianRepository,
        conference_domain_service: ConferenceDomainService,
        extracted_member_repository: ExtractedMemberRepository,
        affiliation_repository: AffiliationRepository,
        web_scraper_service: IWebScraperService,
        llm_service: ILLMService,
    ):
        self.conference_repo = conference_repository
        self.politician_repo = politician_repository
        self.conference_service = conference_domain_service
        self.extracted_repo = extracted_member_repository
        self.affiliation_repo = affiliation_repository
        self.scraper = web_scraper_service
        self.llm = llm_service

    async def extract_members(
        self,
        conference_id: int,
        force: bool = False,
    ) -> list[ExtractedConferenceMemberDTO]:
        """Extract conference members from web."""
        # Get conference
        conference = await self.conference_repo.get_by_id(conference_id)
        if not conference:
            raise ValueError(f"Conference {conference_id} not found")

        if not conference.members_introduction_url:
            raise ValueError(
                f"Conference {conference_id} has no members introduction URL"
            )

        # Check if already extracted
        if not force:
            existing = await self.extracted_repo.get_by_conference(conference_id)
            if existing:
                return [self._to_extracted_dto(m) for m in existing]

        # Scrape members
        raw_members = await self.scraper.scrape_conference_members(
            conference.members_introduction_url
        )

        # Save to staging table
        extracted: list[ExtractedConferenceMemberDTO] = []
        for raw in raw_members:
            member = ExtractedConferenceMemberDTO(
                name=raw["name"],
                conference_id=conference_id,
                party_name=raw.get("party"),
                role=self.conference_service.extract_member_role(raw.get("role", "")),
                profile_url=raw.get("profile_url"),
            )

            # Save to staging
            saved = await self.extracted_repo.create(member)
            extracted.append(self._to_extracted_dto(saved))

        return extracted

    async def match_members(
        self,
        conference_id: int | None = None,
        threshold: float = 0.7,
    ) -> list[ConferenceMemberMatchingDTO]:
        """Match extracted members with politicians."""
        # Get pending members
        if conference_id:
            members = await self.extracted_repo.get_pending_by_conference(conference_id)
        else:
            members = await self.extracted_repo.get_all_pending()

        results: list[ConferenceMemberMatchingDTO] = []

        for member in members:
            # Try to find matching politician
            match_result = await self._match_member_to_politician(member, threshold)
            results.append(match_result)

            # Update status in staging table
            await self.extracted_repo.update_matching_status(
                member.id,
                match_result.status,
                match_result.matched_politician_id,
                match_result.confidence_score,
            )

        return results

    async def create_affiliations(
        self,
        conference_id: int | None = None,
        start_date: date | None = None,
        only_matched: bool = True,
    ) -> list[CreateAffiliationDTO]:
        """Create affiliations from matched members."""
        # Get members to process
        if conference_id:
            members = await self.extracted_repo.get_by_conference_and_status(
                conference_id, "matched" if only_matched else None
            )
        else:
            members = await self.extracted_repo.get_by_status(
                "matched" if only_matched else None
            )

        if not start_date:
            start_date = date.today()

        created: list[CreateAffiliationDTO] = []

        for member in members:
            if not member.matched_politician_id:
                continue

            # Check for existing affiliation
            existing = await self.affiliation_repo.get_by_politician_and_conference(
                member.matched_politician_id, member.conference_id
            )

            if existing:
                # Check for overlap
                overlaps = [
                    a
                    for a in existing
                    if self.conference_service.calculate_affiliation_overlap(
                        start_date, None, a.start_date, a.end_date
                    )
                ]

                if overlaps:
                    continue  # Skip if overlapping affiliation exists

            # Create affiliation
            affiliation = CreateAffiliationDTO(
                politician_id=member.matched_politician_id,
                conference_id=member.conference_id,
                start_date=start_date,
                end_date=None,
                role=member.role,
            )

            await self.affiliation_repo.create(affiliation)
            created.append(affiliation)

            # Mark member as processed
            await self.extracted_repo.mark_processed(member.id)

        return created

    async def _match_member_to_politician(
        self, member: ExtractedMemberEntity, threshold: float
    ) -> ConferenceMemberMatchingDTO:
        """Match a single member to a politician."""
        # Normalize party name
        normalized_party = self.conference_service.normalize_party_name(
            member.party_affiliation or ""
        )

        # Search for candidates
        candidates = await self.politician_repo.search_by_name(member.name)

        if not candidates:
            # Try LLM matching with broader search
            # Search more broadly for politicians
            all_politicians = await self.politician_repo.get_all()
            politician_dtos = [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "party": p.political_party.name if p.political_party else None,
                }
                for p in all_politicians
            ]

            llm_result = await self.llm.match_conference_member(
                member.name,
                normalized_party,
                politician_dtos,
            )

            if llm_result and llm_result["confidence"] >= threshold:
                # Get politician details if matched
                politician = None
                if llm_result["matched_id"]:
                    politician = await self.politician_repo.get_by_id(
                        llm_result["matched_id"]
                    )

                return ConferenceMemberMatchingDTO(
                    extracted_member_id=member.id,
                    member_name=member.name,
                    matched_politician_id=llm_result["matched_id"],
                    matched_politician_name=politician.name if politician else None,
                    confidence_score=llm_result["confidence"],
                    status="matched"
                    if llm_result["confidence"] >= 0.7
                    else "needs_review",
                )

        # Calculate best match
        best_match = None
        best_score = 0.0

        for candidate in candidates:
            # Calculate confidence score
            party_match = False  # Would need party name lookup
            role_match = (
                False  # Candidate doesn't have position attribute in base entity
            )

            score = self.conference_service.calculate_member_confidence_score(
                member.name,
                candidate.name,
                party_match,
                role_match,
            )

            if score > best_score:
                best_match = candidate
                best_score = score

        if best_match and best_score >= threshold:
            status = "matched" if best_score >= 0.7 else "needs_review"
        else:
            status = "no_match"

        return ConferenceMemberMatchingDTO(
            extracted_member_id=member.id,
            member_name=member.name,
            matched_politician_id=best_match.id if best_match else None,
            matched_politician_name=best_match.name if best_match else None,
            confidence_score=best_score,
            status=status,
        )

    def _to_extracted_dto(
        self, entity: ExtractedMemberEntity
    ) -> ExtractedConferenceMemberDTO:
        """Convert entity to DTO."""
        return ExtractedConferenceMemberDTO(
            name=entity.name,
            conference_id=entity.conference_id,
            party_name=entity.party_affiliation,
            role=entity.role,
            profile_url=None,  # Not available in ExtractedMemberEntity
        )
