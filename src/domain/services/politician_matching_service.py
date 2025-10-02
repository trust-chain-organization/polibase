"""
LLMを活用した発言者と政治家の高精度マッチングサービス
"""

import logging
import re
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.domain.repositories.politician_repository import PoliticianRepository
from src.domain.services.interfaces.llm_service import ILLMService
from src.exceptions import DatabaseError, LLMError, QueryError

logger = logging.getLogger(__name__)


class PoliticianMatch(BaseModel):
    """政治家マッチング結果のデータモデル"""

    matched: bool = Field(description="マッチングが成功したかどうか")
    politician_id: int | None = Field(description="マッチした政治家のID", default=None)
    politician_name: str | None = Field(
        description="マッチした政治家の名前", default=None
    )
    political_party_name: str | None = Field(
        description="マッチした政治家の所属政党", default=None
    )
    confidence: float = Field(description="マッチングの信頼度 (0.0-1.0)", default=0.0)
    reason: str = Field(description="マッチング判定の理由")


class PoliticianMatchingService:
    """LLMを活用した発言者-政治家マッチングサービス"""

    def __init__(
        self,
        llm_service: ILLMService,
        politician_repository: PoliticianRepository,
        session: Session,
    ):
        """
        Initialize PoliticianMatchingService

        Args:
            llm_service: LLM service instance (domain interface)
            politician_repository: Politician repository instance (domain interface)
            session: Database session
        """
        self.llm_service = llm_service
        self.politician_repository = politician_repository
        self.session = session

        # プロンプト名を使ってチェーンを取得
        prompt_name = "politician_matching"
        self.chain: Any = self.llm_service.get_prompt(prompt_name)

    def find_best_match(
        self,
        speaker_name: str,
        speaker_type: str | None = None,
        speaker_party: str | None = None,
    ) -> PoliticianMatch:
        """
        発言者に最適な政治家マッチを見つける

        Args:
            speaker_name: マッチングする発言者名
            speaker_type: 発言者の種別
            speaker_party: 発言者の所属政党（もしあれば）

        Returns:
            PoliticianMatch: マッチング結果
        """
        # 既存の政治家リストを取得
        available_politicians = self._get_available_politicians()

        if not available_politicians:
            return PoliticianMatch(
                matched=False, confidence=0.0, reason="利用可能な政治家リストが空です"
            )

        # まず従来のルールベースマッチングを試行
        rule_based_match = self._rule_based_matching(
            speaker_name, speaker_party, available_politicians
        )
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            return rule_based_match

        # LLMによる高度なマッチング
        try:
            # 候補を絞り込み（パフォーマンス向上のため）
            filtered_politicians = self._filter_candidates(
                speaker_name, speaker_party, available_politicians
            )

            result = self.llm_service.invoke_with_retry(
                self.chain,
                {
                    "speaker_name": speaker_name,
                    "speaker_type": speaker_type or "不明",
                    "speaker_party": speaker_party or "不明",
                    "available_politicians": self._format_politicians_for_llm(
                        filtered_politicians
                    ),
                },
            )

            # 結果の検証
            if isinstance(result, dict):
                # Cast to Any to avoid unknown type issues
                result_dict: dict[str, Any] = result  # type: ignore[assignment]
                match_result = PoliticianMatch(**result_dict)
            elif isinstance(result, PoliticianMatch):
                match_result = result
            else:
                # Fallback to no match if result type is unexpected
                match_result = PoliticianMatch(
                    matched=False, confidence=0.0, reason="LLM返答の形式が不正です"
                )

            # 信頼度が低い場合はマッチしないとして扱う
            if match_result.confidence < 0.7:
                match_result.matched = False
                match_result.politician_id = None
                match_result.politician_name = None
                match_result.political_party_name = None

            return match_result

        except LLMError:
            # LLM specific errors are already properly handled, re-raise
            raise
        except Exception as e:
            logger.error(f"LLM政治家マッチング中の予期しないエラー: {e}")
            # Wrap unexpected errors as LLMError
            raise LLMError(
                "Unexpected error during LLM politician matching",
                {"speaker_name": speaker_name, "error": str(e)},
            ) from e

    def _get_available_politicians(self) -> list[dict[str, Any]]:
        """利用可能な政治家リストを取得

        Raises:
            QueryError: If database query fails
        """
        try:
            query = text("""
                SELECT p.id, p.name, p.position, p.prefecture,
                       p.electoral_district, pp.name as party_name
                FROM politicians p
                LEFT JOIN political_parties pp ON p.political_party_id = pp.id
                ORDER BY p.name
            """)
            result = self.session.execute(query)

            politicians: list[dict[str, Any]] = []
            for row in result.fetchall():
                politicians.append(
                    {
                        "id": row[0],
                        "name": row[1],
                        "position": row[2],
                        "prefecture": row[3],
                        "electoral_district": row[4],
                        "party_name": row[5],
                    }
                )

            return politicians
        except SQLAlchemyError as e:
            logger.error(f"Database error getting available politicians: {e}")
            raise QueryError(
                "Failed to retrieve available politicians",
                {"error": str(e)},
            ) from e

    def _rule_based_matching(
        self,
        speaker_name: str,
        speaker_party: str | None,
        available_politicians: list[dict[str, Any]],
    ) -> PoliticianMatch:
        """従来のルールベースマッチング"""

        # 1. 完全一致（名前と政党）
        if speaker_party:
            for politician in available_politicians:
                if (
                    politician["name"] == speaker_name
                    and politician["party_name"] == speaker_party
                ):
                    return PoliticianMatch(
                        matched=True,
                        politician_id=politician["id"],
                        politician_name=politician["name"],
                        political_party_name=politician["party_name"],
                        confidence=1.0,
                        reason="名前と政党が完全一致",
                    )

        # 2. 名前のみ完全一致
        exact_matches = [p for p in available_politicians if p["name"] == speaker_name]
        if len(exact_matches) == 1:
            politician = exact_matches[0]
            return PoliticianMatch(
                matched=True,
                politician_id=politician["id"],
                politician_name=politician["name"],
                political_party_name=politician["party_name"],
                confidence=0.9,
                reason="名前が完全一致（唯一の候補）",
            )

        # 3. 敬称を除去して検索
        cleaned_name = re.sub(r"(議員|氏|さん|様|先生)$", "", speaker_name)
        if cleaned_name != speaker_name:
            for politician in available_politicians:
                if politician["name"] == cleaned_name:
                    return PoliticianMatch(
                        matched=True,
                        politician_id=politician["id"],
                        politician_name=politician["name"],
                        political_party_name=politician["party_name"],
                        confidence=0.85,
                        reason=f"敬称除去後に一致: {speaker_name} → {cleaned_name}",
                    )

        return PoliticianMatch(
            matched=False, confidence=0.0, reason="ルールベースマッチングでは一致なし"
        )

    def _filter_candidates(
        self,
        speaker_name: str,
        speaker_party: str | None,
        available_politicians: list[dict[str, Any]],
        max_candidates: int = 20,
    ) -> list[dict[str, Any]]:
        """候補を絞り込む（LLMの処理効率向上のため）"""
        candidates: list[dict[str, Any]] = []

        # 敬称を除去
        cleaned_name = re.sub(r"(議員|氏|さん|様|先生)$", "", speaker_name)

        for politician in available_politicians:
            score = 0

            # 完全一致
            if politician["name"] == speaker_name:
                score += 10

            # 敬称除去後の一致
            if politician["name"] == cleaned_name:
                score += 8

            # 部分一致
            if politician["name"] in speaker_name or speaker_name in politician["name"]:
                score += 5

            # 政党一致
            if speaker_party and politician["party_name"] == speaker_party:
                score += 3

            # 姓または名の一致（スペースで分割）
            speaker_parts = speaker_name.split()
            politician_parts = politician["name"].split()
            for sp in speaker_parts:
                if sp in politician_parts:
                    score += 2

            # 文字列長の類似性
            len_diff = abs(len(politician["name"]) - len(speaker_name))
            if len_diff <= 2:
                score += 1

            if score > 0:
                candidates.append({**politician, "score": score})

        # スコア順にソート
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 最大候補数に制限
        return candidates[:max_candidates]

    def _format_politicians_for_llm(self, politicians: list[dict[str, Any]]) -> str:
        """政治家リストをLLM用にフォーマット"""
        formatted: list[str] = []
        for p in politicians:
            info = f"ID: {p['id']}, 名前: {p['name']}"
            if p.get("party_name"):
                info += f", 政党: {p['party_name']}"
            if p.get("position"):
                info += f", 役職: {p['position']}"
            if p.get("prefecture"):
                info += f", 都道府県: {p['prefecture']}"
            if p.get("electoral_district"):
                info += f", 選挙区: {p['electoral_district']}"
            formatted.append(info)
        return "\n".join(formatted)

    def batch_link_speakers_to_politicians(self) -> dict[str, int]:
        """
        未紐付けの発言者を一括で政治家とマッチング

        Returns:
            Dict[str, int]: 更新統計
        """
        stats = {
            "total_processed": 0,
            "successfully_matched": 0,
            "high_confidence_matches": 0,
            "failed_matches": 0,
        }

        try:
            # is_politician=Falseのspeakerを取得
            query = text("""
                SELECT id, name, type, political_party_name
                FROM speakers
                WHERE is_politician = FALSE
                ORDER BY id
            """)

            result = self.session.execute(query)
            unlinked_speakers = result.fetchall()

            stats["total_processed"] = len(unlinked_speakers)

            for (
                speaker_id,
                speaker_name,
                speaker_type,
                speaker_party,
            ) in unlinked_speakers:
                logger.info(f"政治家マッチング処理中: {speaker_name}")

                match_result = self.find_best_match(
                    speaker_name, speaker_type, speaker_party
                )

                if match_result.matched and match_result.politician_id:
                    # speakerを更新
                    update_query = text("""
                        UPDATE speakers
                        SET is_politician = TRUE,
                            political_party_name = COALESCE(:party_name,
                                                           political_party_name)
                        WHERE id = :speaker_id
                    """)

                    self.session.execute(
                        update_query,
                        {
                            "speaker_id": speaker_id,
                            "party_name": match_result.political_party_name,
                        },
                    )

                    stats["successfully_matched"] += 1

                    if match_result.confidence >= 0.9:
                        stats["high_confidence_matches"] += 1

                    logger.info(
                        f"マッチ成功: {speaker_name} → "
                        f"{match_result.politician_name} "
                        f"({match_result.political_party_name}) "
                        f"(信頼度: {match_result.confidence:.2f})"
                    )
                else:
                    stats["failed_matches"] += 1
                    logger.info(f"マッチ失敗: {speaker_name} ({match_result.reason})")

            self.session.commit()

            logger.info("政治家マッチング結果:")
            logger.info(f"   - 処理総数: {stats['total_processed']}人")
            logger.info(f"   - マッチ成功: {stats['successfully_matched']}人")
            logger.info(f"   - 高信頼度マッチ: {stats['high_confidence_matches']}人")
            logger.info(f"   - マッチ失敗: {stats['failed_matches']}人")

            return stats

        except SQLAlchemyError as e:
            self.session.rollback()
            logger.error(f"Database error during batch politician matching: {e}")
            raise DatabaseError(
                "Failed to update politician links in batch",
                {"processed": stats.get("total_processed", 0), "error": str(e)},
            ) from e
        except Exception as e:
            self.session.rollback()
            logger.error(f"Unexpected error during batch politician matching: {e}")
            raise DatabaseError(
                "Unexpected error during batch politician link update",
                {"error": str(e)},
            ) from e
        finally:
            self.session.close()
