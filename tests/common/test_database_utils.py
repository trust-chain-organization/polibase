"""Unit tests for database_utils module"""

from unittest.mock import MagicMock

import pytest

from src.common.database_utils import (
    batch_save_with_logging,
    display_repository_status,
    save_data_with_logging,
)
from src.infrastructure.exceptions import DatabaseError, RepositoryException


class MockRepository:
    """Mock repository for testing"""

    def __init__(self, count=5, records=None):
        self.count = count
        self.records = records or [
            {"id": i, "name": f"Record {i}", "value": i * 10}
            for i in range(1, count + 1)
        ]

    def get_count(self):
        return self.count

    def get_all(self):
        return self.records


class TestDisplayRepositoryStatus:
    """Test cases for display_repository_status function"""

    def test_display_status_with_records(self, capsys):
        """Test displaying status when records exist"""
        # Setup
        repo = MockRepository(count=5)

        # Execute
        display_repository_status(repo, "test_table")

        # Verify
        captured = capsys.readouterr()
        assert "📊 現在のtest_tableテーブルレコード数: 5件" in captured.out
        assert "📋 最新の5件のレコード:" in captured.out
        assert "ID: 1" in captured.out
        assert "name: Record 1" in captured.out

    def test_display_status_with_no_records(self, capsys):
        """Test displaying status when no records exist"""
        # Setup
        repo = MockRepository(count=0, records=[])

        # Execute
        display_repository_status(repo, "empty_table")

        # Verify
        captured = capsys.readouterr()
        assert "📊 現在のempty_tableテーブルレコード数: 0件" in captured.out
        assert "📋 最新の5件のレコード:" not in captured.out

    def test_display_status_with_additional_stats(self, capsys):
        """Test displaying status with additional statistics"""
        # Setup
        repo = MockRepository(count=10)
        additional_stats = {"アクティブレコード": 8, "非アクティブレコード": 2}

        # Execute
        display_repository_status(repo, "stats_table", additional_stats)

        # Verify
        captured = capsys.readouterr()
        assert "📊 現在のstats_tableテーブルレコード数: 10件" in captured.out
        assert "- アクティブレコード: 8件" in captured.out
        assert "- 非アクティブレコード: 2件" in captured.out

    def test_display_status_with_long_text(self, capsys):
        """Test displaying records with long text values"""
        # Setup
        long_text = "A" * 100
        repo = MockRepository(
            count=1,
            records=[{"id": 1, "description": long_text}],
        )

        # Execute
        display_repository_status(repo, "long_text_table")

        # Verify
        captured = capsys.readouterr()
        assert "description: " + "A" * 50 + "..." in captured.out

    def test_display_status_missing_method(self):
        """Test error when repository doesn't implement required method"""

        # Setup
        class BadRepository:
            pass

        repo = BadRepository()

        # Execute and verify
        with pytest.raises(RepositoryException) as exc_info:
            display_repository_status(repo, "bad_table")

        assert "does not implement required method" in str(exc_info.value)

    def test_display_status_repository_error(self):
        """Test error handling when repository operation fails"""

        # Setup
        class FailingRepository:
            def get_count(self):
                raise RuntimeError("Database connection failed")

        repo = FailingRepository()

        # Execute and verify
        with pytest.raises(RepositoryException) as exc_info:
            display_repository_status(repo, "failing_table")

        assert "failing_table" in str(exc_info.value)


class TestSaveDataWithLogging:
    """Test cases for save_data_with_logging function"""

    def test_save_data_success(self, capsys):
        """Test successful data save"""
        # Setup
        mock_save_func = MagicMock(return_value=[1, 2, 3])
        test_data = {"test": "data"}

        # Execute
        result = save_data_with_logging(mock_save_func, test_data, "test_data")

        # Verify
        assert result == [1, 2, 3]
        mock_save_func.assert_called_once_with(test_data)
        captured = capsys.readouterr()
        assert (
            "💾 データベース保存完了: 3件のtest_dataレコードを保存しました"
            in captured.out
        )

    def test_save_data_empty(self, capsys):
        """Test save with empty data"""
        # Setup
        mock_save_func = MagicMock()

        # Execute
        result = save_data_with_logging(mock_save_func, None, "empty_data")

        # Verify
        assert result == []
        mock_save_func.assert_not_called()

    def test_save_data_wrong_return_type(self):
        """Test error when save function returns wrong type"""
        # Setup
        mock_save_func = MagicMock(return_value="not a list")
        test_data = {"test": "data"}

        # Execute and verify
        with pytest.raises(DatabaseError) as exc_info:
            save_data_with_logging(mock_save_func, test_data, "wrong_type")

        assert "Failed to save wrong_type data" in str(exc_info.value)

    def test_save_data_database_error(self):
        """Test re-raising DatabaseError"""
        # Setup
        mock_save_func = MagicMock(
            side_effect=DatabaseError("Connection failed", {"code": 500})
        )
        test_data = {"test": "data"}

        # Execute and verify
        with pytest.raises(DatabaseError) as exc_info:
            save_data_with_logging(mock_save_func, test_data, "error_data")

        assert "Connection failed" in str(exc_info.value)

    def test_save_data_generic_error(self, capsys):
        """Test generic error handling"""
        # Setup
        mock_save_func = MagicMock(side_effect=RuntimeError("Unexpected error"))
        test_data = {"test": "data"}

        # Execute and verify
        with pytest.raises(DatabaseError) as exc_info:
            save_data_with_logging(mock_save_func, test_data, "generic_error")

        assert "Failed to save generic_error data" in str(exc_info.value)
        assert exc_info.value.details["data_type"] == "generic_error"
        captured = capsys.readouterr()
        assert "❌ データベース保存エラー:" in captured.out


class TestBatchSaveWithLogging:
    """Test cases for batch_save_with_logging function"""

    def test_batch_save_success(self, capsys):
        """Test successful batch save"""
        # Setup
        items = list(range(10))
        saved_ids = []

        def mock_save_func(batch):
            ids = [i * 10 for i in batch]
            saved_ids.extend(ids)
            return ids

        # Execute
        result = batch_save_with_logging(
            mock_save_func, items, batch_size=3, data_type="test_items"
        )

        # Verify
        assert len(result) == 10
        assert result == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
        captured = capsys.readouterr()
        assert (
            "バッチ処理完了: 合計 10件のtest_itemsレコードを保存しました"
            in captured.out
        )

    def test_batch_save_empty_items(self, capsys):
        """Test batch save with empty items"""
        # Setup
        mock_save_func = MagicMock()

        # Execute
        result = batch_save_with_logging(
            mock_save_func, [], batch_size=10, data_type="empty_items"
        )

        # Verify
        assert result == []
        mock_save_func.assert_not_called()

    def test_batch_save_single_batch(self, capsys):
        """Test batch save with items fitting in single batch"""
        # Setup
        items = [1, 2, 3]
        mock_save_func = MagicMock(return_value=[10, 20, 30])

        # Execute
        result = batch_save_with_logging(
            mock_save_func, items, batch_size=10, data_type="single_batch"
        )

        # Verify
        assert result == [10, 20, 30]
        mock_save_func.assert_called_once_with([1, 2, 3])
        captured = capsys.readouterr()
        assert "バッチ 1/1 完了: 3件保存" in captured.out

    def test_batch_save_error_mid_process(self, capsys):
        """Test batch save error in the middle of processing"""
        # Setup
        items = list(range(10))
        call_count = 0

        def mock_save_func(batch):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Database error")
            return [i * 10 for i in batch]

        # Execute and verify
        with pytest.raises(DatabaseError) as exc_info:
            batch_save_with_logging(
                mock_save_func, items, batch_size=3, data_type="error_batch"
            )

        assert "Batch save failed after saving 3 items" in str(exc_info.value)
        assert exc_info.value.details["saved_count"] == 3
        captured = capsys.readouterr()
        assert "バッチ保存エラー: 3件保存後にエラーが発生しました" in captured.out

    def test_batch_save_exact_batches(self):
        """Test batch save when items divide evenly into batches"""
        # Setup
        items = list(range(9))  # 3 batches of 3
        batches_processed = []

        def mock_save_func(batch):
            batches_processed.append(len(batch))
            return [i * 10 for i in batch]

        # Execute
        result = batch_save_with_logging(
            mock_save_func, items, batch_size=3, data_type="exact_batches"
        )

        # Verify
        assert len(result) == 9
        assert batches_processed == [3, 3, 3]
