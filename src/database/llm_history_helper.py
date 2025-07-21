"""Helper for synchronous LLM history recording."""

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.config.settings import settings

logger = logging.getLogger(__name__)


class SyncLLMHistoryHelper:
    """Synchronous helper for recording LLM processing history."""

    def __init__(self):
        """Initialize helper with sync database engine."""
        # Create sync engine for history recording
        database_url = settings.get_database_url()
        self.engine = create_engine(database_url, echo=False)
        self.session_maker = sessionmaker(self.engine, expire_on_commit=False)

    def record_speaker_matching(
        self,
        speaker_name: str,
        matched: bool,
        speaker_id: int | None,
        confidence: float,
        reason: str,
        model_name: str = "gemini-1.5-flash",
        prompt_template: str = "speaker_matching",
    ) -> None:
        """
        Record speaker matching operation synchronously.

        Args:
            speaker_name: Name of the speaker being matched
            matched: Whether a match was found
            speaker_id: ID of matched speaker (if found)
            confidence: Confidence score of the match
            reason: Reason for the match/no match
            model_name: Name of the LLM model used
            prompt_template: Template used for the prompt
        """
        session = self.session_maker()
        try:
            # Create history entry directly in the database
            history_data: dict[str, object] = {
                "processing_type": "speaker_matching",
                "model_name": model_name,
                "model_version": "1.5",  # Could be extracted from model_name
                "prompt_template": prompt_template,
                "prompt_variables": json.dumps(
                    {
                        "speaker_name": speaker_name,
                    }
                ),
                "input_reference_type": "speaker_name",
                "input_reference_id": hash(speaker_name) % 1000000,
                "status": "completed",
                "processing_metadata": json.dumps(
                    {
                        "matched": matched,
                        "speaker_id": speaker_id,
                        "confidence": confidence,
                        "reason": reason,
                    }
                ),
                "started_at": datetime.now(UTC),
                "completed_at": datetime.now(UTC),
                "token_usage": json.dumps(
                    {
                        "prompt_tokens": 0,
                        "completion_tokens": 0,
                        "total_tokens": 0,
                    }
                ),
            }

            # Save to database using direct SQL
            insert_query = text("""
                INSERT INTO llm_processing_history (
                    processing_type, model_name, model_version,
                    prompt_template, prompt_variables,
                    input_reference_type, input_reference_id,
                    status, processing_metadata,
                    started_at, completed_at, token_usage
                ) VALUES (
                    :processing_type, :model_name, :model_version,
                    :prompt_template, :prompt_variables,
                    :input_reference_type, :input_reference_id,
                    :status, :processing_metadata,
                    :started_at, :completed_at, :token_usage
                )
            """)

            session.execute(insert_query, history_data)
            session.commit()

            match_status = "matched" if matched else "not matched"
            logger.debug(
                f"Recorded speaker matching history: {speaker_name} -> "
                f"{match_status} (confidence: {confidence})"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record speaker matching history: {e}")
            # Don't raise - history recording should not break main flow
        finally:
            session.close()

    def close(self) -> None:
        """Close the sync engine."""
        self.engine.dispose()

    def __enter__(self) -> "SyncLLMHistoryHelper":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Context manager exit."""
        self.close()
