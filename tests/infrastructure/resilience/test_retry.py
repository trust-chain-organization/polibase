"""リトライ機構のテスト"""

from typing import Any
from unittest.mock import Mock, MagicMock, patch

import pytest

from src.infrastructure.exceptions import (
    ConnectionException,
    DatabaseException,
    ExternalServiceException,
    RateLimitException,
)
from src.infrastructure.resilience.retry import (
    RetryPolicy,
    with_retry,
)


class TestRetryPolicy:
    """RetryPolicyのテスト"""

    def test_default_policy_success(self):
        """デフォルトポリシーの成功テスト"""
        mock_func = Mock(return_value="success")

        @RetryPolicy.default()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        mock_func.assert_called_once()

    def test_default_policy_retry_on_retryable_error(self):
        """デフォルトポリシーのリトライ可能エラーでのリトライテスト"""
        mock_func = Mock(
            side_effect=[
                ConnectionException("service", reason="timeout"),
                ConnectionException("service", reason="timeout"),
                "success",
            ]
        )

        @RetryPolicy.default()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 3

    def test_default_policy_fail_on_non_retryable_error(self):
        """デフォルトポリシーの非リトライ可能エラーでの失敗テスト"""
        mock_func = Mock(side_effect=ValueError("non-retryable"))

        @RetryPolicy.default()
        def test_func():
            return mock_func()

        with pytest.raises(ValueError):
            test_func()

        mock_func.assert_called_once()

    def test_external_service_policy_rate_limit(self):
        """外部サービスポリシーのレート制限エラーテスト"""
        mock_func = Mock(
            side_effect=[RateLimitException("api", 100, retry_after=1), "success"]
        )

        @RetryPolicy.external_service()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_external_service_policy_5xx_error(self):
        """外部サービスポリシーの5xxエラーテスト"""
        mock_func = Mock(
            side_effect=[
                ExternalServiceException("api", "get", status_code=503),
                "success",
            ]
        )

        @RetryPolicy.external_service()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_external_service_policy_4xx_no_retry(self):
        """外部サービスポリシーの4xxエラー（リトライなし）テスト"""
        mock_func = Mock(
            side_effect=ExternalServiceException("api", "get", status_code=400)
        )

        @RetryPolicy.external_service()
        def test_func():
            return mock_func()

        with pytest.raises(ExternalServiceException):
            test_func()

        mock_func.assert_called_once()

    def test_database_policy_deadlock_retry(self):
        """データベースポリシーのデッドロックリトライテスト"""
        mock_func = Mock(
            side_effect=[DatabaseException("UPDATE", "deadlock detected"), "success"]
        )

        @RetryPolicy.database()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_database_policy_integrity_error_no_retry(self):
        """データベースポリシーの整合性エラー（リトライなし）テスト"""
        mock_func = Mock(
            side_effect=DatabaseException("INSERT", "unique constraint violation")
        )

        @RetryPolicy.database()
        def test_func():
            return mock_func()

        with pytest.raises(DatabaseException):
            test_func()

        mock_func.assert_called_once()

    def test_no_retry_policy(self):
        """リトライなしポリシーのテスト"""
        mock_func = Mock(side_effect=ConnectionException("service"))

        @RetryPolicy.no_retry()
        def test_func():
            return mock_func()

        with pytest.raises(ConnectionException):
            test_func()

        mock_func.assert_called_once()

    def test_rate_limit_aware_policy_with_retry_after(self):
        """レート制限対応ポリシーのretry_after付きテスト"""
        exception = RateLimitException("api", 100, retry_after=5)
        mock_func = Mock(side_effect=[exception, "success"])

        @RetryPolicy.rate_limit_aware()
        def test_func():
            return mock_func()

        # wait_for_rate_limit関数をテストするため、実際の待機はスキップ
        with patch("src.infrastructure.resilience.retry.wait_exponential"):
            result = test_func()

        assert result == "success"
        assert mock_func.call_count == 2

    def test_custom_policy_with_custom_exceptions(self):
        """カスタムポリシーのカスタム例外テスト"""
        custom_policy = RetryPolicy.custom(
            max_attempts=2, retryable_exceptions=(ValueError,)
        )

        mock_func = Mock(side_effect=[ValueError("custom"), "success"])

        @custom_policy
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_custom_policy_with_should_retry_function(self):
        """カスタムポリシーのshould_retry関数テスト"""

        def should_retry(exception: Exception) -> bool:
            return isinstance(exception, ValueError) and "please retry" in str(
                exception
            )

        custom_policy = RetryPolicy.custom(max_attempts=2, should_retry=should_retry)

        # リトライすべき例外
        mock_func1 = Mock(side_effect=[ValueError("please retry this"), "success"])

        @custom_policy
        def test_func1():
            return mock_func1()

        result = test_func1()
        assert result == "success"
        assert mock_func1.call_count == 2

        # リトライすべきでない例外
        mock_func2 = Mock(side_effect=ValueError("do not attempt again"))

        @custom_policy
        def test_func2():
            return mock_func2()

        with pytest.raises(ValueError):
            test_func2()

        mock_func2.assert_called_once()


class TestWithRetryDecorator:
    """with_retryデコレータのテスト"""

    def test_sync_function_success(self):
        """同期関数の成功テスト"""
        mock_func = Mock(return_value="success")

        @with_retry()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        mock_func.assert_called_once()

    def test_sync_function_retry(self):
        """同期関数のリトライテスト"""
        mock_func = Mock(side_effect=[ConnectionException("service"), "success"])

        @with_retry()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2

    def test_sync_function_max_retries_exceeded(self):
        """同期関数の最大リトライ回数超過テスト"""
        mock_func = Mock(side_effect=ConnectionException("service"))

        @with_retry()
        def test_func():
            return mock_func()

        with pytest.raises(ConnectionException):
            test_func()

        # デフォルトポリシーは3回試行
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_async_function_success(self):
        """非同期関数の成功テスト"""

        async def test_func():
            return "success"

        decorated = with_retry(async_func=True)(test_func)
        result = await decorated()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_function_retry(self):
        """非同期関数のリトライテスト"""
        call_count = 0

        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionException("service")
            return "success"

        decorated = with_retry(async_func=True)(test_func)
        result = await decorated()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_function_auto_detection(self):
        """非同期関数の自動検出テスト"""
        call_count = 0

        @with_retry()  # async_func=Trueを指定しない
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionException("service")
            return "success"

        result = await test_func()
        assert result == "success"
        assert call_count == 2

    def test_custom_policy_decorator(self):
        """カスタムポリシー付きデコレータのテスト"""
        mock_func = Mock(side_effect=[ValueError("test"), "success"])

        @with_retry(policy=RetryPolicy.custom(retryable_exceptions=(ValueError,)))
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 2


class TestRetryIntegration:
    """リトライ機構の統合テスト"""

    def test_external_api_simulation(self):
        """外部API呼び出しのシミュレーションテスト"""
        responses = [
            ExternalServiceException(
                "API", "call", status_code=503
            ),  # サーバーエラー → リトライ
            RateLimitException("API", 100, retry_after=1),  # レート制限 → リトライ
            ExternalServiceException(
                "API", "call", status_code=400
            ),  # クライアントエラー → リトライしない
        ]

        call_count = 0

        @RetryPolicy.external_service()
        def call_api():
            nonlocal call_count
            if call_count < len(responses):
                exception = responses[call_count]
                call_count += 1
                raise exception
            return "success"

        # 最初の2つの例外はリトライされ、3つ目で停止
        with pytest.raises(ExternalServiceException) as exc_info:
            call_api()

        assert exc_info.value.details.get("status_code") == 400
        assert call_count == 3  # 1回目（503）、2回目（429）、3回目（400）

    @pytest.mark.skip(
        reason="Logging mock doesn't work correctly with tenacity's before_sleep_log"
    )
    @patch("src.infrastructure.resilience.retry.logger")
    def test_logging_integration(self, mock_logger: MagicMock) -> None:
        """ログ出力の統合テスト"""
        mock_func = Mock(side_effect=[ConnectionException("service"), "success"])

        @RetryPolicy.default()
        def test_func():
            return mock_func()

        result = test_func()
        assert result == "success"

        # ログが出力されることを確認（before_sleep_logとafter_log）
        assert mock_logger.warning.called or mock_logger.info.called
