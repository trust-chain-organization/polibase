# Use absolute import from the 'src' package when running as a module
import src.config.config as config
from src.utils.text_extractor import extract_text_from_pdf
from src.database.conversation_repository import ConversationRepository
from langchain_google_genai import ChatGoogleGenerativeAI
# Absolute import for MinutesProcessAgent
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
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

def save_to_database(speaker_and_speech_content_list: List) -> List[int]:
    """
    SpeakerAndSpeechContentのリストをデータベースのConversationsテーブルに保存する
    
    Args:
        speaker_and_speech_content_list: 保存する発言データリスト
        
    Returns:
        List[int]: 保存されたレコードのIDリスト
    """
    conversation_repo = ConversationRepository()
    try:
        saved_ids = conversation_repo.save_speaker_and_speech_content_list(speaker_and_speech_content_list)
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
    
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    agent = MinutesProcessAgent(llm=llm)
    speaker_and_speech_content_list = agent.run(original_minutes=extracted_text)
    # データベースに保存 (CSVファイル出力からデータベース保存に変更)
    saved_ids = save_to_database(speaker_and_speech_content_list)
    print(f"発言データの抽出が完了しました。{len(saved_ids)}件のレコードをデータベースに保存しました。")
    
    print("\n📊 処理後のデータベース状態:")
    display_database_status()
    
    return speaker_and_speech_content_list

if __name__ == "__main__":
    speaker_and_speech_content_list = main()
    print("--------結果出力--------")
    print(speaker_and_speech_content_list)
    print('全部終わったよ')
