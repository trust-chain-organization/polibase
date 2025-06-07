"""Data models for scraped content"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any


@dataclass
class SpeakerData:
    """発言者データモデル"""
    name: str
    content: str
    role: Optional[str] = None  # 議員、委員、市長、局長など
    
    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "content": self.content,
            "role": self.role
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpeakerData":
        """辞書からインスタンスを生成"""
        return cls(
            name=data["name"],
            content=data["content"],
            role=data.get("role")
        )


@dataclass
class MinutesData:
    """議事録データモデル"""
    council_id: str
    schedule_id: str
    title: str
    date: Optional[datetime]
    content: str
    speakers: List[SpeakerData]
    url: str
    scraped_at: datetime
    pdf_url: Optional[str] = None
    text_view_url: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
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
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MinutesData":
        """辞書からインスタンスを生成"""
        # 日付の変換
        date = None
        if data.get("date"):
            date = datetime.fromisoformat(data["date"])
        
        scraped_at = datetime.now()
        if data.get("scraped_at"):
            scraped_at = datetime.fromisoformat(data["scraped_at"])
        
        # スピーカーデータの変換
        speakers = []
        for speaker_data in data.get("speakers", []):
            if isinstance(speaker_data, dict):
                # 新しい形式
                if "name" in speaker_data and "content" in speaker_data:
                    speakers.append(SpeakerData.from_dict(speaker_data))
                # 古い形式の互換性
                elif "name" in speaker_data:
                    speakers.append(SpeakerData(
                        name=speaker_data["name"],
                        content=speaker_data.get("content", "")
                    ))
        
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
            metadata=data.get("metadata", {})
        )
    
    @property
    def has_content(self) -> bool:
        """コンテンツが存在するかチェック"""
        return bool(self.content and len(self.content.strip()) > 10)
    
    @property
    def speaker_count(self) -> int:
        """発言者数を取得"""
        return len(self.speakers)
    
    def get_speaker_names(self) -> List[str]:
        """発言者名のリストを取得"""
        return list(set(speaker.name for speaker in self.speakers))