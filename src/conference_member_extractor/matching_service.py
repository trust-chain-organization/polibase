"""Service for matching extracted conference members with politicians"""

import logging
from datetime import date, timedelta

from langchain_core.prompts import PromptTemplate

from src.database.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)
from src.database.politician_affiliation_repository import (
    PoliticianAffiliationRepository,
)
from src.database.politician_repository import PoliticianRepository
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class ConferenceMemberMatchingService:
    """抽出された会議体メンバーと政治家をマッチングするサービス"""

    def __init__(self):
        self.extracted_repo = ExtractedConferenceMemberRepository()
        self.politician_repo = PoliticianRepository()
        self.affiliation_repo = PoliticianAffiliationRepository()
        self.llm_service = LLMService()

    def find_politician_candidates(
        self, extracted_name: str, party_name: str | None
    ) -> list[dict]:
        """候補となる政治家を検索"""
        # 名前で検索（部分一致も含む）
        candidates = self.politician_repo.search_by_name(extracted_name)

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
        self, extracted_member: dict, candidates: list[dict]
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
            template="""以下の抽出された議員情報と最も一致する政治家を選んでください。

抽出された議員情報:
- 名前: {extracted_name}
- 政党: {extracted_party}
- 役職: {extracted_role}
- 会議体: {conference_name}

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
                "conference_name",
                "candidates_list",
            ],
        )

        # 候補リストを作成
        candidates_text = ""
        for i, candidate in enumerate(candidates, 1):
            party_info = f"（{candidate.get('party_name', '無所属')}）"
            additional_info = []
            if candidate.get("position"):
                additional_info.append(candidate["position"])
            if candidate.get("prefecture"):
                additional_info.append(candidate["prefecture"])

            info_str = f" - {', '.join(additional_info)}" if additional_info else ""
            candidates_text += f"{i}. {candidate['name']} {party_info}{info_str}\n"

        prompt = prompt_template.format(
            extracted_name=extracted_member["extracted_name"],
            extracted_party=extracted_member.get("extracted_party_name", "不明"),
            extracted_role=extracted_member.get("extracted_role", "委員"),
            conference_name=extracted_member.get("conference_name", ""),
            candidates_list=candidates_text.strip(),
        )

        try:
            response = self.llm_service.llm.invoke(prompt)
            content = response.content.strip()

            # レスポンスをパース
            lines = content.split("\n")
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
                    f"politician ID {selected_politician_id} "
                    f"with confidence {confidence}"
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

    def process_extracted_member(self, extracted_member: dict) -> dict:
        """単一の抽出メンバーを処理"""
        result = {
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
                    matched_politician_id=None,
                    matching_confidence=0.0,
                    matching_status="no_match",
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
                        matched_politician_id=politician_id,
                        matching_confidence=confidence,
                        matching_status="matched",
                    )
                    result["status"] = "matched"
                    result["politician_id"] = politician_id
                    result["confidence"] = confidence

                elif politician_id and confidence >= 0.5:
                    # 要確認
                    self.extracted_repo.update_matching_result(
                        member_id=extracted_member["id"],
                        matched_politician_id=politician_id,
                        matching_confidence=confidence,
                        matching_status="needs_review",
                    )
                    result["status"] = "needs_review"
                    result["politician_id"] = politician_id
                    result["confidence"] = confidence

                else:
                    # マッチング失敗
                    self.extracted_repo.update_matching_result(
                        member_id=extracted_member["id"],
                        matched_politician_id=None,
                        matching_confidence=0.0,
                        matching_status="no_match",
                    )
                    result["status"] = "no_match"

        except Exception as e:
            logger.error(f"Error processing member {extracted_member['id']}: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        return result

    def process_pending_members(self, conference_id: int | None = None) -> dict:
        """未処理の抽出メンバーを処理"""
        # 未処理メンバーを取得
        pending_members = self.extracted_repo.get_pending_members(conference_id)

        results = {
            "total": len(pending_members),
            "matched": 0,
            "no_match": 0,
            "needs_review": 0,
            "error": 0,
        }

        logger.info(f"Processing {len(pending_members)} pending members")

        for member in pending_members:
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

    def create_affiliations_from_matched(
        self, conference_id: int | None = None, start_date: date | None = None
    ) -> dict:
        """マッチング済みメンバーから所属情報を作成"""
        # マッチング済みメンバーを取得
        matched_members = self.extracted_repo.get_matched_members(conference_id)

        if not start_date:
            start_date = date.today()

        results = {
            "total": len(matched_members),
            "created": 0,
            "updated": 0,
            "failed": 0,
        }

        logger.info(f"Creating affiliations for {len(matched_members)} matched members")

        for member in matched_members:
            try:
                # 既存のアクティブな所属情報を確認
                repo = self.affiliation_repo
                existing_affiliations = (
                    repo.get_active_affiliations_by_politician_and_conference(
                        politician_id=member["matched_politician_id"],
                        conference_id=member["conference_id"],
                    )
                )

                # 既存のアクティブな所属がある場合の処理
                # 基本方針：
                # - 新しい開始日より前の所属は、新開始日の前日で終了
                # - 同じ開始日の所属はupsertで更新される
                # - 新しい開始日より後の所属は保持（将来の予定として）
                for existing in existing_affiliations:
                    if existing["start_date"] < start_date:
                        # 既存の所属が新しい開始日より前の場合、前日で終了
                        end_date = start_date - timedelta(days=1)
                        self.affiliation_repo.end_affiliation(
                            affiliation_id=existing["id"], end_date=end_date
                        )
                        logger.info(
                            f"Ended existing affiliation {existing['id']} for "
                            f"politician {member['politician_name']} on {end_date}"
                        )

                # 所属情報をUPSERT
                affiliation_id = self.affiliation_repo.upsert_affiliation(
                    politician_id=member["matched_politician_id"],
                    conference_id=member["conference_id"],
                    start_date=start_date,
                    role=member.get("extracted_role"),
                )

                if affiliation_id:
                    results["created"] += 1
                    logger.info(
                        f"Created/Updated affiliation for politician "
                        f"{member['politician_name']} in {member['conference_name']}"
                    )
                else:
                    results["failed"] += 1

            except Exception as e:
                logger.error(
                    f"Error creating affiliation for member {member['id']}: {e}"
                )
                results["failed"] += 1

        return results

    def close(self):
        """リポジトリの接続を閉じる"""
        self.extracted_repo.close()
        self.politician_repo.close()
        self.affiliation_repo.close()
