"""Performance test for minutes processing with LLM history recording."""

import time
from statistics import mean, stdev
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from src.minutes_divide_processor.minutes_divider import MinutesDivider


class TestMinutesProcessingPerformance:
    """Test performance impact of LLM history recording."""

    @pytest.fixture
    def mock_llm_service(self):
        """Create a mock LLM service with realistic delays."""
        # Create a mock without spec to allow arbitrary attributes
        mock = Mock()

        # Mock methods with small delays to simulate real processing
        def mock_get_structured_llm(schema):
            time.sleep(0.001)  # 1ms delay
            # Return a mock that acts like a structured LLM
            return lambda x: x  # Pass through for now

        def mock_get_prompt(prompt_name):
            time.sleep(0.001)  # 1ms delay
            # Return a mock prompt template
            from langchain_core.prompts import ChatPromptTemplate

            return ChatPromptTemplate.from_template("Test prompt: {minutes}")

        def mock_invoke_with_retry(chain, inputs):
            time.sleep(0.05)  # 50ms delay to simulate LLM call
            # Import the model to return proper type
            from src.minutes_divide_processor.models import SectionInfo, SectionInfoList

            return SectionInfoList(
                section_info_list=[
                    SectionInfo(chapter_number=1, keyword="開会"),
                    SectionInfo(chapter_number=2, keyword="議事"),
                ]
            )

        mock.get_structured_llm = Mock(side_effect=mock_get_structured_llm)
        mock.get_prompt = Mock(side_effect=mock_get_prompt)
        mock.invoke_with_retry = Mock(side_effect=mock_invoke_with_retry)

        # Mock async methods
        mock.set_history_repository = AsyncMock()
        mock.get_processing_history = AsyncMock(return_value=[])
        mock.extract_speeches_from_text = AsyncMock(return_value=[])

        return mock

    @pytest.fixture
    def mock_history_repository(self):
        """Create a mock history repository with realistic delays."""
        mock = AsyncMock()

        # Simulate database operations with small delays
        async def mock_create(entry):
            await AsyncMock(side_effect=lambda: time.sleep(0.002))()  # 2ms delay
            return entry

        async def mock_update(entry):
            await AsyncMock(side_effect=lambda: time.sleep(0.002))()  # 2ms delay
            return entry

        mock.create = AsyncMock(side_effect=mock_create)
        mock.update = AsyncMock(side_effect=mock_update)
        return mock

    @patch("src.minutes_divide_processor.minutes_divider.hub.pull")
    def test_performance_impact_within_5_percent(
        self, mock_hub_pull, mock_llm_service, mock_history_repository
    ):
        """Test that history recording adds less than 5% overhead."""
        # Mock hub.pull to avoid network calls
        from langchain_core.prompts import ChatPromptTemplate

        mock_hub_pull.return_value = ChatPromptTemplate.from_template(
            "Test prompt: {minutes}"
        )

        test_text = "これはテスト議事録です。" * 100  # Realistic size text

        # Measure baseline performance (without history recording)
        baseline_times = []
        divider_without_history = MinutesDivider(llm_service=mock_llm_service)

        for _ in range(10):  # Run 10 iterations
            start_time = time.time()
            divider_without_history.pre_process(test_text)
            divider_without_history.section_divide_run(test_text)
            end_time = time.time()
            baseline_times.append(end_time - start_time)

        baseline_mean = mean(baseline_times)
        baseline_std = stdev(baseline_times)

        # Measure performance with history recording
        instrumented_times = []
        instrumented_service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="test-model",
            model_version="1.0",
        )
        divider_with_history = MinutesDivider(llm_service=instrumented_service)

        for _ in range(10):  # Run 10 iterations
            start_time = time.time()
            divider_with_history.pre_process(test_text)
            divider_with_history.section_divide_run(test_text)
            end_time = time.time()
            instrumented_times.append(end_time - start_time)

        instrumented_mean = mean(instrumented_times)
        instrumented_std = stdev(instrumented_times)

        # Calculate performance impact
        overhead_percentage = (
            (instrumented_mean - baseline_mean) / baseline_mean
        ) * 100

        # Print performance metrics
        print("\nPerformance Test Results:")
        print(f"Baseline mean: {baseline_mean:.3f}s (±{baseline_std:.3f}s)")
        print(f"With history mean: {instrumented_mean:.3f}s (±{instrumented_std:.3f}s)")
        print(f"Overhead: {overhead_percentage:.2f}%")

        # Assert that overhead is less than 5%
        assert overhead_percentage < 5.0, (
            f"Performance overhead {overhead_percentage:.2f}% exceeds 5% threshold"
        )

    @patch("src.minutes_divide_processor.minutes_divider.hub.pull")
    def test_history_recording_does_not_block_main_processing(
        self, mock_hub_pull, mock_llm_service, mock_history_repository
    ):
        """Test that history recording failures don't block main processing."""
        # Mock hub.pull
        from langchain_core.prompts import ChatPromptTemplate

        mock_hub_pull.return_value = ChatPromptTemplate.from_template(
            "Test prompt: {minutes}"
        )

        # Configure history repository to fail
        mock_history_repository.create = AsyncMock(
            side_effect=Exception("Database error")
        )

        # Create instrumented service
        instrumented_service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="test-model",
            model_version="1.0",
        )

        # Processing should still work even if history recording fails
        divider = MinutesDivider(llm_service=instrumented_service)

        # This should not raise an exception
        result = divider.section_divide_run("テスト議事録")
        assert result is not None

    @pytest.mark.asyncio
    async def test_async_history_recording_performance(
        self, mock_llm_service, mock_history_repository
    ):
        """Test async history recording performance."""

        # Configure LLM service with realistic async delay
        async def mock_extract_speeches(text):
            await AsyncMock(side_effect=lambda: time.sleep(0.1))()  # 100ms delay
            return [{"speaker": "テスト", "content": "内容"}]

        mock_llm_service.extract_speeches_from_text = AsyncMock(
            side_effect=mock_extract_speeches
        )

        # Create instrumented service
        instrumented_service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="test-model",
            model_version="1.0",
        )

        # Measure time for async operation
        start_time = time.time()
        result = await instrumented_service.extract_speeches_from_text("テストテキスト")
        end_time = time.time()

        # Total time should be close to LLM delay (100ms) plus small overhead
        total_time = end_time - start_time
        # Allow up to 60ms overhead for history recording (async operations)
        assert total_time < 0.16  # 100ms + 60ms overhead tolerance
        assert len(result) == 1
        # Ensure it's not too slow
        assert total_time > 0.09  # Should be at least close to 100ms

    def test_memory_usage_remains_stable(
        self, mock_llm_service, mock_history_repository
    ):
        """Test that history recording doesn't cause memory leaks."""
        import gc
        import tracemalloc

        # Start memory tracking
        tracemalloc.start()

        # Create instrumented service
        instrumented_service = InstrumentedLLMService(
            llm_service=mock_llm_service,
            history_repository=mock_history_repository,
            model_name="test-model",
            model_version="1.0",
        )
        divider = MinutesDivider(llm_service=instrumented_service)

        # Get baseline memory
        gc.collect()
        baseline_memory = tracemalloc.get_traced_memory()[0]

        # Process many iterations
        for i in range(100):
            divider.section_divide_run(f"テスト議事録 {i}")

        # Get memory after processing
        gc.collect()
        final_memory = tracemalloc.get_traced_memory()[0]

        # Stop tracking
        tracemalloc.stop()

        # Memory increase should be minimal (less than 10MB)
        memory_increase_mb = (final_memory - baseline_memory) / (1024 * 1024)
        print(f"\nMemory increase: {memory_increase_mb:.2f} MB")

        assert memory_increase_mb < 10.0, (
            f"Memory increase {memory_increase_mb:.2f} MB exceeds threshold"
        )
