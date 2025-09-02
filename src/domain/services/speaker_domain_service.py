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

        # First extract actual person name from title if present
        speaker_name = self.extract_person_name_from_title(speaker_name)

        match = re.search(r"（([^）]+)）", speaker_name)
        if match:
            content = match.group(1)
            # Clean the name
            clean_name = speaker_name[: match.start()].strip()
            return clean_name, content
        return speaker_name, None

    def extract_person_name_from_title(self, speaker_name: str) -> str:
        """Extract actual person name from title-based speaker name.

        Examples:
            "議長 (西村義直)" -> "西村義直"
            "委員長 (田中太郎)" -> "田中太郎"
            "議長" -> "議長" (no change if no name found)
            "(「異議なし」と呼ぶ者あり)" -> "(「異議なし」と呼ぶ者あり)" (no change for non-person entries)
        """
        import re

        # 役職名のパターン
        title_patterns = [
            r"^(議長|委員長|副議長|副委員長|委員|議員|理事|監事|会長|副会長|事務局長|局長|部長|課長|係長|主査|主任|主事)",
            r"^(市長|副市長|町長|副町長|村長|副村長|知事|副知事)",
            r"^(教育長|教育委員長|農業委員長|選挙管理委員長|監査委員)",
        ]

        # スペース＋括弧内の人名を探す (例: "議長 (西村義直)")
        match = re.search(r"^\S+\s+[（\(]([^）\)]+)[）\)]", speaker_name)
        if match:
            name_in_parentheses = match.group(1)

            # 役職名パターンにマッチする場合
            for pattern in title_patterns:
                if re.match(pattern, speaker_name):
                    # 括弧内が人名らしい場合（発言や注釈は除外）
                    if (
                        not name_in_parentheses.startswith("「")
                        and not name_in_parentheses.endswith("」")
                        and "呼ぶ者あり" not in name_in_parentheses
                        and "異議" not in name_in_parentheses
                        and "拍手" not in name_in_parentheses
                        and "する者あり" not in name_in_parentheses
                        and len(name_in_parentheses) >= 2  # 最低2文字以上
                    ):
                        return name_in_parentheses
                    break

        # 変更なし
        return speaker_name

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
