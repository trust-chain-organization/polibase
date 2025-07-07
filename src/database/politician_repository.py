"""Repository for managing politician data using Pydantic models"""

import logging
from difflib import SequenceMatcher
from typing import Any

from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError

from src.database.typed_repository import TypedRepository
from src.exceptions import (
    DatabaseError,
    DuplicateRecordError,
    SaveError,
)
from src.models.politician import Politician, PoliticianCreate, PoliticianUpdate

logger = logging.getLogger(__name__)


class PoliticianRepository(TypedRepository[Politician]):
    """Politician repository with Pydantic model support"""

    def __init__(self, db=None):
        # If db session is provided, use it; otherwise fall back to engine
        if db:
            super().__init__(Politician, "politicians", use_session=True)
            self._session = db  # Set internal _session attribute
        else:
            super().__init__(Politician, "politicians", use_session=False)

    def fetch_as_model(
        self,
        model_class: type[Politician],
        query: str,
        params: dict[str, Any] | None = None,
    ) -> Politician | None:
        """Fetch single row as model - wrapper for TypedRepository.fetch_one"""
        return self.fetch_one(query, params)

    def fetch_all_as_models(
        self,
        model_class: type[Politician],
        query: str,
        params: dict[str, Any] | None = None,
    ) -> list[Politician]:
        """Fetch all rows as models - wrapper for TypedRepository.fetch_all"""
        return list(self.fetch_all(query, params))

    def fetch_as_dict(
        self, query: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute query and return results as list of dictionaries"""
        result = self.execute_query(query, params)
        columns = result.keys()
        return [dict(zip(columns, row, strict=False)) for row in result.fetchall()]

    def create_politician(self, politician: PoliticianCreate) -> Politician | None:
        """新しい政治家を作成（既存の場合は更新）

        Raises:
            SaveError: If creating or updating politician fails
            DatabaseError: If database operation fails
        """
        try:
            # 既存の政治家をチェック（名前と政党でマッチング）
            existing = self.get_by_name_and_party(
                politician.name, politician.political_party_id
            )

            if existing:
                # 既存レコードがある場合、更新が必要かチェック
                update_data = PoliticianUpdate()
                needs_update = False

                # 各フィールドを比較
                if politician.position and politician.position != existing.position:
                    update_data.position = politician.position
                    needs_update = True
                if (
                    politician.prefecture
                    and politician.prefecture != existing.prefecture
                ):
                    update_data.prefecture = politician.prefecture
                    needs_update = True
                if (
                    politician.electoral_district
                    and politician.electoral_district != existing.electoral_district
                ):
                    update_data.electoral_district = politician.electoral_district
                    needs_update = True
                if (
                    politician.profile_url
                    and politician.profile_url != existing.profile_url
                ):
                    update_data.profile_url = politician.profile_url
                    needs_update = True
                if (
                    politician.party_position
                    and politician.party_position != existing.party_position
                ):
                    update_data.party_position = politician.party_position
                    needs_update = True
                if (
                    politician.speaker_id
                    and politician.speaker_id != existing.speaker_id
                ):
                    update_data.speaker_id = politician.speaker_id
                    needs_update = True

                if needs_update:
                    self.update_politician(existing.id, update_data)
                    logger.info(
                        f"政治家情報を更新しました: {politician.name} "
                        f"(ID: {existing.id})"
                    )
                    # 更新後のデータを取得
                    return self.get_by_id(existing.id)
                else:
                    logger.info(
                        f"政治家は既に存在し、更新の必要はありません: "
                        f"{politician.name} (ID: {existing.id})"
                    )
                    return existing
            else:
                # 新規作成
                politician_id = self.insert_model("politicians", politician, "id")
                if politician_id:
                    logger.info(
                        f"新しい政治家を作成しました: {politician.name} "
                        f"(ID: {politician_id})"
                    )
                    return self.get_by_id(politician_id)
                raise SaveError(
                    f"Failed to create politician: {politician.name}",
                    {"politician_data": politician.model_dump()},
                )
        except SQLIntegrityError as e:
            logger.error(f"Integrity error creating politician {politician.name}: {e}")
            raise DuplicateRecordError("Politician", politician.name) from e
        except SQLAlchemyError as e:
            logger.error(f"Database error creating politician {politician.name}: {e}")
            raise DatabaseError(
                f"Failed to create politician: {politician.name}",
                {"error": str(e), "politician_data": politician.model_dump()},
            ) from e
        except (SaveError, DuplicateRecordError, DatabaseError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating politician {politician.name}: {e}")
            raise SaveError(
                f"Unexpected error creating politician: {politician.name}",
                {"error": str(e), "politician_data": politician.model_dump()},
            ) from e

    def get_by_id(self, politician_id: int) -> Politician | None:
        """IDで政治家を取得"""
        query = "SELECT * FROM politicians WHERE id = :id"
        return self.fetch_as_model(Politician, query, {"id": politician_id})

    def get_by_name_and_party(
        self, name: str, party_id: int | None
    ) -> Politician | None:
        """名前と政党IDで政治家を取得"""
        if party_id is None:
            query = (
                "SELECT * FROM politicians WHERE name = :name "
                "AND political_party_id IS NULL"
            )
            params = {"name": name}
        else:
            query = (
                "SELECT * FROM politicians WHERE name = :name "
                "AND political_party_id = :party_id"
            )
            params = {"name": name, "party_id": party_id}

        return self.fetch_as_model(Politician, query, params)

    def get_all(self) -> list[Politician]:
        """全ての政治家を取得"""
        query = "SELECT * FROM politicians ORDER BY id"
        return self.fetch_all_as_models(Politician, query)

    def get_by_party(self, party_id: int) -> list[Politician]:
        """政党IDで政治家を取得"""
        query = (
            "SELECT * FROM politicians WHERE political_party_id = :party_id "
            "ORDER BY name"
        )
        return self.fetch_all_as_models(Politician, query, {"party_id": party_id})

    def update_politician(
        self, politician_id: int, update_data: PoliticianUpdate
    ) -> bool:
        """政治家情報を更新"""
        rows_affected = self.update_model(
            "politicians", update_data, {"id": politician_id}
        )
        return rows_affected > 0

    def delete_politician(self, politician_id: int) -> bool:
        """政治家を削除"""
        rows_affected = self.delete("politicians", {"id": politician_id})
        return rows_affected > 0

    def search_by_name(self, name: str, threshold: float = 0.8) -> list[dict]:
        """
        名前で政治家を検索（ファジーマッチング）

        Args:
            name: 検索する名前
            threshold: 類似度の閾値（0-1）

        Returns:
            list of dict with politician data and similarity score
        """
        # 全政治家を取得（政党名を含む）
        query = """
            SELECT p.*, pp.name as party_name
            FROM politicians p
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            ORDER BY p.id
        """
        politicians_data = self.fetch_as_dict(query)

        # ファジーマッチング
        results = []
        for politician_dict in politicians_data:
            similarity = SequenceMatcher(None, name, politician_dict["name"]).ratio()
            if similarity >= threshold:
                politician_dict["similarity"] = similarity
                results.append(politician_dict)

        # 類似度でソート
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results

    def find_by_name(self, name: str) -> list[Politician]:
        """名前で政治家を検索（完全一致）"""
        query = "SELECT * FROM politicians WHERE name = :name ORDER BY id"
        return self.fetch_all_as_models(Politician, query, {"name": name})

    def find_by_name_and_party(
        self, name: str, party_id: int | None
    ) -> Politician | None:
        """名前と政党IDで政治家を取得"""
        return self.get_by_name_and_party(name, party_id)

    def create(self, politician: PoliticianCreate) -> Politician | None:
        """新しい政治家を作成（v2インターフェース）"""
        return self.create_politician(politician)

    def update_v2(
        self, politician_id: int, update_data: PoliticianUpdate
    ) -> Politician | None:
        """政治家情報を更新（v2インターフェース）"""
        success = self.update_politician(politician_id, update_data)
        if success:
            return self.get_by_id(politician_id)
        return None

    def bulk_create_politicians(
        self, politicians_data: list[dict]
    ) -> dict[str, list[Politician]]:
        """
        複数の政治家を一括作成または更新

        Args:
            politicians_data: 政治家データの辞書リスト

        Returns:
            dict: created, updated, errors のリストを含む辞書
        """
        created = []
        updated = []
        errors = []

        for data in politicians_data:
            try:
                # dictからPydanticモデルを作成
                politician_create = PoliticianCreate(**data)

                # 既存の政治家をチェック
                existing = self.find_by_name_and_party(
                    politician_create.name, politician_create.political_party_id
                )

                if existing:
                    # 更新が必要かチェック
                    update_data = PoliticianUpdate()
                    needs_update = False

                    for field in [
                        "position",
                        "prefecture",
                        "electoral_district",
                        "profile_url",
                        "party_position",
                        "speaker_id",
                    ]:
                        new_value = getattr(politician_create, field, None)
                        if new_value and new_value != getattr(existing, field):
                            setattr(update_data, field, new_value)
                            needs_update = True

                    if needs_update:
                        updated_politician = self.update_v2(existing.id, update_data)
                        if updated_politician:
                            updated.append(updated_politician)
                else:
                    # 新規作成
                    new_politician = self.create(politician_create)
                    if new_politician:
                        created.append(new_politician)

            except SQLIntegrityError as e:
                logger.error(
                    f"Integrity error processing politician {data.get('name')}: {e}"
                )
                errors.append(
                    {
                        "data": data,
                        "error": f"Duplicate or constraint violation: {str(e)}",
                    }
                )
            except SQLAlchemyError as e:
                logger.error(
                    f"Database error processing politician {data.get('name')}: {e}"
                )
                errors.append({"data": data, "error": f"Database error: {str(e)}"})
            except Exception as e:
                logger.error(
                    f"Unexpected error processing politician {data.get('name')}: {e}"
                )
                errors.append({"data": data, "error": f"Unexpected error: {str(e)}"})

        return {"created": created, "updated": updated, "errors": errors}

    def close(self):
        """セッションをクローズ（BaseRepositoryで処理）"""
        # BaseRepositoryのデストラクタで自動的に処理されるため、
        # ここでは何もしない
        pass
