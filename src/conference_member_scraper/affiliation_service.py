"""Service for creating politician affiliations from scraped conference members"""

import logging
from datetime import date
from typing import Optional

from sqlalchemy import text

from src.conference_member_scraper.models import ConferenceMember, ConferenceMemberList
from src.config.database import get_db_engine
from src.database.politician_affiliation_repository import PoliticianAffiliationRepository
from src.database.politician_repository import PoliticianRepository
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class AffiliationService:
    """スクレイピングした会議体メンバーから政治家所属情報を作成するサービス"""

    def __init__(self):
        self.politician_repo = PoliticianRepository()
        self.affiliation_repo = PoliticianAffiliationRepository()
        self.llm_service = LLMService()

    def find_politician_by_name(self, member: ConferenceMember) -> Optional[int]:
        """メンバー名から既存の政治家を検索"""
        # まず完全一致で検索
        politicians = self.politician_repo.search_by_name(member.name)
        
        if len(politicians) == 1:
            return politicians[0]["id"]
        
        # 政党名も含めて検索
        if member.party_name:
            for politician in politicians:
                if politician.get("party_name") == member.party_name:
                    return politician["id"]
        
        # 複数候補がある場合や見つからない場合はLLMで判定
        if len(politicians) > 0:
            return self._match_politician_with_llm(member, politicians)
        
        # 見つからない場合はNone
        logger.warning(f"Politician not found for member: {member.name}")
        return None

    def _match_politician_with_llm(
        self, member: ConferenceMember, candidates: list[dict]
    ) -> Optional[int]:
        """LLMを使用して最適な政治家を選択"""
        prompt = f"""以下の会議体メンバーと最も一致する政治家を選んでください。

会議体メンバー情報:
- 名前: {member.name}
- 政党: {member.party_name or "不明"}
- 役職: {member.role or "なし"}

候補の政治家:
"""
        for i, candidate in enumerate(candidates):
            prompt += f"{i+1}. {candidate['name']} ({candidate.get('party_name', '無所属')})\n"

        prompt += "\n最も一致する番号を答えてください。一致しない場合は0を答えてください。"

        try:
            response = self.llm_service.get_llm().invoke(prompt)
            choice = int(response.content.strip())
            
            if 1 <= choice <= len(candidates):
                selected = candidates[choice - 1]
                logger.info(f"LLM matched {member.name} to {selected['name']}")
                return selected["id"]
            else:
                logger.info(f"LLM found no match for {member.name}")
                return None
                
        except Exception as e:
            logger.error(f"Error in LLM matching: {e}")
            return None

    def create_affiliations_from_members(
        self, member_list: ConferenceMemberList
    ) -> dict:
        """スクレイピングしたメンバーリストから所属情報を作成"""
        results = {
            "created": 0,
            "updated": 0,
            "failed": 0,
            "not_found": 0,
        }

        for member in member_list.members:
            # 政治家を検索
            politician_id = self.find_politician_by_name(member)
            
            if not politician_id:
                results["not_found"] += 1
                continue

            # 所属情報を作成/更新
            try:
                # デフォルトの開始日（スクレイピング日またはメンバーの開始日）
                start_date = member.start_date or member_list.scraped_at
                
                # UPSERTで所属情報を登録
                affiliation_id = self.affiliation_repo.upsert_affiliation(
                    politician_id=politician_id,
                    conference_id=member_list.conference_id,
                    start_date=start_date,
                    end_date=member.end_date,
                    role=member.role,
                )
                
                if affiliation_id:
                    results["created"] += 1
                    logger.info(
                        f"Created/Updated affiliation for {member.name} "
                        f"(politician_id: {politician_id}, role: {member.role})"
                    )
                else:
                    results["failed"] += 1
                    
            except Exception as e:
                logger.error(f"Error creating affiliation for {member.name}: {e}")
                results["failed"] += 1

        return results

    def process_conference(self, conference_id: int) -> Optional[dict]:
        """会議体の議員紹介URLから所属情報を作成"""
        # 会議体情報を取得
        engine = get_db_engine()
        with engine.connect() as conn:
            query = text("""
                SELECT c.id, c.name, c.members_introduction_url
                FROM conferences c
                WHERE c.id = :conference_id
            """)
            result = conn.execute(query, {"conference_id": conference_id})
            conference = result.fetchone()

        if not conference or not conference.members_introduction_url:
            logger.error(
                f"Conference {conference_id} not found or has no members URL"
            )
            return None

        # スクレイピング実行
        from src.conference_member_scraper.scraper import ConferenceMemberScraper
        
        scraper = ConferenceMemberScraper()
        member_list = asyncio.run(
            scraper.scrape_conference_members(
                conference_id=conference.id,
                conference_name=conference.name,
                url=conference.members_introduction_url,
            )
        )

        # 所属情報を作成
        results = self.create_affiliations_from_members(member_list)
        
        logger.info(
            f"Processed conference {conference.name}: "
            f"created={results['created']}, "
            f"updated={results['updated']}, "
            f"failed={results['failed']}, "
            f"not_found={results['not_found']}"
        )

        return results


# asyncioインポート
import asyncio