"""Use case for reviewing extracted parliamentary group members."""

from datetime import datetime

from pydantic import BaseModel

from src.domain.repositories.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)


class ReviewExtractedMemberInputDto(BaseModel):
    """Input DTO for reviewing an extracted member."""

    member_id: int
    action: str  # 'approve', 'reject', 'match'
    politician_id: int | None = None
    confidence: float | None = None


class ReviewExtractedMemberOutputDto(BaseModel):
    """Output DTO for reviewing an extracted member."""

    success: bool
    message: str
    member_id: int | None = None


class ReviewExtractedMemberUseCase:
    """抽出メンバーレビューユースケース

    抽出された議員団メンバーをレビューし、マッチング結果を更新します。

    Actions:
        - approve: マッチ済みメンバーを承認
        - reject: メンバーを却下（no_match）
        - match: 手動でマッチング実行

    Transaction Management:
        リポジトリメソッドはflush()のみを実行し、
        RepositoryAdapterが自動的にcommit/rollbackを管理します。
    """

    def __init__(
        self,
        member_repository: ExtractedParliamentaryGroupMemberRepository,
    ):
        """Initialize the use case.

        Args:
            member_repository: 抽出メンバーリポジトリ
        """
        self.member_repo = member_repository

    async def execute(
        self, input_dto: ReviewExtractedMemberInputDto
    ) -> ReviewExtractedMemberOutputDto:
        """抽出メンバーをレビューする

        Args:
            input_dto: 入力DTO

        Returns:
            レビュー結果のDTO

        Transaction Boundary:
            このUse Caseは単一の更新操作を実行します。
            RepositoryAdapterが自動的にトランザクションを管理し、
            更新が成功した場合はコミット、失敗した場合はロールバックします。
        """
        try:
            # Get member
            member = await self.member_repo.get_by_id(input_dto.member_id)
            if not member:
                return ReviewExtractedMemberOutputDto(
                    success=False,
                    message="メンバーが見つかりません",
                    member_id=input_dto.member_id,
                )

            # Determine status and matched_at based on action
            if input_dto.action == "approve":
                # Approve matched member
                if member.matching_status != "matched":
                    return ReviewExtractedMemberOutputDto(
                        success=False,
                        message="マッチ済みのメンバーのみ承認できます",
                        member_id=input_dto.member_id,
                    )
                status = "matched"
                matched_at = datetime.now()
                politician_id = member.matched_politician_id
                confidence = member.matching_confidence

            elif input_dto.action == "reject":
                # Reject member
                status = "no_match"
                matched_at = None
                politician_id = None
                confidence = None

            elif input_dto.action == "match":
                # Manual match
                if input_dto.politician_id is None:
                    return ReviewExtractedMemberOutputDto(
                        success=False,
                        message="政治家IDが必要です",
                        member_id=input_dto.member_id,
                    )
                status = "matched"
                matched_at = datetime.now()
                politician_id = input_dto.politician_id
                confidence = input_dto.confidence or 0.8

            else:
                return ReviewExtractedMemberOutputDto(
                    success=False,
                    message=f"不明なアクション: {input_dto.action}",
                    member_id=input_dto.member_id,
                )

            # Update matching result
            updated_member = await self.member_repo.update_matching_result(
                member_id=input_dto.member_id,
                politician_id=politician_id,
                confidence=confidence,
                status=status,
                matched_at=matched_at,
            )

            if updated_member:
                action_messages = {
                    "approve": "承認しました",
                    "reject": "却下しました",
                    "match": "マッチングを実行しました",
                }
                message = action_messages.get(
                    input_dto.action, f"{input_dto.action}を実行しました"
                )
                return ReviewExtractedMemberOutputDto(
                    success=True, message=message, member_id=input_dto.member_id
                )
            else:
                return ReviewExtractedMemberOutputDto(
                    success=False,
                    message="データベース更新に失敗しました",
                    member_id=input_dto.member_id,
                )

        except Exception as e:
            return ReviewExtractedMemberOutputDto(
                success=False,
                message=f"エラーが発生しました: {str(e)}",
                member_id=input_dto.member_id,
            )
