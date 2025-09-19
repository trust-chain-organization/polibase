"""ProposalParliamentaryGroupJudge entity module."""

from src.domain.entities.base import BaseEntity


class ProposalParliamentaryGroupJudge(BaseEntity):
    """議案への会派単位の賛否情報を表すエンティティ."""

    def __init__(
        self,
        proposal_id: int,
        parliamentary_group_id: int,
        judgment: str,
        member_count: int | None = None,
        note: str | None = None,
        id: int | None = None,
    ) -> None:
        """Initialize ProposalParliamentaryGroupJudge entity.

        Args:
            proposal_id: 議案ID
            parliamentary_group_id: 会派ID
            judgment: 賛否判断（賛成/反対/棄権/欠席）
            member_count: この判断をした会派メンバーの人数
            note: 備考（自由投票など特記事項）
            id: エンティティID
        """
        super().__init__(id)
        self.proposal_id = proposal_id
        self.parliamentary_group_id = parliamentary_group_id
        self.judgment = judgment
        self.member_count = member_count
        self.note = note

    def is_approve(self) -> bool:
        """賛成かどうかを判定."""
        return self.judgment == "賛成"

    def is_oppose(self) -> bool:
        """反対かどうかを判定."""
        return self.judgment == "反対"

    def is_abstain(self) -> bool:
        """棄権かどうかを判定."""
        return self.judgment == "棄権"

    def is_absent(self) -> bool:
        """欠席かどうかを判定."""
        return self.judgment == "欠席"

    def __str__(self) -> str:
        return (
            f"ProposalParliamentaryGroupJudge: "
            f"Group {self.parliamentary_group_id} - {self.judgment}"
            f"{f' ({self.member_count}人)' if self.member_count else ''}"
        )
