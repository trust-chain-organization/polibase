"""
Speaker テーブルへのデータ操作を管理するリポジトリクラス
Legacy wrapper for Clean Architecture implementation
"""

from sqlalchemy.orm import Session

from src.infrastructure.persistence.sync_speaker_repository_adapter import (
    SyncSpeakerRepositoryAdapter,
)


class SpeakerRepository(SyncSpeakerRepositoryAdapter):
    """
    Speakerテーブルに対するデータベース操作を管理するクラス

    This is a legacy wrapper that maintains backward compatibility
    while using the new Clean Architecture implementation internally.
    """

    def __init__(self, session: Session | None = None):
        super().__init__(session=session)

    # All methods are inherited from SyncSpeakerRepositoryAdapter
    # which provides backward compatibility with the legacy interface
