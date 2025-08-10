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
        expected = {"id": "sm_001", "expected_output": {"results": None}}
        actual = {}

        metrics = MetricsCalculator.calculate_speaker_matching_metrics(expected, actual)

        # Should handle None gracefully with default values and set error
        assert metrics.error is not None  # Error is expected when results is None
        assert metrics.passed is False
        assert metrics.metrics["politician_id_match_rate"] == 0.0
        assert metrics.metrics["confidence_score_mean"] == 0.0
