"""
Conversations テーブルへのデータ操作を管理するリポジトリクラス
"""
from typing import List, Optional
from sqlalchemy import text
from src.config.database import get_db_session
from src.minutes_divide_processor.models import SpeakerAndSpeechContent, SpeakerAndSpeechContentList


class ConversationRepository:
    """Conversationsテーブルに対するデータベース操作を管理するクラス"""
    
    def __init__(self):
        self.session = get_db_session()
    
    def save_speaker_and_speech_content_list(self, speaker_and_speech_content_list: List[SpeakerAndSpeechContent]) -> List[int]:
        """
        SpeakerAndSpeechContentのリストをConversationsテーブルに保存する
        
        Args:
            speaker_and_speech_content_list: 保存する発言データリスト
            
        Returns:
            List[int]: 保存されたレコードのIDリスト
        """
        saved_ids = []
        
        try:
            for speaker_and_speech_content in speaker_and_speech_content_list:
                conversation_id = self._save_conversation(speaker_and_speech_content)
                if conversation_id:
                    saved_ids.append(conversation_id)
            
            self.session.commit()
            print(f"✅ {len(saved_ids)}件の発言データをデータベースに保存しました")
            return saved_ids
            
        except Exception as e:
            self.session.rollback()
            print(f"❌ データベース保存エラー: {e}")
            raise
        finally:
            self.session.close()
    
    def _save_conversation(self, speaker_and_speech_content: SpeakerAndSpeechContent) -> Optional[int]:
        """
        個別のSpeakerAndSpeechContentをConversationsテーブルに保存する
        
        Args:
            speaker_and_speech_content: 保存する発言データ
            
        Returns:
            Optional[int]: 保存されたレコードのID
        """
        # speaker_idを検索（名前の完全一致または部分一致）
        speaker_id = self._find_speaker_id(speaker_and_speech_content.speaker)
        
        # 新規レコードの挿入
        query = text("""
            INSERT INTO conversations (
                minutes_id, speaker_id, speaker_name, comment, sequence_number, 
                chapter_number, sub_chapter_number
            )
            VALUES (:minutes_id, :speaker_id, :speaker_name, :comment, :sequence_number, 
                    :chapter_number, :sub_chapter_number)
            RETURNING id
        """)
        
        result = self.session.execute(query, {
            'minutes_id': None,  # 現時点では議事録IDは未設定
            'speaker_id': speaker_id,
            'speaker_name': speaker_and_speech_content.speaker,
            'comment': speaker_and_speech_content.speech_content,
            'sequence_number': speaker_and_speech_content.speech_order,
            'chapter_number': speaker_and_speech_content.chapter_number,
            'sub_chapter_number': speaker_and_speech_content.sub_chapter_number
        })
        
        conversation_id = result.fetchone()[0]
        
        if speaker_id:
            print(f"➕ 新規追加: {speaker_and_speech_content.speaker} (ID: {conversation_id}, Speaker ID: {speaker_id})")
        else:
            print(f"➕ 新規追加: {speaker_and_speech_content.speaker} (ID: {conversation_id}, Speaker ID: NULL)")
        
        return conversation_id
    
    def _find_speaker_id(self, speaker_name: str) -> Optional[int]:
        """
        既存のSpeakerレコードから一致する発言者IDを検索する
        
        Args:
            speaker_name: 検索する発言者名
            
        Returns:
            Optional[int]: 一致するSpeakerのID（見つからない場合はNone）
        """
        # 完全一致を優先して検索
        query = text("""
            SELECT id FROM speakers 
            WHERE name = :speaker_name
            LIMIT 1
        """)
        
        result = self.session.execute(query, {'speaker_name': speaker_name})
        row = result.fetchone()
        
        if row:
            return row[0]
        
        # 括弧内の名前を抽出して検索（例: "委員長(平山たかお)" → "平山たかお"）
        import re
        match = re.search(r'\(([^)]+)\)', speaker_name)
        if match:
            extracted_name = match.group(1)
            query = text("""
                SELECT id FROM speakers 
                WHERE name = :extracted_name
                LIMIT 1
            """)
            
            result = self.session.execute(query, {'extracted_name': extracted_name})
            row = result.fetchone()
            
            if row:
                return row[0]
        
        # 記号を除去して検索（例: "◆委員(下村あきら)" → "委員(下村あきら)"）
        cleaned_name = re.sub(r'^[◆○◎]', '', speaker_name)
        if cleaned_name != speaker_name:
            # 再帰的に検索
            return self._find_speaker_id(cleaned_name)
        
        # それでも見つからない場合は部分一致を試行
        query = text("""
            SELECT id FROM speakers 
            WHERE name LIKE :speaker_pattern
            OR :speaker_name LIKE CONCAT('%', name, '%')
            LIMIT 1
        """)
        
        result = self.session.execute(query, {
            'speaker_pattern': f'%{speaker_name}%',
            'speaker_name': speaker_name
        })
        row = result.fetchone()
        
        return row[0] if row else None
    
    def get_all_conversations(self) -> List[dict]:
        """
        全てのConversationレコードを取得する
        
        Returns:
            List[dict]: Conversationレコードのリスト
        """
        query = text("""
            SELECT c.id, c.minutes_id, c.speaker_id, c.speaker_name, c.comment, 
                   c.sequence_number, c.chapter_number, c.sub_chapter_number,
                   c.created_at, c.updated_at, s.name as linked_speaker_name
            FROM conversations c
            LEFT JOIN speakers s ON c.speaker_id = s.id
            ORDER BY c.sequence_number ASC
        """)
        
        result = self.session.execute(query)
        columns = result.keys()
        
        conversations = []
        for row in result.fetchall():
            conversation_dict = dict(zip(columns, row))
            conversations.append(conversation_dict)
        
        self.session.close()
        return conversations
    
    def get_conversations_count(self) -> int:
        """
        Conversationsテーブルのレコード数を取得する
        
        Returns:
            int: レコード数
        """
        query = text("SELECT COUNT(*) FROM conversations")
        result = self.session.execute(query)
        count = result.fetchone()[0]
        self.session.close()
        return count
    
    def get_speaker_linking_stats(self) -> dict:
        """
        発言者の紐付け統計を取得する
        
        Returns:
            dict: 紐付け統計（総数、紐付けあり、紐付けなし）
        """
        query = text("""
            SELECT 
                COUNT(*) as total_conversations,
                COUNT(speaker_id) as linked_conversations,
                COUNT(*) - COUNT(speaker_id) as unlinked_conversations
            FROM conversations
        """)
        
        result = self.session.execute(query)
        row = result.fetchone()
        
        stats = {
            'total_conversations': row[0],
            'linked_conversations': row[1], 
            'unlinked_conversations': row[2]
        }
        
        self.session.close()
        return stats
    
    def update_speaker_links(self) -> int:
        """
        既存のConversationsレコードのspeaker_idを更新する
        
        Returns:
            int: 更新されたレコード数
        """
        try:
            # speaker_idがNULLのレコードを取得
            query = text("""
                SELECT id, speaker_name FROM conversations 
                WHERE speaker_id IS NULL
            """)
            
            result = self.session.execute(query)
            unlinked_conversations = result.fetchall()
            
            updated_count = 0
            
            for conversation_id, speaker_name in unlinked_conversations:
                speaker_id = self._find_speaker_id(speaker_name)
                
                if speaker_id:
                    # speaker_idを更新
                    update_query = text("""
                        UPDATE conversations 
                        SET speaker_id = :speaker_id 
                        WHERE id = :conversation_id
                    """)
                    
                    self.session.execute(update_query, {
                        'speaker_id': speaker_id,
                        'conversation_id': conversation_id
                    })
                    
                    updated_count += 1
                    print(f"🔗 Speaker紐付け更新: {speaker_name} → Speaker ID: {speaker_id}")
            
            self.session.commit()
            print(f"✅ {updated_count}件のSpeaker紐付けを更新しました")
            return updated_count
            
        except Exception as e:
            self.session.rollback()
            print(f"❌ Speaker紐付け更新エラー: {e}")
            raise
        finally:
            self.session.close()
