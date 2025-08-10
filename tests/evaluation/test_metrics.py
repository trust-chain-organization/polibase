"""Tests for evaluation metrics calculation"""

import pytest

from src.evaluation.metrics import EvaluationMetrics, MetricsCalculator


class TestEvaluationMetrics:
    """Test EvaluationMetrics class"""

    def test_to_dict(self):
        """Test converting metrics to dictionary"""
        metrics = EvaluationMetrics(
            task_type="test_task",
            test_case_id="test_001",
            metrics={"accuracy": 0.95},
            passed=True,
            error=None,
        )

        result = metrics.to_dict()

        assert result["task_type"] == "test_task"
        assert result["test_case_id"] == "test_001"
        assert result["metrics"]["accuracy"] == 0.95
        assert result["passed"] is True
        assert result["error"] is None


class TestMetricsCalculator:
    """Test MetricsCalculator class"""

    def test_calculate_minutes_division_metrics_success(self):
        """Test successful minutes division metrics calculation"""
        expected = {
            "id": "md_001",
            "expected_output": {
                "speaker_and_speech_content_list": [
                    {
                        "speaker": "山田太郎",
                        "speech_content": "こんにちは",
                        "chapter_number": 1,
                        "sub_chapter_number": 1,
                        "speech_order": 1,
                    },
                    {
                        "speaker": "田中花子",
                        "speech_content": "よろしくお願いします",
                        "chapter_number": 1,
                        "sub_chapter_number": 1,
                        "speech_order": 2,
                    },
                ]
            },
        }

        actual = {
            "speaker_and_speech_content_list": [
                {
                    "speaker": "山田太郎",
                    "speech_content": "こんにちは",
                    "chapter_number": 1,
                    "sub_chapter_number": 1,
                    "speech_order": 1,
                },
                {
                    "speaker": "田中花子",
                    "speech_content": "よろしくお願いします",
                    "chapter_number": 1,
                    "sub_chapter_number": 1,
                    "speech_order": 2,
                },
            ]
        }

        metrics = MetricsCalculator.calculate_minutes_division_metrics(expected, actual)

        assert metrics.task_type == "minutes_division"
        assert metrics.test_case_id == "md_001"
        assert metrics.metrics["speaker_match_rate"] == 1.0
        assert metrics.metrics["content_similarity"] == 1.0
        assert metrics.metrics["order_accuracy"] is True
        assert metrics.passed is True

    def test_calculate_minutes_division_metrics_partial_match(self):
        """Test minutes division metrics with partial match"""
        expected = {
            "id": "md_002",
            "expected_output": {
                "speaker_and_speech_content_list": [
                    {"speaker": "山田太郎", "speech_content": "こんにちは"},
                    {"speaker": "田中花子", "speech_content": "よろしく"},
                ]
            },
        }

        actual = {
            "speaker_and_speech_content_list": [
                {"speaker": "山田太郎", "speech_content": "こんにちは"},
                {"speaker": "佐藤次郎", "speech_content": "よろしく"},  # Wrong speaker
            ]
        }

        metrics = MetricsCalculator.calculate_minutes_division_metrics(expected, actual)

        assert metrics.metrics["speaker_match_rate"] == 0.5
        assert metrics.passed is False  # Below 80% threshold

    def test_calculate_speaker_matching_metrics_success(self):
        """Test successful speaker matching metrics calculation"""
        expected = {
            "id": "sm_001",
            "expected_output": {
                "results": [
                    {"speaker_id": 1, "politician_id": 101, "confidence_score": 0.95},
                    {"speaker_id": 2, "politician_id": 102, "confidence_score": 0.90},
                ]
            },
        }

        actual = {
            "results": [
                {"speaker_id": 1, "politician_id": 101, "confidence_score": 0.95},
                {"speaker_id": 2, "politician_id": 102, "confidence_score": 0.88},
            ]
        }

        metrics = MetricsCalculator.calculate_speaker_matching_metrics(expected, actual)

        assert metrics.task_type == "speaker_matching"
        assert metrics.test_case_id == "sm_001"
        assert metrics.metrics["politician_id_match_rate"] == 1.0
        assert metrics.metrics["confidence_score_mean"] == pytest.approx(0.915, 0.01)
        assert metrics.passed is True

    def test_calculate_party_member_extraction_metrics_success(self):
        """Test successful party member extraction metrics calculation"""
        expected = {
            "id": "pm_001",
            "expected_output": {
                "members": [
                    {"name": "山田太郎", "position": "代表", "district": "東京1区"},
                    {"name": "田中花子", "position": "副代表", "district": "東京2区"},
                ]
            },
        }

        actual = {
            "members": [
                {"name": "山田太郎", "position": "代表", "district": "東京1区"},
                {"name": "田中花子", "position": "副代表", "district": "東京2区"},
            ]
        }

        metrics = MetricsCalculator.calculate_party_member_extraction_metrics(
            expected, actual
        )

        assert metrics.task_type == "party_member_extraction"
        assert metrics.test_case_id == "pm_001"
        assert metrics.metrics["extraction_rate"] == 1.0
        assert metrics.metrics["name_accuracy"] == 1.0
        assert metrics.metrics["attribute_accuracy"] == 1.0
        assert metrics.passed is True

    def test_calculate_conference_member_matching_metrics_success(self):
        """Test successful conference member matching metrics calculation"""
        expected = {
            "id": "cm_001",
            "expected_output": {
                "matched_members": [
                    {
                        "member_name": "山田太郎",
                        "politician_id": 101,
                        "confidence_score": 0.9,
                    },
                    {
                        "member_name": "田中花子",
                        "politician_id": 102,
                        "confidence_score": 0.85,
                    },
                ]
            },
        }

        actual = {
            "matched_members": [
                {
                    "member_name": "山田太郎",
                    "politician_id": 101,
                    "confidence_score": 0.92,
                },
                {
                    "member_name": "田中花子",
                    "politician_id": 102,
                    "confidence_score": 0.88,
                },
            ]
        }

        metrics = MetricsCalculator.calculate_conference_member_matching_metrics(
            expected, actual
        )

        assert metrics.task_type == "conference_member_matching"
        assert metrics.test_case_id == "cm_001"
        assert metrics.metrics["match_precision"] == 1.0
        assert metrics.metrics["match_recall"] == 1.0
        assert metrics.metrics["f1_score"] == 1.0
        assert metrics.passed is True

    def test_calculate_metrics_unknown_task_type(self):
        """Test metrics calculation with unknown task type"""
        expected = {"id": "unknown_001"}
        actual = {}

        metrics = MetricsCalculator.calculate_metrics("unknown_task", expected, actual)

        assert metrics.task_type == "unknown_task"
        assert metrics.error == "Unknown task type: unknown_task"
        assert metrics.passed is False

    def test_calculate_metrics_with_none_values(self):
        """Test metrics calculation handles None values gracefully"""
        expected = None  # Invalid data
        actual = {}

        metrics = MetricsCalculator.calculate_minutes_division_metrics(expected, actual)

        # Should handle None gracefully with default values
        assert metrics.error is None
        assert metrics.passed is False
        assert metrics.metrics["speaker_match_rate"] == 0.0
        assert metrics.metrics["content_similarity"] == 0.0
