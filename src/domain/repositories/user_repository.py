"""User repository interface."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from src.domain.entities.user import User


class IUserRepository(ABC):
    """Repository interface for users.

    UUIDベースのユーザー管理を提供します。
    """

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by ID.

        Args:
            user_id: ユーザーID（UUID）

        Returns:
            ユーザーエンティティ、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Get user by email address.

        Args:
            email: メールアドレス

        Returns:
            ユーザーエンティティ、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def get_all(
        self, limit: int | None = None, offset: int | None = None
    ) -> list[User]:
        """Get all users with optional pagination.

        Args:
            limit: 取得する最大件数
            offset: スキップする件数

        Returns:
            ユーザーエンティティのリスト
        """
        pass

    @abstractmethod
    async def create(self, user: User) -> User:
        """Create a new user.

        Args:
            user: 作成するユーザーエンティティ

        Returns:
            作成されたユーザーエンティティ（IDと作成日時が設定されている）
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        """Update an existing user.

        Args:
            user: 更新するユーザーエンティティ（user_idが必須）

        Returns:
            更新されたユーザーエンティティ
        """
        pass

    @abstractmethod
    async def update_last_login(self, user_id: UUID, last_login_at: datetime) -> bool:
        """Update user's last login timestamp.

        Args:
            user_id: ユーザーID
            last_login_at: 最終ログイン日時

        Returns:
            更新に成功した場合True
        """
        pass

    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete a user by ID.

        Args:
            user_id: ユーザーID

        Returns:
            削除に成功した場合True
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total number of users.

        Returns:
            ユーザーの総数
        """
        pass

    @abstractmethod
    async def find_or_create_by_email(
        self, email: str, name: str | None = None, picture: str | None = None
    ) -> User:
        """Find user by email or create if not exists.

        ログイン時に使用します。既存ユーザーの場合はlast_login_atを更新し、
        新規ユーザーの場合は作成します。

        Args:
            email: メールアドレス
            name: ユーザー名（新規作成時）
            picture: プロフィール画像URL（新規作成時）

        Returns:
            見つかったまたは作成されたユーザーエンティティ
        """
        pass
