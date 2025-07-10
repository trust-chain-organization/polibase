"""計測機能を持つリポジトリ基底クラス."""

from typing import Any

from src.common.instrumentation import MetricsContext, measure_time
from src.common.logging import get_logger
from src.common.metrics import CommonMetrics
from src.database.base_repository import BaseRepository, T

logger = get_logger(__name__)


class InstrumentedRepository(BaseRepository):
    """計測機能を追加したリポジトリ基底クラス."""

    def __init__(self, use_session: bool = True):
        """初期化."""
        super().__init__(use_session)
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

    @measure_time(metric_name="db_query", log_slow_operations=0.5)
    def find_all(self, model_class: type[T], **filters) -> list[T]:
        """全件検索（計測付き）."""
        with MetricsContext(
            operation="db_find_all",
            labels={"table": model_class.__tablename__},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "select",
                    "table": model_class.__tablename__,
                },
            )
            return super().find_all(model_class, **filters)

    @measure_time(metric_name="db_query", log_slow_operations=0.5)
    def find_by_id(self, model_class: type[T], id: Any) -> T | None:
        """ID検索（計測付き）."""
        with MetricsContext(
            operation="db_find_by_id",
            labels={"table": model_class.__tablename__},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "select",
                    "table": model_class.__tablename__,
                },
            )
            return super().find_by_id(model_class, id)

    @measure_time(metric_name="db_mutation", log_slow_operations=0.5)
    def create(self, instance: T, flush: bool = False) -> T:
        """作成（計測付き）."""
        with MetricsContext(
            operation="db_create",
            labels={"table": instance.__tablename__},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "insert",
                    "table": instance.__tablename__,
                },
            )
            return super().create(instance, flush)

    @measure_time(metric_name="db_mutation", log_slow_operations=0.5)
    def bulk_create(self, instances: list[T]) -> list[T]:
        """一括作成（計測付き）."""
        if not instances:
            return []

        table_name = instances[0].__tablename__
        with MetricsContext(
            operation="db_bulk_create",
            labels={"table": table_name, "count": str(len(instances))},
        ):
            self.db_operations.add(
                len(instances),
                attributes={
                    "operation": "bulk_insert",
                    "table": table_name,
                },
            )
            return super().bulk_create(instances)

    @measure_time(metric_name="db_mutation", log_slow_operations=0.5)
    def update(self, instance: T, flush: bool = False) -> T:
        """更新（計測付き）."""
        with MetricsContext(
            operation="db_update",
            labels={"table": instance.__tablename__},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "update",
                    "table": instance.__tablename__,
                },
            )
            return super().update(instance, flush)

    @measure_time(metric_name="db_mutation", log_slow_operations=0.5)
    def delete(self, instance: T) -> bool:
        """削除（計測付き）."""
        with MetricsContext(
            operation="db_delete",
            labels={"table": instance.__tablename__},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "delete",
                    "table": instance.__tablename__,
                },
            )
            return super().delete(instance)

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

    @measure_time(metric_name="db_mutation", log_slow_operations=1.0)
    def execute_update(self, query: str, params: dict | None = None) -> int:
        """更新クエリ実行（計測付き）."""
        with MetricsContext(
            operation="db_execute_update",
            labels={"query_type": "raw_sql"},
        ):
            self.db_operations.add(
                1,
                attributes={
                    "operation": "raw_query",
                    "query_type": "update",
                },
            )
            return super().execute_update(query, params)
