#!/usr/bin/env python3
"""
議員団メンバー抽出機能の詳細動作検証スクリプト
"""

import asyncio
import sys
from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

# Polibaseモジュールのインポート
from src.config.database import get_db_engine
from src.database.extracted_parliamentary_group_member_repository import (
    ExtractedParliamentaryGroupMemberRepository,
)
from src.database.parliamentary_group_repository import (
    ParliamentaryGroupMembershipRepository,
    ParliamentaryGroupRepository,
)
from src.database.politician_repository import PoliticianRepository
from src.parliamentary_group_extractor.membership_service import (
    ParliamentaryGroupMembershipService,
)

console = Console()


class ParliamentaryGroupTester:
    """議員団機能のテストクラス"""

    def __init__(self):
        self.pg_repo = ParliamentaryGroupRepository()
        self.pgm_repo = ParliamentaryGroupMembershipRepository()
        self.extracted_repo = ExtractedParliamentaryGroupMemberRepository()
        self.politician_repo = PoliticianRepository()
        self.service = ParliamentaryGroupMembershipService()

    def cleanup(self):
        """リポジトリのクリーンアップ"""
        self.pg_repo.close()
        self.pgm_repo.close()
        self.extracted_repo.close()
        self.politician_repo.close()

    def show_parliamentary_groups(self):
        """議員団一覧を表示"""
        console.print(Panel("[bold]議員団一覧[/bold]", expand=False))

        groups = self.pg_repo.search_parliamentary_groups()
        if not groups:
            console.print("[yellow]議員団が登録されていません[/yellow]")
            return

        table = Table(title="登録済み議員団")
        table.add_column("ID", style="cyan", width=6)
        table.add_column("議員団名", style="green")
        table.add_column("会議体ID", style="yellow")
        table.add_column("URL", style="blue")
        table.add_column("状態", style="magenta")

        for group in groups:
            status = "✓ 活動中" if group.get("is_active") else "× 非活動"
            url = (
                group.get("url", "未設定")[:50] + "..."
                if group.get("url") and len(group.get("url")) > 50
                else group.get("url", "未設定")
            )
            table.add_row(
                str(group["id"]),
                group["name"],
                str(group["conference_id"]),
                url,
                status,
            )

        console.print(table)

    def test_extraction(self, group_id: int):
        """メンバー抽出のテスト"""
        console.print(
            f"\n[bold cyan]テスト1: メンバー抽出 (議員団ID: {group_id})[/bold cyan]"
        )

        # 議員団情報取得
        group = self.pg_repo.get_parliamentary_group_by_id(group_id)
        if not group:
            console.print(f"[red]議員団ID {group_id} が見つかりません[/red]")
            return False

        console.print(f"議員団: [green]{group['name']}[/green]")
        console.print(f"URL: [blue]{group.get('url', '未設定')}[/blue]")

        if not group.get("url"):
            console.print("[red]URLが設定されていません[/red]")
            return False

        # 抽出実行
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("メンバー抽出中...", total=None)

            try:
                result = asyncio.run(self.service.extract_members(group_id, force=True))
                progress.update(task, completed=True)
            except Exception as e:
                console.print(f"[red]エラー: {e}[/red]")
                return False

        # 結果表示
        console.print("\n[green]抽出結果:[/green]")
        console.print(f"  抽出数: {result['extracted_count']}名")
        console.print(f"  保存数: {result['saved_count']}名")

        if result["errors"]:
            console.print("[red]エラー:[/red]")
            for error in result["errors"]:
                console.print(f"  - {error}")

        # 抽出データ確認
        extracted = self.extracted_repo.get_pending_members(group_id)
        if extracted:
            table = Table(title="抽出されたメンバー")
            table.add_column("名前", style="cyan")
            table.add_column("役職", style="green")
            table.add_column("政党", style="yellow")
            table.add_column("選挙区", style="blue")

            for member in extracted:
                table.add_row(
                    member["extracted_name"],
                    member.get("extracted_role", "-"),
                    member.get("extracted_party_name", "-"),
                    member.get("extracted_electoral_district", "-"),
                )

            console.print(table)

        return result["extracted_count"] > 0

    def test_matching(self, group_id: int):
        """マッチングのテスト"""
        console.print(
            f"\n[bold cyan]テスト2: 政治家マッチング (議員団ID: {group_id})[/bold cyan]"
        )

        # マッチング実行
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("マッチング処理中...", total=None)

            try:
                result = asyncio.run(self.service.match_members(group_id))
                progress.update(task, completed=True)
            except Exception as e:
                console.print(f"[red]エラー: {e}[/red]")
                return False

        # 結果表示
        console.print("\n[green]マッチング結果:[/green]")
        console.print(f"  処理数: {result['processed_count']}名")
        console.print(f"  マッチ成功: {result['matched_count']}名")
        console.print(f"  要確認: {result['needs_review_count']}名")
        console.print(f"  マッチなし: {result['no_match_count']}名")

        # 詳細表示
        summary = self.extracted_repo.get_extraction_summary(group_id)
        if summary.get("total_count", 0) > 0:
            # マッチング詳細を表示
            engine = get_db_engine()
            with engine.connect() as conn:
                from sqlalchemy import text

                query = text("""
                    SELECT
                        epgm.extracted_name,
                        epgm.matching_status,
                        epgm.matching_confidence,
                        p.name as politician_name
                    FROM extracted_parliamentary_group_members epgm
                    LEFT JOIN politicians p ON epgm.matched_politician_id = p.id
                    WHERE epgm.parliamentary_group_id = :group_id
                    ORDER BY epgm.matching_status, epgm.extracted_name
                """)
                result = conn.execute(query, {"group_id": group_id})

                table = Table(title="マッチング詳細")
                table.add_column("抽出名", style="cyan")
                table.add_column("状態", style="green")
                table.add_column("信頼度", style="yellow")
                table.add_column("マッチした政治家", style="blue")

                for row in result:
                    status_display = {
                        "matched": "✓ マッチ",
                        "needs_review": "⚠ 要確認",
                        "no_match": "✗ 該当なし",
                        "pending": "○ 未処理",
                    }.get(row[1], row[1])

                    confidence = f"{row[2]:.2f}" if row[2] else "-"
                    politician = row[3] if row[3] else "-"

                    table.add_row(row[0], status_display, confidence, politician)

                console.print(table)

        return True

    def test_membership_creation(self, group_id: int):
        """メンバーシップ作成のテスト"""
        console.print(
            f"\n[bold cyan]テスト3: メンバーシップ作成 "
            f"(議員団ID: {group_id})[/bold cyan]"
        )

        # 作成実行
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("メンバーシップ作成中...", total=None)

            try:
                result = asyncio.run(
                    self.service.create_memberships_from_matched(
                        group_id, start_date=date.today()
                    )
                )
                progress.update(task, completed=True)
            except Exception as e:
                console.print(f"[red]エラー: {e}[/red]")
                return False

        # 結果表示
        console.print("\n[green]作成結果:[/green]")
        console.print(f"  処理数: {result['processed_count']}名")
        console.print(f"  作成数: {result['created_count']}名")
        console.print(f"  スキップ: {result['skipped_count']}名")

        # メンバーシップ詳細
        members = self.pgm_repo.get_current_members(group_id)
        if members:
            table = Table(title="現在のメンバーシップ")
            table.add_column("政治家名", style="cyan")
            table.add_column("役職", style="green")
            table.add_column("開始日", style="yellow")

            for member in members:
                table.add_row(
                    member["politician_name"],
                    member.get("role", "-"),
                    str(member["start_date"]),
                )

            console.print(table)

        return True

    def run_all_tests(self, group_id: int = None):
        """すべてのテストを実行"""
        console.print(
            Panel.fit(
                "[bold green]議員団メンバー抽出機能 総合テスト[/bold green]",
                border_style="green",
            )
        )

        # 議員団一覧表示
        self.show_parliamentary_groups()

        # テスト対象の議員団を選択
        if group_id is None:
            groups = self.pg_repo.search_parliamentary_groups()
            url_groups = [g for g in groups if g.get("url")]

            if not url_groups:
                console.print("[red]URLが設定されている議員団がありません[/red]")
                return

            # 最初のURL付き議員団を使用
            group_id = url_groups[0]["id"]
            group_name = url_groups[0]["name"]
            console.print(
                f"\n[yellow]テスト対象: {group_name} (ID: {group_id})[/yellow]"
            )

        # 各テストを実行
        console.print("\n" + "=" * 60 + "\n")

        # 1. 抽出テスト
        if not self.test_extraction(group_id):
            console.print("[red]抽出テストが失敗しました[/red]")
            return

        console.print("\n" + "-" * 60 + "\n")

        # 2. マッチングテスト
        if not self.test_matching(group_id):
            console.print("[red]マッチングテストが失敗しました[/red]")
            return

        console.print("\n" + "-" * 60 + "\n")

        # 3. メンバーシップ作成テスト
        if not self.test_membership_creation(group_id):
            console.print("[red]メンバーシップ作成テストが失敗しました[/red]")
            return

        # 最終状態確認
        console.print("\n" + "=" * 60 + "\n")
        console.print(Panel("[bold]最終状態サマリー[/bold]", expand=False))

        summary = self.extracted_repo.get_extraction_summary(group_id)
        memberships_count = len(self.pgm_repo.get_current_members(group_id))

        console.print(f"抽出総数: {summary.get('total_count', 0)}名")
        console.print(f"マッチ済み: {summary.get('matched_count', 0)}名")
        console.print(f"要確認: {summary.get('needs_review_count', 0)}名")
        console.print(f"該当なし: {summary.get('no_match_count', 0)}名")
        console.print(f"作成されたメンバーシップ: {memberships_count}件")

        console.print("\n[bold green]✓ すべてのテストが正常に完了しました[/bold green]")


def main():
    """メイン関数"""
    tester = ParliamentaryGroupTester()

    try:
        # コマンドライン引数から議員団IDを取得
        group_id = None
        if len(sys.argv) > 1:
            try:
                group_id = int(sys.argv[1])
            except ValueError:
                console.print(f"[red]無効な議員団ID: {sys.argv[1]}[/red]")
                return

        # テスト実行
        tester.run_all_tests(group_id)

    except KeyboardInterrupt:
        console.print("\n[yellow]テストが中断されました[/yellow]")
    except Exception as e:
        console.print(f"\n[red]予期しないエラー: {e}[/red]")
        import traceback

        traceback.print_exc()
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()
