"""User entity for managing logged-in users."""

from datetime import datetime
from uuid import UUID


class User:
    """ユーザーを表すエンティティ.

    Googleアカウントでログインしたユーザー情報を管理します。
    """

    def __init__(
        self,
        email: str,
        name: str | None = None,
        picture: str | None = None,
        user_id: UUID | None = None,
        created_at: datetime | None = None,
        last_login_at: datetime | None = None,
    ) -> None:
        """Initialize User entity.

        Args:
            email: ユーザーのメールアドレス（必須、一意）
            name: ユーザーの表示名
            picture: プロフィール画像のURL
            user_id: ユーザーID（UUID）
            created_at: ユーザー作成日時
            last_login_at: 最終ログイン日時
        """
        self.user_id = user_id
        self.email = email
        self.name = name
        self.picture = picture
        self.created_at = created_at
        self.last_login_at = last_login_at

    def __eq__(self, other: object) -> bool:
        """Compare users by email."""
        if not isinstance(other, User):
            return False
        return self.email == other.email

    def __hash__(self) -> int:
        """Hash user by email."""
        return hash(self.email)

    def __str__(self) -> str:
        """String representation of user."""
        return f"User(email={self.email}, name={self.name})"

    def __repr__(self) -> str:
        """Representation of user."""
        return (
            f"User(user_id={self.user_id}, email={self.email}, "
            f"name={self.name}, picture={self.picture})"
        )
