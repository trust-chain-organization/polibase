"""Evaluation runner for executing test cases and calculating metrics"""

import json
import logging
from pathlib import Path
from typing import Any

from .metrics import EvaluationMetrics, MetricsCalculator

logger = logging.getLogger(__name__)


class EvaluationRunner:
    """Run evaluation tests and calculate metrics"""

    def __init__(self):
        """Initialize evaluation runner"""
        self.metrics_calculator = MetricsCalculator()

    def load_dataset(self, dataset_path: str) -> dict[str, Any]:
        """Load evaluation dataset from JSON file

        Args:
            dataset_path: Path to the dataset JSON file

        Returns:
            Loaded dataset dictionary

        Raises:
            FileNotFoundError: If dataset file doesn't exist
            json.JSONDecodeError: If dataset file is not valid JSON
        """
        path = Path(dataset_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def execute_test_case(
        self, task_type: str, test_case: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a single test case

        This is a placeholder that should be replaced with actual system execution.
        In production, this would call the actual LLM-based systems.

        Args:
            task_type: Type of task to execute
            test_case: Test case data

        Returns:
            Actual output from system
        """
        # TODO: Implement actual system execution based on task type
        # For now, return a mock response that matches expected format

        mock_responses = {
            "minutes_division": {
                "speaker_and_speech_content_list": test_case.get(
                    "expected_output", {}
                ).get("speaker_and_speech_content_list", [])
            },
            "speaker_matching": {
                "results": test_case.get("expected_output", {}).get("results", [])
            },
            "party_member_extraction": {
                "members": test_case.get("expected_output", {}).get("members", [])
            },
            "conference_member_matching": {
                "matched_members": test_case.get("expected_output", {}).get(
                    "matched_members", []
                )
            },
        }

        # In production, this would actually call the respective systems:
        # - minutes_division: MinutesDivider
        # - speaker_matching: SpeakerMatcher with LLM
        # - party_member_extraction: PartyMemberExtractor
        # - conference_member_matching: ConferenceMemberMatcher

        logger.info(f"Executing test case {test_case.get('id')} for task {task_type}")

        # Return mock response for now
        return mock_responses.get(task_type, {})

    def run_evaluation(
        self,
        task_type: str | None = None,
        dataset_path: str | None = None,
        run_all: bool = False,
    ) -> list[EvaluationMetrics]:
        """Run evaluation for specified task or all tasks

        Args:
            task_type: Type of task to evaluate (if None and not run_all, error)
            dataset_path: Path to dataset file (if None, uses default)
            run_all: Whether to run all tasks

        Returns:
            List of evaluation metrics
        """
        all_metrics = []

        if run_all:
            # Run all tasks
            task_types = [
                "minutes_division",
                "speaker_matching",
                "party_member_extraction",
                "conference_member_matching",
            ]
        elif task_type:
            task_types = [task_type]
        else:
            raise ValueError("Either specify task_type or use run_all=True")

        for current_task in task_types:
            # Determine dataset path
            if dataset_path and not run_all:
                current_dataset_path = dataset_path
            else:
                # Use default path pattern
                current_dataset_path = (
                    f"data/evaluation/datasets/{current_task}/basic_cases.json"
                )

            try:
                # Load dataset
                dataset = self.load_dataset(current_dataset_path)

                # Check task type matches
                if dataset.get("task_type") != current_task:
                    logger.warning(
                        f"Task type mismatch: expected {current_task}, "
                        f"got {dataset.get('task_type')}"
                    )

                # Process each test case
                test_cases = dataset.get("test_cases", [])
                print(f"\nRunning {len(test_cases)} test cases for {current_task}")

                for test_case in test_cases:
                    # Execute test case
                    actual_output = self.execute_test_case(current_task, test_case)

                    # Calculate metrics
                    metrics = self.metrics_calculator.calculate_metrics(
                        current_task, test_case, actual_output
                    )

                    all_metrics.append(metrics)

                    # Display test case result
                    status = "✅ PASSED" if metrics.passed else "❌ FAILED"
                    print(f"  Test {test_case.get('id', 'unknown')}: {status}")

            except FileNotFoundError as e:
                logger.error(f"Dataset not found for {current_task}: {e}")
                print(f"Dataset not found for {current_task}")
            except Exception as e:
                logger.error(f"Error processing {current_task}: {e}")
                print(f"Error processing {current_task}: {e}")

        return all_metrics

    def display_results(self, metrics_list: list[EvaluationMetrics]) -> None:
        """Display evaluation results in a formatted output

        Args:
            metrics_list: List of evaluation metrics to display
        """
        if not metrics_list:
            print("No evaluation results to display")
            return

        # Group metrics by task type
        task_groups: dict[str, list[EvaluationMetrics]] = {}
        for metrics in metrics_list:
            task_type = metrics.task_type
            if task_type not in task_groups:
                task_groups[task_type] = []
            task_groups[task_type].append(metrics)

        # Display results for each task type
        for task_type, task_metrics in task_groups.items():
            print(f"\nResults for {task_type}:")
            print("-" * 60)

            # Get metric columns based on task type
            metric_columns = self._get_metric_columns(task_type)

            # Print header
            header = f"{'Test Case':<20} {'Status':<10}"
            for col in metric_columns:
                header += f" {col:<15}"
            print(header)
            print("=" * 60)

            # Print rows
            for metrics in task_metrics:
                row = f"{metrics.test_case_id:<20} "
                row += f"{'✅ PASS' if metrics.passed else '❌ FAIL':<10}"

                # Add metric values
                for col in metric_columns:
                    col_key = col.lower().replace(" ", "_")
                    value = metrics.metrics.get(col_key, "-")
                    if isinstance(value, float):
                        formatted = f"{value:.2%}" if value <= 1.0 else f"{value:.2f}"
                        row += f" {formatted:<15}"
                    else:
                        row += f" {str(value):<15}"

                print(row)

            # Calculate and display summary statistics
            self._display_summary(task_type, task_metrics)

    def _get_metric_columns(self, task_type: str) -> list[str]:
        """Get metric column names for task type

        Args:
            task_type: Type of task

        Returns:
            List of metric column names
        """
        columns_map = {
            "minutes_division": ["Speaker Match", "Content Similarity", "Count"],
            "speaker_matching": ["ID Match Rate", "Confidence", "Accuracy"],
            "party_member_extraction": ["Extraction Rate", "Name Accuracy", "Count"],
            "conference_member_matching": ["Precision", "Recall", "F1 Score"],
        }
        return columns_map.get(task_type, ["Metric 1", "Metric 2", "Metric 3"])

    def _display_summary(
        self, task_type: str, metrics_list: list[EvaluationMetrics]
    ) -> None:
        """Display summary statistics for a task type

        Args:
            task_type: Type of task
            metrics_list: List of metrics for the task
        """
        total = len(metrics_list)
        passed = sum(1 for m in metrics_list if m.passed)
        pass_rate = passed / total if total > 0 else 0

        print("\nSummary:")
        print(f"  Total test cases: {total}")
        print(f"  Passed: {passed}")
        print(f"  Failed: {total - passed}")
        print(f"  Pass rate: {pass_rate:.1%}")

        # Calculate average metrics
        if metrics_list and metrics_list[0].metrics:
            print("\nAverage Metrics:")
            metric_sums: dict[str, float] = {}
            metric_counts: dict[str, int] = {}

            for metrics in metrics_list:
                for key, value in metrics.metrics.items():
                    if isinstance(value, int | float) and not key.endswith("_count"):
                        if key not in metric_sums:
                            metric_sums[key] = 0
                            metric_counts[key] = 0
                        metric_sums[key] += value
                        metric_counts[key] += 1

            for key in sorted(metric_sums.keys()):
                avg = metric_sums[key] / metric_counts[key]
                display_key = key.replace("_", " ").title()
                if avg <= 1.0:  # Likely a percentage
                    print(f"  {display_key}: {avg:.1%}")
                else:
                    print(f"  {display_key}: {avg:.2f}")
