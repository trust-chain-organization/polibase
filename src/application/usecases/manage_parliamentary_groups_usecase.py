"""Use case for managing parliamentary groups."""

from dataclasses import dataclass
from datetime import date

from src.common.logging import get_logger
from src.domain.entities import ParliamentaryGroup
from src.domain.repositories import ParliamentaryGroupRepository

logger = get_logger(__name__)


@dataclass
class ParliamentaryGroupListInputDto:
    """Input DTO for listing parliamentary groups."""

    conference_id: int | None = None
    active_only: bool = False


@dataclass
class ParliamentaryGroupListOutputDto:
    """Output DTO for listing parliamentary groups."""

    parliamentary_groups: list[ParliamentaryGroup]


@dataclass
class CreateParliamentaryGroupInputDto:
    """Input DTO for creating a parliamentary group."""

    name: str
    conference_id: int
    url: str | None = None
    description: str | None = None
    is_active: bool = True


@dataclass
class CreateParliamentaryGroupOutputDto:
    """Output DTO for creating a parliamentary group."""

    success: bool
    parliamentary_group: ParliamentaryGroup | None = None
    error_message: str | None = None


@dataclass
class UpdateParliamentaryGroupInputDto:
    """Input DTO for updating a parliamentary group."""

    id: int
    name: str
    url: str | None = None
    description: str | None = None
    is_active: bool = True


@dataclass
class UpdateParliamentaryGroupOutputDto:
    """Output DTO for updating a parliamentary group."""

    success: bool
    error_message: str | None = None


@dataclass
class DeleteParliamentaryGroupInputDto:
    """Input DTO for deleting a parliamentary group."""

    id: int


@dataclass
class DeleteParliamentaryGroupOutputDto:
    """Output DTO for deleting a parliamentary group."""

    success: bool
    error_message: str | None = None


@dataclass
class ExtractMembersInputDto:
    """Input DTO for extracting members from URL."""

    parliamentary_group_id: int
    url: str
    confidence_threshold: float = 0.7
    start_date: date | None = None
    dry_run: bool = True


@dataclass
class ExtractedMember:
    """Extracted member information."""

    name: str
    role: str | None = None
    party_name: str | None = None
    district: str | None = None
    additional_info: str | None = None


@dataclass
class MemberMatchingResult:
    """Member matching result."""

    extracted_member: ExtractedMember
    politician_id: int | None = None
    politician_name: str | None = None
    confidence_score: float = 0.0
    matching_reason: str = ""


@dataclass
class ExtractMembersOutputDto:
    """Output DTO for extracting members."""

    success: bool
    extracted_members: list[ExtractedMember] | None = None
    matching_results: list[MemberMatchingResult] | None = None
    created_count: int = 0
    skipped_count: int = 0
    error_message: str | None = None
    errors: list[str] | None = None


@dataclass
class GenerateSeedFileOutputDto:
    """Output DTO for generating seed file."""

    success: bool
    seed_content: str | None = None
    file_path: str | None = None
    error_message: str | None = None


class ManageParliamentaryGroupsUseCase:
    """Use case for managing parliamentary groups."""

    def __init__(self, parliamentary_group_repository: ParliamentaryGroupRepository):
        """Initialize the use case."""
        self.parliamentary_group_repository = parliamentary_group_repository

    def list_parliamentary_groups(
        self, input_dto: ParliamentaryGroupListInputDto
    ) -> ParliamentaryGroupListOutputDto:
        """List parliamentary groups with optional filters."""
        try:
            if input_dto.conference_id:
                groups = self.parliamentary_group_repository.get_by_conference_id(
                    input_dto.conference_id, input_dto.active_only
                )
            else:
                groups = self.parliamentary_group_repository.get_all()
                if input_dto.active_only:
                    groups = [g for g in groups if g.is_active]

            return ParliamentaryGroupListOutputDto(parliamentary_groups=groups)
        except Exception as e:
            logger.error(f"Failed to list parliamentary groups: {e}")
            raise

    def create_parliamentary_group(
        self, input_dto: CreateParliamentaryGroupInputDto
    ) -> CreateParliamentaryGroupOutputDto:
        """Create a new parliamentary group."""
        try:
            # Check for duplicates
            existing = self.parliamentary_group_repository.get_by_name_and_conference(
                input_dto.name, input_dto.conference_id
            )
            if existing:
                return CreateParliamentaryGroupOutputDto(
                    success=False,
                    error_message="同じ名前の議員団が既に存在します。",
                )

            # Create new parliamentary group
            parliamentary_group = ParliamentaryGroup(
                id=0,  # Will be assigned by database
                name=input_dto.name,
                conference_id=input_dto.conference_id,
                url=input_dto.url,
                description=input_dto.description,
                is_active=input_dto.is_active,
            )

            created = self.parliamentary_group_repository.create(parliamentary_group)
            return CreateParliamentaryGroupOutputDto(
                success=True, parliamentary_group=created
            )
        except Exception as e:
            logger.error(f"Failed to create parliamentary group: {e}")
            return CreateParliamentaryGroupOutputDto(
                success=False, error_message=str(e)
            )

    def update_parliamentary_group(
        self, input_dto: UpdateParliamentaryGroupInputDto
    ) -> UpdateParliamentaryGroupOutputDto:
        """Update an existing parliamentary group."""
        try:
            # Get existing parliamentary group
            existing = self.parliamentary_group_repository.get_by_id(input_dto.id)
            if not existing:
                return UpdateParliamentaryGroupOutputDto(
                    success=False, error_message="議員団が見つかりません。"
                )

            # Update fields
            existing.name = input_dto.name
            existing.url = input_dto.url
            existing.description = input_dto.description
            existing.is_active = input_dto.is_active

            self.parliamentary_group_repository.update(existing)
            return UpdateParliamentaryGroupOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to update parliamentary group: {e}")
            return UpdateParliamentaryGroupOutputDto(
                success=False, error_message=str(e)
            )

    def delete_parliamentary_group(
        self, input_dto: DeleteParliamentaryGroupInputDto
    ) -> DeleteParliamentaryGroupOutputDto:
        """Delete a parliamentary group."""
        try:
            # Check if parliamentary group exists
            existing = self.parliamentary_group_repository.get_by_id(input_dto.id)
            if not existing:
                return DeleteParliamentaryGroupOutputDto(
                    success=False, error_message="議員団が見つかりません。"
                )

            # Check if it's active
            if existing.is_active:
                return DeleteParliamentaryGroupOutputDto(
                    success=False,
                    error_message="活動中の議員団は削除できません。先に非活動にしてください。",
                )

            # TODO: Check if it has members
            # This would require a membership repository

            self.parliamentary_group_repository.delete(input_dto.id)
            return DeleteParliamentaryGroupOutputDto(success=True)
        except Exception as e:
            logger.error(f"Failed to delete parliamentary group: {e}")
            return DeleteParliamentaryGroupOutputDto(
                success=False, error_message=str(e)
            )

    def extract_members(
        self, input_dto: ExtractMembersInputDto
    ) -> ExtractMembersOutputDto:
        """Extract members from parliamentary group URL."""
        try:
            # This would integrate with the parliamentary group member extractor
            # For now, return a placeholder
            return ExtractMembersOutputDto(
                success=False,
                error_message="メンバー抽出機能は現在実装中です。",
            )
        except Exception as e:
            logger.error(f"Failed to extract members: {e}")
            return ExtractMembersOutputDto(success=False, error_message=str(e))

    def generate_seed_file(self) -> GenerateSeedFileOutputDto:
        """Generate seed file for parliamentary groups."""
        try:
            # Get all parliamentary groups
            all_groups = self.parliamentary_group_repository.get_all()

            # Generate SQL content
            seed_content = "-- Parliamentary Groups Seed Data\n"
            seed_content += "-- Generated from current database\n\n"
            seed_content += (
                "INSERT INTO parliamentary_groups "
                "(id, name, conference_id, url, description, is_active) VALUES\n"
            )

            values = []
            for group in all_groups:
                url = f"'{group.url}'" if group.url else "NULL"
                description = f"'{group.description}'" if group.description else "NULL"
                is_active = "true" if group.is_active else "false"
                values.append(
                    f"    ({group.id}, '{group.name}', {group.conference_id}, "
                    f"{url}, {description}, {is_active})"
                )

            seed_content += ",\n".join(values) + "\n"
            seed_content += "ON CONFLICT (id) DO UPDATE SET\n"
            seed_content += "    name = EXCLUDED.name,\n"
            seed_content += "    conference_id = EXCLUDED.conference_id,\n"
            seed_content += "    url = EXCLUDED.url,\n"
            seed_content += "    description = EXCLUDED.description,\n"
            seed_content += "    is_active = EXCLUDED.is_active;\n"

            # Save to file
            file_path = "database/seed_parliamentary_groups_generated.sql"
            with open(file_path, "w") as f:
                f.write(seed_content)

            return GenerateSeedFileOutputDto(
                success=True, seed_content=seed_content, file_path=file_path
            )
        except Exception as e:
            logger.error(f"Failed to generate seed file: {e}")
            return GenerateSeedFileOutputDto(success=False, error_message=str(e))
