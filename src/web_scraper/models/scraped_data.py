"""Data models for scraped content"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class SpeakerData:
    """発言者データモデル"""

    name: str
    content: str
    role: str | None = None  # 議員、委員、市長、局長など

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {"name": self.name, "content": self.content, "role": self.role}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SpeakerData":
        """辞書からインスタンスを生成"""
        return cls(name=data["name"], content=data["content"], role=data.get("role"))


@dataclass
class MinutesData:
    """議事録データモデル"""

    council_id: str
    schedule_id: str
    title: str
    date: datetime | None
    content: str
    speakers: list[SpeakerData]
    url: str
    scraped_at: datetime
    pdf_url: str | None = None
    text_view_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)  # type: ignore

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        return {
            "council_id": self.council_id,
            "schedule_id": self.schedule_id,
            "title": self.title,
            "date": self.date.isoformat() if self.date else None,
            "content": self.content,
            "speakers": [speaker.to_dict() for speaker in self.speakers],
            "url": self.url,
            "pdf_url": self.pdf_url,
            "text_view_url": self.text_view_url,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MinutesData":
        """辞書からインスタンスを生成"""
        # 日付の変換
        date = None
        if data.get("date"):
            date = datetime.fromisoformat(data["date"])

        scraped_at = datetime.now()
        if data.get("scraped_at"):
            scraped_at = datetime.fromisoformat(data["scraped_at"])

        # スピーカーデータの変換
        speakers: list[SpeakerData] = []
        speakers_list: Any = data.get("speakers", [])
        if isinstance(speakers_list, list):
            for speaker_item in speakers_list:  # type: ignore
                if isinstance(speaker_item, dict):
                    # 新しい形式
                    if "name" in speaker_item and "content" in speaker_item:
                        # dict[str, Any]にキャスト
                        speaker_dict: dict[str, Any] = {}
                        for key, value in speaker_item.items():  # type: ignore
                            key_str = str(key)  # type: ignore
                            speaker_dict[key_str] = value
                        speakers.append(SpeakerData.from_dict(speaker_dict))
                    # 古い形式の互換性
                    elif "name" in speaker_item:
                        speaker_name: Any = speaker_item["name"]  # type: ignore
                        speaker_content: Any = speaker_item.get("content", "")  # type: ignore
                        if isinstance(speaker_name, str) and isinstance(
                            speaker_content, str
                        ):
                            speakers.append(
                                SpeakerData(
                                    name=speaker_name,
                                    content=speaker_content,
                                )
                            )

        metadata_dict: dict[str, Any] = {}
        if "metadata" in data:
            metadata_value = data["metadata"]
            if isinstance(metadata_value, dict):
                # metadataフィールドの型を明示的に構築
                for key, value in metadata_value.items():  # type: ignore
                    key_str = str(key)  # type: ignore
                    metadata_dict[key_str] = value

        return cls(
            council_id=data["council_id"],
            schedule_id=data["schedule_id"],
            title=data["title"],
            date=date,
            content=data["content"],
            speakers=speakers,
            url=data["url"],
            scraped_at=scraped_at,
            pdf_url=data.get("pdf_url"),
            text_view_url=data.get("text_view_url"),
            metadata=metadata_dict,
        )

    @property
    def has_content(self) -> bool:
        """コンテンツが存在するかチェック"""
        return bool(self.content and len(self.content.strip()) > 10)

    @property
    def speaker_count(self) -> int:
        """発言者数を取得"""
        return len(self.speakers)

    def get_speaker_names(self) -> list[str]:
        """発言者名のリストを取得"""
        return list({speaker.name for speaker in self.speakers})
