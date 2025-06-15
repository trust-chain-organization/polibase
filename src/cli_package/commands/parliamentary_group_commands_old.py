"""議員団関連のCLIコマンド"""

import asyncio
import logging

import click
from rich.console import Console
from rich.table import Table

from src.database.parliamentary_group_repository import (
    ParliamentaryGroupMembershipRepository,
    ParliamentaryGroupRepository,
)
from src.parliamentary_group_extractor.membership_service import (
    ParliamentaryGroupMembershipService,
)

logger = logging.getLogger(__name__)
console = Console()


def get_parliamentary_group_commands() -> list[click.Command]:
    """議員団関連のコマンドを返す"""
    return [
        extract_group_members,
        list_parliamentary_groups,
    ]


@click.command()
@click.option(
    "--group-id",
    type=int,
    help="特定の議員団IDのメンバーを抽出",
)
@click.option(
    "--all-groups",
    is_flag=True,
    help="URLが設定されている全議員団のメンバーを抽出",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="実際にはメンバーシップを作成しない",
)
def extract_group_members(
    group_id: int | None, all_groups: bool, dry_run: bool
) -> None:
    """議員団URLからメンバーを抽出"""
    if not group_id and not all_groups:
        console.print(
            "[red]エラー: --group-id または --all-groups を指定してください[/red]"
        )
        return

    pg_repo = ParliamentaryGroupRepository()
    service = ParliamentaryGroupMembershipService()

    # 処理対象の議員団を取得
    if group_id:
        group = pg_repo.get_parliamentary_group_by_id(group_id)
        if not group:
            console.print(f"[red]議員団ID {group_id} が見つかりません[/red]")
            return
        groups = [group]
    else:
        all_groups_list = pg_repo.search_parliamentary_groups()
        groups = [g for g in all_groups_list if g.get("url")]
        if not groups:
            console.print("[yellow]URLが設定されている議員団がありません[/yellow]")
            return

    # 実行確認
    if dry_run:
        console.print("[yellow]ドライランモードで実行します[/yellow]")
    else:
        console.print("[red]実際にメンバーシップを作成します[/red]")

    # 各議員団を処理
    total_extracted = 0
    total_matched = 0
    total_created = 0

    for group in groups:
        console.print(f"\n[bold]{group['name']}[/bold] を処理中...")
        console.print(f"URL: {group['url']}")

        try:
            result = asyncio.run(
                service.extract_and_create_memberships(group["id"], dry_run=dry_run)
            )

            # 結果を表示
            console.print(f"  抽出: {result['extracted_count']}名")
            console.print(f"  マッチング: {result['matched_count']}名")
            if not dry_run:
                console.print(f"  作成: {result['created_count']}名")

            total_extracted += result["extracted_count"]
            total_matched += result["matched_count"]
            total_created += result["created_count"]

            # エラーがあれば表示
            if result["errors"]:
                console.print("  [red]エラー:[/red]")
                for error in result["errors"]:
                    console.print(f"    - {error}")

        except Exception as e:
            console.print(f"  [red]処理エラー: {e}[/red]")
            logger.error(f"Error processing group {group['id']}: {e}", exc_info=True)

    # 総計を表示
    console.print("\n[bold]処理結果総計:[/bold]")
    console.print(f"  抽出総数: {total_extracted}名")
    console.print(f"  マッチング総数: {total_matched}名")
    if not dry_run:
        console.print(f"  作成総数: {total_created}名")


@click.command()
@click.option(
    "--conference-id",
    type=int,
    help="特定の会議体の議員団のみ表示",
)
@click.option(
    "--with-members",
    is_flag=True,
    help="現在のメンバー数も表示",
)
def list_parliamentary_groups(conference_id: int | None, with_members: bool) -> None:
    """議員団一覧を表示"""
    pg_repo = ParliamentaryGroupRepository()
    pgm_repo = ParliamentaryGroupMembershipRepository()

    # 議員団を取得
    if conference_id:
        groups = pg_repo.get_parliamentary_groups_by_conference(
            conference_id, active_only=False
        )
    else:
        groups = pg_repo.search_parliamentary_groups()

    if not groups:
        console.print("[yellow]議員団が見つかりません[/yellow]")
        return

    # テーブルを作成
    table = Table(title="議員団一覧", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="dim", width=6)
    table.add_column("議員団名", style="cyan", width=30)
    table.add_column("会議体", width=20)
    table.add_column("URL", width=40)
    table.add_column("状態", width=8)
    if with_members:
        table.add_column("メンバー数", justify="right", width=10)

    # 各議員団の情報を表示
    for group in groups:
        row = [
            str(group["id"]),
            group["name"],
            group.get("conference_name", ""),
            group.get("url", "") or "未設定",
            "活動中" if group.get("is_active", True) else "非活動",
        ]

        if with_members:
            members = pgm_repo.get_current_members(group["id"])
            row.append(str(len(members)))

        table.add_row(*row)

    console.print(table)
    console.print(f"\n合計: {len(groups)}議員団")
