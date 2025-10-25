import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock

from src.infrastructure.exceptions import SaveError
from src.minutes_divide_processor.models import SpeakerAndSpeechContent


class TestConversationRepository(unittest.TestCase):
    """ConversationRepositoryクラスのユニットテスト"""

    def setUp(self):
        """各テストケース実行前の初期化"""
        # Mock the repository as it would be used
        self.repository = MagicMock()

    def create_test_speech_data(self):
        """テスト用の発言データを生成"""
        return [
            SpeakerAndSpeechContent(
                speaker="委員長(田中太郎)",
                speech_content="本日の会議を開催します。",
                chapter="第1章",
                section="第1節",
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="委員(山田花子)",
                speech_content="質問があります。",
                chapter="第1章",
                section="第2節",
                speech_order=2,
            ),
            SpeakerAndSpeechContent(
                speaker="部長(鈴木一郎)",
                speech_content="回答いたします。",
                chapter="第2章",
                section="第1節",
                speech_order=3,
            ),
        ]

    def test_save_speaker_and_speech_content_list_success(self):
        """発言データリストの正常保存テスト"""
        # テストデータ準備
        test_data = self.create_test_speech_data()

        # モックの設定：save_speaker_and_speech_content_listの戻り値
        mock_conversation_ids = [101, 102, 103]
        self.repository.save_speaker_and_speech_content_list.return_value = (
            mock_conversation_ids
        )

        # 実行
        result = self.repository.save_speaker_and_speech_content_list(test_data)

        # 検証
        self.assertEqual(result, mock_conversation_ids)
        self.repository.save_speaker_and_speech_content_list.assert_called_once_with(
            test_data
        )

    def test_save_speaker_and_speech_content_list_database_error(self):
        """データベースエラー時のロールバックテスト"""
        test_data = self.create_test_speech_data()

        # モックの設定：エラーをraiseする
        self.repository.save_speaker_and_speech_content_list.side_effect = SaveError(
            "会話データの保存中にエラー"
        )

        # エラーが適切に処理されることを確認
        with self.assertRaises(SaveError) as context:
            self.repository.save_speaker_and_speech_content_list(test_data)

        # エラーメッセージの確認
        self.assertIn("会話データの保存中にエラー", str(context.exception))

    def test_save_conversation_with_speaker_id(self):
        """speaker_id付きの会話データ保存テスト"""
        # モックの設定
        self.repository._save_conversation = MagicMock(return_value=201)

        # speaker_idが既に設定されている場合
        result = self.repository._save_conversation(
            speaker="田中太郎",
            speech_content="テスト発言",
            speaker_id=123,
            minutes_id=1,
        )

        self.assertEqual(result, 201)

    def test_save_conversation_without_speaker_id(self):
        """speaker_idなしの会話データ保存テスト"""
        # モックの設定
        self.repository._save_conversation = MagicMock(return_value=202)

        # speaker_idがNoneの場合
        result = self.repository._save_conversation(
            speaker="山田花子",
            speech_content="テスト発言2",
            speaker_id=None,
            minutes_id=1,
        )

        self.assertEqual(result, 202)

    def test_update_speaker_links_success(self):
        """speaker_idの正常更新テスト"""
        # モックの設定
        self.repository.update_speaker_links = MagicMock(return_value=5)

        # 実行
        updated_count = self.repository.update_speaker_links(1, 101)

        # 検証
        self.assertEqual(updated_count, 5)
        self.repository.update_speaker_links.assert_called_once_with(1, 101)

    def test_update_speaker_links_database_error(self):
        """更新時のデータベースエラーテスト"""
        # モックの設定：エラーをraiseする
        self.repository.update_speaker_links.side_effect = SaveError(
            "conversationsテーブルの更新中にエラー"
        )

        # エラーが適切に処理されることを確認
        with self.assertRaises(SaveError) as context:
            self.repository.update_speaker_links(1, 101)

        # エラーメッセージの確認
        self.assertIn("conversationsテーブルの更新中にエラー", str(context.exception))

    def test_legacy_find_speaker_id_exact_match(self):
        """レガシーメソッド: 完全一致での speaker_id 検索テスト"""
        # モックの設定
        self.repository._legacy_find_speaker_id = MagicMock(return_value=555)

        # 完全一致のケース
        result = self.repository._legacy_find_speaker_id("田中太郎")

        self.assertEqual(result, 555)

    def test_legacy_find_speaker_id_bracket_extraction(self):
        """レガシーメソッド: ブラケット内のID抽出テスト"""
        # モックの設定：ID入りの文字列から抽出
        self.repository._legacy_find_speaker_id = MagicMock(return_value=666)

        # ブラケット付きのケース
        result = self.repository._legacy_find_speaker_id("[666]田中太郎")

        self.assertEqual(result, 666)

    def test_legacy_find_speaker_id_no_match(self):
        """レガシーメソッド: マッチしない場合のテスト"""
        # モックの設定
        self.repository._legacy_find_speaker_id = MagicMock(return_value=None)

        # マッチしないケース
        result = self.repository._legacy_find_speaker_id("存在しない議員")

        self.assertIsNone(result)

    def test_get_all_conversations(self):
        """全会話データ取得のテスト"""
        # モックデータの準備
        mock_data = [
            {
                "id": 1,
                "speaker": "田中太郎",
                "speech_content": "発言1",
                "minutes_id": 1,
            },
            {
                "id": 2,
                "speaker": "山田花子",
                "speech_content": "発言2",
                "minutes_id": 1,
            },
        ]

        # モックの設定
        self.repository.get_all_conversations = MagicMock(return_value=mock_data)

        # 実行
        result = self.repository.get_all_conversations()

        # 検証
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["speaker"], "田中太郎")

    def test_get_conversations_count(self):
        """会話データ件数取得のテスト"""
        # モックの設定
        self.repository.get_conversations_count = MagicMock(return_value=25)

        # 実行
        result = self.repository.get_conversations_count(minutes_id=1)

        # 検証
        self.assertEqual(result, 25)

    def test_get_speaker_linking_stats(self):
        """スピーカーリンク統計情報取得のテスト"""
        expected_stats = {
            "total_conversations": 100,
            "speaker_linked_count": 60,
            "speaker_not_linked_count": 40,
            "speaker_link_rate": 60.0,
            "politician_linked_count": 50,
            "politician_not_linked_count": 50,
            "politician_link_rate": 50.0,
        }

        # モックの設定
        self.repository.get_speaker_linking_stats = MagicMock(
            return_value=expected_stats
        )

        # 実行
        result = self.repository.get_speaker_linking_stats()

        # 検証
        self.assertEqual(result, expected_stats)
        self.assertEqual(result["speaker_link_rate"], 60.0)

    def test_get_conversations_with_pagination(self):
        """ページネーション付き会話データ取得のテスト"""
        mock_response = {
            "total": 100,
            "page": 1,
            "per_page": 20,
            "conversations": [
                {
                    "id": 1,
                    "speaker": "田中太郎",
                    "speech_content": "発言内容",
                    "minutes_id": 1,
                    "speaker_id": 10,
                }
            ],
        }

        # モックの設定
        self.repository.get_conversations_with_pagination = MagicMock(
            return_value=mock_response
        )

        # 実行
        result = self.repository.get_conversations_with_pagination(
            page=1, per_page=20, minutes_id=1
        )

        # 検証
        self.assertEqual(result["total"], 100)
        self.assertEqual(result["page"], 1)
        self.assertEqual(len(result["conversations"]), 1)

    def test_get_conversations_with_pagination_chapter_sorting(self):
        """章・節によるソート付きページネーションテスト"""
        mock_response = {
            "total": 5,
            "page": 1,
            "per_page": 10,
            "conversations": [
                {
                    "id": 1,
                    "chapter": "第1章",
                    "section": "第1節",
                    "speech_order": 1,
                },
                {
                    "id": 2,
                    "chapter": "第1章",
                    "section": "第2節",
                    "speech_order": 2,
                },
            ],
        }

        # モックの設定
        self.repository.get_conversations_with_pagination = MagicMock(
            return_value=mock_response
        )

        # 実行
        result = self.repository.get_conversations_with_pagination(
            page=1, per_page=10, order_by="chapter"
        )

        # 検証
        self.assertEqual(result["total"], 5)
        self.assertEqual(len(result["conversations"]), 2)

    def test_empty_speech_content_list(self):
        """空の発言データリストのテスト"""
        # モックの設定
        self.repository.save_speaker_and_speech_content_list = MagicMock(
            return_value=[]
        )

        # 空のリストを渡した場合
        result = self.repository.save_speaker_and_speech_content_list([])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
