"""SEEDファイル生成モジュールのテスト"""

import io
from unittest.mock import MagicMock, patch

import pytest

from src.seed_generator import SeedGenerator


class TestSeedGenerator:
    """SeedGeneratorのテスト"""

    @pytest.fixture
    def seed_generator(self):
        """SeedGeneratorのインスタンスを返すフィクスチャ"""
        return SeedGenerator()

    def test_generate_governing_bodies_seed(self, seed_generator):
        """governing_bodiesのSEED生成テスト"""
        # モックデータの準備
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {"id": 1, "name": "日本国", "type": "国"},
            {"id": 2, "name": "東京都", "type": "都道府県"},
            {"id": 3, "name": "大阪府", "type": "都道府県"},
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        output = io.StringIO()
        result = seed_generator.generate_governing_bodies_seed(output=output)

        # 検証
        assert "INSERT INTO governing_bodies (name, type) VALUES" in result
        assert "('日本国', '国')" in result
        assert "('東京都', '都道府県')" in result
        assert "('大阪府', '都道府県')" in result
        assert "ON CONFLICT (name, type) DO NOTHING;" in result

        # コメントの確認
        assert "-- 国" in result
        assert "-- 都道府県" in result

    def test_generate_conferences_seed(self, seed_generator):
        """conferencesのSEED生成テスト"""
        # モックデータの準備
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {
                "id": 1,
                "name": "国会",
                "type": "立法",
                "governing_body_id": 1,
                "governing_body_name": "日本国",
                "governing_body_type": "国",
            },
            {
                "id": 2,
                "name": "東京都議会",
                "type": "立法",
                "governing_body_id": 2,
                "governing_body_name": "東京都",
                "governing_body_type": "都道府県",
            },
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        output = io.StringIO()
        result = seed_generator.generate_conferences_seed(output=output)

        # 検証
        assert (
            "INSERT INTO conferences (name, type, governing_body_id) VALUES" in result
        )
        assert (
            "('国会', '立法', (SELECT id FROM governing_bodies WHERE name = "
            "'日本国' AND type = '国'))" in result
        )
        assert (
            "('東京都議会', '立法', (SELECT id FROM governing_bodies WHERE name = "
            "'東京都' AND type = '都道府県'))" in result
        )
        assert "ON CONFLICT (name, governing_body_id) DO NOTHING;" in result

        # コメントの確認
        assert "-- 日本国 (国)" in result
        assert "-- 東京都 (都道府県)" in result

    def test_generate_political_parties_seed(self, seed_generator):
        """political_partiesのSEED生成テスト"""
        # モックデータの準備
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {"id": 1, "name": "自由民主党"},
            {"id": 2, "name": "立憲民主党"},
            {"id": 3, "name": "無所属"},
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        output = io.StringIO()
        result = seed_generator.generate_political_parties_seed(output=output)

        # 検証
        assert "INSERT INTO political_parties (name) VALUES" in result
        assert "('自由民主党')" in result
        assert "('立憲民主党')" in result
        assert "('無所属')" in result
        assert "ON CONFLICT (name) DO NOTHING;" in result

    def test_sql_injection_protection(self, seed_generator):
        """SQLインジェクション対策のテスト"""
        # 悪意のあるデータを含むモックデータ
        mock_result = MagicMock()
        mock_result.fetchall.return_value = [
            {
                "id": 1,
                "name": "O'Reilly's Party",
                "type": "国",
            },  # シングルクォートを含む
        ]

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_governing_bodies_seed()

        # 検証: シングルクォートが適切にエスケープされていること
        assert "('O''Reilly''s Party', '国')" in result

    def test_empty_data(self, seed_generator):
        """データが空の場合のテスト"""
        # 空のモックデータ
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_conn = MagicMock()
        mock_conn.execute.return_value = mock_result
        seed_generator.engine = MagicMock()
        seed_generator.engine.connect.return_value.__enter__.return_value = mock_conn

        # 実行
        result = seed_generator.generate_governing_bodies_seed()

        # 検証: 基本的なSQL構造は生成されるが、データはない
        assert "INSERT INTO governing_bodies (name, type) VALUES" in result
        assert "ON CONFLICT (name, type) DO NOTHING;" in result
        # データ行がないことを確認（VALUESとON CONFLICTの間に改行のみ）
        lines = result.split("\n")
        values_line = next(i for i, line in enumerate(lines) if "VALUES" in line)
        conflict_line = next(i for i, line in enumerate(lines) if "ON CONFLICT" in line)
        assert conflict_line - values_line == 1  # 直接隣接している

    @patch("src.seed_generator.get_db_engine")
    @patch("builtins.open", create=True)
    def test_generate_all_seeds(self, mock_open, mock_get_engine):
        """generate_all_seeds関数のテスト"""
        # モックの設定
        mock_engine = MagicMock()
        mock_get_engine.return_value = mock_engine
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # 各クエリに対する結果を設定
        mock_results = [
            # governing_bodies
            [{"id": 1, "name": "日本国", "type": "国"}],
            # conferences
            [
                {
                    "id": 1,
                    "name": "国会",
                    "type": "立法",
                    "governing_body_id": 1,
                    "governing_body_name": "日本国",
                    "governing_body_type": "国",
                }
            ],
            # political_parties
            [{"id": 1, "name": "自由民主党"}],
        ]

        mock_conn = MagicMock()
        results = []
        for mock_data in mock_results:
            mock_result = MagicMock()
            mock_result.fetchall.return_value = mock_data
            results.append(mock_result)

        mock_conn.execute.side_effect = results
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        # インポートして実行
        from src.seed_generator import generate_all_seeds

        generate_all_seeds("test_output/")

        # ファイルが3つ開かれたことを確認
        assert mock_open.call_count == 3

        # 正しいファイル名で開かれたことを確認
        expected_files = [
            "test_output/seed_governing_bodies_generated.sql",
            "test_output/seed_conferences_generated.sql",
            "test_output/seed_political_parties_generated.sql",
        ]
        actual_files = [call[0][0] for call in mock_open.call_args_list]
        assert set(actual_files) == set(expected_files)
