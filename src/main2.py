# Use absolute import from the 'src' package when running as a module
import src.config.config as config
from src.utils.text_extractor import extract_text_from_pdf
from src.politician_extract_processor.models import (
    PoliticianInfo,
    PoliticianInfoList,
    PoliticianProcessState
)
from src.database.speaker_repository import SpeakerRepository
from langchain_google_genai import ChatGoogleGenerativeAI
# ↓↓↓ インポート元を __init__.py 経由に変更 ↓↓↓
from src.politician_extract_processor import PoliticianProcessAgent
from typing import List
import os

# config.pyを呼び出して環境変数を設定
config.set_env()

# PDF ファイルを読み込み
try:
    with open('data/minutes.pdf', 'rb') as f:
        file_content = f.read()
except FileNotFoundError:
    print("Source file not found: data/minutes.pdf")
    exit()
extracted_text = extract_text_from_pdf(file_content)

def save_to_database(politician_info_list_obj: PoliticianInfoList) -> List[int]:
    """
    PoliticianInfoListをデータベースのSpeakersテーブルに保存する
    
    Args:
        politician_info_list_obj: 保存する政治家情報リスト
        
    Returns:
        List[int]: 保存されたレコードのIDリスト
    """
    speaker_repo = SpeakerRepository()
    try:
        saved_ids = speaker_repo.save_politician_info_list(politician_info_list_obj)
        print(f"💾 データベース保存完了: {len(saved_ids)}件のレコードを保存しました")
        return saved_ids
    except Exception as e:
        print(f"❌ データベース保存エラー: {e}")
        raise

def display_database_status():
    """
    データベースの状態を表示する
    """
    try:
        speaker_repo = SpeakerRepository()
        count = speaker_repo.get_speakers_count()
        print(f"📊 現在のSpeakersテーブルレコード数: {count}件")
        
        if count > 0:
            print("\n📋 最新の5件のレコード:")
            speakers = speaker_repo.get_all_speakers()[:5]
            for speaker in speakers:
                print(f"  ID: {speaker['id']}, 名前: {speaker['name']}, 政党: {speaker['political_party_name']}, 役職: {speaker['position']}")
        
    except Exception as e:
        print(f"❌ データベース状態確認エラー: {e}")

def main():
    # データベース接続テスト
    print("🔍 データベース接続テストを開始...")
    from src.config.database import test_connection
    if not test_connection():
        print("❌ データベースに接続できません。docker compose でPostgreSQLが起動していることを確認してください。")
        return None
    
    print("📊 処理前のデータベース状態:")
    display_database_status()
    
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0) # モデル名を修正
    agent = PoliticianProcessAgent(llm=llm)
    # ↓↓↓ agent.run の戻り値の型が PoliticianInfoList であることを前提とする ↓↓↓
    politician_info_list_result = agent.run(original_minutes=extracted_text) # 変数名を変更して明確化
    # データベースに保存 (CSVファイル出力からデータベース保存に変更)
    saved_ids = save_to_database(politician_info_list_result)
    print(f"政治家情報の抽出が完了しました。{len(saved_ids)}件のレコードをデータベースに保存しました。")
    
    print("\n📊 処理後のデータベース状態:")
    display_database_status()
    
    # ↓↓↓ 戻り値の型に合わせて修正 ↓↓↓
    return politician_info_list_result

if __name__ == "__main__":
    # ↓↓↓ main() の戻り値に合わせて変数名を変更 ↓↓↓
    politician_info_list_output = main() # 変数名を変更して明確化
    print("--------結果出力--------")
    # ↓↓↓ 変数名を変更 ↓↓↓
    print(politician_info_list_output)
    print('全部終わったよ')
