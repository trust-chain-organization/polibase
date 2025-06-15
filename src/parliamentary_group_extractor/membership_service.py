"""議員団メンバーシップ管理サービス"""

import logging
from datetime import date

from langchain_google_genai import ChatGoogleGenerativeAI

from src.database.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)
from src.database.parliamentary_group_repository import (
    ParliamentaryGroupMembershipRepository,
    ParliamentaryGroupRepository,
)
from src.database.politician_repository import PoliticianRepository

from .extractor import ParliamentaryGroupMemberExtractor

logger = logging.getLogger(__name__)


class ParliamentaryGroupMembershipService:
    """議員団メンバーシップを管理するサービス"""

    def __init__(self, llm: ChatGoogleGenerativeAI | None = None):
        self.extractor = ParliamentaryGroupMemberExtractor(llm)
        self.pg_repo = ParliamentaryGroupRepository()
        self.pgm_repo = ParliamentaryGroupMembershipRepository()
        self.politician_repo = PoliticianRepository()
        self.extracted_repo = ExtractedParliamentaryGroupMemberRepository()

        # マッチング用のLLM
        if llm is None:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp", temperature=0.1
            )
        else:
            self.llm = llm

    async def extract_members(
        self, parliamentary_group_id: int, force: bool = False
    ) -> dict:
        """議員団URLからメンバーを抽出してステージングテーブルに保存"""
        # 議員団情報を取得
        group = self.pg_repo.get_parliamentary_group_by_id(parliamentary_group_id)
        if not group:
            raise ValueError(f"Parliamentary group {parliamentary_group_id} not found")

        if not group.get("url"):
            raise ValueError(
                f"Parliamentary group {group['name']} has no URL configured"
            )

        # 既存データをクリア（強制更新の場合）
        if force:
            cleared = self.extracted_repo.clear_extracted_members(
                parliamentary_group_id
            )
            if cleared > 0:
                logger.info(f"Cleared {cleared} existing extracted members")

        # メンバーを抽出
        member_list = await self.extractor.extract_from_url(group["url"], group["name"])

        if not member_list.members:
            logger.warning(f"No members found for {group['name']}")
            return {
                "parliamentary_group": group["name"],
                "url": group["url"],
                "extracted_count": 0,
                "saved_count": 0,
                "errors": [],
            }

        # 抽出結果を保存
        results = {
            "parliamentary_group": group["name"],
            "url": group["url"],
            "extracted_count": len(member_list.members),
            "saved_count": 0,
            "errors": [],
        }

        for member in member_list.members:
            try:
                saved = self.extracted_repo.create_extracted_member(
                    parliamentary_group_id=parliamentary_group_id,
                    extracted_name=member.name,
                    extracted_role=member.role,
                    extracted_party_name=member.political_party,
                    extracted_electoral_district=member.electoral_district,
                    extracted_profile_url=member.profile_url,
                    source_url=group["url"],
                )

                if saved:
                    results["saved_count"] += 1
                    logger.info(f"Saved extracted member: {member.name}")

            except Exception as e:
                logger.error(f"Error saving member {member.name}: {e}")
                results["errors"].append(f"Error saving {member.name}: {str(e)}")

        return results

    async def match_members(self, parliamentary_group_id: int | None = None) -> dict:
        """抽出済みメンバーを既存の政治家とマッチング"""
        # 未処理のメンバーを取得
        pending_members = self.extracted_repo.get_pending_members(
            parliamentary_group_id
        )

        if not pending_members:
            logger.info("No pending members to match")
            return {
                "processed_count": 0,
                "matched_count": 0,
                "needs_review_count": 0,
                "no_match_count": 0,
                "errors": [],
            }

        results = {
            "processed_count": len(pending_members),
            "matched_count": 0,
            "needs_review_count": 0,
            "no_match_count": 0,
            "errors": [],
        }

        for member in pending_members:
            try:
                # マッチング実行
                match_result = await self._match_politician_with_confidence(member)

                # 結果を更新
                self.extracted_repo.update_matching_result(
                    extracted_member_id=member["id"],
                    matched_politician_id=match_result["politician_id"],
                    matching_status=match_result["status"],
                    matching_confidence=match_result["confidence"],
                    matching_notes=match_result["notes"],
                )

                # カウント更新
                if match_result["status"] == "matched":
                    results["matched_count"] += 1
                elif match_result["status"] == "needs_review":
                    results["needs_review_count"] += 1
                elif match_result["status"] == "no_match":
                    results["no_match_count"] += 1

                logger.info(
                    f"Matched {member['extracted_name']}: {match_result['status']} "
                    f"(confidence: {match_result['confidence']})"
                )

            except Exception as e:
                logger.error(f"Error matching member {member['extracted_name']}: {e}")
                results["errors"].append(
                    f"Error matching {member['extracted_name']}: {str(e)}"
                )

        return results

    async def create_memberships_from_matched(
        self, parliamentary_group_id: int, start_date: date | None = None
    ) -> dict:
        """マッチング済みメンバーからメンバーシップを作成"""
        # マッチング済みメンバーを取得
        matched_members = self.extracted_repo.get_matched_members(
            parliamentary_group_id
        )

        if not matched_members:
            logger.info("No matched members to create memberships")
            return {
                "processed_count": 0,
                "created_count": 0,
                "updated_count": 0,
                "skipped_count": 0,
                "errors": [],
            }

        results = {
            "processed_count": len(matched_members),
            "created_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "errors": [],
        }

        if start_date is None:
            start_date = date.today()

        for member in matched_members:
            try:
                politician_id = member["matched_politician_id"]
                if not politician_id:
                    continue

                # 既存のメンバーシップを確認
                current_groups = self.pgm_repo.get_politician_groups(
                    politician_id, current_only=True
                )

                # 既に同じ議員団に所属している場合はスキップ
                is_already_member = any(
                    g["parliamentary_group_id"] == parliamentary_group_id
                    for g in current_groups
                )

                if not is_already_member:
                    # メンバーシップを作成
                    self.pgm_repo.add_membership(
                        politician_id=politician_id,
                        parliamentary_group_id=parliamentary_group_id,
                        start_date=start_date,
                        role=member["extracted_role"],
                    )
                    results["created_count"] += 1
                    logger.info(
                        f"Created membership for {member['extracted_name']} "
                        f"(politician_id: {politician_id})"
                    )
                else:
                    results["skipped_count"] += 1
                    logger.info(f"{member['extracted_name']} is already a member")

            except Exception as e:
                logger.error(
                    f"Error creating membership for {member['extracted_name']}: {e}"
                )
                results["errors"].append(
                    f"Error for {member['extracted_name']}: {str(e)}"
                )

        return results

    # 旧メソッドは互換性のため残す（deprecated）
    async def extract_and_create_memberships(
        self, parliamentary_group_id: int, dry_run: bool = False
    ) -> dict:
        """[Deprecated] 議員団URLからメンバーを抽出し、メンバーシップを作成"""
        logger.warning(
            "extract_and_create_memberships is deprecated. "
            "Use extract_members, match_members, and "
            "create_memberships_from_matched instead."
        )

        # ステップ1: 抽出
        extract_result = await self.extract_members(parliamentary_group_id, force=True)

        # ステップ2: マッチング
        match_result = await self.match_members(parliamentary_group_id)

        # ステップ3: メンバーシップ作成（dry_runでない場合）
        if not dry_run and match_result["matched_count"] > 0:
            membership_result = await self.create_memberships_from_matched(
                parliamentary_group_id
            )
        else:
            membership_result = {
                "created_count": 0,
                "skipped_count": 0,
            }

        # 結果を統合
        return {
            "parliamentary_group": extract_result.get("parliamentary_group", ""),
            "url": extract_result.get("url", ""),
            "extracted_count": extract_result.get("extracted_count", 0),
            "matched_count": match_result.get("matched_count", 0),
            "created_count": membership_result.get("created_count", 0),
            "errors": (
                extract_result.get("errors", [])
                + match_result.get("errors", [])
                + membership_result.get("errors", [])
            ),
        }

    async def _match_politician_with_confidence(self, extracted_member: dict) -> dict:
        """抽出済みメンバーを既存の政治家とマッチングし、信頼度を返す"""
        # 名前で検索
        politicians = self.politician_repo.search_by_name(
            extracted_member["extracted_name"]
        )

        # 政党名でフィルタリング（あれば）
        if extracted_member.get("extracted_party_name") and politicians:
            # 政党名が一致する候補を優先
            filtered = [
                p
                for p in politicians
                if p.get("party_name", "").lower()
                == extracted_member["extracted_party_name"].lower()
            ]
            if filtered:
                politicians = filtered

        if not politicians:
            return {
                "politician_id": None,
                "status": "no_match",
                "confidence": 0.0,
                "notes": "一致する政治家が見つかりませんでした",
            }

        if len(politicians) == 1:
            # 1人だけ見つかった場合
            # 名前の完全一致した場合は高信頼度
            if politicians[0]["name"] == extracted_member["extracted_name"]:
                return {
                    "politician_id": politicians[0]["id"],
                    "status": "matched",
                    "confidence": 0.95,
                    "notes": "名前が完全一致",
                }
            else:
                # 部分一致の場合はLLMで確認
                return await self._llm_match_single(extracted_member, politicians[0])

        # 複数候補がある場合はLLMで最適なマッチを選択
        return await self._llm_match_multiple(extracted_member, politicians)

    async def _llm_match_single(self, extracted_member: dict, politician: dict) -> dict:
        """単一候補とのLLMマッチング"""
        prompt = f"""
以下の議員団メンバーと政治家が同一人物か判定してください。

議員団メンバー情報:
- 名前: {extracted_member["extracted_name"]}
- 政党: {extracted_member.get("extracted_party_name") or "不明"}
- 選挙区: {extracted_member.get("extracted_electoral_district") or "不明"}
- 役職: {extracted_member.get("extracted_role") or "なし"}

政治家情報:
- 名前: {politician["name"]}
- 政党: {politician.get("party_name", "無所属")}
- 役職: {politician.get("position", "不明")}
- 選挙区: {politician.get("electoral_district", "不明")}
- 都道府県: {politician.get("prefecture", "不明")}

以下の形式で回答してください:
- 同一人物の可能性が高い場合: "YES [0.7-1.0の信頼度]"
- 同一人物の可能性が低い場合: "NO [0.0-0.3の信頼度]"
- 判断が難しい場合: "MAYBE [0.3-0.7の信頼度]"

例: "YES 0.95" または "NO 0.1" または "MAYBE 0.5"
"""

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()

            parts = content.split()
            if len(parts) >= 2:
                decision = parts[0].upper()
                confidence = float(parts[1])

                if decision == "YES" and confidence >= 0.7:
                    return {
                        "politician_id": politician["id"],
                        "status": "matched",
                        "confidence": confidence,
                        "notes": "LLMによるマッチング",
                    }
                elif decision == "MAYBE" or 0.5 <= confidence < 0.7:
                    return {
                        "politician_id": politician["id"],
                        "status": "needs_review",
                        "confidence": confidence,
                        "notes": "LLMマッチングで確認が必要",
                    }
                else:
                    return {
                        "politician_id": None,
                        "status": "no_match",
                        "confidence": confidence,
                        "notes": "LLMマッチングで不一致",
                    }
            else:
                raise ValueError(f"Invalid LLM response format: {content}")

        except Exception as e:
            logger.error(f"Error in LLM single matching: {e}")
            # エラーの場合は低信頼度でneeds_review
            return {
                "politician_id": politician["id"],
                "status": "needs_review",
                "confidence": 0.5,
                "notes": f"LLMエラー: {str(e)}",
            }

    async def _llm_match_multiple(
        self, extracted_member: dict, politicians: list
    ) -> dict:
        """複数候補とのLLMマッチング"""
        prompt = f"""
以下の議員団メンバー情報に最も適合する政治家を選んでください。

議員団メンバー情報:
- 名前: {extracted_member["extracted_name"]}
- 政党: {extracted_member.get("extracted_party_name") or "不明"}
- 選挙区: {extracted_member.get("extracted_electoral_district") or "不明"}
- 役職: {extracted_member.get("extracted_role") or "なし"}

候補の政治家:
"""
        for i, pol in enumerate(politicians):
            prompt += f"""
{i + 1}. {pol["name"]}
   - 政党: {pol.get("party_name", "無所属")}
   - 役職: {pol.get("position", "不明")}
   - 選挙区: {pol.get("electoral_district", "不明")}
   - 都道府県: {pol.get("prefecture", "不明")}
"""

        prompt += """

以下の形式で回答してください:
[候補番号] [0.0-1.0の信頼度]

例: "2 0.85"

適合する候補がない場合は "0 0.0" と回答してください。
"""

        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content.strip()

            parts = content.split()
            if len(parts) >= 2:
                choice = int(parts[0])
                confidence = float(parts[1])

                if 1 <= choice <= len(politicians):
                    politician = politicians[choice - 1]

                    if confidence >= 0.7:
                        return {
                            "politician_id": politician["id"],
                            "status": "matched",
                            "confidence": confidence,
                            "notes": f"LLMが{len(politicians)}名の候補から選択",
                        }
                    elif confidence >= 0.5:
                        return {
                            "politician_id": politician["id"],
                            "status": "needs_review",
                            "confidence": confidence,
                            "notes": (
                                f"LLMが{len(politicians)}名の候補から選択（信頼度低）"
                            ),
                        }
                    else:
                        return {
                            "politician_id": None,
                            "status": "no_match",
                            "confidence": confidence,
                            "notes": (
                                f"{len(politicians)}名の候補がありましたが、"
                                "信頼度が低いためマッチさせませんでした"
                            ),
                        }
                else:
                    return {
                        "politician_id": None,
                        "status": "no_match",
                        "confidence": 0.0,
                        "notes": (
                            f"{len(politicians)}名の候補から"
                            "適合者が見つかりませんでした"
                        ),
                    }
            else:
                raise ValueError(f"Invalid LLM response format: {content}")

        except Exception as e:
            logger.error(f"Error in LLM multiple matching: {e}")
            # エラーの場合は名前の完全一致を試みる
            for pol in politicians:
                if pol["name"] == extracted_member["extracted_name"]:
                    return {
                        "politician_id": pol["id"],
                        "status": "needs_review",
                        "confidence": 0.6,
                        "notes": f"LLMエラーのため名前一致で選択: {str(e)}",
                    }

            return {
                "politician_id": None,
                "status": "no_match",
                "confidence": 0.0,
                "notes": f"LLMエラー: {str(e)}",
            }
