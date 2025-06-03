# Use absolute import from the 'src' package when running as a module
from src.politician_extract_processor.models import (
    PoliticianInfo,
    PoliticianInfoList,
    PoliticianProcessState
)
from src.database.speaker_repository import SpeakerRepository
from langchain_google_genai import ChatGoogleGenerativeAI
# ↓↓↓ インポート元を __init__.py 経由に変更 ↓↓↓
from src.politician_extract_processor import PoliticianProcessAgent
from src.common.app_logic import setup_environment, load_pdf_text, run_main_process, print_completion_message
from typing import List


def save_to_database(politician_info_list_obj: PoliticianInfoList) -> List[int]:
    """
    PoliticianInfoListをデータベースのSpeakersテーブルに保存する
    
    Args:
        politician_info_list_obj: 保存する政治家情報リスト
        
    Returns:
        List[int]: 保存されたレコードのIDリスト
    """
    speaker_repo = SpeakerRepository()
    return speaker_repo.save_politician_info_list(politician_info_list_obj)

def display_database_status():
    """
    データベースの状態を表示する
    """
    speaker_repo = SpeakerRepository()
    count = speaker_repo.get_speakers_count()
    print(f"📊 現在のSpeakersテーブルレコード数: {count}件")
    
    if count > 0:
        print("\n📋 最新の5件のレコード:")
        speakers = speaker_repo.get_all_speakers()[:5]
        for speaker in speakers:
            print(f"  ID: {speaker['id']}, 名前: {speaker['name']}, 政党: {speaker['political_party_name']}, 役職: {speaker['position']}")


def process_politicians(extracted_text: str):
    """
    政治家抽出処理を実行する
    
    Args:
        extracted_text: 処理対象のテキスト
        
    Returns:
        政治家情報リスト
    """
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)  # モデル名を修正
    agent = PoliticianProcessAgent(llm=llm)
    return agent.run(original_minutes=extracted_text)

def main():
    """
    政治家抽出処理のメイン関数
    """
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
        extracted_text=extracted_text
    )


if __name__ == "__main__":
    result = main()
    print_completion_message(result, "政治家抽出処理")
