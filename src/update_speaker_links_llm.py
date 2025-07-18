#!/usr/bin/env python3
"""
LLMを活用したSpeaker fuzzy matchingの更新スクリプト
"""

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import config
from src.config.database import test_connection
from src.database.conversation_repository import ConversationRepository
from src.database.speaker_matching_service import SpeakerMatchingService


def main():
    """メイン処理"""
    print("🤖 LLMベースSpeaker Fuzzy Matching更新スクリプト")
    print("=" * 60)

    # 環境変数設定
    config.set_env()

    # データベース接続テスト
    print("🔍 データベース接続テストを開始...")
    if not test_connection():
        print("❌ データベース接続に失敗しました。")
        print("   以下を確認してください:")
        print("   1. Docker Composeサービスが起動しているか")
        print("   2. 環境変数が正しく設定されているか")
        sys.exit(1)

    print("✅ データベース接続成功")

    # マッチングサービスの初期化（LLMServiceを内部で使用）
    print("\n🎯 Speaker Matchingサービスを初期化中...")
    try:
        # Enable history recording for speaker matching
        matching_service = SpeakerMatchingService(enable_history=True)
        print("✅ Speaker Matchingサービス初期化完了")
        print("✅ LLM履歴記録機能: 有効")
    except Exception as e:
        print(f"❌ サービス初期化エラー: {e}")
        print("   環境変数 GOOGLE_API_KEY が正しく設定されているか確認してください")
        sys.exit(1)

    # リポジトリの初期化（マッチングサービス付き）
    repository = ConversationRepository(speaker_matching_service=matching_service)

    # 現在の状態を確認
    print("\n📊 Speaker紐付け現状確認...")
    stats = repository.get_speaker_linking_stats()
    print(f"   - 総会話数: {stats['total_conversations']}件")
    print(f"   - 紐付け済み: {stats['linked_conversations']}件")
    print(f"   - 未紐付け: {stats['unlinked_conversations']}件")

    if stats["unlinked_conversations"] == 0:
        print("✅ 全ての会話が既に紐付け済みです。")
        return

    # ユーザー確認（Streamlitから実行される場合はスキップ）
    if os.environ.get("STREAMLIT_RUNNING") != "true":
        print(
            f"\n❓ {stats['unlinked_conversations']}件の未紐付け会話を"
            f"LLMでマッチング処理しますか？"
        )
        print(
            "   注意: この処理にはGoogle Gemini APIが使用され、"
            "料金が発生する可能性があります。"
        )

        while True:
            user_input = input("続行しますか？ (y/n): ").lower().strip()
            if user_input in ["y", "yes"]:
                break
            elif user_input in ["n", "no"]:
                print("処理を中止しました。")
                return
            else:
                print("yまたはnで回答してください。")

    # LLMベースのマッチング実行
    print("\n🚀 LLMベースマッチング処理を開始...")
    print("-" * 50)

    try:
        matching_stats = matching_service.batch_update_speaker_links()

        print("\n🎉 マッチング処理完了！")
        print("=" * 40)
        print("📈 処理結果:")
        print(f"   - 処理総数: {matching_stats['total_processed']}件")
        print(f"   - マッチ成功: {matching_stats['successfully_matched']}件")
        print(f"   - 高信頼度マッチ: {matching_stats['high_confidence_matches']}件")
        print(f"   - マッチ失敗: {matching_stats['failed_matches']}件")

        success_rate = (
            (
                matching_stats["successfully_matched"]
                / matching_stats["total_processed"]
                * 100
            )
            if matching_stats["total_processed"] > 0
            else 0
        )
        print(f"   - 成功率: {success_rate:.1f}%")

        if matching_stats["failed_matches"] > 0:
            print(f"\n⚠️  {matching_stats['failed_matches']}件のマッチに失敗しました。")
            print("   これらの発言者名は手動での確認が必要かもしれません。")

    except Exception as e:
        print(f"❌ マッチング処理エラー: {e}")
        sys.exit(1)

    # 最終状態の確認
    print("\n📊 最終状態確認...")
    final_stats = repository.get_speaker_linking_stats()
    print(f"   - 総会話数: {final_stats['total_conversations']}件")
    print(f"   - 紐付け済み: {final_stats['linked_conversations']}件")
    print(f"   - 未紐付け: {final_stats['unlinked_conversations']}件")

    improvement = final_stats["linked_conversations"] - stats["linked_conversations"]
    print(f"   - 改善: +{improvement}件の紐付け完了")


def test_single_match():
    """単一マッチのテスト用関数"""
    print("🧪 単一マッチングテスト")
    print("-" * 30)

    config.set_env()

    # Use LLMService with history recording enabled
    matching_service = SpeakerMatchingService(enable_history=True)

    # テスト用の発言者名
    test_names = [
        "委員長(平山たかお)",
        "◆委員(下村あきら)",
        "○委員長(平山たかお)",
        "総務部長(中野晋)",
        "総務部お客さまサービス推進室長(橋本悟)",
    ]

    for name in test_names:
        print(f"\n🔍 テスト: {name}")
        result = matching_service.find_best_match(name)

        if result.matched:
            print(f"   ✅ マッチ: {result.speaker_name} (ID: {result.speaker_id})")
            print(f"   信頼度: {result.confidence:.2f}")
            print(f"   理由: {result.reason}")
        else:
            print(f"   ❌ マッチ失敗: {result.reason}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_single_match()
    else:
        main()
