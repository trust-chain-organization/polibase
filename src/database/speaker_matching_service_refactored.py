"""Refactored Speaker Matching Service using shared LLM service layer"""

import logging
import re

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..config.database import get_db_session
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

    def __init__(self, llm: ChatGoogleGenerativeAI | None = None):
        """
        Initialize speaker matching service

        Args:
            llm: Optional LLM instance for backward compatibility
        """
        # Initialize services
        if llm:
            # Backward compatibility
            self.llm_service = LLMService(
                model_name=llm.model_name,
                temperature=llm.temperature,
                max_tokens=getattr(llm, "max_tokens", 1000),
            )
        else:
            # Use fast model with low temperature for consistency
            self.llm_service = LLMService.create_fast_instance(
                temperature=0.1, max_tokens=1000
            )

        self.chain_factory = ChainFactory(self.llm_service)
        self.session = get_db_session()

        # Create matching chain
        self._matching_chain = self.chain_factory.create_speaker_matching_chain(
            SpeakerMatch
        )

    def find_best_match(self, speaker_name: str) -> SpeakerMatch:
        """
        発言者名に最適なマッチを見つける

        Args:
            speaker_name: マッチングする発言者名

        Returns:
            SpeakerMatch: マッチング結果
        """
        # 既存の発言者リストを取得
        available_speakers = self._get_available_speakers()

        if not available_speakers:
            return SpeakerMatch(
                matched=False,
                confidence=0.0,
                reason="利用可能な発言者リストが空です"
            )

        # まず従来のルールベースマッチングを試行
        rule_based_match = self._rule_based_matching(
            speaker_name, available_speakers
        )
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            return rule_based_match

        # LLMによる高度なマッチング
        try:
            # 候補を絞り込み（パフォーマンス向上のため）
            filtered_speakers = self._filter_candidates(
                speaker_name, available_speakers
            )

            # Use chain factory with retry logic
            result = self.chain_factory.invoke_with_retry(
                self._matching_chain,
                {
                    "speaker_name": speaker_name,
                    "available_speakers": self._format_speakers_for_llm(
                        filtered_speakers
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

        except Exception as e:
            logger.error(f"LLMマッチングエラー: {e}")
            # エラー時はルールベースの結果を返す
            return rule_based_match

    def _get_available_speakers(self) -> list[dict]:
        """利用可能な発言者リストを取得"""
        query = text("SELECT id, name FROM speakers ORDER BY name")
        result = self.session.execute(query)

        speakers = []
        for row in result.fetchall():
            speakers.append({"id": row[0], "name": row[1]})

        return speakers

    def _rule_based_matching(
        self, speaker_name: str, available_speakers: list[dict]
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
            matched=False,
            confidence=0.0,
            reason="ルールベースマッチングでは一致なし"
        )

    def _filter_candidates(
        self,
        speaker_name: str,
        available_speakers: list[dict],
        max_candidates: int = 10,
    ) -> list[dict]:
        """候補を絞り込む（LLMの処理効率向上のため）"""
        candidates = []

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
                speaker["name"] == extracted_name
                or extracted_name in speaker["name"]
            ):
                score += 5

            # 清理された名前との一致
            if speaker["name"] in cleaned_name or cleaned_name in speaker["name"]:
                score += 2

            # 文字列長の類似性
            len_diff = abs(len(speaker["name"]) - len(speaker_name))
            if len_diff <= 3:
                score += 1

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

    def _format_speakers_for_llm(self, speakers: list[dict]) -> str:
        """発言者リストをLLM用にフォーマット"""
        formatted = []
        for speaker in speakers:
            formatted.append(f"ID: {speaker['id']}, 名前: {speaker['name']}")
        return "\n".join(formatted)

    def batch_update_speaker_links(self) -> dict[str, int]:
        """
        未マッチの会話レコードを一括でマッチング更新

        Returns:
            Dict[str, int]: 更新統計
        """
        try:
            # speaker_idがNULLのレコードを取得
            query = text("""
                SELECT id, speaker_name FROM conversations
                WHERE speaker_id IS NULL
                ORDER BY id
            """)

            result = self.session.execute(query)
            unlinked_conversations = result.fetchall()

            stats = {
                "total_processed": len(unlinked_conversations),
                "successfully_matched": 0,
                "high_confidence_matches": 0,
                "failed_matches": 0,
            }

            for conversation_id, speaker_name in unlinked_conversations:
                logger.info(f"マッチング処理中: {speaker_name}")

                match_result = self.find_best_match(speaker_name)

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

                    confidence_emoji = (
                        "🟢" if match_result.confidence >= 0.9 else "🟡"
                    )
                    logger.info(
                        f"  {confidence_emoji} マッチ成功: {speaker_name} → "
                        f"{match_result.speaker_name} "
                        f"(信頼度: {match_result.confidence:.2f})"
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
            logger.info(
                f"   - 高信頼度マッチ: {stats['high_confidence_matches']}件"
            )
            logger.info(f"   - マッチ失敗: {stats['failed_matches']}件")

            return stats

        except Exception as e:
            self.session.rollback()
            logger.error(f"一括マッチング更新エラー: {e}")
            raise
        finally:
            self.session.close()
