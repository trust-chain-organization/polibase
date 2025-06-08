"""
政治家抽出処理のメインスクリプト

Extracts politician information from meeting minutes using LLM.
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
from src.database.speaker_repository import SpeakerRepository
from src.exceptions import (
    APIKeyError,
    DatabaseError,
    PDFProcessingError,
    ProcessingError,
)
from src.politician_extract_processor import PoliticianProcessAgent

# Use absolute import from the 'src' package when running as a module
from src.politician_extract_processor.models import (
    PoliticianInfoList,
)

logger = logging.getLogger(__name__)


def save_to_database(politician_info_list_obj: PoliticianInfoList) -> list[int]:
    """
    PoliticianInfoListをデータベースのSpeakersテーブルに保存する

    Args:
        politician_info_list_obj: 保存する政治家情報リスト

    Returns:
        List[int]: 保存されたレコードのIDリスト

    Raises:
        DatabaseError: If database save fails
    """
    if (
        not politician_info_list_obj
        or not politician_info_list_obj.politician_info_list
    ):
        logger.warning("No politicians to save")
        return []

    try:
        speaker_repo = SpeakerRepository()
        saved_ids = speaker_repo.save_politician_info_list(politician_info_list_obj)
        logger.info(f"Saved {len(saved_ids)} politicians to database")
        return saved_ids
    except Exception as e:
        logger.error(f"Failed to save politicians: {e}")
        raise DatabaseError(
            "Failed to save politicians to database",
            {
                "count": len(politician_info_list_obj.politician_info_list),
                "error": str(e),
            },
        )


def display_database_status() -> None:
    """
    データベースの状態を表示する

    Raises:
        DatabaseError: If database query fails
    """
    try:
        speaker_repo = SpeakerRepository()
        count = speaker_repo.get_speakers_count()
        print(f"📊 現在のSpeakersテーブルレコード数: {count}件")

        if count > 0:
            print("\n📋 最新の5件のレコード:")
            speakers = speaker_repo.get_all_speakers()[:5]
            for speaker in speakers:
                print(
                    f"  ID: {speaker['id']}, 名前: {speaker['name']}, "
                    f"政党: {speaker['political_party_name']}, "
                    f"役職: {speaker['position']}"
                )
    except Exception as e:
        logger.error(f"Failed to get database status: {e}")
        raise DatabaseError(
            "Failed to retrieve speaker database status", {"error": str(e)}
        )


def process_politicians(extracted_text: str) -> PoliticianInfoList:
    """
    政治家抽出処理を実行する

    Args:
        extracted_text: 処理対象のテキスト

    Returns:
        PoliticianInfoList: 抽出された政治家情報

    Raises:
        ProcessingError: If politician extraction fails
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

        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
        agent = PoliticianProcessAgent(llm=llm)

        logger.info(f"Processing politicians with {len(extracted_text)} characters")
        results = agent.run(original_minutes=extracted_text)
        logger.info(f"Extracted {len(results.politician_info_list)} politicians")

        return results

    except Exception as e:
        if isinstance(e, ProcessingError | APIKeyError):
            raise
        logger.error(f"Politician extraction failed: {e}")
        raise ProcessingError(
            "Failed to extract politicians from text",
            {"error": str(e), "text_length": len(extracted_text)},
        )


def main() -> list[int] | None:
    """
    政治家抽出処理のメイン関数

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
            process_func=process_politicians,
            process_name="政治家情報",
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
        print_completion_message(result, "政治家抽出処理")
