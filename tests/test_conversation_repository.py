import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock, patch

from src.database.conversation_repository import ConversationRepository
from src.minutes_divide_processor.models import SpeakerAndSpeechContent


class TestConversationRepository(unittest.TestCase):
    """ConversationRepositoryクラスのユニットテスト"""

    def setUp(self):
        """各テストケース実行前の初期化"""
        # データベースセッションをモック化
        self.mock_session = MagicMock()

        # ConversationRepositoryのインスタンスを作成し、セッションをモック化
        with patch("src.config.database.get_db_session") as mock_get_session:
            mock_get_session.return_value = self.mock_session
            self.repository = ConversationRepository()
            # Ensure the repository is using our mock session
            self.repository._session = self.mock_session

    def create_test_speech_data(self):
        """テスト用の発言データを生成"""
        return [
            SpeakerAndSpeechContent(
                speaker="委員長(田中太郎)",
                speech_content="議事を開始します。",
                chapter_number=1,
                sub_chapter_number=1,
                speech_order=1,
            ),
            SpeakerAndSpeechContent(
                speaker="◆委員(佐藤花子)",
                speech_content="質問があります。予算について教えてください。",
                chapter_number=1,
                sub_chapter_number=2,
                speech_order=2,
            ),
            SpeakerAndSpeechContent(
                speaker="部長(山田次郎)",
                speech_content="予算についてお答えします。",
                chapter_number=2,
                sub_chapter_number=1,
                speech_order=3,
            ),
        ]

    def test_save_speaker_and_speech_content_list_success(self):
        """発言データリストの正常保存テスト"""
        # テストデータ準備
        test_data = self.create_test_speech_data()

        # モックの設定：各_save_conversationの戻り値
        mock_conversation_ids = [101, 102, 103]
        with patch.object(
            self.repository, "_save_conversation", side_effect=mock_conversation_ids
        ):
            # 実行
            result = self.repository.save_speaker_and_speech_content_list(test_data)

            # 検証
            self.assertEqual(result, mock_conversation_ids)
            self.mock_session.commit.assert_called_once()
            self.mock_session.close.assert_called_once()

    def test_save_speaker_and_speech_content_list_database_error(self):
        """データベースエラー時のロールバックテスト"""
        test_data = self.create_test_speech_data()

        # _save_conversationでエラーを発生させる
        with patch.object(
            self.repository, "_save_conversation", side_effect=Exception("DB Error")
        ):
            # エラーが発生することを検証
            with self.assertRaises(Exception):
                self.repository.save_speaker_and_speech_content_list(test_data)

            # ロールバックが呼ばれることを検証
            self.mock_session.rollback.assert_called_once()
            self.mock_session.close.assert_called_once()

    def test_save_conversation_with_speaker_id(self):
        """発言者IDが見つかる場合の個別保存テスト"""
        test_speech = self.create_test_speech_data()[0]

        # _legacy_find_speaker_idが123を返すように設定
        with patch.object(self.repository, "_legacy_find_speaker_id", return_value=123):
            # SQLクエリ実行結果をモック
            mock_result = MagicMock()
            mock_result.fetchone.return_value = [456]  # 新しく作成されたconversation_id
            self.mock_session.execute.return_value = mock_result

            # 実行
            result = self.repository._save_conversation(test_speech)

            # 検証
            self.assertEqual(result, 456)
            self.mock_session.execute.assert_called_once()

            # 実行されたクエリの引数を検証
            args, kwargs = self.mock_session.execute.call_args
            query_params = kwargs if kwargs else args[1]
            self.assertEqual(query_params["speaker_id"], 123)
            self.assertEqual(query_params["speaker_name"], "委員長(田中太郎)")
            self.assertEqual(query_params["comment"], "議事を開始します。")

    def test_save_conversation_without_speaker_id(self):
        """発言者IDが見つからない場合の個別保存テスト"""
        test_speech = self.create_test_speech_data()[1]

        # _legacy_find_speaker_idがNoneを返すように設定
        with patch.object(
            self.repository, "_legacy_find_speaker_id", return_value=None
        ):
            # SQLクエリ実行結果をモック
            mock_result = MagicMock()
            mock_result.fetchone.return_value = [789]
            self.mock_session.execute.return_value = mock_result

            # 実行
            result = self.repository._save_conversation(test_speech)

            # 検証
            self.assertEqual(result, 789)

            # 実行されたクエリの引数を検証
            args, kwargs = self.mock_session.execute.call_args
            query_params = kwargs if kwargs else args[1]
            self.assertIsNone(query_params["speaker_id"])
            self.assertEqual(query_params["speaker_name"], "◆委員(佐藤花子)")

    def test_legacy_find_speaker_id_exact_match(self):
        """発言者名の完全一致テスト"""
        # 完全一致で見つかる場合のモック設定
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [555]
        self.mock_session.execute.return_value = mock_result

        # 実行
        result = self.repository._legacy_find_speaker_id("田中太郎")

        # 検証
        self.assertEqual(result, 555)
        self.mock_session.execute.assert_called_once()

    def test_legacy_find_speaker_id_bracket_extraction(self):
        """括弧内名前抽出テスト"""
        # 完全一致では見つからず、括弧内抽出で見つかる場合
        mock_results = [
            MagicMock(),  # 1回目（完全一致）は見つからない
            MagicMock(),  # 2回目（括弧内抽出）で見つかる
        ]
        mock_results[0].fetchone.return_value = None
        mock_results[1].fetchone.return_value = [666]

        self.mock_session.execute.side_effect = mock_results

        # 実行
        result = self.repository._legacy_find_speaker_id("委員長(田中太郎)")

        # 検証
        self.assertEqual(result, 666)
        self.assertEqual(self.mock_session.execute.call_count, 2)

    def test_legacy_find_speaker_id_no_match(self):
        """発言者が見つからない場合のテスト"""
        # 全ての検索で見つからない場合
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        self.mock_session.execute.return_value = mock_result

        # 実行
        result = self.repository._legacy_find_speaker_id("存在しない発言者")

        # 検証
        self.assertIsNone(result)

    def test_get_all_conversations(self):
        """全発言データ取得テスト"""
        # モックデータ準備
        mock_conversations = [
            (
                1,
                None,
                123,
                "委員長(田中太郎)",
                "議事を開始します。",
                1,
                1,
                1,
                "2024-01-01",
                "2024-01-01",
                "田中太郎",
            ),
            (
                2,
                None,
                None,
                "◆委員(佐藤花子)",
                "質問があります。",
                2,
                1,
                2,
                "2024-01-01",
                "2024-01-01",
                None,
            ),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_conversations
        mock_result.keys.return_value = [
            "id",
            "minutes_id",
            "speaker_id",
            "speaker_name",
            "comment",
            "sequence_number",
            "chapter_number",
            "sub_chapter_number",
            "created_at",
            "updated_at",
            "linked_speaker_name",
        ]
        self.mock_session.execute.return_value = mock_result

        # 実行
        result = self.repository.get_all_conversations()

        # 検証
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["speaker_id"], 123)
        self.assertEqual(result[1]["speaker_id"], None)
        self.mock_session.close.assert_called_once()

    def test_get_conversations_count(self):
        """発言データ件数取得テスト"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [25]
        self.mock_session.execute.return_value = mock_result

        # 実行
        result = self.repository.get_conversations_count()

        # 検証
        self.assertEqual(result, 25)
        self.mock_session.close.assert_called_once()

    def test_get_speaker_linking_stats(self):
        """発言者紐付け統計取得テスト"""
        mock_result = MagicMock()
        mock_result.fetchone.return_value = [
            100,
            75,
            25,
        ]  # 総数, 紐付けあり, 紐付けなし
        self.mock_session.execute.return_value = mock_result

        # 実行
        result = self.repository.get_speaker_linking_stats()

        # 検証
        expected_stats = {
            "total_conversations": 100,
            "linked_conversations": 75,
            "unlinked_conversations": 25,
        }
        self.assertEqual(result, expected_stats)
        self.mock_session.close.assert_called_once()

    def test_update_speaker_links_success(self):
        """発言者紐付け更新成功テスト"""
        # 紐付けされていない発言データをモック
        unlinked_conversations = [(1, "委員長(田中太郎)"), (2, "◆委員(佐藤花子)")]

        mock_select_result = MagicMock()
        mock_select_result.fetchall.return_value = unlinked_conversations

        # _legacy_find_speaker_idの戻り値を設定
        with patch.object(
            self.repository, "_legacy_find_speaker_id", side_effect=[123, None]
        ):
            # update メソッドをモック
            with patch.object(self.repository, "update", return_value=1) as mock_update:
                self.mock_session.execute.return_value = mock_select_result

                # 実行
                result = self.repository.update_speaker_links()

                # 検証
                self.assertEqual(result, 1)  # 1件だけ更新される
                mock_update.assert_called_once_with(
                    table="conversations", data={"speaker_id": 123}, where={"id": 1}
                )
                self.mock_session.commit.assert_called_once()
                self.mock_session.close.assert_called_once()

    def test_update_speaker_links_database_error(self):
        """発言者紐付け更新エラーテスト"""
        # SELECTでエラーが発生
        self.mock_session.execute.side_effect = Exception("DB Error")

        # エラーが発生することを検証
        with self.assertRaises(Exception):
            self.repository.update_speaker_links()

        # ロールバックが呼ばれることを検証
        self.mock_session.rollback.assert_called_once()
        self.mock_session.close.assert_called_once()

    def test_empty_speech_content_list(self):
        """空の発言データリスト保存テスト"""
        # 空のリストで実行
        result = self.repository.save_speaker_and_speech_content_list([])

        # 検証
        self.assertEqual(result, [])
        self.mock_session.commit.assert_called_once()
        self.mock_session.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
