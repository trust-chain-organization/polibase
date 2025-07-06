"""Conversation entity."""

from src.domain.entities.base import BaseEntity


class Conversation(BaseEntity):
    """発言を表すエンティティ."""

    def __init__(
        self,
        comment: str,
        sequence_number: int,
        minutes_id: int | None = None,
        speaker_id: int | None = None,
        speaker_name: str | None = None,
        chapter_number: int | None = None,
        sub_chapter_number: int | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.comment = comment
        self.sequence_number = sequence_number
        self.minutes_id = minutes_id
        self.speaker_id = speaker_id
        self.speaker_name = speaker_name
        self.chapter_number = chapter_number
        self.sub_chapter_number = sub_chapter_number

    def __str__(self) -> str:
        speaker = (
            self.speaker_name or f"Speaker #{self.speaker_id}"
            if self.speaker_id
            else "Unknown"
        )
        return (
            f"{speaker}: {self.comment[:50]}..."
            if len(self.comment) > 50
            else f"{speaker}: {self.comment}"
        )
