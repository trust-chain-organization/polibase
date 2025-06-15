"""Parliamentary Group commands for CLI"""

import asyncio
from datetime import datetime

import click
from rich.console import Console

from src.database.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)
from src.database.parliamentary_group_repository import (
    ParliamentaryGroupRepository,
)
from src.parliamentary_group_extractor.membership_service import (
    ParliamentaryGroupMembershipService,
)

console = Console()


# ステップ1: 議員団メンバー抽出
@click.command()
@click.option(
    "--group-id",
    type=int,
    help="特定の議員団のメンバーを抽出",
)
@click.option(
    "--all-groups",
    is_flag=True,
    help="URLが設定されている全議員団のメンバーを抽出",
)
@click.option(
    "--force",
    is_flag=True,
    help="既存の抽出データを削除して再抽出",
)
def extract_group_members(group_id: int | None, all_groups: bool, force: bool) -> None:
    """議員団URLからメンバーを抽出（ステップ1）"""
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

    console.print("[bold]ステップ1: 議員団メンバー抽出[/bold]")
    if force:
        console.print("[yellow]既存データを削除して再抽出します[/yellow]")
    console.print()

    # 総計
    total_results = {
        "extracted_count": 0,
        "saved_count": 0,
        "errors": [],
    }

    for group in groups:
        console.print(f"[bold]{group['name']}[/bold] を処理中...")
        console.print(f"URL: {group['url']}")

        try:
            result = asyncio.run(service.extract_members(group["id"], force=force))

            # 結果表示
            console.print(f"  抽出: {result['extracted_count']}名")
            console.print(f"  保存: {result['saved_count']}名")

            if result["errors"]:
                console.print("  エラー:")
                for error in result["errors"]:
                    console.print(f"    - {error}")

            # 総計更新
            total_results["extracted_count"] += result["extracted_count"]
            total_results["saved_count"] += result["saved_count"]
            total_results["errors"].extend(result["errors"])

            console.print()

        except Exception as e:
            console.print(f"[red]エラー: {e}[/red]")
            total_results["errors"].append(f"{group['name']}: {str(e)}")

    # 総計表示
    console.print("[bold]処理結果総計:[/bold]")
    console.print(f"  抽出総数: {total_results['extracted_count']}名")
    console.print(f"  保存総数: {total_results['saved_count']}名")

    pg_repo.close()


# ステップ2: メンバーマッチング
@click.command()
@click.option(
    "--group-id",
    type=int,
    help="特定の議員団のメンバーをマッチング",
)
def match_group_members(group_id: int | None) -> None:
    """抽出済みメンバーを既存の政治家とマッチング（ステップ2）"""
    service = ParliamentaryGroupMembershipService()

    console.print("[bold]ステップ2: メンバーマッチング[/bold]")
    console.print()

    try:
        result = asyncio.run(service.match_members(group_id))

        # 結果表示
        console.print("[bold]処理結果:[/bold]")
        console.print(f"  処理総数: {result['processed_count']}名")
        console.print(f"  マッチ成功: {result['matched_count']}名")
        console.print(f"  要確認: {result['needs_review_count']}名")
        console.print(f"  マッチなし: {result['no_match_count']}名")

        if result["errors"]:
            console.print("\n[red]エラー:[/red]")
            for error in result["errors"]:
                console.print(f"  - {error}")

    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")


# ステップ3: メンバーシップ作成
@click.command()
@click.option(
    "--group-id",
    type=int,
    required=True,
    help="議員団ID",
)
@click.option(
    "--start-date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="所属開始日 (YYYY-MM-DD)",
)
def create_group_memberships(group_id: int, start_date: datetime | None) -> None:
    """マッチング済みメンバーからメンバーシップを作成（ステップ3）"""
    service = ParliamentaryGroupMembershipService()
    pg_repo = ParliamentaryGroupRepository()

    # 議員団情報を取得
    group = pg_repo.get_parliamentary_group_by_id(group_id)
    if not group:
        console.print(f"[red]議員団ID {group_id} が見つかりません[/red]")
        return

    console.print("[bold]ステップ3: メンバーシップ作成[/bold]")
    console.print(f"議員団: {group['name']}")
    console.print()

    try:
        result = asyncio.run(
            service.create_memberships_from_matched(
                group_id, start_date=start_date.date() if start_date else None
            )
        )

        # 結果表示
        console.print("[bold]処理結果:[/bold]")
        console.print(f"  処理総数: {result['processed_count']}名")
        console.print(f"  作成: {result['created_count']}名")
        console.print(f"  更新: {result['updated_count']}名")
        console.print(f"  スキップ: {result['skipped_count']}名")

        if result["errors"]:
            console.print("\n[red]エラー:[/red]")
            for error in result["errors"]:
                console.print(f"  - {error}")

    except Exception as e:
        console.print(f"[red]エラー: {e}[/red]")

    pg_repo.close()


# 議員団抽出状況確認
@click.command()
@click.option(
    "--group-id",
    type=int,
    help="特定の議員団の状況を表示",
)
def group_member_status(group_id: int | None) -> None:
    """議員団メンバー抽出状況を確認"""
    pg_repo = ParliamentaryGroupRepository()
    extracted_repo = ExtractedParliamentaryGroupMemberRepository()

    if group_id:
        groups = [pg_repo.get_parliamentary_group_by_id(group_id)]
        if not groups[0]:
            console.print(f"[red]議員団ID {group_id} が見つかりません[/red]")
            return
    else:
        groups = pg_repo.search_parliamentary_groups()
        groups = [g for g in groups if g.get("url")]

    console.print("[bold]議員団メンバー抽出状況[/bold]")
    console.print()

    for group in groups:
        summary = extracted_repo.get_extraction_summary(group["id"])

        console.print(f"[bold]{group['name']}[/bold]")
        console.print(f"  URL: {group.get('url', '未設定')}")

        if summary.get("total_count", 0) > 0:
            console.print(f"  抽出済み: {summary['total_count']}名")
            console.print(f"    - 未処理: {summary.get('pending_count', 0)}名")
            console.print(f"    - マッチ済み: {summary.get('matched_count', 0)}名")
            console.print(f"    - 要確認: {summary.get('needs_review_count', 0)}名")
            console.print(f"    - マッチなし: {summary.get('no_match_count', 0)}名")
        else:
            console.print("  [dim]未抽出[/dim]")

        console.print()

    pg_repo.close()
    extracted_repo.close()


@click.command()
def list_parliamentary_groups() -> None:
    """議員団一覧を表示"""
    pg_repo = ParliamentaryGroupRepository()

    groups = pg_repo.search_parliamentary_groups()
    if not groups:
        console.print("[yellow]議員団が登録されていません[/yellow]")
        return

    console.print("[bold]議員団一覧[/bold]")
    for group in groups:
        status = "✓" if group.get("is_active") else "×"
        console.print(f"{status} [{group['id']}] {group['name']}")
        if group.get("url"):
            console.print(f"   URL: {group['url']}")

    pg_repo.close()


def get_parliamentary_group_commands() -> list[click.Command]:
    """Get all parliamentary group commands"""
    return [
        extract_group_members,
        match_group_members,
        create_group_memberships,
        group_member_status,
        list_parliamentary_groups,
    ]
