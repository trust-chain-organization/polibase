"""Tests for ExecuteProcessesUseCase."""

import pytest

from src.application.usecases.execute_processes_usecase import (
    ExecuteProcessesUseCase,
    ProcessExecutionInputDto,
    ProcessExecutionOutputDto,
)


class TestExecuteProcessesUseCase:
    """Test cases for ExecuteProcessesUseCase."""

    @pytest.fixture
    def use_case(self):
        """Create ExecuteProcessesUseCase instance."""
        return ExecuteProcessesUseCase()

    def test_execute_process_success(self, use_case):
        """Test successful process execution."""
        # Arrange
        input_dto = ProcessExecutionInputDto(
            process_type="minutes_division",
            command=(
                "docker compose -f docker/docker-compose.yml exec sagebase uv "
                "run python -m src.process_minutes"
            ),
        )

        # Act
        result = use_case.execute_process(input_dto)

        # Assert
        assert isinstance(result, ProcessExecutionOutputDto)
        assert result.success is True
        assert "minutes_division" in result.output
        assert result.error_message is None

    def test_execute_process_with_different_type(self, use_case):
        """Test executing process with different process type."""
        # Arrange
        input_dto = ProcessExecutionInputDto(
            process_type="speaker_extraction",
            command=(
                "docker compose -f docker/docker-compose.yml exec sagebase uv "
                "run sagebase extract-speakers"
            ),
        )

        # Act
        result = use_case.execute_process(input_dto)

        # Assert
        assert result.success is True
        assert "speaker_extraction" in result.output

    def test_execute_process_placeholder_behavior(self, use_case):
        """Test that process execution returns placeholder output."""
        # Arrange
        input_dto = ProcessExecutionInputDto(
            process_type="test_process", command="test command"
        )

        # Act
        result = use_case.execute_process(input_dto)

        # Assert
        assert result.success is True
        assert "would be executed" in result.output
        assert "test command" in result.output

    def test_get_available_processes_returns_dict(self, use_case):
        """Test that get_available_processes returns a dictionary."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        assert isinstance(processes, dict)
        assert len(processes) > 0

    def test_get_available_processes_has_minutes_category(self, use_case):
        """Test that available processes include minutes processing category."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        assert "議事録処理" in processes
        assert isinstance(processes["議事録処理"], list)
        assert len(processes["議事録処理"]) > 0

    def test_get_available_processes_has_politician_category(self, use_case):
        """Test that available processes include politician info category."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        assert "政治家情報" in processes
        assert isinstance(processes["政治家情報"], list)

    def test_get_available_processes_has_conference_members_category(self, use_case):
        """Test that available processes include conference members category."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        assert "会議体メンバー" in processes
        assert isinstance(processes["会議体メンバー"], list)

    def test_get_available_processes_has_scraping_category(self, use_case):
        """Test that available processes include scraping category."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        assert "スクレイピング" in processes
        assert isinstance(processes["スクレイピング"], list)

    def test_get_available_processes_has_other_category(self, use_case):
        """Test that available processes include other category."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        assert "その他" in processes
        assert isinstance(processes["その他"], list)

    def test_get_available_processes_process_structure(self, use_case):
        """Test that each process has required fields."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        for _category, process_list in processes.items():
            for process in process_list:
                assert "name" in process
                assert "command" in process
                assert "description" in process
                assert isinstance(process["name"], str)
                assert isinstance(process["command"], str)
                assert isinstance(process["description"], str)

    def test_execute_process_with_empty_command(self, use_case):
        """Test executing process with empty command."""
        # Arrange
        input_dto = ProcessExecutionInputDto(process_type="test", command="")

        # Act
        result = use_case.execute_process(input_dto)

        # Assert
        assert result.success is True
        assert result.output is not None

    def test_get_available_processes_minutes_division_exists(self, use_case):
        """Test that minutes division process exists in available processes."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        minutes_processes = processes.get("議事録処理", [])
        process_names = [p["name"] for p in minutes_processes]
        assert "議事録分割処理" in process_names

    def test_get_available_processes_speaker_extraction_exists(self, use_case):
        """Test that speaker extraction process exists in available processes."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        minutes_processes = processes.get("議事録処理", [])
        process_names = [p["name"] for p in minutes_processes]
        assert "発言者抽出" in process_names

    def test_get_available_processes_speaker_matching_exists(self, use_case):
        """Test that speaker matching process exists in available processes."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        minutes_processes = processes.get("議事録処理", [])
        process_names = [p["name"] for p in minutes_processes]
        assert "発言者マッチング（LLM）" in process_names

    def test_get_available_processes_politician_scraping_exists(self, use_case):
        """Test that politician scraping process exists in available processes."""
        # Act
        processes = use_case.get_available_processes()

        # Assert
        politician_processes = processes.get("政治家情報", [])
        process_names = [p["name"] for p in politician_processes]
        assert "政党議員スクレイピング" in process_names
