"""Speaker domain service for handling speaker-related business logic."""

from src.domain.entities.politician import Politician
from src.domain.entities.speaker import Speaker


class SpeakerDomainService:
    """Domain service for speaker-related business logic."""

    def normalize_speaker_name(self, name: str) -> str:
        """Normalize speaker name for matching."""
        # Remove honorifics and extra spaces
        honorifics = ["議員", "君", "さん", "氏", "先生", "委員長", "議長"]
        normalized = name.strip()
        for honorific in honorifics:
            normalized = normalized.replace(honorific, "")
        return normalized.strip()

    def extract_party_from_name(self, speaker_name: str) -> tuple[str, str | None]:
        """Extract party name from speaker name if included."""
        # Pattern: "名前（党名）" or "名前（役職・党名）"
        import re

        match = re.search(r"（([^）]+)）", speaker_name)
        if match:
            content = match.group(1)
            # Clean the name
            clean_name = speaker_name[: match.start()].strip()
            return clean_name, content
        return speaker_name, None

    def is_likely_politician(self, speaker: Speaker) -> bool:
        """Determine if a speaker is likely a politician based on attributes."""
        politician_indicators = [
            speaker.is_politician,
            speaker.political_party_name is not None,
            speaker.type == "政治家",
            "議員" in (speaker.position or ""),
        ]
        return any(politician_indicators)

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names."""
        norm1 = self.normalize_speaker_name(name1)
        norm2 = self.normalize_speaker_name(name2)

        if norm1 == norm2:
            return 1.0

        # Simple character-based similarity
        common_chars = set(norm1) & set(norm2)
        if not common_chars:
            return 0.0

        return len(common_chars) / max(len(set(norm1)), len(set(norm2)))

    def merge_speaker_info(self, existing: Speaker, new_info: Speaker) -> Speaker:
        """Merge new speaker information with existing speaker."""
        # Keep existing ID
        merged = Speaker(
            name=existing.name,
            type=new_info.type or existing.type,
            political_party_name=new_info.political_party_name
            or existing.political_party_name,
            position=new_info.position or existing.position,
            is_politician=new_info.is_politician or existing.is_politician,
            id=existing.id,
        )
        return merged

    def validate_speaker_politician_link(
        self, speaker: Speaker, politician: Politician
    ) -> bool:
        """Validate if a speaker can be linked to a politician."""
        # Names should be similar
        similarity = self.calculate_name_similarity(speaker.name, politician.name)
        if similarity < 0.7:
            return False

        # If speaker has party info, it should match
        if speaker.political_party_name and politician.political_party_id:
            # This would need party name lookup in real implementation
            # For now, we assume it's valid
            pass

        return True
