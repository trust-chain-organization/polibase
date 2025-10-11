"""Use case for managing political parties.

This module provides use cases for political party management including
listing, updating URLs, and generating seed files.
"""

from dataclasses import dataclass

from src.common.logging import get_logger
from src.domain.entities.political_party import PoliticalParty
from src.domain.repositories.political_party_repository import PoliticalPartyRepository
from src.seed_generator import SeedGenerator


@dataclass
class PoliticalPartyListInputDto:
    """Input DTO for listing political parties."""

    filter_type: str | None = None  # 'all', 'with_url', 'without_url'
    order_by: str = "name"


@dataclass
class PoliticalPartyStatistics:
    """Statistics for political parties."""

    total: int
    with_url: int
    without_url: int

    @property
    def with_url_percentage(self) -> float:
        """Calculate percentage of parties with URL."""
        if self.total == 0:
            return 0.0
        return (self.with_url / self.total) * 100

    @property
    def without_url_percentage(self) -> float:
        """Calculate percentage of parties without URL."""
        if self.total == 0:
            return 0.0
        return (self.without_url / self.total) * 100


@dataclass
class PoliticalPartyListOutputDto:
    """Output DTO for listing political parties."""

    parties: list[PoliticalParty]
    statistics: PoliticalPartyStatistics


@dataclass
class UpdatePoliticalPartyUrlInputDto:
    """Input DTO for updating political party URL."""

    party_id: int
    members_list_url: str | None


@dataclass
class UpdatePoliticalPartyUrlOutputDto:
    """Output DTO for updating political party URL."""

    success: bool
    message: str
    party: PoliticalParty | None = None


@dataclass
class GenerateSeedFileOutputDto:
    """Output DTO for generating seed file."""

    success: bool
    message: str
    content: str | None = None
    file_path: str | None = None


class ManagePoliticalPartiesUseCase:
    """Use case for managing political parties."""

    def __init__(self, repository: PoliticalPartyRepository):
        """Initialize the use case.

        Args:
            repository: Political party repository (can be sync or async)
        """
        self.repository = repository
        self.logger = get_logger(self.__class__.__name__)

    def list_parties(
        self, input_dto: PoliticalPartyListInputDto
    ) -> PoliticalPartyListOutputDto:
        """List political parties with optional filtering.

        Args:
            input_dto: Input parameters for listing

        Returns:
            Output DTO with parties and statistics
        """
        try:
            # Get all parties
            all_parties = self.repository.get_all()
            # Sort by name
            all_parties.sort(key=lambda p: p.name or "")

            # Calculate statistics
            total = len(all_parties)
            with_url = sum(1 for p in all_parties if p.members_list_url)
            without_url = total - with_url

            statistics = PoliticalPartyStatistics(
                total=total, with_url=with_url, without_url=without_url
            )

            # Filter parties based on filter_type
            if input_dto.filter_type == "with_url":
                filtered_parties = [p for p in all_parties if p.members_list_url]
            elif input_dto.filter_type == "without_url":
                filtered_parties = [p for p in all_parties if not p.members_list_url]
            else:
                filtered_parties = all_parties

            return PoliticalPartyListOutputDto(
                parties=filtered_parties, statistics=statistics
            )

        except Exception as e:
            self.logger.error(f"Error listing political parties: {e}", exc_info=True)
            raise

    def update_party_url(
        self, input_dto: UpdatePoliticalPartyUrlInputDto
    ) -> UpdatePoliticalPartyUrlOutputDto:
        """Update political party members list URL.

        Args:
            input_dto: Input parameters for updating

        Returns:
            Output DTO with result
        """
        try:
            # Get the party
            party = self.repository.get_by_id(input_dto.party_id)
            if not party:
                return UpdatePoliticalPartyUrlOutputDto(
                    success=False,
                    message=f"政党ID {input_dto.party_id} が見つかりません",
                )

            # Update the URL
            party.members_list_url = input_dto.members_list_url
            updated_party = self.repository.update(party)
            return UpdatePoliticalPartyUrlOutputDto(
                success=True, message="URLを更新しました", party=updated_party
            )

        except Exception as e:
            self.logger.error(f"Error updating party URL: {e}", exc_info=True)
            return UpdatePoliticalPartyUrlOutputDto(
                success=False, message=f"更新中にエラーが発生しました: {str(e)}"
            )

    def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """Generate seed file for political parties.

        Returns:
            Output DTO with seed file content
        """
        try:
            # Generate seed content using existing SeedGenerator
            # Note: SeedGenerator fetches data directly from database
            generator = SeedGenerator()
            content = generator.generate_political_parties_seed()

            # Note: File saving should be handled by infrastructure layer
            # For now, we return the content and let the presenter handle display

            return GenerateSeedFileOutputDto(
                success=True, message="SEEDファイルを生成しました", content=content
            )

        except Exception as e:
            self.logger.error(f"Error generating seed file: {e}", exc_info=True)
            return GenerateSeedFileOutputDto(
                success=False, message=f"生成中にエラーが発生しました: {str(e)}"
            )
