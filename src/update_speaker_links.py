#!/usr/bin/env python3
# filepath: /Users/okodoon/project/polibase/update_speaker_links.py
"""
既存のConversationsデータのSpeaker紐付けを更新するスクリプト
"""

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.config.config as config
from src.config.database import test_connection
from src.database.conversation_repository import ConversationRepository


def main():
    # 環境変数設定
    config.set_env()

    # データベース接続テスト
    print("🔍 データベース接続テストを開始...")
    if not test_connection():
        print("❌ データベースに接続できません。")
        return

    print("📊 Speaker紐付け更新前の状態:")
    repo = ConversationRepository()
    stats = repo.get_speaker_linking_stats()
    print(f"   - 総会話数: {stats['total_conversations']}件")
    print(f"   - Speaker紐付けあり: {stats['linked_conversations']}件")
    print(f"   - Speaker紐付けなし: {stats['unlinked_conversations']}件")

    print("\n🔗 Speaker紐付けを更新中...")
    repo = ConversationRepository()
    updated_count = repo.update_speaker_links()

    print("\n📊 Speaker紐付け更新後の状態:")
    repo = ConversationRepository()
    stats = repo.get_speaker_linking_stats()
    print(f"   - 総会話数: {stats['total_conversations']}件")
    print(f"   - Speaker紐付けあり: {stats['linked_conversations']}件")
    print(f"   - Speaker紐付けなし: {stats['unlinked_conversations']}件")

    print(f"\n🎉 Speaker紐付け更新完了！{updated_count}件を更新しました。")


if __name__ == "__main__":
    main()
