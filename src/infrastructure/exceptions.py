"""インフラストラクチャ層の例外クラス定義

外部システムとの連携、データベース、ファイルシステムなど
インフラストラクチャ層で発生する例外を定義
"""

from src.domain.exceptions import PolibaseException


class InfrastructureException(PolibaseException):
    """インフラストラクチャ層の基底例外クラス

    外部システムや技術的な実装に関連する例外の基底クラス
    """

    pass


class DatabaseException(InfrastructureException):
    """データベース関連エラー

    データベースへのアクセスや操作で発生するエラー
    """

    def __init__(
        self,
        operation: str,
        reason: str,
        table: str | None = None,
        query: str | None = None,
        original_error: Exception | None = None,
    ):
        """
        Args:
            operation: 実行した操作（SELECT, INSERT, UPDATE, DELETE等）
            reason: エラーの理由
            table: 対象テーブル名
            query: 実行したクエリ（デバッグ用）
            original_error: 元の例外
        """
        message = f"データベースエラー ({operation}): {reason}"
        if table:
            message += f" - テーブル: {table}"

        super().__init__(
            message=message,
            error_code="INF-001",
            details={
                "operation": operation,
                "reason": reason,
                "table": table,
                "query": query[:200] if query else None,
                "original_error": str(original_error) if original_error else None,
            },
        )


class ConnectionException(InfrastructureException):
    """接続エラー

    外部システムへの接続に失敗した場合のエラー
    """

    def __init__(
        self,
        service: str,
        endpoint: str | None = None,
        reason: str | None = None,
        retry_after: int | None = None,
    ):
        """
        Args:
            service: サービス名（PostgreSQL, Redis, GCS等）
            endpoint: 接続先エンドポイント
            reason: 接続失敗の理由
            retry_after: リトライまでの待機時間（秒）
        """
        message = f"サービス '{service}' への接続に失敗しました"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            error_code="INF-002",
            details={
                "service": service,
                "endpoint": endpoint,
                "reason": reason,
                "retry_after": retry_after,
            },
        )


class ExternalServiceException(InfrastructureException):
    """外部サービスエラー

    外部API呼び出しやサービス連携で発生するエラー
    """

    def __init__(
        self,
        service: str,
        operation: str,
        status_code: int | None = None,
        response_body: str | None = None,
        reason: str | None = None,
    ):
        """
        Args:
            service: サービス名（Gemini API, GCS等）
            operation: 実行した操作
            status_code: HTTPステータスコード
            response_body: レスポンスボディ
            reason: エラーの理由
        """
        message = f"外部サービス '{service}' でエラー ({operation})"
        if status_code:
            message += f" - ステータス: {status_code}"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            error_code="INF-003",
            details={
                "service": service,
                "operation": operation,
                "status_code": status_code,
                "response_body": response_body[:500] if response_body else None,
                "reason": reason,
            },
        )


class FileSystemException(InfrastructureException):
    """ファイルシステムエラー

    ファイルの読み書きや操作で発生するエラー
    """

    def __init__(
        self,
        operation: str,
        file_path: str,
        reason: str,
        original_error: Exception | None = None,
    ):
        """
        Args:
            operation: 実行した操作（read, write, delete等）
            file_path: 対象ファイルパス
            reason: エラーの理由
            original_error: 元の例外
        """
        message = f"ファイル操作エラー ({operation}): {file_path} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-004",
            details={
                "operation": operation,
                "file_path": file_path,
                "reason": reason,
                "original_error": str(original_error) if original_error else None,
            },
        )


class StorageException(InfrastructureException):
    """ストレージエラー

    クラウドストレージやオブジェクトストレージ関連のエラー
    """

    def __init__(
        self,
        storage_type: str,
        operation: str,
        resource: str,
        reason: str,
        bucket: str | None = None,
    ):
        """
        Args:
            storage_type: ストレージタイプ（GCS, S3等）
            operation: 実行した操作（upload, download, delete等）
            resource: 対象リソース（ファイル名等）
            reason: エラーの理由
            bucket: バケット名
        """
        message = f"{storage_type}ストレージエラー ({operation}): {resource} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-005",
            details={
                "storage_type": storage_type,
                "operation": operation,
                "resource": resource,
                "bucket": bucket,
                "reason": reason,
            },
        )


class CacheException(InfrastructureException):
    """キャッシュエラー

    キャッシュシステムに関連するエラー
    """

    def __init__(
        self,
        operation: str,
        cache_key: str,
        reason: str,
        cache_type: str | None = None,
    ):
        """
        Args:
            operation: 実行した操作（get, set, delete等）
            cache_key: キャッシュキー
            reason: エラーの理由
            cache_type: キャッシュタイプ（Redis, Memcached等）
        """
        message = f"キャッシュエラー ({operation}): {cache_key} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-006",
            details={
                "operation": operation,
                "cache_key": cache_key,
                "reason": reason,
                "cache_type": cache_type,
            },
        )


class NetworkException(InfrastructureException):
    """ネットワークエラー

    ネットワーク通信に関連するエラー
    """

    def __init__(
        self,
        operation: str,
        url: str,
        reason: str,
        timeout: int | None = None,
        retry_count: int | None = None,
    ):
        """
        Args:
            operation: 実行した操作（GET, POST等）
            url: URL
            reason: エラーの理由
            timeout: タイムアウト時間（秒）
            retry_count: リトライ回数
        """
        message = f"ネットワークエラー ({operation}): {url} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-007",
            details={
                "operation": operation,
                "url": url,
                "reason": reason,
                "timeout": timeout,
                "retry_count": retry_count,
            },
        )


class SerializationException(InfrastructureException):
    """シリアライゼーションエラー

    データのシリアライズ/デシリアライズで発生するエラー
    """

    def __init__(
        self,
        operation: str,
        data_format: str,
        reason: str,
        data_sample: str | None = None,
    ):
        """
        Args:
            operation: 実行した操作（serialize, deserialize）
            data_format: データフォーマット（JSON, XML, YAML等）
            reason: エラーの理由
            data_sample: データサンプル（デバッグ用）
        """
        message = f"シリアライゼーションエラー ({operation}): {data_format} - {reason}"
        super().__init__(
            message=message,
            error_code="INF-008",
            details={
                "operation": operation,
                "data_format": data_format,
                "reason": reason,
                "data_sample": data_sample[:200] if data_sample else None,
            },
        )


class TimeoutException(InfrastructureException):
    """タイムアウトエラー

    処理がタイムアウトした場合のエラー
    """

    def __init__(
        self, operation: str, timeout_seconds: int, resource: str | None = None
    ):
        """
        Args:
            operation: タイムアウトした操作
            timeout_seconds: タイムアウト時間（秒）
            resource: 対象リソース
        """
        message = f"操作 '{operation}' がタイムアウトしました ({timeout_seconds}秒)"
        if resource:
            message += f" - リソース: {resource}"

        super().__init__(
            message=message,
            error_code="INF-009",
            details={
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                "resource": resource,
            },
        )


class RateLimitException(InfrastructureException):
    """レート制限エラー

    APIのレート制限に達した場合のエラー
    """

    def __init__(
        self,
        service: str,
        limit: int,
        reset_at: str | None = None,
        retry_after: int | None = None,
    ):
        """
        Args:
            service: サービス名
            limit: レート制限値
            reset_at: 制限がリセットされる時刻
            retry_after: リトライまでの待機時間（秒）
        """
        message = f"サービス '{service}' のレート制限に達しました (制限: {limit})"
        super().__init__(
            message=message,
            error_code="INF-010",
            details={
                "service": service,
                "limit": limit,
                "reset_at": reset_at,
                "retry_after": retry_after,
            },
        )
