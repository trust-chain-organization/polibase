"""Use case for matching extracted parliamentary group members to politicians."""

from datetime import datetime

from src.domain.repositories.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)
from src.domain.services.parliamentary_group_member_matching_service import (
    ParliamentaryGroupMemberMatchingService,
)


class MatchParliamentaryGroupMembersUseCase:
    """議員団メンバーマッチングユースケース

    抽出された議員団メンバーと既存の政治家データをマッチングし、
    信頼度スコアとステータスを更新します。

    Attributes:
        member_repository: 抽出メンバーリポジトリ
        matching_service: マッチングドメインサービス

    Example:
        >>> use_case = MatchParliamentaryGroupMembersUseCase(
        ...     member_repo, matching_service
        ... )
        >>> results = await use_case.execute(parliamentary_group_id=1)
        >>> for result in results:
        ...     print(f"{result['member_name']} → {result['status']}")
    """

    def __init__(
        self,
        member_repository: ExtractedParliamentaryGroupMemberRepository,
        matching_service: ParliamentaryGroupMemberMatchingService,
    ):
        """Initialize the use case.

        Args:
            member_repository: 抽出メンバーリポジトリ
            matching_service: マッチングドメインサービス
        """
        self.member_repo = member_repository
        self.matching_service = matching_service

    async def execute(
        self, parliamentary_group_id: int | None = None
    ) -> list[dict[str, str | int | float | None]]:
        """議員団メンバーのマッチング処理を実行する

        Args:
            parliamentary_group_id: 処理対象の議員団ID（Noneの場合は全pending）

        Returns:
            マッチング結果のリスト。各要素は以下を含む：
            - member_id: メンバーID
            - member_name: メンバー名
            - matched_politician_id: マッチした政治家ID（マッチなしの場合None）
            - confidence: マッチング信頼度
            - status: マッチングステータス（matched/needs_review/no_match）
            - reason: マッチング理由
        """
        # pending状態のメンバーを取得
        pending_members = await self.member_repo.get_pending_members(
            parliamentary_group_id
        )

        results: list[dict[str, str | int | float | None]] = []

        for member in pending_members:
            # マッチング処理を実行
            (
                matched_politician_id,
                confidence,
                reason,
            ) = await self.matching_service.find_matching_politician(member)

            # ステータスを決定
            status = self.matching_service.determine_matching_status(confidence)

            # リポジトリで更新
            if member.id is not None:
                await self.member_repo.update_matching_result(
                    member_id=member.id,
                    politician_id=matched_politician_id,
                    confidence=confidence,
                    status=status,
                    matched_at=datetime.now() if status == "matched" else None,
                )

            # 結果を記録
            results.append(
                {
                    "member_id": member.id,
                    "member_name": member.extracted_name,
                    "matched_politician_id": matched_politician_id,
                    "confidence": confidence,
                    "status": status,
                    "reason": reason,
                }
            )

        return results
