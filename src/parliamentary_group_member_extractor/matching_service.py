"""Service for matching extracted parliamentary group members with politicians"""

import logging
from datetime import date, datetime
from typing import Any, cast

from langchain_core.prompts import PromptTemplate

from src.infrastructure.persistence.extracted_parliamentary_group_member_repository_impl import (  # noqa: E501
    ExtractedParliamentaryGroupMemberRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_membership_repository_impl import (  # noqa: E501
    ParliamentaryGroupMembershipRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_sync_impl import (
    PoliticianRepositorySyncImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ParliamentaryGroupMemberMatchingService:
    """抽出された議員団メンバーと政治家をマッチングするサービス"""

    def __init__(self):
        self.extracted_repo = RepositoryAdapter(
            ExtractedParliamentaryGroupMemberRepositoryImpl
        )
        from src.config.database import get_db_session

        session = get_db_session()
        self.politician_repo = PoliticianRepositorySyncImpl(session)
        self.membership_repo = RepositoryAdapter(
            ParliamentaryGroupMembershipRepositoryImpl
        )
        self.llm_service = LLMService()

    def find_politician_candidates(
        self, extracted_name: str, party_name: str | None
    ) -> list[dict[str, Any]]:
        """候補となる政治家を検索"""
        # 名前で検索（部分一致も含む）
        candidates = self.politician_repo.search_by_name_sync(extracted_name)

        # 完全一致を優先
        exact_matches = [c for c in candidates if c["name"] == extracted_name]
        if exact_matches:
            # 政党名も一致する候補を最優先
            if party_name:
                party_matches = [
                    c for c in exact_matches if c.get("party_name") == party_name
                ]
                if party_matches:
                    return party_matches
            return exact_matches

        # 部分一致の候補を返す
        return candidates[:5]  # 最大5候補

    def match_with_llm(
        self, extracted_member: dict[str, Any], candidates: list[dict[str, Any]]
    ) -> tuple[int | None, float]:
        """LLMを使用して最適な政治家をマッチング"""

        if not candidates:
            return None, 0.0

        # 1候補のみの場合は政党名が一致すれば高信頼度でマッチ
        if len(candidates) == 1:
            candidate = candidates[0]
            if (
                extracted_member.get("extracted_party_name")
                and candidate.get("party_name")
                == extracted_member["extracted_party_name"]
            ):
                return candidate["id"], 0.95
            else:
                return candidate["id"], 0.85

        # 複数候補がある場合はLLMで判定
        prompt_template = PromptTemplate(
            template="""以下の抽出された議員団メンバー情報と最も一致する政治家を選んでください。

抽出されたメンバー情報:
- 名前: {extracted_name}
- 政党: {extracted_party}
- 役職: {extracted_role}
- 議員団: {group_name}

候補の政治家:
{candidates_list}

判定基準:
1. 名前の一致度（漢字表記の違いも考慮）
2. 所属政党の一致
3. 地域や役職の関連性

回答形式:
番号: [最も一致する候補の番号（1から始まる）。該当なしの場合は0]
信頼度: [0.0-1.0の数値]
理由: [簡潔な判定理由]

例:
番号: 2
信頼度: 0.95
理由: 名前と所属政党が完全に一致""",
            input_variables=[
                "extracted_name",
                "extracted_party",
                "extracted_role",
                "group_name",
                "candidates_list",
            ],
        )

        # 候補リストを作成
        candidates_text = ""
        for i, candidate in enumerate(candidates, 1):
            party_info = f"（{candidate.get('party_name', '無所属')}）"
            additional_info: list[str] = []
            if candidate.get("position"):
                additional_info.append(cast(str, candidate["position"]))
            if candidate.get("prefecture"):
                additional_info.append(cast(str, candidate["prefecture"]))

            info_str = f" - {', '.join(additional_info)}" if additional_info else ""
            candidates_text += f"{i}. {candidate['name']} {party_info}{info_str}\n"

        prompt = prompt_template.format(
            extracted_name=extracted_member["extracted_name"],
            extracted_party=extracted_member.get("extracted_party_name", "不明"),
            extracted_role=extracted_member.get("extracted_role", "委員"),
            group_name=extracted_member.get("group_name", ""),
            candidates_list=candidates_text.strip(),
        )

        try:
            response = self.llm_service.llm.invoke(prompt)
            content: str = cast(str, response.content).strip()  # type: ignore

            # レスポンスをパース
            lines: list[str] = content.split("\n")
            selected_num = 0
            confidence = 0.0

            for line in lines:
                if line.startswith("番号:"):
                    try:
                        selected_num = int(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass
                elif line.startswith("信頼度:"):
                    try:
                        confidence = float(line.split(":")[1].strip())
                    except (ValueError, IndexError):
                        pass

            if 1 <= selected_num <= len(candidates):
                selected_politician_id = candidates[selected_num - 1]["id"]
                logger.info(
                    f"LLM matched '{extracted_member['extracted_name']}' to "
                    f"politician ID {selected_politician_id} with confidence "
                    f"{confidence}"
                )
                return selected_politician_id, confidence
            else:
                logger.info(
                    f"LLM found no match for '{extracted_member['extracted_name']}'"
                )
                return None, 0.0

        except Exception as e:
            logger.error(f"Error in LLM matching: {e}")
            return None, 0.0

    def process_extracted_member(
        self, extracted_member: dict[str, Any]
    ) -> dict[str, Any]:
        """単一の抽出メンバーを処理"""
        result: dict[str, Any] = {
            "extracted_member_id": extracted_member["id"],
            "extracted_name": extracted_member["extracted_name"],
            "status": "pending",
            "politician_id": None,
            "confidence": 0.0,
        }

        try:
            # 候補を検索
            candidates = self.find_politician_candidates(
                extracted_member["extracted_name"],
                extracted_member.get("extracted_party_name"),
            )

            if not candidates:
                # 候補なし
                self.extracted_repo.update_matching_result(
                    member_id=extracted_member["id"],
                    politician_id=None,
                    confidence=0.0,
                    status="no_match",
                    matched_at=None,
                )
                result["status"] = "no_match"
                logger.info(
                    f"No candidates found for '{extracted_member['extracted_name']}'"
                )

            else:
                # LLMでマッチング
                politician_id, confidence = self.match_with_llm(
                    extracted_member, candidates
                )

                if politician_id and confidence >= 0.7:
                    # マッチング成功
                    self.extracted_repo.update_matching_result(
                        member_id=extracted_member["id"],
                        politician_id=politician_id,
                        confidence=confidence,
                        status="matched",
                        matched_at=datetime.now(),
                    )
                    result["status"] = "matched"
                    result["politician_id"] = politician_id
                    result["confidence"] = confidence

                elif politician_id and confidence >= 0.5:
                    # 要確認
                    self.extracted_repo.update_matching_result(
                        member_id=extracted_member["id"],
                        politician_id=politician_id,
                        confidence=confidence,
                        status="needs_review",
                        matched_at=datetime.now(),
                    )
                    result["status"] = "needs_review"
                    result["politician_id"] = politician_id
                    result["confidence"] = confidence

                else:
                    # マッチング失敗
                    self.extracted_repo.update_matching_result(
                        member_id=extracted_member["id"],
                        politician_id=None,
                        confidence=0.0,
                        status="no_match",
                        matched_at=None,
                    )
                    result["status"] = "no_match"

        except Exception as e:
            logger.error(f"Error processing member {extracted_member['id']}: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def process_pending_members(
        self, parliamentary_group_id: int | None = None
    ) -> dict[str, Any]:
        """未処理の抽出メンバーを処理"""
        # 未処理メンバーを取得
        pending_members = self.extracted_repo.get_pending_members(
            parliamentary_group_id
        )

        results = {
            "total": len(pending_members),
            "matched": 0,
            "no_match": 0,
            "needs_review": 0,
            "error": 0,
        }

        logger.info(f"Processing {len(pending_members)} pending members")

        for member_entity in pending_members:
            # Convert entity to dict for processing
            member = {
                "id": member_entity.id,
                "extracted_name": member_entity.extracted_name,
                "extracted_party_name": member_entity.extracted_party_name,
                "extracted_role": member_entity.extracted_role,
                "group_name": getattr(member_entity, "group_name", ""),
            }
            result = self.process_extracted_member(member)

            if result["status"] == "matched":
                results["matched"] += 1
            elif result["status"] == "no_match":
                results["no_match"] += 1
            elif result["status"] == "needs_review":
                results["needs_review"] += 1
            else:
                results["error"] += 1

        return results

    def create_memberships_from_matched(
        self, parliamentary_group_id: int | None = None, start_date: date | None = None
    ) -> dict[str, Any]:
        """マッチング済みメンバーから議員団所属情報を作成"""
        # マッチング済みメンバーを取得
        matched_members = self.extracted_repo.get_matched_members(
            parliamentary_group_id
        )

        if not start_date:
            start_date = date.today()

        results = {
            "total": len(matched_members),
            "created": 0,
            "updated": 0,
            "failed": 0,
        }

        logger.info(f"Creating memberships for {len(matched_members)} matched members")

        for member_entity in matched_members:
            try:
                # 議員団所属情報をUPSERT
                membership_id = self.membership_repo.upsert_membership(
                    politician_id=member_entity.matched_politician_id,
                    parliamentary_group_id=member_entity.parliamentary_group_id,
                    start_date=start_date,
                    role=member_entity.extracted_role,
                )

                if membership_id:
                    results["created"] += 1
                    logger.info(
                        f"Created/Updated membership for politician ID "
                        f"{member_entity.matched_politician_id} in group ID "
                        f"{member_entity.parliamentary_group_id}"
                    )
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(
                    f"Error creating membership for member {member_entity.id}: {e}"
                )
                results["failed"] += 1

        return results

    def close(self):
        """リポジトリの接続を閉じる"""
        self.extracted_repo.close()
        self.politician_repo.close()
        self.membership_repo.close()
