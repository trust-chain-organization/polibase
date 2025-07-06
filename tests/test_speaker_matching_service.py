#!/usr/bin/env python3
"""
Speaker Matching Serviceのテスト
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database.speaker_matching_service import SpeakerMatch, SpeakerMatchingService


class TestSpeakerMatchingService(unittest.TestCase):
    """SpeakerMatchingServiceのユニットテスト"""

    def setUp(self):
        """テストセットアップ"""
        self.mock_llm = Mock()

        # モックのデータベースセッション
        self.mock_session = Mock()

        with patch(
            "src.database.speaker_matching_service.get_db_session"
        ) as mock_get_session:
            mock_get_session.return_value = self.mock_session
            # LLMServiceのモックも必要
            with patch("src.database.speaker_matching_service.LLMService"):
                self.service = SpeakerMatchingService(self.mock_llm)

    def test_rule_based_exact_match(self):
        """完全一致のルールベーステスト"""
        available_speakers = [
            {"id": 1, "name": "平山たかお"},
            {"id": 2, "name": "下村あきら"},
            {"id": 3, "name": "中野晋"},
        ]

        result = self.service._rule_based_matching("平山たかお", available_speakers)

        self.assertTrue(result.matched)
        self.assertEqual(result.speaker_id, 1)
        self.assertEqual(result.speaker_name, "平山たかお")
        self.assertEqual(result.confidence, 1.0)
        self.assertEqual(result.reason, "完全一致")

    def test_rule_based_bracket_extraction(self):
        """括弧内名前抽出のテスト"""
        available_speakers = [
            {"id": 1, "name": "平山たかお"},
            {"id": 2, "name": "下村あきら"},
        ]

        result = self.service._rule_based_matching(
            "委員長(平山たかお)", available_speakers
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.speaker_id, 1)
        self.assertEqual(result.speaker_name, "平山たかお")
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.reason, "括弧内名前一致: 平山たかお")

    def test_rule_based_symbol_removal(self):
        """記号除去のテスト"""
        available_speakers = [
            {"id": 1, "name": "平山たかお"},
            {"id": 2, "name": "下村あきら"},
        ]

        result = self.service._rule_based_matching(
            "◆委員(下村あきら)", available_speakers
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.speaker_id, 2)
        self.assertEqual(result.speaker_name, "下村あきら")
        self.assertEqual(result.confidence, 0.95)

    def test_rule_based_partial_match(self):
        """部分一致のテスト"""
        available_speakers = [
            {"id": 1, "name": "平山たかお"},
            {"id": 2, "name": "中野晋"},
        ]

        result = self.service._rule_based_matching(
            "総務部長(中野晋)", available_speakers
        )

        self.assertTrue(result.matched)
        self.assertEqual(result.speaker_id, 2)
        self.assertEqual(result.speaker_name, "中野晋")
        self.assertEqual(result.confidence, 0.95)  # 括弧内名前一致のため0.95
        self.assertEqual(result.reason, "括弧内名前一致: 中野晋")

    def test_rule_based_no_match(self):
        """マッチしない場合のテスト"""
        available_speakers = [
            {"id": 1, "name": "平山たかお"},
            {"id": 2, "name": "下村あきら"},
        ]

        result = self.service._rule_based_matching("存在しない人", available_speakers)

        self.assertFalse(result.matched)
        self.assertIsNone(result.speaker_id)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.reason, "ルールベースマッチングでは一致なし")

    def test_filter_candidates(self):
        """候補絞り込みのテスト"""
        available_speakers = [
            {"id": 1, "name": "平山たかお"},
            {"id": 2, "name": "下村あきら"},
            {"id": 3, "name": "中野晋"},
            {"id": 4, "name": "橋本悟"},
            {"id": 5, "name": "谷口淳"},
        ]

        filtered = self.service._filter_candidates(
            "委員長(平山たかお)", available_speakers, max_candidates=3
        )

        # 平山たかおが最上位に来ることを確認
        self.assertTrue(any(speaker["name"] == "平山たかお" for speaker in filtered))
        self.assertLessEqual(len(filtered), 3)

    def test_format_speakers_for_llm(self):
        """LLM用フォーマットのテスト"""
        speakers = [{"id": 1, "name": "平山たかお"}, {"id": 2, "name": "下村あきら"}]

        formatted = self.service._format_speakers_for_llm(speakers)
        expected = "ID: 1, 名前: 平山たかお\nID: 2, 名前: 下村あきら"

        self.assertEqual(formatted, expected)

    @patch("src.database.speaker_matching_service.text")
    def test_get_available_speakers(self, mock_text):
        """利用可能発言者取得のテスト"""
        # モックの戻り値設定
        mock_result = Mock()
        mock_result.fetchall.return_value = [(1, "平山たかお"), (2, "下村あきら")]
        self.mock_session.execute.return_value = mock_result

        speakers = self.service._get_available_speakers()

        expected = [{"id": 1, "name": "平山たかお"}, {"id": 2, "name": "下村あきら"}]

        self.assertEqual(speakers, expected)


class TestSpeakerMatch(unittest.TestCase):
    """SpeakerMatchモデルのテスト"""

    def test_speaker_match_creation(self):
        """SpeakerMatchインスタンス作成のテスト"""
        match = SpeakerMatch(
            matched=True,
            speaker_id=1,
            speaker_name="平山たかお",
            confidence=0.95,
            reason="完全一致",
        )

        self.assertTrue(match.matched)
        self.assertEqual(match.speaker_id, 1)
        self.assertEqual(match.speaker_name, "平山たかお")
        self.assertEqual(match.confidence, 0.95)
        self.assertEqual(match.reason, "完全一致")

    def test_speaker_match_defaults(self):
        """SpeakerMatchデフォルト値のテスト"""
        match = SpeakerMatch(matched=False, reason="テスト理由")

        self.assertFalse(match.matched)
        self.assertIsNone(match.speaker_id)
        self.assertIsNone(match.speaker_name)
        self.assertEqual(match.confidence, 0.0)
        self.assertEqual(match.reason, "テスト理由")


if __name__ == "__main__":
    unittest.main()
