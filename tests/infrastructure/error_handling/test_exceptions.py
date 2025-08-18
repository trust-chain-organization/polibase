"""例外クラスのテスト"""

from src.application.exceptions import (
    AuthorizationException,
    ConcurrencyException,
    ConfigurationException,
    DataProcessingException,
    ResourceNotFoundException,
    ValidationException,
    WorkflowException,
)
from src.domain.exceptions import (
    BusinessRuleViolationException,
    DataIntegrityException,
    DuplicateEntityException,
    EntityNotFoundException,
    InvalidDomainOperationException,
    InvalidEntityStateException,
    PolibaseException,
)
from src.infrastructure.exceptions import (
    ConnectionException,
    DatabaseException,
    ExternalServiceException,
    FileSystemException,
    NetworkException,
    RateLimitException,
    StorageException,
    TimeoutException,
)


class TestPolibaseException:
    """PolibaseException（基底例外）のテスト"""

    def test_init_with_message_only(self):
        """メッセージのみでの初期化テスト"""
        exception = PolibaseException("エラーが発生しました")
        assert str(exception) == "エラーが発生しました"
        assert exception.message == "エラーが発生しました"
        assert exception.error_code is None
        assert exception.details == {}

    def test_init_with_error_code(self):
        """エラーコード付きの初期化テスト"""
        exception = PolibaseException("エラーが発生しました", "TEST-001")
        assert str(exception) == "[TEST-001] エラーが発生しました"
        assert exception.error_code == "TEST-001"

    def test_init_with_details(self):
        """詳細情報付きの初期化テスト"""
        details = {"user_id": 123, "operation": "test"}
        exception = PolibaseException("エラーが発生しました", "TEST-001", details)
        assert exception.details == details


class TestDomainExceptions:
    """ドメイン例外のテスト"""

    def test_entity_not_found_with_id(self):
        """ID付きエンティティ未検出例外のテスト"""
        exception = EntityNotFoundException("Politician", entity_id=123)
        assert "Politicianが見つかりません (ID: 123)" in str(exception)
        assert exception.error_code == "DOM-001"
        assert exception.details["entity_type"] == "Politician"
        assert exception.details["entity_id"] == 123

    def test_entity_not_found_with_criteria(self):
        """検索条件付きエンティティ未検出例外のテスト"""
        criteria = {"name": "田中太郎", "party": "自民党"}
        exception = EntityNotFoundException("Politician", search_criteria=criteria)
        assert "Politicianが見つかりません" in str(exception)
        assert exception.details["search_criteria"] == criteria

    def test_business_rule_violation(self):
        """ビジネスルール違反例外のテスト"""
        exception = BusinessRuleViolationException(
            "meeting_date_validation", "会議日が未来の日付です"
        )
        assert "ビジネスルール違反: 会議日が未来の日付です" in str(exception)
        assert exception.error_code == "DOM-002"
        assert exception.details["rule"] == "meeting_date_validation"

    def test_invalid_entity_state(self):
        """エンティティ状態不正例外のテスト"""
        exception = InvalidEntityStateException(
            "Meeting", "archived", "active", entity_id=456
        )
        assert "Meetingの状態が不正です (現在: archived, 期待: active)" in str(
            exception
        )
        assert exception.error_code == "DOM-003"
        assert exception.details["current_state"] == "archived"
        assert exception.details["expected_state"] == "active"

    def test_duplicate_entity(self):
        """重複エンティティ例外のテスト"""
        criteria = {"name": "田中太郎", "party": "自民党"}
        exception = DuplicateEntityException("Politician", criteria, existing_id=789)
        assert "Politicianが既に存在します" in str(exception)
        assert exception.error_code == "DOM-004"
        assert exception.details["duplicate_criteria"] == criteria
        assert exception.details["existing_id"] == 789

    def test_invalid_domain_operation(self):
        """ドメイン操作無効例外のテスト"""
        exception = InvalidDomainOperationException(
            "delete_speaker", "関連する発言が存在します"
        )
        assert (
            "操作 'delete_speaker' を実行できません: 関連する発言が存在します"
            in str(exception)
        )
        assert exception.error_code == "DOM-005"

    def test_data_integrity(self):
        """データ整合性例外のテスト"""
        exception = DataIntegrityException(
            "foreign_key_constraint", "参照されているレコードを削除できません"
        )
        assert "データ整合性エラー: 参照されているレコードを削除できません" in str(
            exception
        )
        assert exception.error_code == "DOM-006"


class TestApplicationExceptions:
    """アプリケーション例外のテスト"""

    def test_validation_exception(self):
        """バリデーション例外のテスト"""
        exception = ValidationException(
            "email", "invalid-email", "有効なメールアドレスではありません"
        )
        assert exception.error_code == "APP-002"
        assert exception.details["field"] == "email"
        assert exception.details["value"] == "invalid-email"

    def test_authorization_exception(self):
        """認可例外のテスト"""
        exception = AuthorizationException("meeting/123", "delete", "admin")
        assert "リソース 'meeting/123' に対する操作 'delete' の権限がありません" in str(
            exception
        )
        assert exception.error_code == "APP-003"

    def test_resource_not_found_exception(self):
        """リソース未検出例外のテスト"""
        exception = ResourceNotFoundException("User", 123, "authentication_context")
        assert "リソース 'User' (ID: 123) が見つかりません" in str(exception)
        assert "コンテキスト: authentication_context" in str(exception)
        assert exception.error_code == "APP-004"

    def test_workflow_exception(self):
        """ワークフロー例外のテスト"""
        exception = WorkflowException(
            "minutes_processing",
            "text_extraction",
            "PDFが破損しています",
            can_retry=True,
        )
        assert (
            "ワークフロー 'minutes_processing' のステップ 'text_extraction' で失敗"
            in str(exception)
        )
        assert exception.error_code == "APP-005"
        assert exception.details["can_retry"] is True

    def test_concurrency_exception(self):
        """並行実行例外のテスト"""
        exception = ConcurrencyException(
            "meeting/123", "update", "同時に更新されました"
        )
        assert "リソース 'meeting/123' への並行アクセスで競合が発生" in str(exception)
        assert exception.error_code == "APP-006"

    def test_configuration_exception(self):
        """設定例外のテスト"""
        exception = ConfigurationException(
            "GOOGLE_API_KEY",
            "環境変数が設定されていません",
            expected_value="string",
            actual_value=None,
        )
        assert "設定 'GOOGLE_API_KEY' のエラー: 環境変数が設定されていません" in str(
            exception
        )
        assert exception.error_code == "APP-007"

    def test_data_processing_exception(self):
        """データ処理例外のテスト"""
        exception = DataProcessingException(
            "pdf_extraction",
            "PDF",
            "テキストの抽出に失敗しました",
            input_data="sample_data",
        )
        assert (
            "データ処理 'pdf_extraction' でエラー (PDF): テキストの抽出に失敗しました"
            in str(exception)
        )
        assert exception.error_code == "APP-008"


class TestInfrastructureExceptions:
    """インフラストラクチャ例外のテスト"""

    def test_database_exception(self):
        """データベース例外のテスト"""
        exception = DatabaseException(
            "SELECT",
            "接続タイムアウト",
            table="politicians",
            query="SELECT * FROM politicians WHERE id = 123",
        )
        assert (
            "データベースエラー (SELECT): 接続タイムアウト - テーブル: politicians"
            in str(exception)
        )
        assert exception.error_code == "INF-001"
        assert exception.details["operation"] == "SELECT"
        assert exception.details["table"] == "politicians"

    def test_connection_exception(self):
        """接続例外のテスト"""
        exception = ConnectionException(
            "PostgreSQL", "localhost:5432", "接続が拒否されました", retry_after=30
        )
        assert (
            "サービス 'PostgreSQL' への接続に失敗しました: 接続が拒否されました"
            in str(exception)
        )
        assert exception.error_code == "INF-002"
        assert exception.details["retry_after"] == 30

    def test_external_service_exception(self):
        """外部サービス例外のテスト"""
        exception = ExternalServiceException(
            "Gemini API",
            "generate_content",
            status_code=429,
            reason="レート制限に達しました",
        )
        assert (
            "外部サービス 'Gemini API' でエラー (generate_content) - ステータス: 429"
            in str(exception)
        )
        assert exception.error_code == "INF-003"
        assert exception.details["status_code"] == 429

    def test_file_system_exception(self):
        """ファイルシステム例外のテスト"""
        exception = FileSystemException(
            "read", "/path/to/file.pdf", "ファイルが見つかりません"
        )
        assert (
            "ファイル操作エラー (read): /path/to/file.pdf - ファイルが見つかりません"
            in str(exception)
        )
        assert exception.error_code == "INF-004"

    def test_storage_exception(self):
        """ストレージ例外のテスト"""
        exception = StorageException(
            "GCS",
            "upload",
            "document.pdf",
            "バケットが見つかりません",
            bucket="polibase-bucket",
        )
        assert (
            "GCSストレージエラー (upload): document.pdf - バケットが見つかりません"
            in str(exception)
        )
        assert exception.error_code == "INF-005"
        assert exception.details["bucket"] == "polibase-bucket"

    def test_network_exception(self):
        """ネットワーク例外のテスト"""
        exception = NetworkException(
            "GET",
            "https://api.example.com/data",
            "タイムアウト",
            timeout=30,
            retry_count=3,
        )
        assert (
            "ネットワークエラー (GET): https://api.example.com/data - タイムアウト"
            in str(exception)
        )
        assert exception.error_code == "INF-007"
        assert exception.details["timeout"] == 30
        assert exception.details["retry_count"] == 3

    def test_timeout_exception(self):
        """タイムアウト例外のテスト"""
        exception = TimeoutException("database_query", 30, resource="users_table")
        expected_message = (
            "操作 'database_query' がタイムアウトしました (30秒) - "
            "リソース: users_table"
        )
        assert expected_message in str(exception)
        assert exception.error_code == "INF-009"

    def test_rate_limit_exception(self):
        """レート制限例外のテスト"""
        exception = RateLimitException(
            "Gemini API", 1000, reset_at="2024-01-01T12:00:00Z", retry_after=60
        )
        assert "サービス 'Gemini API' のレート制限に達しました (制限: 1000)" in str(
            exception
        )
        assert exception.error_code == "INF-010"
        assert exception.details["retry_after"] == 60
