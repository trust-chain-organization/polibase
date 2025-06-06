"""Repository for managing politician data"""
from typing import List, Dict, Optional
from sqlalchemy import text
from src.config.database import get_db_engine
import logging

logger = logging.getLogger(__name__)


class PoliticianRepository:
    def __init__(self):
        self.engine = get_db_engine()
    
    def create_politician(self, name: str, political_party_id: int, 
                         position: Optional[str] = None,
                         prefecture: Optional[str] = None,
                         electoral_district: Optional[str] = None,
                         profile_url: Optional[str] = None) -> Optional[int]:
        """新しい政治家を作成"""
        with self.engine.connect() as conn:
            try:
                # 既存の政治家をチェック
                check_query = text("""
                    SELECT id FROM politicians 
                    WHERE name = :name AND political_party_id = :party_id
                """)
                existing = conn.execute(check_query, {
                    "name": name,
                    "party_id": political_party_id
                }).fetchone()
                
                if existing:
                    logger.info(f"Politician {name} already exists with id: {existing.id}")
                    return existing.id
                
                # 新規作成
                insert_query = text("""
                    INSERT INTO politicians (name, political_party_id, position, 
                                           prefecture, electoral_district, profile_url, speaker_id)
                    VALUES (:name, :party_id, :position, :prefecture, 
                            :electoral_district, :profile_url, NULL)
                    RETURNING id
                """)
                
                result = conn.execute(insert_query, {
                    "name": name,
                    "party_id": political_party_id,
                    "position": position,
                    "prefecture": prefecture,
                    "electoral_district": electoral_district,
                    "profile_url": profile_url
                })
                conn.commit()
                
                politician_id = result.fetchone().id
                logger.info(f"Created politician: {name} with id: {politician_id}")
                return politician_id
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error creating politician: {e}")
                return None
    
    def bulk_create_politicians(self, politicians_data: List[Dict]) -> List[int]:
        """複数の政治家を一括作成"""
        created_ids = []
        for data in politicians_data:
            politician_id = self.create_politician(
                name=data.get('name'),
                political_party_id=data.get('political_party_id'),
                position=data.get('position'),
                prefecture=data.get('prefecture'),
                electoral_district=data.get('electoral_district'),
                profile_url=data.get('profile_url')
            )
            if politician_id:
                created_ids.append(politician_id)
        
        return created_ids
    
    def get_politicians_by_party(self, party_id: int) -> List[Dict]:
        """特定の政党の政治家を取得"""
        with self.engine.connect() as conn:
            query = text("""
                SELECT id, name, position, prefecture, electoral_district, profile_url
                FROM politicians
                WHERE political_party_id = :party_id
                ORDER BY name
            """)
            result = conn.execute(query, {"party_id": party_id})
            return [dict(row._mapping) for row in result]
    
    def update_politician(self, politician_id: int, **kwargs) -> bool:
        """政治家情報を更新"""
        with self.engine.connect() as conn:
            try:
                # 更新可能なフィールドをフィルタリング
                allowed_fields = ['name', 'position', 'prefecture', 
                                'electoral_district', 'profile_url', 'political_party_id']
                update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
                
                if not update_fields:
                    return True
                
                # UPDATE文を構築
                set_clause = ", ".join([f"{field} = :{field}" for field in update_fields])
                query = text(f"""
                    UPDATE politicians
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """)
                
                update_fields['id'] = politician_id
                conn.execute(query, update_fields)
                conn.commit()
                
                logger.info(f"Updated politician id: {politician_id}")
                return True
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error updating politician: {e}")
                return False
    
    def close(self):
        """リソースをクリーンアップ"""
        self.engine.dispose()