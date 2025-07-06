"""Meeting entity."""

from datetime import date

from src.domain.entities.base import BaseEntity


class Meeting(BaseEntity):
    """会議の具体的な開催インスタンスを表すエンティティ."""

    def __init__(
        self,
        conference_id: int,
        date: date | None = None,
        url: str | None = None,
        name: str | None = None,
        gcs_pdf_uri: str | None = None,
        gcs_text_uri: str | None = None,
        id: int | None = None,
    ) -> None:
        super().__init__(id)
        self.conference_id = conference_id
        self.date = date
        self.url = url
        self.name = name
        self.gcs_pdf_uri = gcs_pdf_uri
        self.gcs_text_uri = gcs_text_uri

    def __str__(self) -> str:
        if self.name:
            return self.name
        if self.date:
            return f"Meeting on {self.date}"
        return f"Meeting #{self.id}" if self.id else "Meeting"
