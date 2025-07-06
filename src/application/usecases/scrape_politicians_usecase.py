"""Use case for scraping politicians from party websites."""

from src.application.dtos.politician_dto import ExtractedPoliticianDTO, PoliticianDTO
from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker
from src.domain.repositories.political_party_repository import PoliticalPartyRepository
from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.repositories.speaker_repository import SpeakerRepository
from src.domain.services.politician_domain_service import PoliticianDomainService
from src.infrastructure.interfaces.web_scraper_service import IWebScraperService


class ScrapePoliticiansUseCase:
    """Use case for scraping politicians from party websites."""

    def __init__(
        self,
        political_party_repository: PoliticalPartyRepository,
        politician_repository: PoliticianRepository,
        speaker_repository: SpeakerRepository,
        politician_domain_service: PoliticianDomainService,
        web_scraper_service: IWebScraperService,
    ):
        self.party_repo = political_party_repository
        self.politician_repo = politician_repository
        self.speaker_repo = speaker_repository
        self.politician_service = politician_domain_service
        self.scraper = web_scraper_service

    async def execute(
        self,
        party_id: int | None = None,
        all_parties: bool = False,
        dry_run: bool = False,
    ) -> list[PoliticianDTO]:
        """Execute the politician scraping use case."""
        # Get parties to scrape
        if party_id:
            party = await self.party_repo.get_by_id(party_id)
            if not party:
                raise ValueError(f"Party {party_id} not found")
            parties = [party] if party.members_list_url else []
        elif all_parties:
            parties = await self.party_repo.get_with_members_url()
        else:
            raise ValueError("Either party_id or all_parties must be specified")

        all_results = []

        for party in parties:
            # Scrape party website
            extracted = await self._scrape_party_website(party)

            if dry_run:
                # Convert to DTOs without saving
                for data in extracted:
                    all_results.append(
                        PoliticianDTO(
                            id=0,  # Not saved
                            name=data.name,
                            speaker_id=0,  # Not created
                            political_party_id=data.party_id,
                            political_party_name=party.name,
                            furigana=data.furigana,
                            position=data.position,
                            district=data.district,
                            profile_image_url=data.profile_image_url,
                            profile_page_url=data.profile_page_url,
                        )
                    )
            else:
                # Save politicians
                for data in extracted:
                    politician_dto = await self._create_or_update_politician(data)
                    if politician_dto:
                        all_results.append(politician_dto)

        return all_results

    async def _scrape_party_website(self, party) -> list[ExtractedPoliticianDTO]:
        """Scrape politicians from party website."""
        if not party.members_list_url:
            return []

        # Use web scraper service
        raw_data = await self.scraper.scrape_party_members(
            party.members_list_url, party.id
        )

        # Convert to DTOs
        extracted = []
        for item in raw_data:
            dto = ExtractedPoliticianDTO(
                name=item["name"],
                party_id=party.id,
                furigana=item.get("furigana"),
                position=item.get("position"),
                district=item.get("district"),
                profile_image_url=item.get("profile_image_url"),
                profile_page_url=item.get("profile_page_url"),
                source_url=party.members_list_url,
            )
            extracted.append(dto)

        return extracted

    async def _create_or_update_politician(
        self, data: ExtractedPoliticianDTO
    ) -> PoliticianDTO | None:
        """Create or update politician from extracted data."""
        # Check for existing politician
        existing = await self.politician_repo.get_by_name_and_party(
            data.name, data.party_id
        )

        if existing:
            # Check if duplicate
            all_politicians = await self.politician_repo.get_by_party(data.party_id)
            duplicate = self.politician_service.is_duplicate_politician(
                Politician(
                    name=data.name,
                    speaker_id=0,  # Temporary
                    political_party_id=data.party_id,
                ),
                all_politicians,
            )

            if duplicate:
                # Update existing if new data
                if any(
                    [
                        data.furigana and not duplicate.furigana,
                        data.position and not duplicate.position,
                        data.district and not duplicate.district,
                        data.profile_image_url and not duplicate.profile_image_url,
                        data.profile_page_url and not duplicate.profile_page_url,
                    ]
                ):
                    merged = self.politician_service.merge_politician_info(
                        duplicate,
                        Politician(
                            name=data.name,
                            speaker_id=duplicate.speaker_id,
                            political_party_id=data.party_id,
                            furigana=data.furigana,
                            position=data.position,
                            district=data.district,
                            profile_image_url=data.profile_image_url,
                            profile_page_url=data.profile_page_url,
                        ),
                    )
                    updated = await self.politician_repo.update(merged)
                    return self._to_dto(updated)
                return None  # Skip duplicate

        # Create new speaker first
        speaker = Speaker(
            name=data.name,
            type="政治家",
            is_politician=True,
        )
        created_speaker = await self.speaker_repo.upsert(speaker)

        # Create politician
        if created_speaker.id is None:
            raise ValueError("Created speaker must have an ID")
        politician = Politician(
            name=data.name,
            speaker_id=created_speaker.id,
            political_party_id=data.party_id,
            furigana=data.furigana,
            position=data.position,
            district=data.district,
            profile_image_url=data.profile_image_url,
            profile_page_url=data.profile_page_url,
        )

        created = await self.politician_repo.create(politician)
        return self._to_dto(created)

    def _to_dto(self, politician: Politician) -> PoliticianDTO:
        """Convert politician entity to DTO."""
        return PoliticianDTO(
            id=politician.id if politician.id is not None else 0,
            name=politician.name,
            speaker_id=politician.speaker_id,
            political_party_id=politician.political_party_id,
            political_party_name=None,  # Would need to fetch
            furigana=politician.furigana,
            position=politician.position,
            district=politician.district,
            profile_image_url=politician.profile_image_url,
            profile_page_url=politician.profile_page_url,
        )
