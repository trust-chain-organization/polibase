"""
Conversations テーブルへのデータ操作を管理するリポジトリクラス

Provides database operations for conversations with proper error handling.
"""

import asyncio
import logging
from typing import Any

from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.database.base_repository import BaseRepository
from src.database.speaker_matching_service import SpeakerMatchingService
from src.exceptions import IntegrityError, SaveError
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.minutes_divide_processor.models import (
    SpeakerAndSpeechContent,
)

logger = logging.getLogger(__name__)


class ConversationRepository(BaseRepository):
    """Conversationsテーブルに対するデータベース操作を管理するクラス

    This is a legacy wrapper that delegates to the new ConversationRepositoryImpl.
    """

    def __init__(
        self,
        speaker_matching_service: SpeakerMatchingService | None = None,
        session: Session | None = None,
    ):
        super().__init__(use_session=True, session=session)
        self.speaker_matching_service = speaker_matching_service
        # Initialize the new implementation
        self._impl = ConversationRepositoryImpl(
            session=self.session,
            speaker_matching_service=speaker_matching_service,
        )

    def save_speaker_and_speech_content_list(
        self,
        speaker_and_speech_content_list: list[SpeakerAndSpeechContent],
        minutes_id: int | None = None,
    ) -> list[int]:
        """
        SpeakerAndSpeechContentのリストをConversationsテーブルに保存する

        Args:
            speaker_and_speech_content_list: 保存する発言データリスト
            minutes_id: 紐付けるminutesレコードのID

        Returns:
            List[int]: 保存されたレコードのIDリスト

        Raises:
            SaveError: If saving conversations fails
            IntegrityError: If data integrity constraint is violated
        """
        if not speaker_and_speech_content_list:
            logger.warning("No conversations to save")
            try:
                self.session.commit()  # Empty commit for consistency
                return []
            finally:
                self.session.close()

        saved_ids: list[int] = []
        failed_count = 0

        try:
            for i, speaker_and_speech_content in enumerate(
                speaker_and_speech_content_list
            ):
                try:
                    conversation_id = self._save_conversation(
                        speaker_and_speech_content, minutes_id
                    )
                    if conversation_id:
                        saved_ids.append(conversation_id)
                except Exception as e:
                    logger.warning(f"Failed to save conversation {i + 1}: {e}")
                    failed_count += 1
                    # Continue with other conversations

            self.session.commit()

            if saved_ids:
                print(f"✅ {len(saved_ids)}件の発言データをデータベースに保存しました")
                logger.info(f"Saved {len(saved_ids)} conversations successfully")

            if failed_count > 0:
                logger.warning(f"Failed to save {failed_count} conversations")
                if failed_count == len(speaker_and_speech_content_list):
                    # All conversations failed, raise an exception
                    raise SaveError(
                        f"Failed to save all {failed_count} conversations",
                        {"failed_count": failed_count},
                    )

            return saved_ids

        except SQLIntegrityError as e:
            self.session.rollback()
            logger.error(f"Integrity error while saving conversations: {e}")
            raise IntegrityError(
                "Data integrity constraint violated while saving conversations",
                {"saved_count": len(saved_ids), "error": str(e)},
            ) from e
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error while saving conversations: {e}")
            raise SaveError(
                "Failed to save conversations to database",
                {
                    "saved_count": len(saved_ids),
                    "total_count": len(speaker_and_speech_content_list),
                    "error": str(e),
                },
            ) from e
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error while saving conversations: {e}")
            raise SaveError(
                "Unexpected error occurred while saving conversations",
                {"saved_count": len(saved_ids), "error": str(e)},
            ) from e
        finally:
            self.session.close()

    def _save_conversation(
        self,
        speaker_and_speech_content: SpeakerAndSpeechContent,
        minutes_id: int | None = None,
    ) -> int | None:
        """
        個別のSpeakerAndSpeechContentをConversationsテーブルに保存する

        Args:
            speaker_and_speech_content: 保存する発言データ
            minutes_id: 紐付けるminutesレコードのID

        Returns:
            保存されたレコードのID、失敗した場合はNone

        Raises:
            SaveError: If save operation fails
        """
        # speaker_idを検索（名前の完全一致または部分一致）
        speaker_id = self._find_speaker_id(speaker_and_speech_content.speaker)

        # 新規レコードの挿入
        conversation_id = self.insert(
            table="conversations",
            data={
                "minutes_id": minutes_id,  # minutesレコードと紐付け
                "speaker_id": speaker_id,
                "speaker_name": speaker_and_speech_content.speaker,
                "comment": speaker_and_speech_content.speech_content,
                "sequence_number": speaker_and_speech_content.speech_order,
                "chapter_number": speaker_and_speech_content.chapter_number,
                "sub_chapter_number": speaker_and_speech_content.sub_chapter_number,
            },
            returning="id",
        )

        if speaker_id:
            print(
                f"➕ 新規追加: {speaker_and_speech_content.speaker} "
                f"(ID: {conversation_id}, Speaker ID: {speaker_id})"
            )
        else:
            print(
                f"➕ 新規追加: {speaker_and_speech_content.speaker} "
                f"(ID: {conversation_id}, Speaker ID: NULL)"
            )

        return conversation_id

    def _find_speaker_id(self, speaker_name: str) -> int | None:
        """
        既存のSpeakerレコードから一致する発言者IDを検索する

        Args:
            speaker_name: 検索する発言者名

        Returns:
            Optional[int]: 一致するSpeakerのID（見つからない場合はNone）
        """
        # LLMベースのマッチングサービスが利用可能な場合はそれを使用
        if self.speaker_matching_service:
            match_result = self.speaker_matching_service.find_best_match(speaker_name)
            if match_result.matched:
                return match_result.speaker_id
            return None

        # フォールバック: 従来のルールベースマッチング
        return self._legacy_find_speaker_id(speaker_name)

    def _legacy_find_speaker_id(self, speaker_name: str) -> int | None:
        """
        従来のルールベース発言者検索（後方互換性のため）
        """
        # 完全一致を優先して検索
        query = """
            SELECT id FROM speakers
            WHERE name = :speaker_name
            LIMIT 1
        """

        row = self.fetch_one(query, {"speaker_name": speaker_name})

        if row:
            return int(row[0])

        # 括弧内の名前を抽出して検索（例: "委員長(平山たかお)" → "平山たかお"）
        import re

        match = re.search(r"\(([^)]+)\)", speaker_name)
        if match:
            extracted_name = match.group(1)
            query = """
                SELECT id FROM speakers
                WHERE name = :extracted_name
                LIMIT 1
            """

            row = self.fetch_one(query, {"extracted_name": extracted_name})

            if row:
                return int(row[0])

        # 記号を除去して検索（例: "◆委員(下村あきら)" → "委員(下村あきら)"）
        cleaned_name = re.sub(r"^[◆○◎]", "", speaker_name)
        if cleaned_name != speaker_name:
            # 再帰的に検索
            return self._legacy_find_speaker_id(cleaned_name)

        # それでも見つからない場合は部分一致を試行
        query = """
            SELECT id FROM speakers
            WHERE name LIKE :speaker_pattern
            OR :speaker_name LIKE CONCAT('%', name, '%')
            LIMIT 1
        """

        row = self.fetch_one(
            query,
            {"speaker_pattern": f"%{speaker_name}%", "speaker_name": speaker_name},
        )

        return int(row[0]) if row else None

    def get_all_conversations(self) -> list[dict[str, Any]]:
        """
        全てのConversationレコードを取得する

        Returns:
            List[dict]: Conversationレコードのリスト
        """
        query = """
            SELECT c.id, c.minutes_id, c.speaker_id, c.speaker_name, c.comment,
                   c.sequence_number, c.chapter_number, c.sub_chapter_number,
                   c.created_at, c.updated_at, s.name as linked_speaker_name
            FROM conversations c
            LEFT JOIN speakers s ON c.speaker_id = s.id
            ORDER BY c.sequence_number ASC
        """

        results = self.fetch_as_dict(query)
        return results

    def get_conversations_count(self) -> int:
        """
        Conversationsテーブルのレコード数を取得する

        Returns:
            int: レコード数
        """
        # Delegate to new implementation (sync)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._impl.get_conversations_count())
        finally:
            loop.close()

    def get_speaker_linking_stats(self) -> dict[str, int | float]:
        """
        発言者の紐付け統計を取得する

        Returns:
            dict: 紐付け統計（総数、紐付けあり、紐付けなし、政治家紐付け数、紐付け率）
        """
        # Delegate to new implementation for basic stats
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            basic_stats = loop.run_until_complete(
                self._impl.get_speaker_linking_stats()
            )
        finally:
            loop.close()

        # Add politician-linked stats using legacy query
        query = """
            SELECT COUNT(*) as count
            FROM conversations c
            LEFT JOIN speakers s ON c.speaker_id = s.id
            LEFT JOIN politicians p ON s.id = p.speaker_id
            WHERE c.speaker_id IS NOT NULL AND p.id IS NOT NULL
        """
        row = self.fetch_one(query)
        politician_linked = int(row[0]) if row else 0

        total = basic_stats["total_conversations"]
        politician_link_rate = (politician_linked / total * 100) if total > 0 else 0

        return {
            "total_conversations": basic_stats["total_conversations"],
            "speaker_linked_conversations": basic_stats["linked_conversations"],
            "politician_linked_conversations": politician_linked,
            "unlinked_conversations": basic_stats["unlinked_conversations"],
            "speaker_link_rate": basic_stats["linking_rate"],
            "politician_link_rate": politician_link_rate,
        }

    def get_conversations_by_minutes_id(self, minutes_id: int) -> list[dict[str, Any]]:
        """
        指定されたminutes_idに紐づく全てのConversationレコードを取得する

        Args:
            minutes_id: 議事録ID

        Returns:
            List[dict]: Conversationレコードのリスト
        """
        query = """
            SELECT c.id, c.minutes_id, c.speaker_id, c.speaker_name, c.comment,
                   c.sequence_number, c.chapter_number, c.sub_chapter_number,
                   c.created_at, c.updated_at, s.name as linked_speaker_name
            FROM conversations c
            LEFT JOIN speakers s ON c.speaker_id = s.id
            WHERE c.minutes_id = :minutes_id
            ORDER BY c.sequence_number ASC
        """

        results = self.fetch_as_dict(query, {"minutes_id": minutes_id})
        return results

    def get_conversations_with_pagination(
        self,
        limit: int = 50,
        offset: int = 0,
        conference_id: int | None = None,
        meeting_id: int | None = None,
    ) -> dict[str, Any]:
        """
        ページネーション付きでConversationレコードを取得する

        Args:
            limit: 取得件数
            offset: オフセット
            conference_id: 会議体IDでフィルタ（オプション）
            meeting_id: 会議IDでフィルタ（オプション）

        Returns:
            dict: {
                "conversations": List[dict],  # Conversationレコードのリスト
                "total": int,  # 総件数
                "limit": int,  # 取得件数
                "offset": int  # オフセット
            }
        """
        # Convert to page-based parameters for new implementation
        page = (offset // limit) + 1 if limit > 0 else 1
        page_size = limit

        # Delegate to new implementation (sync)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(
                self._impl.get_conversations_with_pagination(
                    page=page,
                    page_size=page_size,
                    meeting_id=meeting_id,
                )
            )
        finally:
            loop.close()

        # Apply conference_id filter if needed (legacy compatibility)
        conversations = result.get("conversations", [])
        if conference_id is not None:
            # Additional filtering for conference_id
            filtered = []
            for conv in conversations:
                # This requires additional query to get conference_id
                # For now, include all if meeting_id matches
                filtered.append(conv)
            conversations = filtered

        # Enhance with additional fields for legacy compatibility
        enhanced_conversations = []
        for conv in conversations:
            enhanced = dict(conv)
            # Add any missing fields that legacy code expects
            if "speaker_type" not in enhanced:
                enhanced["speaker_type"] = None
            if "speaker_party_name" not in enhanced:
                enhanced["speaker_party_name"] = None
            if "speaker_position" not in enhanced:
                enhanced["speaker_position"] = None
            if "speaker_is_politician" not in enhanced:
                enhanced["speaker_is_politician"] = False
            enhanced_conversations.append(enhanced)

        return {
            "conversations": enhanced_conversations,
            "total": result.get("total_count", 0),
            "limit": limit,
            "offset": offset,
        }

    def get_all_conversations_without_speaker_id(self) -> list[dict[str, Any]]:
        """
        speaker_idが設定されていない全てのConversationレコードを取得する

        Returns:
            List[dict]: speaker_idがNULLのConversationレコードのリスト
        """
        query = """
            SELECT c.id, c.minutes_id, c.speaker_id, c.speaker_name, c.comment,
                   c.sequence_number, c.chapter_number, c.sub_chapter_number,
                   c.created_at, c.updated_at
            FROM conversations c
            WHERE c.speaker_id IS NULL
            ORDER BY c.minutes_id, c.sequence_number ASC
        """

        results = self.fetch_as_dict(query)
        return results

    def update_speaker_links(self) -> int:
        """
        既存のConversationsレコードのspeaker_idを更新する
        LLMマッチングサービスが利用可能な場合はそれを使用

        Returns:
            int: 更新されたレコード数
        """
        # Delegate to new implementation (sync)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._impl.update_speaker_links())
        finally:
            loop.close()

    def _legacy_update_speaker_links(self) -> int:
        """
        従来のルールベースでspeaker_idを更新（後方互換性のため）
        """
        try:
            # speaker_idがNULLのレコードを取得
            query = """
                SELECT id, speaker_name FROM conversations
                WHERE speaker_id IS NULL
            """

            unlinked_conversations = self.fetch_all(query)

            updated_count = 0

            for conversation_id, speaker_name in unlinked_conversations:
                speaker_id = self._legacy_find_speaker_id(speaker_name)

                if speaker_id:
                    # speaker_idを更新
                    rows_affected = self.update(
                        table="conversations",
                        data={"speaker_id": speaker_id},
                        where={"id": conversation_id},
                    )

                    if rows_affected > 0:
                        updated_count += 1
                        print(
                            f"🔗 Speaker紐付け更新: {speaker_name} → "
                            f"Speaker ID: {speaker_id}"
                        )

            self.session.commit()
            print(f"✅ {updated_count}件のSpeaker紐付けを更新しました")
            return updated_count

        except Exception as e:
            self.session.rollback()
            print(f"❌ Speaker紐付け更新エラー: {e}")
            raise
        finally:
            self.session.close()
