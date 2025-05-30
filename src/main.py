"""
議事録分割処理のメインスクリプト
"""
from typing import List
from langchain_google_genai import ChatGoogleGenerativeAI
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
from src.database.conversation_repository import ConversationRepository
from src.common.app_logic import setup_environment, load_pdf_text, run_main_process, print_completion_message

def save_to_database(speaker_and_speech_content_list: List) -> List[int]:
    """
    SpeakerAndSpeechContentのリストをデータベースのConversationsテーブルに保存する
    
    Args:
        speaker_and_speech_content_list: 保存する発言データリスト
        
    Returns:
        List[int]: 保存されたレコードのIDリスト
    """
    conversation_repo = ConversationRepository()
    return conversation_repo.save_speaker_and_speech_content_list(speaker_and_speech_content_list)

def display_database_status():
    """
    データベースの状態を表示する
    """
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


def process_minutes(extracted_text: str):
    """
    議事録分割処理を実行する
    
    Args:
        extracted_text: 処理対象のテキスト
        
    Returns:
        発言データリスト
    """
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    agent = MinutesProcessAgent(llm=llm)
    return agent.run(original_minutes=extracted_text)

def main():
    """
    議事録分割処理のメイン関数
    """
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


if __name__ == "__main__":
    result = main()
    print_completion_message(result, "議事録分割処理")
