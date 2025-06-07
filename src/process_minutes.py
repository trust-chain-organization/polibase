"""
議事録分割処理のメインスクリプト

Processes meeting minutes PDF files and extracts individual conversations.
"""

import logging
import sys

from langchain_google_genai import ChatGoogleGenerativeAI

from src.common.app_logic import (
    load_pdf_text,
    print_completion_message,
    run_main_process,
    setup_environment,
)
from src.config import config
from src.database.conversation_repository import ConversationRepository
from src.exceptions import (
    APIKeyError,
    DatabaseError,
    PDFProcessingError,
    ProcessingError,
)
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.minutes_divide_processor.models import SpeakerAndSpeechContent

logger = logging.getLogger(__name__)


def save_to_database(
    speaker_and_speech_content_list: list[SpeakerAndSpeechContent],
) -> list[int]:
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
        saved_ids = conversation_repo.save_speaker_and_speech_content_list(
            speaker_and_speech_content_list
        )
        logger.info(f"Saved {len(saved_ids)} conversations to database")
        return saved_ids
    except Exception as e:
        logger.error(f"Failed to save conversations: {e}")
        raise DatabaseError(
            "Failed to save conversations to database",
            {"count": len(speaker_and_speech_content_list), "error": str(e)},
        ) from e


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
                linked_info = (
                    f"→ {conv['linked_speaker_name']}"
                    if conv["linked_speaker_name"]
                    else "（紐付けなし）"
                )
                print(
                    f"  ID: {conv['id']}, 発言者: {conv['speaker_name']} {linked_info}"
                )
                print(f"      発言: {conv['comment'][:50]}...")
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        raise DatabaseError(
            "Failed to retrieve database status", {"error": str(e)}
        ) from e


def process_minutes(extracted_text: str) -> list[SpeakerAndSpeechContent]:
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
        raise ProcessingError("No text provided for processing", {"text_length": 0})

    try:
        # Check for API key
        import os

        if not os.getenv("GOOGLE_API_KEY"):
            raise APIKeyError(
                "GOOGLE_API_KEY not set. Please configure it in your .env file",
                {"env_var": "GOOGLE_API_KEY"},
            )

        llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
        agent = MinutesProcessAgent(llm=llm)

        logger.info(f"Processing minutes with {len(extracted_text)} characters")
        results = agent.run(original_minutes=extracted_text)
        logger.info(f"Extracted {len(results)} conversations")

        return results

    except Exception as e:
        if isinstance(e, ProcessingError | APIKeyError):
            raise
        logger.error(f"Minutes processing failed: {e}")
        raise ProcessingError(
            "Failed to process meeting minutes",
            {"error": str(e), "text_length": len(extracted_text)},
        ) from e


def main() -> list[int] | None:
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

        # コマンドライン引数からmeeting_idを取得（オプション）
        import argparse

        parser = argparse.ArgumentParser(description="Process meeting minutes")
        parser.add_argument(
            "--meeting-id",
            type=int,
            help="Meeting ID to process (will fetch from GCS if available)",
        )
        args = parser.parse_args()

        extracted_text = None

        # meeting_idが指定された場合、GCS URIをチェック
        if args.meeting_id:
            from src.database.meeting_repository import MeetingRepository
            from src.utils.gcs_storage import GCSStorage

            repo = MeetingRepository()
            meeting = repo.get_meeting_by_id(args.meeting_id)
            repo.close()

            if meeting and meeting.get("gcs_text_uri"):
                logger.info(
                    f"Found GCS text URI for meeting {args.meeting_id}: "
                    f"{meeting['gcs_text_uri']}"
                )
                # GCSからテキストを取得
                try:
                    gcs_storage = GCSStorage(
                        bucket_name=config.GCS_BUCKET_NAME,
                        project_id=config.GCS_PROJECT_ID,
                    )
                    extracted_text = gcs_storage.download_content(
                        meeting["gcs_text_uri"]
                    )
                    if extracted_text:
                        logger.info(
                            f"Successfully downloaded text from GCS "
                            f"({len(extracted_text)} characters)"
                        )
                    else:
                        logger.warning(
                            "Failed to download text from GCS, "
                            "falling back to PDF extraction"
                        )
                except Exception as e:
                    logger.warning(
                        f"Failed to initialize GCS or download content: {e}, "
                        "falling back to PDF extraction"
                    )

        # GCSから取得できなかった場合は、通常のPDF読み込み
        if not extracted_text:
            extracted_text = load_pdf_text()

        # メイン処理の実行
        return run_main_process(
            process_func=process_minutes,
            process_name="発言データ",
            display_status_func=display_database_status,
            save_func=save_to_database,
            extracted_text=extracted_text,
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
