"""議員団メンバーシップ管理サービス"""

import logging
from datetime import date

from langchain_google_genai import ChatGoogleGenerativeAI

from src.database.parliamentary_group_repository import (
    ParliamentaryGroupMembershipRepository,
    ParliamentaryGroupRepository,
)
from src.database.politician_repository import PoliticianRepository

from .extractor import ParliamentaryGroupMemberExtractor
from .models import ParliamentaryGroupMember

logger = logging.getLogger(__name__)


class ParliamentaryGroupMembershipService:
    """議員団メンバーシップを管理するサービス"""

    def __init__(self, llm: ChatGoogleGenerativeAI | None = None):
        self.extractor = ParliamentaryGroupMemberExtractor(llm)
        self.pg_repo = ParliamentaryGroupRepository()
        self.pgm_repo = ParliamentaryGroupMembershipRepository()
        self.politician_repo = PoliticianRepository()

        # マッチング用のLLM
        if llm is None:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.0-flash-exp", temperature=0.1
            )
        else:
            self.llm = llm

    async def extract_and_create_memberships(
        self, parliamentary_group_id: int, dry_run: bool = False
    ) -> dict:
        """議員団URLからメンバーを抽出し、メンバーシップを作成"""
        # 議員団情報を取得
        group = self.pg_repo.get_parliamentary_group_by_id(parliamentary_group_id)
        if not group:
            raise ValueError(f"Parliamentary group {parliamentary_group_id} not found")

        if not group.get("url"):
            raise ValueError(
                f"Parliamentary group {group['name']} has no URL configured"
            )

        # メンバーを抽出
        member_list = await self.extractor.extract_from_url(group["url"], group["name"])

        if not member_list.members:
            logger.warning(f"No members found for {group['name']}")
            return {
                "parliamentary_group": group["name"],
                "url": group["url"],
                "extracted_count": 0,
                "matched_count": 0,
                "created_count": 0,
                "errors": [],
            }

        # 各メンバーを既存の政治家とマッチング
        results = {
            "parliamentary_group": group["name"],
            "url": group["url"],
            "extracted_count": len(member_list.members),
            "matched_count": 0,
            "created_count": 0,
            "errors": [],
        }

        for member in member_list.members:
            try:
                politician_id = await self._match_politician(member)

                if politician_id:
                    results["matched_count"] += 1

                    if not dry_run:
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
                                start_date=date.today(),
                                role=member.role,
                            )
                            results["created_count"] += 1
                            logger.info(
                                f"Created membership for {member.name} "
                                f"in {group['name']}"
                            )
                        else:
                            logger.info(
                                f"{member.name} is already a member of {group['name']}"
                            )
                else:
                    logger.warning(f"Could not match politician: {member.name}")
                    results["errors"].append(f"No match found for {member.name}")

            except Exception as e:
                logger.error(f"Error processing member {member.name}: {e}")
                results["errors"].append(f"Error processing {member.name}: {str(e)}")

        return results

    async def _match_politician(self, member: ParliamentaryGroupMember) -> int | None:
        """メンバー情報を既存の政治家とマッチング"""
        # まず政党名でフィルタリング（あれば）
        if member.political_party:
            politicians = self.politician_repo.search_politicians(
                name_query=member.name, party_name=member.political_party
            )
        else:
            politicians = self.politician_repo.search_politicians(
                name_query=member.name
            )

        if not politicians:
            return None

        if len(politicians) == 1:
            # 1人だけ見つかった場合は自動的にマッチ
            return politicians[0]["id"]

        # 複数候補がある場合はLLMで最適なマッチを選択
        prompt = f"""
以下の議員団メンバー情報に最も適合する政治家を選んでください。

議員団メンバー情報:
- 名前: {member.name}
- 政党: {member.political_party or "不明"}
- 選挙区: {member.electoral_district or "不明"}
- 役職: {member.role or "なし"}

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
最も適合する候補の番号を答えてください。適合する候補がない場合は0を答えてください。
番号のみを回答してください。
"""

        try:
            response = await self.llm.ainvoke(prompt)
            choice = int(response.content.strip())

            if 1 <= choice <= len(politicians):
                return politicians[choice - 1]["id"]
            else:
                return None

        except Exception as e:
            logger.error(f"Error in LLM matching: {e}")
            # エラーの場合は名前の完全一致を試みる
            for pol in politicians:
                if pol["name"] == member.name:
                    return pol["id"]
            return None
