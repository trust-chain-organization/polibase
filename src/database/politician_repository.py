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
                         profile_url: Optional[str] = None,
                         party_position: Optional[str] = None) -> Optional[int]:
        """新しい政治家を作成（既存の場合は更新）"""
        with self.engine.connect() as conn:
            try:
                # 既存の政治家をチェック（名前と政党でマッチング）
                check_query = text("""
                    SELECT id, position, prefecture, electoral_district, 
                           profile_url, party_position
                    FROM politicians 
                    WHERE name = :name AND political_party_id = :party_id
                """)
                existing = conn.execute(check_query, {
                    "name": name,
                    "party_id": political_party_id
                }).fetchone()
                
                if existing:
                    # 既存レコードがある場合、更新が必要かチェック
                    needs_update = False
                    update_fields = {}
                    
                    # 各フィールドを比較
                    if position and position != existing.position:
                        update_fields['position'] = position
                        needs_update = True
                    if prefecture and prefecture != existing.prefecture:
                        update_fields['prefecture'] = prefecture
                        needs_update = True
                    if electoral_district and electoral_district != existing.electoral_district:
                        update_fields['electoral_district'] = electoral_district
                        needs_update = True
                    if profile_url and profile_url != existing.profile_url:
                        update_fields['profile_url'] = profile_url
                        needs_update = True
                    if party_position and party_position != existing.party_position:
                        update_fields['party_position'] = party_position
                        needs_update = True
                    
                    if needs_update:
                        # 更新を実行
                        set_clause = ", ".join([f"{field} = :{field}" for field in update_fields])
                        update_query = text(f"""
                            UPDATE politicians
                            SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                            WHERE id = :id
                        """)
                        update_fields['id'] = existing.id
                        conn.execute(update_query, update_fields)
                        conn.commit()
                        logger.info(f"Updated politician: {name} (id: {existing.id})")
                    else:
                        logger.info(f"Politician {name} already exists with id: {existing.id}, no update needed")
                    
                    return existing.id
                
                # 新規作成
                insert_query = text("""
                    INSERT INTO politicians (name, political_party_id, position, 
                                           prefecture, electoral_district, profile_url, 
                                           party_position, speaker_id)
                    VALUES (:name, :party_id, :position, :prefecture, 
                            :electoral_district, :profile_url, :party_position, NULL)
                    RETURNING id
                """)
                
                result = conn.execute(insert_query, {
                    "name": name,
                    "party_id": political_party_id,
                    "position": position,
                    "prefecture": prefecture,
                    "electoral_district": electoral_district,
                    "profile_url": profile_url,
                    "party_position": party_position
                })
                conn.commit()
                
                politician_id = result.fetchone().id
                logger.info(f"Created new politician: {name} with id: {politician_id}")
                return politician_id
                
            except Exception as e:
                conn.rollback()
                logger.error(f"Error creating/updating politician: {e}")
                return None
    
    def bulk_create_politicians(self, politicians_data: List[Dict]) -> Dict[str, List[int]]:
        """複数の政治家を一括作成・更新"""
        stats = {
            'created': [],
            'updated': [],
            'skipped': [],
            'errors': []
        }
        
        for data in politicians_data:
            # 処理前の状態を確認
            with self.engine.connect() as conn:
                check_query = text("""
                    SELECT id FROM politicians 
                    WHERE name = :name AND political_party_id = :party_id
                """)
                existing = conn.execute(check_query, {
                    "name": data.get('name'),
                    "party_id": data.get('political_party_id')
                }).fetchone()
                
                was_existing = existing is not None
            
            # create_politicianは内部で更新/作成を判断
            politician_id = self.create_politician(
                name=data.get('name'),
                political_party_id=data.get('political_party_id'),
                position=data.get('position'),
                prefecture=data.get('prefecture'),
                electoral_district=data.get('electoral_district'),
                profile_url=data.get('profile_url'),
                party_position=data.get('party_position')
            )
            
            if politician_id:
                if was_existing:
                    # ログを確認して更新されたかスキップされたか判断
                    # 簡易的に、既存の場合は更新としてカウント
                    stats['updated'].append(politician_id)
                else:
                    stats['created'].append(politician_id)
            else:
                stats['errors'].append(data.get('name', 'Unknown'))
        
        logger.info(f"Bulk operation completed - Created: {len(stats['created'])}, "
                   f"Updated: {len(stats['updated'])}, Errors: {len(stats['errors'])}")
        
        return stats
    
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