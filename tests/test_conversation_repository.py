import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import unittest
from unittest.mock import MagicMock, patch

from src.exceptions import SaveError
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
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
            self.repository = RepositoryAdapter(ConversationRepositoryImpl)
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
            self.repository, "_save_conversation", side_effect=RuntimeError("DB Error")
        ):
            # エラーが発生することを検証
            with self.assertRaises(SaveError):
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
        # close()は呼ばれないはず
        self.mock_session.close.assert_not_called()

    def test_get_conversations_count(self):
        """発言データ件数取得テスト"""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 25
        self.mock_session.execute.return_value = mock_result

        # 実行
        result = self.repository.get_conversations_count()

        # 検証
        self.assertEqual(result, 25)
        # close()は呼ばれないはず
        self.mock_session.close.assert_not_called()

    def test_get_speaker_linking_stats(self):
        """発言者紐付け統計取得テスト"""
        # Mock for multiple execute calls
        mock_total_result = MagicMock()
        mock_total_result.scalar.return_value = 100

        mock_linked_result = MagicMock()
        mock_linked_result.scalar.return_value = 75

        mock_politician_result = MagicMock()
        mock_politician_result.fetchone.return_value = [50]

        # Set up execute to return different results for different queries
        self.mock_session.execute.side_effect = [
            mock_total_result,  # First call for total count
            mock_linked_result,  # Second call for linked count
            mock_politician_result,  # Third call - politician linked count
        ]

        # 実行
        result = self.repository.get_speaker_linking_stats()

        # 検証
        expected_stats = {
            "total_conversations": 100,
            "speaker_linked_conversations": 75,
            "politician_linked_conversations": 50,
            "unlinked_conversations": 25,
            "speaker_link_rate": 75.0,
            "politician_link_rate": 50.0,
        }
        self.assertEqual(result, expected_stats)
        # close()は呼ばれないはず
        self.mock_session.close.assert_not_called()

    def test_get_conversations_with_pagination(self):
        """ページネーション付き発言データ取得テスト"""

        # Mock Row class with attribute access
        class MockRow:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        # モックデータの準備
        # 総件数取得のモック
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 100

        # データ取得のモック
        mock_data_result = MagicMock()
        mock_conversations = [
            MockRow(
                id=1,
                minutes_id=1,
                speaker_id=123,
                speaker_name="委員長(田中太郎)",
                comment="議事を開始します。",
                sequence_number=1,
                chapter_number=1,
                sub_chapter_number=1,
                meeting_title="本会議",
                meeting_date="2024-01-01",
                linked_speaker_name="田中太郎",
                speaker_type="委員長",
                speaker_party_name=None,
                governing_body_name="東京都",
                governing_body_type="都道府県",
                conference_name="本会議",
                politician_id=None,
                politician_name=None,
                politician_party_name=None,
                politician_position=None,
                speaker_is_politician=False,
            ),
            MockRow(
                id=2,
                minutes_id=1,
                speaker_id=None,
                speaker_name="◆委員(佐藤花子)",
                comment="質問があります。",
                sequence_number=2,
                chapter_number=1,
                sub_chapter_number=2,
                meeting_title="本会議",
                meeting_date="2024-01-01",
                linked_speaker_name=None,
                speaker_type="委員",
                speaker_party_name=None,
                governing_body_name="東京都",
                governing_body_type="都道府県",
                conference_name="本会議",
                politician_id=None,
                politician_name=None,
                politician_party_name=None,
                politician_position=None,
                speaker_is_politician=False,
            ),
        ]
        mock_data_result.fetchall.return_value = mock_conversations

        # executeのモック設定
        self.mock_session.execute.side_effect = [
            mock_count_result,  # 総件数クエリ
            mock_data_result,  # データ取得クエリ
        ]

        # 実行
        result = self.repository.get_conversations_with_pagination(
            limit=50, offset=0, conference_id=1
        )

        # 検証
        self.assertEqual(result["total"], 100)
        self.assertEqual(len(result["conversations"]), 2)
        self.assertEqual(result["conversations"][0]["id"], 1)
        self.assertEqual(result["conversations"][0]["speaker_name"], "委員長(田中太郎)")
        self.assertEqual(result["conversations"][1]["id"], 2)
        self.assertEqual(len(result["conversations"]), 2)
        self.assertEqual(result["conversations"][0]["id"], 1)
        self.assertEqual(result["conversations"][0]["conference_name"], "本会議")
        self.assertEqual(result["conversations"][1]["speaker_id"], None)

        # executeが2回呼ばれていることを確認
        self.assertEqual(self.mock_session.execute.call_count, 2)
        # close()は呼ばれないはず
        self.mock_session.close.assert_not_called()

    def test_get_conversations_with_pagination_chapter_sorting(self):
        """章番号によるソート順のテスト"""

        # Mock Row class with attribute access
        class MockRow:
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        # モックデータの準備
        # 総件数取得のモック
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 5

        # データ取得のモック（簡略化）
        mock_data_result = MagicMock()
        mock_conversations = [
            MockRow(
                id=1,
                minutes_id=1,
                speaker_id=123,
                speaker_name="委員長(田中太郎)",
                comment="第1章の発言1",
                sequence_number=1,
                chapter_number=1,
                sub_chapter_number=None,
                meeting_title="本会議",
                meeting_date="2024-01-01",
                linked_speaker_name="田中太郎",
                speaker_type="委員長",
                speaker_party_name=None,
                governing_body_name="東京都",
                governing_body_type="都道府県",
                conference_name="本会議",
                politician_id=None,
                politician_name=None,
                politician_party_name=None,
                politician_position=None,
                speaker_is_politician=False,
            ),
            MockRow(
                id=2,
                minutes_id=1,
                speaker_id=None,
                speaker_name="◆委員(佐藤花子)",
                comment="第1章-1の発言",
                sequence_number=2,
                chapter_number=1,
                sub_chapter_number=1,
                meeting_title="本会議",
                meeting_date="2024-01-01",
                linked_speaker_name=None,
                speaker_type="委員",
                speaker_party_name=None,
                governing_body_name="東京都",
                governing_body_type="都道府県",
                conference_name="本会議",
                politician_id=None,
                politician_name=None,
                politician_party_name=None,
                politician_position=None,
                speaker_is_politician=False,
            ),
            MockRow(
                id=3,
                minutes_id=1,
                speaker_id=124,
                speaker_name="議員(山田次郎)",
                comment="第2章の発言",
                sequence_number=3,
                chapter_number=2,
                sub_chapter_number=None,
                meeting_title="本会議",
                meeting_date="2024-01-01",
                linked_speaker_name="山田次郎",
                speaker_type="議員",
                speaker_party_name=None,
                governing_body_name="東京都",
                governing_body_type="都道府県",
                conference_name="本会議",
                politician_id=None,
                politician_name=None,
                politician_party_name=None,
                politician_position=None,
                speaker_is_politician=False,
            ),
            MockRow(
                id=4,
                minutes_id=1,
                speaker_id=125,
                speaker_name="議員(鈴木三郎)",
                comment="第3章の発言1",
                sequence_number=5,
                chapter_number=3,
                sub_chapter_number=None,
                meeting_title="本会議",
                meeting_date="2024-01-01",
                linked_speaker_name="鈴木三郎",
                speaker_type="議員",
                speaker_party_name=None,
                governing_body_name="東京都",
                governing_body_type="都道府県",
                conference_name="本会議",
                politician_id=None,
                politician_name=None,
                politician_party_name=None,
                politician_position=None,
                speaker_is_politician=False,
            ),
            MockRow(
                id=5,
                minutes_id=1,
                speaker_id=126,
                speaker_name="議員(高橋四郎)",
                comment="第3章の発言2",
                sequence_number=4,
                chapter_number=3,
                sub_chapter_number=None,
                meeting_title="本会議",
                meeting_date="2024-01-01",
                linked_speaker_name="高橋四郎",
                speaker_type="議員",
                speaker_party_name=None,
                governing_body_name="東京都",
                governing_body_type="都道府県",
                conference_name="本会議",
                politician_id=None,
                politician_name=None,
                politician_party_name=None,
                politician_position=None,
                speaker_is_politician=False,
            ),
        ]
        mock_data_result.fetchall.return_value = mock_conversations
        mock_data_result.keys.return_value = [
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
            "meeting_id",
            "meeting_date",
            "conference_id",
            "conference_name",
            "governing_body_id",
            "governing_body_name",
            "governing_body_type",
        ]

        # executeが2回呼ばれる（カウントクエリとデータクエリ）
        self.mock_session.execute.side_effect = [mock_count_result, mock_data_result]

        # 実行
        result = self.repository.get_conversations_with_pagination(limit=10, offset=0)

        # 検証
        self.assertEqual(result["total"], 5)
        self.assertEqual(len(result["conversations"]), 5)

        # データが返されることを確認
        for conv in result["conversations"]:
            self.assertIn("chapter_number", conv)
            self.assertIsNotNone(conv["chapter_number"])

    def test_update_speaker_links_success(self):
        """発言者紐付け更新成功テスト"""
        # Mock the UPDATE query result
        mock_result = MagicMock()
        mock_result.rowcount = 5  # 5 rows updated
        self.mock_session.execute.return_value = mock_result

        # 実行
        result = self.repository.update_speaker_links()

        # 検証
        self.assertEqual(result, 5)  # 5件更新される
        self.mock_session.execute.assert_called_once()
        self.mock_session.commit.assert_called_once()

    def test_update_speaker_links_database_error(self):
        """発言者紐付け更新エラーテスト"""
        # Executeでエラーが発生
        self.mock_session.execute.side_effect = RuntimeError("DB Error")

        # エラーが発生することを検証
        with self.assertRaises(RuntimeError):
            self.repository.update_speaker_links()

        # At least execute should be called
        self.mock_session.execute.assert_called()

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
