"""認証用セッション管理モジュール。

このモジュールは、Streamlitアプリケーションでの認証状態を管理します。
既存のSessionManagerを拡張し、認証情報の保存・取得機能を提供します。
"""

from datetime import datetime
from typing import Any

from src.interfaces.web.streamlit.utils.session_manager import SessionManager


class AuthSessionManager(SessionManager):
    """認証情報を管理する特化したSessionManager。

    このクラスは、ユーザーの認証状態、トークン、ユーザー情報を管理します。
    """

    def __init__(self):
        """認証セッションマネージャーを初期化します。"""
        super().__init__(namespace="auth")

    def is_authenticated(self) -> bool:
        """ユーザーが認証されているか確認します。

        Returns:
            認証されている場合True
        """
        token = self.get_token()
        if not token:
            return False

        # トークンの有効期限をチェック
        if self._is_token_expired(token):
            self.clear_auth()
            return False

        return True

    def get_token(self) -> dict[str, Any] | None:
        """認証トークンを取得します。

        Returns:
            トークン辞書、存在しない場合はNone
        """
        return self.get("token")

    def set_token(self, token: dict[str, Any]) -> None:
        """認証トークンを保存します。

        Args:
            token: 保存するトークン辞書
        """
        self.set("token", token)

    def get_user_info(self) -> dict[str, Any] | None:
        """ユーザー情報を取得します。

        Returns:
            ユーザー情報辞書、存在しない場合はNone
        """
        return self.get("user_info")

    def set_user_info(self, user_info: dict[str, Any]) -> None:
        """ユーザー情報を保存します。

        Args:
            user_info: 保存するユーザー情報辞書
        """
        self.set("user_info", user_info)
        self.set("authenticated_at", datetime.now().isoformat())

    def get_user_email(self) -> str | None:
        """ユーザーのメールアドレスを取得します。

        Returns:
            メールアドレス、存在しない場合はNone
        """
        user_info = self.get_user_info()
        return user_info.get("email") if user_info else None

    def get_user_name(self) -> str | None:
        """ユーザーの名前を取得します。

        Returns:
            ユーザー名、存在しない場合はNone
        """
        user_info = self.get_user_info()
        if not user_info:
            return None
        return user_info.get("name") or user_info.get("email")

    def clear_auth(self) -> None:
        """認証情報をクリアします。"""
        self.delete("token")
        self.delete("user_info")
        self.delete("authenticated_at")

    def _is_token_expired(self, token: dict[str, Any]) -> bool:
        """トークンが期限切れかチェックします。

        Args:
            token: チェックするトークン辞書

        Returns:
            期限切れの場合True
        """
        # expires_inまたはexpiresフィールドをチェック
        expires_in = token.get("expires_in")
        expires_at = token.get("expires_at")

        if expires_at:
            # expires_atがある場合、現在時刻と比較
            try:
                expires_datetime = datetime.fromisoformat(expires_at)
                return datetime.now() >= expires_datetime
            except (ValueError, TypeError):
                # パースエラーの場合は期限切れとみなす
                return True

        if expires_in:
            # expires_inがある場合、認証時刻からの経過時間をチェック
            authenticated_at_str = self.get("authenticated_at")
            if authenticated_at_str:
                try:
                    authenticated_at = datetime.fromisoformat(authenticated_at_str)
                    from datetime import timedelta

                    expiry_time = authenticated_at + timedelta(seconds=int(expires_in))
                    return datetime.now() >= expiry_time
                except (ValueError, TypeError):
                    return True

        # 期限情報がない場合は、有効とみなす（リスクを考慮）
        return False

    def get_authenticated_at(self) -> datetime | None:
        """認証時刻を取得します。

        Returns:
            認証時刻、存在しない場合はNone
        """
        authenticated_at_str = self.get("authenticated_at")
        if not authenticated_at_str:
            return None
        try:
            return datetime.fromisoformat(authenticated_at_str)
        except (ValueError, TypeError):
            return None
