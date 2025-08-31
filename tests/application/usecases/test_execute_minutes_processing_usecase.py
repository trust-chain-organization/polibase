"""ExecuteMinutesProcessingUseCaseのテスト"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingDTO,
    ExecuteMinutesProcessingUseCase,
)
from src.domain.entities.conversation import Conversation
from src.domain.entities.meeting import Meeting
from src.domain.entities.minutes import Minutes
from src.exceptions import APIKeyError


@pytest.fixture
def mock_repositories():
    """モックリポジトリのフィクスチャ"""
    meeting_repo = AsyncMock()
    minutes_repo = AsyncMock()
    conversation_repo = AsyncMock()
    speaker_repo = AsyncMock()
    speaker_service = MagicMock()

    return {
        "meeting_repo": meeting_repo,
        "minutes_repo": minutes_repo,
        "conversation_repo": conversation_repo,
        "speaker_repo": speaker_repo,
        "speaker_service": speaker_service,
    }


@pytest.fixture
def use_case(mock_repositories):
    """ユースケースのフィクスチャ"""
    return ExecuteMinutesProcessingUseCase(
        meeting_repository=mock_repositories["meeting_repo"],
        minutes_repository=mock_repositories["minutes_repo"],
        conversation_repository=mock_repositories["conversation_repo"],
        speaker_repository=mock_repositories["speaker_repo"],
        speaker_domain_service=mock_repositories["speaker_service"],
    )


@pytest.fixture
def sample_meeting():
    """サンプル会議エンティティ"""
    return Meeting(
        id=1,
        conference_id=1,
        date=datetime(2024, 1, 1),
        url="https://example.com",
        gcs_text_uri="gs://bucket/text.txt",
        gcs_pdf_uri=None,
    )


@pytest.fixture
def sample_minutes():
    """サンプル議事録エンティティ"""
    return Minutes(
        id=1,
        meeting_id=1,
        url="https://example.com",
    )


@pytest.mark.asyncio
async def test_execute_success(
    use_case, mock_repositories, sample_meeting, sample_minutes
):
    """正常に議事録処理が実行されることをテスト"""
    # モックの設定
    mock_repositories["meeting_repo"].get_by_id.return_value = sample_meeting
    mock_repositories["minutes_repo"].get_by_meeting.return_value = None
    mock_repositories["minutes_repo"].create.return_value = sample_minutes
    mock_repositories["conversation_repo"].get_by_minutes.return_value = []

    # GCSStorageをモック
    with patch(
        "src.application.usecases.execute_minutes_processing_usecase.GCSStorage"
    ) as mock_gcs_patch:
        mock_gcs = mock_gcs_patch.return_value
        mock_gcs.download_content.return_value = "議事録テキスト"

        # MinutesProcessAgentをモック
        with patch(
            "src.application.usecases.execute_minutes_processing_usecase.MinutesProcessAgent"
        ) as mock_agent_patch:
            mock_agent = mock_agent_patch.return_value
            mock_agent.run.return_value = [
                MagicMock(speaker="田中太郎", speech_content="発言1"),
                MagicMock(speaker="山田花子", speech_content="発言2"),
            ]

            # LLMServiceFactoryをモック
            with patch(
                "src.application.usecases.execute_minutes_processing_usecase.LLMServiceFactory"
            ) as mock_llm_factory:
                # LLMサービスのモックを設定
                mock_llm_service = MagicMock()
                mock_llm_factory.create_gemini_service.return_value = mock_llm_service

                # 環境変数をモック
                with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
                    # Conversationのバルク作成をモック
                    created_conversations = [
                        Conversation(
                            id=1,
                            minutes_id=1,
                            speaker_name="田中太郎",
                            comment="発言1",
                            sequence_number=1,
                        ),
                        Conversation(
                            id=2,
                            minutes_id=1,
                            speaker_name="山田花子",
                            comment="発言2",
                            sequence_number=2,
                        ),
                    ]
                    mock_repositories[
                        "conversation_repo"
                    ].bulk_create.return_value = created_conversations

                    # Speakerの作成をモック
                    mock_repositories[
                        "speaker_service"
                    ].extract_party_from_name.side_effect = [
                        ("田中太郎", "自民党"),
                        ("山田花子", "立憲民主党"),
                    ]
                    mock_repositories[
                        "speaker_repo"
                    ].get_by_name_party_position.return_value = None
                    mock_repositories["speaker_repo"].create.return_value = Mock()

                    # 実行
                    request = ExecuteMinutesProcessingDTO(meeting_id=1)
                    result = await use_case.execute(request)

                    # 検証
                    assert result.meeting_id == 1
                    assert result.minutes_id == 1
                    assert result.total_conversations == 2
                    assert result.unique_speakers == 2
                    assert result.processing_time_seconds > 0
                    assert result.errors is None

                    # リポジトリメソッドが呼ばれたことを確認
                    mock_repositories["meeting_repo"].get_by_id.assert_called_once_with(
                        1
                    )
                    mock_repositories["minutes_repo"].create.assert_called_once()
                    mock_repositories[
                        "conversation_repo"
                    ].bulk_create.assert_called_once()
                    assert mock_repositories["speaker_repo"].create.call_count == 2


@pytest.mark.asyncio
async def test_execute_meeting_not_found(use_case, mock_repositories):
    """会議が見つからない場合のエラーテスト"""
    # モックの設定
    mock_repositories["meeting_repo"].get_by_id.return_value = None

    # 実行と検証
    request = ExecuteMinutesProcessingDTO(meeting_id=999)
    with pytest.raises(ValueError, match="Meeting 999 not found"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_execute_already_has_conversations(
    use_case, mock_repositories, sample_meeting, sample_minutes
):
    """既にConversationsが存在する場合のエラーテスト"""
    # モックの設定
    mock_repositories["meeting_repo"].get_by_id.return_value = sample_meeting
    mock_repositories["minutes_repo"].get_by_meeting.return_value = sample_minutes
    mock_repositories["conversation_repo"].get_by_minutes.return_value = [
        Conversation(
            id=1,
            minutes_id=1,
            speaker_name="既存の発言者",
            comment="既存の発言",
            sequence_number=1,
        )
    ]

    # 実行と検証
    request = ExecuteMinutesProcessingDTO(meeting_id=1, force_reprocess=False)
    with pytest.raises(ValueError, match="already has conversations"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_execute_force_reprocess(
    use_case, mock_repositories, sample_meeting, sample_minutes
):
    """強制再処理の場合、既存のConversationsがあっても処理されることをテスト"""
    # モックの設定
    mock_repositories["meeting_repo"].get_by_id.return_value = sample_meeting
    mock_repositories["minutes_repo"].get_by_meeting.return_value = sample_minutes
    mock_repositories["conversation_repo"].get_by_minutes.return_value = [
        Conversation(
            id=1,
            minutes_id=1,
            speaker_name="既存の発言者",
            comment="既存の発言",
            sequence_number=1,
        )
    ]

    # GCSStorageをモック
    with patch(
        "src.application.usecases.execute_minutes_processing_usecase.GCSStorage"
    ) as mock_gcs_patch:
        mock_gcs = mock_gcs_patch.return_value
        mock_gcs.download_content.return_value = "議事録テキスト"

        # MinutesProcessAgentをモック
        with patch(
            "src.application.usecases.execute_minutes_processing_usecase.MinutesProcessAgent"
        ) as mock_agent_patch:
            mock_agent = mock_agent_patch.return_value
            mock_agent.run.return_value = []

            # LLMServiceFactoryをモック
            with patch(
                "src.application.usecases.execute_minutes_processing_usecase.LLMServiceFactory"
            ) as mock_llm_factory:
                # LLMサービスのモックを設定
                mock_llm_service = MagicMock()
                mock_llm_factory.create_gemini_service.return_value = mock_llm_service

                # 環境変数をモック
                with patch.dict("os.environ", {"GOOGLE_API_KEY": "test-key"}):
                    mock_repositories["conversation_repo"].bulk_create.return_value = []

                    # 実行
                    request = ExecuteMinutesProcessingDTO(
                        meeting_id=1, force_reprocess=True
                    )
                    result = await use_case.execute(request)

                    # 検証
                    assert result.meeting_id == 1
                    assert result.total_conversations == 0


@pytest.mark.asyncio
async def test_execute_no_gcs_uri(use_case, mock_repositories):
    """GCS URIがない場合のエラーテスト"""
    # モックの設定
    meeting_without_gcs = Meeting(
        id=1,
        conference_id=1,
        date=datetime(2024, 1, 1),
        url="https://example.com",
        gcs_text_uri=None,
        gcs_pdf_uri=None,
    )
    mock_repositories["meeting_repo"].get_by_id.return_value = meeting_without_gcs
    mock_repositories["minutes_repo"].get_by_meeting.return_value = None

    # 実行と検証
    request = ExecuteMinutesProcessingDTO(meeting_id=1)
    with pytest.raises(ValueError, match="No valid source found"):
        await use_case.execute(request)


@pytest.mark.asyncio
async def test_execute_api_key_not_set(use_case, mock_repositories, sample_meeting):
    """APIキーが設定されていない場合のエラーテスト"""
    # モックの設定
    mock_repositories["meeting_repo"].get_by_id.return_value = sample_meeting
    mock_repositories["minutes_repo"].get_by_meeting.return_value = None
    mock_repositories["minutes_repo"].create.return_value = Minutes(
        id=1, meeting_id=1, url="https://example.com"
    )

    # GCSStorageをモック
    with patch(
        "src.application.usecases.execute_minutes_processing_usecase.GCSStorage"
    ) as mock_gcs_patch:
        mock_gcs = mock_gcs_patch.return_value
        mock_gcs.download_content.return_value = "議事録テキスト"

        # 環境変数をモック（APIキーなし）
        with patch.dict("os.environ", {}, clear=True):
            # 実行と検証
            request = ExecuteMinutesProcessingDTO(meeting_id=1)
            with pytest.raises(APIKeyError, match="GOOGLE_API_KEY not set"):
                await use_case.execute(request)


@pytest.mark.asyncio
async def test_extract_and_create_speakers(use_case, mock_repositories):
    """発言者の抽出と作成のテスト"""
    # テストデータ
    conversations = [
        Conversation(
            id=1,
            minutes_id=1,
            speaker_name="田中太郎（自民党）",
            comment="発言1",
            sequence_number=1,
        ),
        Conversation(
            id=2,
            minutes_id=1,
            speaker_name="山田花子",
            comment="発言2",
            sequence_number=2,
        ),
        Conversation(
            id=3,
            minutes_id=1,
            speaker_name="田中太郎（自民党）",  # 重複
            comment="発言3",
            sequence_number=3,
        ),
    ]

    # モックの設定
    mock_repositories["speaker_service"].extract_party_from_name.side_effect = [
        ("田中太郎", "自民党"),
        ("山田花子", None),
        ("田中太郎", "自民党"),  # 重複
    ]
    mock_repositories["speaker_repo"].get_by_name_party_position.return_value = None

    # 実行
    created_count = await use_case._extract_and_create_speakers(conversations)

    # 検証
    assert created_count == 2  # 重複を除いた数
    assert mock_repositories["speaker_repo"].create.call_count == 2
