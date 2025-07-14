"""Refactored Speaker Matching Service using shared LLM service layer"""

import logging
import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..config.database import get_db_session
from ..exceptions import DatabaseError, LLMError, QueryError
from ..services import ChainFactory, LLMService

logger = logging.getLogger(__name__)


class SpeakerMatch(BaseModel):
    """マッチング結果のデータモデル"""

    matched: bool = Field(description="マッチングが成功したかどうか")
    speaker_id: int | None = Field(description="マッチしたspeakerのID", default=None)
    speaker_name: str | None = Field(
        description="マッチしたspeakerの名前", default=None
    )
    confidence: float = Field(description="マッチングの信頼度 (0.0-1.0)", default=0.0)
    reason: str = Field(description="マッチング判定の理由")


class SpeakerMatchingService:
    """LLMを活用した発言者名マッチングサービス"""

    def __init__(self, llm_service: LLMService | None = None):
        """
        Initialize speaker matching service

        Args:
            llm_service: Optional LLMService instance
        """
        # Initialize services
        if llm_service is None:
            # Use fast model with low temperature for consistency
            self.llm_service = LLMService.create_fast_instance(
                temperature=0.1, max_tokens=1000
            )
        else:
            self.llm_service = llm_service

        self.chain_factory = ChainFactory(self.llm_service)
        self.session = get_db_session()

        # Create matching chain
        self._matching_chain = self.chain_factory.create_speaker_matching_chain(
            SpeakerMatch
        )

    def find_best_match(
        self,
        speaker_name: str,
        meeting_date: str | None = None,
        conference_id: int | None = None,
    ) -> SpeakerMatch:
        """
        発言者名に最適なマッチを見つける（会議体所属を考慮）

        Args:
            speaker_name: マッチングする発言者名
            meeting_date: 会議開催日（YYYY-MM-DD形式）
            conference_id: 会議体ID

        Returns:
            SpeakerMatch: マッチング結果
        """
        # 既存の発言者リストを取得
        available_speakers = self._get_available_speakers()

        if not available_speakers:
            return SpeakerMatch(
                matched=False, confidence=0.0, reason="利用可能な発言者リストが空です"
            )

        # 会議体所属情報を取得（利用可能な場合）
        affiliated_speakers: list[dict[str, Any]] = []
        affiliated_speaker_ids: set[int] = set()
        if meeting_date and conference_id:
            affiliated_speakers = self._get_affiliated_speakers(
                meeting_date, conference_id
            )
            affiliated_speaker_ids = {s["speaker_id"] for s in affiliated_speakers}

        # まず従来のルールベースマッチングを試行
        rule_based_match = self._rule_based_matching(speaker_name, available_speakers)
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            return rule_based_match

        # LLMによる高度なマッチング
        try:
            # 候補を絞り込み（パフォーマンス向上のため）
            filtered_speakers = self._filter_candidates(
                speaker_name, available_speakers, affiliated_speaker_ids
            )

            # Use chain factory with retry logic
            result = self.chain_factory.invoke_with_retry(
                self._matching_chain,
                {
                    "speaker_name": speaker_name,
                    "available_speakers": self._format_speakers_for_llm(
                        filtered_speakers, affiliated_speaker_ids
                    ),
                },
                max_retries=3,
            )

            # 結果の検証
            if isinstance(result, dict):
                match_result = SpeakerMatch(**result)
            else:
                match_result = result

            # 信頼度が低い場合はマッチしないとして扱う
            if match_result.confidence < 0.8:
                match_result.matched = False
                match_result.speaker_id = None
                match_result.speaker_name = None

            return match_result

        except LLMError:
            # LLM specific errors are already properly handled, re-raise
            raise
        except Exception as e:
            logger.error(f"LLMマッチング中の予期しないエラー: {e}")
            # Wrap unexpected errors as LLMError
            raise LLMError(
                "Unexpected error during LLM matching",
                {"error": str(e)},
            ) from e

    def _get_available_speakers(self) -> list[dict[str, Any]]:
        """利用可能な発言者リストを取得

        Raises:
            QueryError: If database query fails
        """
        try:
            query = text("SELECT id, name FROM speakers ORDER BY name")
            result = self.session.execute(query)

            speakers: list[dict[str, Any]] = []
            for row in result.fetchall():
                speakers.append({"id": row[0], "name": row[1]})

            return speakers
        except SQLAlchemyError as e:
            logger.error(f"Database error getting available speakers: {e}")
            raise QueryError(
                "Failed to retrieve available speakers", {"error": str(e)}
            ) from e

    def _get_affiliated_speakers(
        self, meeting_date: str, conference_id: int
    ) -> list[dict[str, Any]]:
        """
        指定された会議日と会議体IDに基づいて、その時点でアクティブな所属を持つ発言者を取得

        Args:
            meeting_date: 会議開催日（YYYY-MM-DD形式）
            conference_id: 会議体ID

        Returns:
            List[dict]: アフィリエーション情報を含む発言者リスト

        Raises:
            QueryError: If database query fails
        """
        try:
            query = text("""
                SELECT DISTINCT
                    s.id as speaker_id,
                    s.name as speaker_name,
                    p.id as politician_id,
                    p.name as politician_name,
                    pa.role as role
                FROM politician_affiliations pa
                JOIN politicians p ON pa.politician_id = p.id
                JOIN speakers s ON p.speaker_id = s.id
                WHERE pa.conference_id = :conference_id
                    AND pa.start_date <= CAST(:meeting_date AS date)
                    AND (pa.end_date IS NULL OR
                         pa.end_date >= CAST(:meeting_date AS date))
                ORDER BY s.name
            """)

            result = self.session.execute(
                query, {"conference_id": conference_id, "meeting_date": meeting_date}
            )

            affiliated_speakers: list[dict[str, Any]] = []
            for row in result.fetchall():
                affiliated_speakers.append(
                    {
                        "speaker_id": row[0],
                        "speaker_name": row[1],
                        "politician_id": row[2],
                        "politician_name": row[3],
                        "role": row[4],
                    }
                )

            return affiliated_speakers
        except SQLAlchemyError as e:
            logger.error(f"Database error getting affiliated speakers: {e}")
            raise QueryError(
                "Failed to retrieve affiliated speakers",
                {
                    "conference_id": conference_id,
                    "meeting_date": meeting_date,
                    "error": str(e),
                },
            ) from e

    def _rule_based_matching(
        self, speaker_name: str, available_speakers: list[dict[str, Any]]
    ) -> SpeakerMatch:
        """従来のルールベースマッチング"""

        # 1. 完全一致
        for speaker in available_speakers:
            if speaker["name"] == speaker_name:
                return SpeakerMatch(
                    matched=True,
                    speaker_id=speaker["id"],
                    speaker_name=speaker["name"],
                    confidence=1.0,
                    reason="完全一致",
                )

        # 2. 括弧内の名前を抽出して検索
        match = re.search(r"\(([^)]+)\)", speaker_name)
        if match:
            extracted_name = match.group(1)
            for speaker in available_speakers:
                if speaker["name"] == extracted_name:
                    return SpeakerMatch(
                        matched=True,
                        speaker_id=speaker["id"],
                        speaker_name=speaker["name"],
                        confidence=0.95,
                        reason=f"括弧内名前一致: {extracted_name}",
                    )

        # 3. 記号除去後の一致
        cleaned_name = re.sub(r"^[◆○◎]", "", speaker_name)
        if cleaned_name != speaker_name:
            return self._rule_based_matching(cleaned_name, available_speakers)

        # 4. 部分一致
        for speaker in available_speakers:
            if speaker["name"] in speaker_name or speaker_name in speaker["name"]:
                return SpeakerMatch(
                    matched=True,
                    speaker_id=speaker["id"],
                    speaker_name=speaker["name"],
                    confidence=0.8,
                    reason=f"部分一致: {speaker['name']}",
                )

        return SpeakerMatch(
            matched=False, confidence=0.0, reason="ルールベースマッチングでは一致なし"
        )

    def _filter_candidates(
        self,
        speaker_name: str,
        available_speakers: list[dict[str, Any]],
        affiliated_speaker_ids: set[int] | None = None,
        max_candidates: int = 10,
    ) -> list[dict[str, Any]]:
        """候補を絞り込む（LLMの処理効率向上のため、会議体所属を優先）"""
        candidates: list[dict[str, Any]] = []

        # 括弧内の名前を抽出
        extracted_name = None
        match = re.search(r"\(([^)]+)\)", speaker_name)
        if match:
            extracted_name = match.group(1)

        # 記号除去
        cleaned_name = re.sub(r"^[◆○◎]", "", speaker_name)

        for speaker in available_speakers:
            score = 0

            # 部分一致スコア
            if speaker["name"] in speaker_name or speaker_name in speaker["name"]:
                score += 3

            # 括弧内名前との一致
            if extracted_name and (
                speaker["name"] == extracted_name or extracted_name in speaker["name"]
            ):
                score += 5

            # 清理された名前との一致
            if speaker["name"] in cleaned_name or cleaned_name in speaker["name"]:
                score += 2

            # 文字列長の類似性
            len_diff = abs(len(speaker["name"]) - len(speaker_name))
            if len_diff <= 3:
                score += 1

            # 会議体所属ボーナス
            if affiliated_speaker_ids and speaker["id"] in affiliated_speaker_ids:
                score += 10  # 大きなボーナスを付与

            if score > 0:
                candidates.append({**speaker, "score": score})

        # スコア順にソート
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 最大候補数に制限
        return (
            candidates[:max_candidates]
            if candidates
            else available_speakers[:max_candidates]
        )

    def _format_speakers_for_llm(
        self, speakers: list[dict[str, Any]], affiliated_speaker_ids: set[int] | None = None
    ) -> str:
        """発言者リストをLLM用にフォーマット（会議体所属情報を含む）"""
        formatted: list[str] = []
        for speaker in speakers:
            entry = f"ID: {speaker['id']}, 名前: {speaker['name']}"
            if affiliated_speaker_ids and speaker["id"] in affiliated_speaker_ids:
                entry += " 【会議体所属議員】"
            formatted.append(entry)
        return "\n".join(formatted)

    def batch_update_speaker_links(self) -> dict[str, int]:
        """
        未マッチの会話レコードを一括でマッチング更新

        Returns:
            Dict[str, int]: 更新統計
        """
        stats = {
            "total_processed": 0,
            "successfully_matched": 0,
            "high_confidence_matches": 0,
            "failed_matches": 0,
            "affiliation_aided_matches": 0,
        }

        try:
            # speaker_idがNULLのレコードを取得（会議情報も含む）
            query = text("""
                SELECT c.id, c.speaker_name, m.date, m.conference_id
                FROM conversations c
                JOIN minutes min ON c.minute_id = min.id
                JOIN meetings m ON min.meeting_id = m.id
                WHERE c.speaker_id IS NULL
                ORDER BY c.id
            """)

            result = self.session.execute(query)
            unlinked_conversations = result.fetchall()

            stats["total_processed"] = len(unlinked_conversations)

            for (
                conversation_id,
                speaker_name,
                meeting_date,
                conference_id,
            ) in unlinked_conversations:
                logger.info(f"マッチング処理中: {speaker_name}")

                # 会議日付をYYYY-MM-DD形式に変換
                meeting_date_str = (
                    meeting_date.strftime("%Y-%m-%d") if meeting_date else None
                )

                match_result = self.find_best_match(
                    speaker_name, meeting_date_str, conference_id
                )

                if match_result.matched and match_result.speaker_id:
                    # speaker_idを更新
                    update_query = text("""
                        UPDATE conversations
                        SET speaker_id = :speaker_id
                        WHERE id = :conversation_id
                    """)

                    self.session.execute(
                        update_query,
                        {
                            "speaker_id": match_result.speaker_id,
                            "conversation_id": conversation_id,
                        },
                    )

                    stats["successfully_matched"] += 1

                    if match_result.confidence >= 0.9:
                        stats["high_confidence_matches"] += 1

                    confidence_emoji = "🟢" if match_result.confidence >= 0.9 else "🟡"
                    logger.info(
                        f"  {confidence_emoji} マッチ成功: {speaker_name} → {match_result.speaker_name} (信頼度: {match_result.confidence:.2f})"
                    )
                else:
                    stats["failed_matches"] += 1
                    logger.warning(
                        f"  🔴 マッチ失敗: {speaker_name} ({match_result.reason})"
                    )

            self.session.commit()

            logger.info("マッチング結果:")
            logger.info(f"   - 処理総数: {stats['total_processed']}件")
            logger.info(f"   - マッチ成功: {stats['successfully_matched']}件")
            logger.info(f"   - 高信頼度マッチ: {stats['high_confidence_matches']}件")
            logger.info(f"   - マッチ失敗: {stats['failed_matches']}件")

            return stats

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error during batch matching update: {e}")
            raise DatabaseError(
                "Failed to update speaker links in batch",
                {"processed": stats.get("total_processed", 0), "error": str(e)},
            ) from e
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error during batch matching update: {e}")
            raise DatabaseError(
                "Unexpected error during batch speaker link update",
                {"error": str(e)},
            ) from e
        finally:
            self.session.close()
