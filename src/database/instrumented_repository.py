"""計測機能を持つリポジトリ基底クラス."""

from typing import Any

from src.common.instrumentation import MetricsContext, measure_time
from src.common.logging import get_logger
from src.common.metrics import CommonMetrics
from src.database.base_repository import BaseRepository

logger = get_logger(__name__)


class InstrumentedRepository(BaseRepository):
    """計測機能を追加したリポジトリ基底クラス."""

    def __init__(self, use_session: bool = True, table_name: str | None = None):
        """初期化."""
        super().__init__(use_session)
        self.table_name = table_name or "unknown"
        self._setup_metrics()

    def _setup_metrics(self):
        """メトリクスの初期化."""
        self.db_operations = CommonMetrics.db_operations_total()
        self.db_connections = CommonMetrics.db_connections_active()

        # 接続時にアクティブ接続数を増やす
        if self._session or self._engine:
            self.db_connections.add(1)

    def close(self):
        """データベース接続を閉じる."""
        try:
            # アクティブ接続数を減らす
            self.db_connections.add(-1)
        finally:
            super().close()

    @measure_time(metric_name="db_mutation", log_slow_operations=0.5)
    def insert(
        self, table: str, data: dict[str, Any], returning: str | None = None
    ) -> Any | None:
        """挿入（計測付き）."""
        with MetricsContext(
            operation="db_insert",
            labels={"table": table},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "insert",
                    "table": table,
                },
            )
            return super().insert(table, data, returning)

    @measure_time(metric_name="db_mutation", log_slow_operations=0.5)
    def update(self, table: str, data: dict[str, Any], where: dict[str, Any]) -> int:
        """更新（計測付き）."""
        with MetricsContext(
            operation="db_update",
            labels={"table": table},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "update",
                    "table": table,
                },
            )
            return super().update(table, data, where)

    @measure_time(metric_name="db_mutation", log_slow_operations=0.5)
    def delete(self, table: str, where: dict[str, Any]) -> int:
        """削除（計測付き）."""
        with MetricsContext(
            operation="db_delete",
            labels={"table": table},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "delete",
                    "table": table,
                },
            )
            return super().delete(table, where)

    @measure_time(metric_name="db_query", log_slow_operations=1.0)
    def execute_query(self, query: str, params: dict | None = None) -> list[Any]:
        """SQLクエリ実行（計測付き）."""
        with MetricsContext(
            operation="db_execute_query",
            labels={"query_type": "raw_sql"},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "raw_query",
                    "query_type": "select",
                },
            )
            return super().execute_query(query, params)

    @measure_time(metric_name="db_query", log_slow_operations=1.0)
    def fetch_one(self, query: str, params: dict[str, Any] | None = None) -> Any | None:
        """単一結果取得（計測付き）."""
        with MetricsContext(
            operation="db_fetch_one",
            labels={"query_type": "raw_sql"},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "raw_query",
                    "query_type": "select",
                },
            )
            return super().fetch_one(query, params)

    @measure_time(metric_name="db_query", log_slow_operations=1.0)
    def fetch_all(self, query: str, params: dict[str, Any] | None = None) -> list[Any]:
        """全結果取得（計測付き）."""
        with MetricsContext(
            operation="db_fetch_all",
            labels={"query_type": "raw_sql"},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "raw_query",
                    "query_type": "select",
                },
            )
            return super().fetch_all(query, params)
