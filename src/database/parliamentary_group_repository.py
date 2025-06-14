"""議員団関連のリポジトリクラス"""

from datetime import date

from src.database.base_repository import BaseRepository


class ParliamentaryGroupRepository(BaseRepository):
    """議員団のリポジトリ"""

    def create_parliamentary_group(
        self,
        name: str,
        conference_id: int,
        url: str | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> dict:
        """議員団を作成する

        Args:
            name: 議員団名
            conference_id: 所属する会議体ID
            url: 議員団の公式URL
            description: 議員団の説明
            is_active: 現在活動中かどうか

        Returns:
            作成された議員団の情報
        """
        query = """
        INSERT INTO parliamentary_groups
            (name, conference_id, url, description, is_active)
        VALUES (:name, :conference_id, :url, :description, :is_active)
        RETURNING id, name, conference_id, url, description, is_active, created_at,
                  updated_at
        """
        result = self.execute_query(
            query,
            {
                "name": name,
                "conference_id": conference_id,
                "url": url,
                "description": description,
                "is_active": is_active,
            },
        )
        row = result.fetchone()
        return dict(row) if row else {}

    def get_parliamentary_group_by_id(self, group_id: int) -> dict | None:
        """IDで議員団を取得する

        Args:
            group_id: 議員団ID

        Returns:
            議員団情報、見つからない場合はNone
        """
        query = """
        SELECT pg.*, c.name as conference_name
        FROM parliamentary_groups pg
        JOIN conferences c ON pg.conference_id = c.id
        WHERE pg.id = :group_id
        """
        result = self.execute_query(query, {"group_id": group_id})
        row = result.fetchone()
        return dict(row) if row else None

    def get_parliamentary_groups_by_conference(
        self, conference_id: int, active_only: bool = True
    ) -> list[dict]:
        """会議体に所属する議員団を取得する

        Args:
            conference_id: 会議体ID
            active_only: 活動中の議員団のみ取得するか

        Returns:
            議員団のリスト
        """
        query = """
        SELECT * FROM parliamentary_groups
        WHERE conference_id = :conference_id
        """
        if active_only:
            query += " AND is_active = true"
        query += " ORDER BY name"

        result = self.execute_query(query, {"conference_id": conference_id})
        return [dict(row) for row in result.fetchall()]

    def search_parliamentary_groups(
        self, name: str | None = None, conference_id: int | None = None
    ) -> list[dict]:
        """議員団を検索する

        Args:
            name: 議員団名（部分一致）
            conference_id: 会議体ID

        Returns:
            検索結果のリスト
        """
        query = "SELECT * FROM parliamentary_groups WHERE 1=1"
        params = {}

        if name:
            query += " AND name LIKE :name"
            params["name"] = f"%{name}%"

        if conference_id:
            query += " AND conference_id = :conference_id"
            params["conference_id"] = conference_id

        query += " ORDER BY name"

        result = self.execute_query(query, params)
        return [dict(row) for row in result.fetchall()]

    def update_parliamentary_group(
        self,
        group_id: int,
        name: str | None = None,
        url: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> bool:
        """議員団情報を更新する

        Args:
            group_id: 議員団ID
            name: 議員団名
            url: 議員団の公式URL
            description: 議員団の説明
            is_active: 現在活動中かどうか

        Returns:
            更新成功ならTrue
        """
        updates = []
        params: dict[str, str | int | bool] = {"group_id": group_id}

        if name is not None:
            updates.append("name = :name")
            params["name"] = name

        if url is not None:
            updates.append("url = :url")
            params["url"] = url

        if description is not None:
            updates.append("description = :description")
            params["description"] = description

        if is_active is not None:
            updates.append("is_active = :is_active")
            params["is_active"] = is_active

        if not updates:
            return False

        query = f"""
        UPDATE parliamentary_groups
        SET {", ".join(updates)}
        WHERE id = :group_id
        """
        self.execute_query(query, params)
        return True


class ParliamentaryGroupMembershipRepository(BaseRepository):
    """議員団所属履歴のリポジトリ"""

    def add_membership(
        self,
        politician_id: int,
        parliamentary_group_id: int,
        start_date: date,
        end_date: date | None = None,
        role: str | None = None,
    ) -> dict:
        """議員団所属履歴を追加する

        Args:
            politician_id: 政治家ID
            parliamentary_group_id: 議員団ID
            start_date: 所属開始日
            end_date: 所属終了日
            role: 議員団内での役職

        Returns:
            作成された所属履歴
        """
        query = """
        INSERT INTO parliamentary_group_memberships
        (politician_id, parliamentary_group_id, start_date, end_date, role)
        VALUES (:politician_id, :parliamentary_group_id, :start_date, :end_date, :role)
        RETURNING id, politician_id, parliamentary_group_id, start_date, end_date,
                  role, created_at
        """
        result = self.execute_query(
            query,
            {
                "politician_id": politician_id,
                "parliamentary_group_id": parliamentary_group_id,
                "start_date": start_date,
                "end_date": end_date,
                "role": role,
            },
        )
        row = result.fetchone()
        return dict(row) if row else {}

    def get_current_members(self, parliamentary_group_id: int) -> list[dict]:
        """議員団の現在のメンバーを取得する

        Args:
            parliamentary_group_id: 議員団ID

        Returns:
            現在所属しているメンバーのリスト
        """
        query = """
        SELECT pgm.*, p.name as politician_name, pp.name as party_name
        FROM parliamentary_group_memberships pgm
        JOIN politicians p ON pgm.politician_id = p.id
        LEFT JOIN political_parties pp ON p.political_party_id = pp.id
        WHERE pgm.parliamentary_group_id = :group_id
        AND pgm.end_date IS NULL
        ORDER BY pgm.start_date DESC, p.name
        """
        result = self.execute_query(query, {"group_id": parliamentary_group_id})
        return [dict(row) for row in result.fetchall()]

    def get_member_history(
        self, parliamentary_group_id: int, include_past: bool = True
    ) -> list[dict]:
        """議員団のメンバー履歴を取得する

        Args:
            parliamentary_group_id: 議員団ID
            include_past: 過去のメンバーも含めるか

        Returns:
            メンバー履歴のリスト
        """
        query = """
        SELECT pgm.*, p.name as politician_name, pp.name as party_name
        FROM parliamentary_group_memberships pgm
        JOIN politicians p ON pgm.politician_id = p.id
        LEFT JOIN political_parties pp ON p.political_party_id = pp.id
        WHERE pgm.parliamentary_group_id = :group_id
        """
        if not include_past:
            query += " AND pgm.end_date IS NULL"

        query += " ORDER BY pgm.start_date DESC, pgm.end_date DESC NULLS FIRST, p.name"

        result = self.execute_query(query, {"group_id": parliamentary_group_id})
        return [dict(row) for row in result.fetchall()]

    def get_politician_groups(
        self, politician_id: int, current_only: bool = True
    ) -> list[dict]:
        """政治家が所属する（した）議員団を取得する

        Args:
            politician_id: 政治家ID
            current_only: 現在所属中の議員団のみ取得するか

        Returns:
            議員団のリスト
        """
        query = """
        SELECT pgm.*, pg.name as group_name, pg.description, c.name as conference_name
        FROM parliamentary_group_memberships pgm
        JOIN parliamentary_groups pg ON pgm.parliamentary_group_id = pg.id
        JOIN conferences c ON pg.conference_id = c.id
        WHERE pgm.politician_id = :politician_id
        """
        if current_only:
            query += " AND pgm.end_date IS NULL"

        query += " ORDER BY pgm.start_date DESC"

        result = self.execute_query(query, {"politician_id": politician_id})
        return [dict(row) for row in result.fetchall()]

    def end_membership(
        self, politician_id: int, parliamentary_group_id: int, end_date: date
    ) -> bool:
        """議員団所属を終了させる

        Args:
            politician_id: 政治家ID
            parliamentary_group_id: 議員団ID
            end_date: 所属終了日

        Returns:
            更新成功ならTrue
        """
        query = """
        UPDATE parliamentary_group_memberships
        SET end_date = :end_date
        WHERE politician_id = :politician_id
        AND parliamentary_group_id = :parliamentary_group_id
        AND end_date IS NULL
        """
        self.execute_query(
            query,
            {
                "politician_id": politician_id,
                "parliamentary_group_id": parliamentary_group_id,
                "end_date": end_date,
            },
        )
        return True

    def get_group_members_at_date(
        self, parliamentary_group_id: int, target_date: date
    ) -> list[dict]:
        """特定の日付における議員団のメンバーを取得する

        Args:
            parliamentary_group_id: 議員団ID
            target_date: 対象日付

        Returns:
            その日付に所属していたメンバーのリスト
        """
        query = """
        SELECT pgm.*, p.name as politician_name, pp.name as party_name
        FROM parliamentary_group_memberships pgm
        JOIN politicians p ON pgm.politician_id = p.id
        LEFT JOIN political_parties pp ON p.political_party_id = pp.id
        WHERE pgm.parliamentary_group_id = :group_id
        AND pgm.start_date <= :target_date
        AND (pgm.end_date IS NULL OR pgm.end_date >= :target_date)
        ORDER BY p.name
        """
        result = self.execute_query(
            query, {"group_id": parliamentary_group_id, "target_date": target_date}
        )
        return [dict(row) for row in result.fetchall()]
