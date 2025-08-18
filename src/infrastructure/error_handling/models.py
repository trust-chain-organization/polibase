"""エラーレスポンスモデル

APIやUIに返すエラーレスポンスのモデル定義
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ErrorDetail:
    """エラーの詳細情報"""

    field: str
    message: str
    code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        result = {"field": self.field, "message": self.message}
        if self.code:
            result["code"] = self.code
        return result


@dataclass
class ErrorResponse:
    """エラーレスポンス

    APIやUIに返すエラー情報の標準フォーマット
    """

    status_code: int
    message: str
    error_code: str | None = None
    details: dict[str, Any] | None = None
    errors: list[ErrorDetail] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（JSONシリアライズ用）"""
        result = {
            "status_code": self.status_code,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
        }

        if self.error_code:
            result["error_code"] = self.error_code

        if self.details:
            result["details"] = self.details

        if self.errors:
            result["errors"] = [error.to_dict() for error in self.errors]

        if self.request_id:
            result["request_id"] = self.request_id

        return result

    def add_error(self, field: str, message: str, code: str | None = None) -> None:
        """エラー詳細を追加"""
        self.errors.append(ErrorDetail(field=field, message=message, code=code))

    def has_errors(self) -> bool:
        """エラー詳細があるかチェック"""
        return len(self.errors) > 0

    def get_user_message(self) -> str:
        """ユーザー向けメッセージを取得"""
        # 技術的な詳細を除いたメッセージを返す
        if self.status_code >= 500:
            return (
                "システムエラーが発生しました。しばらく経ってから再度お試しください。"
            )
        return self.message

    def get_developer_message(self) -> str:
        """開発者向けメッセージを取得"""
        # 技術的な詳細を含むメッセージを返す
        messages = [
            f"[{self.error_code}] {self.message}" if self.error_code else self.message
        ]

        if self.errors:
            error_msgs = [f"  - {e.field}: {e.message}" for e in self.errors]
            messages.extend(error_msgs)

        return "\n".join(messages)


@dataclass
class RecoverableError:
    """回復可能なエラー情報

    ユーザーに対処方法を提示するための情報
    """

    error_response: ErrorResponse
    recovery_suggestions: list[str]
    can_retry: bool = False
    retry_after_seconds: int | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換"""
        result = {
            **self.error_response.to_dict(),
            "recovery": {
                "suggestions": self.recovery_suggestions,
                "can_retry": self.can_retry,
            },
        }

        if self.retry_after_seconds:
            result["recovery"]["retry_after_seconds"] = self.retry_after_seconds

        return result
