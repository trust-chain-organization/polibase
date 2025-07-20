"""LLM処理履歴リポジトリ"""

from datetime import datetime
from typing import Any, cast

from sqlalchemy import text

from src.database.base_repository import BaseRepository
from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)


class LLMProcessingHistoryRepository(BaseRepository):
    """LLM処理履歴のリポジトリ"""

    def search(
        self,
        processing_type: ProcessingType | None = None,
        model_name: str | None = None,
        status: ProcessingStatus | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """検索条件に基づいて履歴を取得"""
        query = """
            SELECT id, processing_type, model_name, model_version,
                   prompt_template, prompt_variables, input_reference_type,
                   input_reference_id, status, result, error_message,
                   processing_metadata, started_at, completed_at,
                   created_at, updated_at
            FROM llm_processing_history
            WHERE 1=1
        """
        params: dict[str, Any] = {}

        # フィルター条件を適用
        if processing_type:
            query += " AND processing_type = :processing_type"
            params["processing_type"] = processing_type.value
        if model_name:
            query += " AND model_name = :model_name"
            params["model_name"] = model_name
        if status:
            query += " AND status = :status"
            params["status"] = status.value
        if start_date:
            query += " AND created_at >= :start_date"
            params["start_date"] = start_date
        if end_date:
            query += " AND created_at <= :end_date"
            params["end_date"] = end_date

        # ソートとページネーション
        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT :limit"
            params["limit"] = limit
        if offset:
            query += " OFFSET :offset"
            params["offset"] = offset

        # 結果をエンティティに変換
        result = self.session.execute(text(query), params)
        rows = result.fetchall()
        return [self._to_entity(row) for row in rows]

    def count_by_status(
        self,
        status: ProcessingStatus,
        processing_type: ProcessingType | None = None,
    ) -> int:
        """ステータス別の件数を取得"""
        query = "SELECT COUNT(*) FROM llm_processing_history WHERE status = :status"
        params: dict[str, Any] = {"status": status.value}

        if processing_type:
            query += " AND processing_type = :processing_type"
            params["processing_type"] = processing_type.value

        result = self.session.execute(text(query), params)
        return cast(int, result.scalar() or 0)

    def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int | None = None,
    ) -> list[LLMProcessingHistory]:
        """日付範囲で履歴を取得"""
        query = """
            SELECT id, processing_type, model_name, model_version,
                   prompt_template, prompt_variables, input_reference_type,
                   input_reference_id, status, result, error_message,
                   processing_metadata, started_at, completed_at,
                   created_at, updated_at
            FROM llm_processing_history
            WHERE created_at >= :start_date AND created_at <= :end_date
            ORDER BY created_at DESC
        """
        params: dict[str, Any] = {"start_date": start_date, "end_date": end_date}

        if limit:
            query += " LIMIT :limit"
            params["limit"] = limit

        result = self.session.execute(text(query), params)
        rows = result.fetchall()
        return [self._to_entity(row) for row in rows]

    def _to_entity(self, row: Any) -> LLMProcessingHistory:
        """データベースの行をエンティティに変換"""
        entity = LLMProcessingHistory(
            id=row.id,
            processing_type=ProcessingType(row.processing_type),
            model_name=row.model_name,
            model_version=row.model_version,
            prompt_template=row.prompt_template,
            prompt_variables=row.prompt_variables or {},
            input_reference_type=row.input_reference_type,
            input_reference_id=row.input_reference_id,
            status=ProcessingStatus(row.status),
            result=row.result,
            error_message=row.error_message,
            processing_metadata=row.processing_metadata or {},
            started_at=row.started_at,
            completed_at=row.completed_at,
        )
        # BaseEntity fields
        entity.created_at = row.created_at
        entity.updated_at = row.updated_at
        return entity
