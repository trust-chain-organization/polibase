"""
議事録分割処理のメインスクリプト

Processes meeting minutes PDF files and extracts individual conversations.
"""

import sys

from src.common.app_logic import (
    load_pdf_text,
    print_completion_message,
    run_main_process,
    setup_environment,
)
from src.common.logging import get_logger
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
from src.services.llm_factory import LLMServiceFactory

logger = get_logger(__name__)


def save_to_database(
    speaker_and_speech_content_list: list[SpeakerAndSpeechContent],
    minutes_id: int | None = None,
) -> list[int]:
    """
    SpeakerAndSpeechContentのリストをデータベースのConversationsテーブルに保存する

    Args:
        speaker_and_speech_content_list: 保存する発言データリスト
        minutes_id: 紐付けるminutesレコードのID

    Returns:
        List[int]: 保存されたレコードのIDリスト

    Raises:
        DatabaseError: If database save fails
    """
    if not speaker_and_speech_content_list:
        logger.warning("No conversations to save", count=0)
        return []

    conversation_repo = None
    try:
        conversation_repo = ConversationRepository()
        saved_ids = conversation_repo.save_speaker_and_speech_content_list(
            speaker_and_speech_content_list, minutes_id=minutes_id
        )
        logger.info(
            "Saved conversations to database",
            count=len(saved_ids),
            minutes_id=minutes_id,
        )
        return saved_ids
    except Exception as e:
        logger.error(
            "Failed to save conversations",
            error=str(e),
            count=len(speaker_and_speech_content_list),
            exc_info=True,
        )
        raise DatabaseError(
            "Failed to save conversations to database",
            {"count": len(speaker_and_speech_content_list), "error": str(e)},
        ) from e
    finally:
        if conversation_repo:
            conversation_repo.close()


def display_database_status() -> None:
    """
    データベースの状態を表示する

    Raises:
        DatabaseError: If database query fails
    """
    conversation_repo = None
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
        logger.error("Failed to get database status", error=str(e), exc_info=True)
        raise DatabaseError(
            "Failed to retrieve database status", {"error": str(e)}
        ) from e
    finally:
        if conversation_repo:
            conversation_repo.close()


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

        # Create LLM service using factory
        factory = LLMServiceFactory()
        llm_service = factory.create_advanced(temperature=0.0)

        agent = MinutesProcessAgent(llm_service=llm_service)

        logger.info("Processing minutes", text_length=len(extracted_text))
        results = agent.run(original_minutes=extracted_text)
        logger.info("Extracted conversations", count=len(results))

        return results

    except Exception as e:
        if isinstance(e, ProcessingError | APIKeyError):
            raise
        logger.error("Minutes processing failed", error=str(e), exc_info=True)
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
        parser.add_argument(
            "--process-all-gcs",
            action="store_true",
            help="Process all meetings with GCS text URIs",
        )
        args = parser.parse_args()

        extracted_text = None

        # --process-all-gcsが指定された場合、すべてのGCS URIを持つmeetingを処理
        if args.process_all_gcs:
            from src.database.meeting_repository import MeetingRepository
            from src.utils.gcs_storage import GCSStorage

            repo = MeetingRepository()
            # GCS text URIを持つすべてのmeetingを取得
            meetings_with_gcs = repo.fetch_as_dict(
                """
                SELECT id, url, gcs_text_uri
                FROM meetings
                WHERE gcs_text_uri IS NOT NULL
                ORDER BY id
                """
            )
            repo.close()

            if not meetings_with_gcs:
                logger.warning("No meetings found with GCS text URIs")
                print("⚠️  GCS text URIを持つmeetingが見つかりませんでした")
                return None

            print(f"📋 {len(meetings_with_gcs)}件のmeetingを処理します")

            # GCS storageを初期化
            try:
                gcs_storage = GCSStorage(
                    bucket_name=config.GCS_BUCKET_NAME,
                    project_id=config.GCS_PROJECT_ID,
                )
            except Exception as e:
                logger.error(f"Failed to initialize GCS storage: {e}")
                print(f"❌ GCS初期化エラー: {e}")
                return None

            all_saved_ids = []

            # 各meetingを処理
            for meeting in meetings_with_gcs:
                meeting_id = meeting["id"]
                gcs_uri = meeting["gcs_text_uri"]

                print(f"\n🔍 Meeting ID {meeting_id} を処理中...")
                print(f"   GCS URI: {gcs_uri}")

                try:
                    # GCSからテキストを取得
                    extracted_text = gcs_storage.download_content(gcs_uri)
                    if not extracted_text:
                        logger.warning(
                            f"No content downloaded for meeting {meeting_id}"
                        )
                        print("   ⚠️  コンテンツが取得できませんでした")
                        continue

                    print(f"   ✅ テキストを取得しました ({len(extracted_text)} 文字)")

                    # minutesレコードを作成（既存のものがあるかチェック）
                    from src.database.base_repository import BaseRepository

                    minutes_repo = BaseRepository(use_session=False)

                    # 既存のminutesレコードを確認
                    existing_minutes = minutes_repo.fetch_one(
                        "SELECT id FROM minutes WHERE meeting_id = :meeting_id",
                        {"meeting_id": meeting_id},
                    )

                    if existing_minutes:
                        minutes_id = existing_minutes[0]
                        print(f"   ℹ️  既存のMinutes ID {minutes_id} を使用します")
                    else:
                        minutes_id = minutes_repo.insert(
                            table="minutes",
                            data={
                                "meeting_id": meeting_id,
                                "url": meeting["url"],
                            },
                            returning="id",
                        )
                        print(f"   ✅ Minutes ID {minutes_id} を作成しました")

                    # 議事録を処理
                    results = process_minutes(extracted_text)
                    if results:
                        # データベースに保存（minutes_idを紐付け）
                        saved_ids = save_to_database(results, minutes_id=minutes_id)
                        all_saved_ids.extend(saved_ids)
                        print(
                            f"   ✅ {len(saved_ids)}件の発言を保存しました "
                            f"(Minutes ID: {minutes_id})"
                        )
                    else:
                        print("   ⚠️  発言が抽出されませんでした")

                except Exception as e:
                    logger.error(f"Failed to process meeting {meeting_id}: {e}")
                    print(f"   ❌ 処理エラー: {e}")
                    continue

            # 処理結果を表示
            display_database_status()
            print(f"\n✅ 処理完了: 合計 {len(all_saved_ids)}件の発言を保存しました")
            return all_saved_ids

        # meeting_idが指定された場合、GCS URIをチェック
        elif args.meeting_id:
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

                        # minutesレコードを作成（既存のものがあるかチェック）
                        from src.database.base_repository import BaseRepository

                        minutes_repo = BaseRepository(use_session=False)

                        # 既存のminutesレコードを確認
                        existing_minutes = minutes_repo.fetch_one(
                            "SELECT id FROM minutes WHERE meeting_id = :meeting_id",
                            {"meeting_id": args.meeting_id},
                        )

                        if existing_minutes:
                            minutes_id = existing_minutes[0]
                            logger.info(
                                f"Using existing minutes record with ID: {minutes_id}"
                            )
                        else:
                            minutes_id = minutes_repo.insert(
                                table="minutes",
                                data={
                                    "meeting_id": args.meeting_id,
                                    "url": meeting["url"],
                                },
                                returning="id",
                            )
                            logger.info(f"Created minutes record with ID: {minutes_id}")

                        # メイン処理の実行（minutes_idを渡す）
                        return run_main_process(
                            process_func=process_minutes,
                            process_name="発言データ",
                            display_status_func=display_database_status,
                            save_func=lambda results: save_to_database(
                                results, minutes_id=minutes_id
                            ),
                            extracted_text=extracted_text,
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
