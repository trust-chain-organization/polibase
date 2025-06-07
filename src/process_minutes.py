"""
議事録分割処理のメインスクリプト

Processes meeting minutes PDF files and extracts individual conversations.
"""
import logging
import sys
from typing import List, Dict, Any, Optional

from langchain_google_genai import ChatGoogleGenerativeAI

from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.minutes_divide_processor.models import SpeakerAndSpeechContent
from src.database.conversation_repository import ConversationRepository
from src.common.app_logic import setup_environment, load_pdf_text, run_main_process, print_completion_message
from src.exceptions import (
    ProcessingError, APIKeyError, DatabaseError, PDFProcessingError
)

logger = logging.getLogger(__name__)

def save_to_database(speaker_and_speech_content_list: List[SpeakerAndSpeechContent]) -> List[int]:
    """
    SpeakerAndSpeechContentのリストをデータベースのConversationsテーブルに保存する
    
    Args:
        speaker_and_speech_content_list: 保存する発言データリスト
        
    Returns:
        List[int]: 保存されたレコードのIDリスト
        
    Raises:
        DatabaseError: If database save fails
    """
    if not speaker_and_speech_content_list:
        logger.warning("No conversations to save")
        return []
        
    try:
        conversation_repo = ConversationRepository()
        saved_ids = conversation_repo.save_speaker_and_speech_content_list(speaker_and_speech_content_list)
        logger.info(f"Saved {len(saved_ids)} conversations to database")
        return saved_ids
    except Exception as e:
        logger.error(f"Failed to save conversations: {e}")
        raise DatabaseError(
            "Failed to save conversations to database",
            {"count": len(speaker_and_speech_content_list), "error": str(e)}
        )

def display_database_status() -> None:
    """
    データベースの状態を表示する
    
    Raises:
        DatabaseError: If database query fails
    """
    try:
        conversation_repo = ConversationRepository()
        count = conversation_repo.get_conversations_count()
        stats = conversation_repo.get_speaker_linking_stats()
        
        print(f"📊 現在のConversationsテーブルレコード数: {count}件")
        print(f"   - Speaker紐付けあり: {stats['linked_conversations']}件")
        print(f"   - Speaker紐付けなし: {stats['unlinked_conversations']}件")
        
        if count > 0:
            print("\n📋 最新の5件のレコード:")
            conversations = conversation_repo.get_all_conversations()[:5]
            for conv in conversations:
                linked_info = f"→ {conv['linked_speaker_name']}" if conv['linked_speaker_name'] else "（紐付けなし）"
                print(f"  ID: {conv['id']}, 発言者: {conv['speaker_name']} {linked_info}")
                print(f"      発言: {conv['comment'][:50]}...")
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        raise DatabaseError(
            "Failed to retrieve database status",
            {"error": str(e)}
        )


def process_minutes(extracted_text: str) -> List[SpeakerAndSpeechContent]:
    """
    議事録分割処理を実行する
    
    Args:
        extracted_text: 処理対象のテキスト
        
    Returns:
        List[SpeakerAndSpeechContent]: 抽出された発言データ
        
    Raises:
        ProcessingError: If minutes processing fails
        APIKeyError: If API key is not configured
        
    """
    if not extracted_text:
        raise ProcessingError(
            "No text provided for processing",
            {"text_length": 0}
        )
        
    try:
        # Check for API key
        import os
        if not os.getenv("GOOGLE_API_KEY"):
            raise APIKeyError(
                "GOOGLE_API_KEY not set. Please configure it in your .env file",
                {"env_var": "GOOGLE_API_KEY"}
            )
            
        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        agent = MinutesProcessAgent(llm=llm)
        
        logger.info(f"Processing minutes with {len(extracted_text)} characters")
        results = agent.run(original_minutes=extracted_text)
        logger.info(f"Extracted {len(results)} conversations")
        
        return results
        
    except Exception as e:
        if isinstance(e, (ProcessingError, APIKeyError)):
            raise
        logger.error(f"Minutes processing failed: {e}")
        raise ProcessingError(
            "Failed to process meeting minutes",
            {"error": str(e), "text_length": len(extracted_text)}
        )


def main() -> Optional[List[int]]:
    """
    議事録分割処理のメイン関数
    
    Returns:
        List[int]: 保存されたレコードのIDリスト、またはNone
        
    Raises:
        SystemExit: If critical error occurs
    """
    try:
        # 環境設定
        setup_environment()
        
        # PDFテキストの読み込み
        extracted_text = load_pdf_text()
        
        # メイン処理の実行
        return run_main_process(
            process_func=process_minutes,
            process_name="発言データ",
            display_status_func=display_database_status,
            save_func=save_to_database,
            extracted_text=extracted_text
        )
        
    except APIKeyError as e:
        logger.error(f"API key configuration error: {e}")
        print(f"\n❌ 設定エラー: {e}")
        print("   .envファイルにGOOGLE_API_KEYを設定してください")
        sys.exit(1)
        
    except PDFProcessingError as e:
        logger.error(f"PDF processing error: {e}")
        print(f"\n❌ PDF処理エラー: {e}")
        sys.exit(1)
        
    except DatabaseError as e:
        logger.error(f"Database error: {e}")
        print(f"\n❌ データベースエラー: {e}")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ 予期しないエラーが発生しました: {e}")
        sys.exit(1)


if __name__ == "__main__":
    result = main()
    if result:
        print_completion_message(result, "議事録分割処理")
