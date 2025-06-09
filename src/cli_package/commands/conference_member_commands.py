"""Commands for managing conference member extraction and matching"""

import asyncio
import logging
from datetime import date

import click

from src.cli_package.base import BaseCommand
from src.cli_package.progress import ProgressBar
from src.conference_member_extractor.extractor import ConferenceMemberExtractor
from src.conference_member_extractor.matching_service import (
    ConferenceMemberMatchingService,
)
from src.database.conference_repository import ConferenceRepository
from src.database.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)

logger = logging.getLogger(__name__)


class ConferenceMemberCommands(BaseCommand):
    """Commands for conference member extraction and matching"""
    
    @staticmethod
    def echo_info(message: str):
        """Show an info message"""
        click.echo(message)
    
    @staticmethod
    def echo_success(message: str):
        """Show a success message"""
        click.echo(click.style(f"✓ {message}", fg="green"))
    
    @staticmethod
    def echo_warning(message: str):
        """Show a warning message"""
        click.echo(click.style(f"⚠️  {message}", fg="yellow"))
    
    @staticmethod
    def echo_error(message: str):
        """Show an error message"""
        click.echo(click.style(f"✗ {message}", fg="red"), err=True)

    def get_commands(self) -> list[click.Command]:
        """Get list of conference member commands"""
        return [
            ConferenceMemberCommands.extract_conference_members,
            ConferenceMemberCommands.match_conference_members,
            ConferenceMemberCommands.create_affiliations,
            ConferenceMemberCommands.member_status,
        ]

    @staticmethod
    @click.command("extract-conference-members")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合はURLが設定されている全会議体を処理）",
    )
    @click.option(
        "--force",
        is_flag=True,
        help="既存の抽出データを削除して再抽出",
    )
    def extract_conference_members(conference_id: int = None, force: bool = False):
        """会議体の議員紹介URLから議員情報を抽出（ステップ1）"""
        
        click.echo("📋 会議体メンバー情報の抽出を開始します（ステップ1/3）")

        # 対象の会議体を取得
        conf_repo = ConferenceRepository()
        
        if conference_id:
            # 特定の会議体のみ
            conference = conf_repo.get_conference_by_id(conference_id)
            if not conference:
                ConferenceMemberCommands.echo_error(f"会議体ID {conference_id} が見つかりません")
                conf_repo.close()
                return
            conferences = [conference]
        else:
            # URLが設定されている全会議体
            all_conferences = conf_repo.get_all_conferences()
            conferences = [
                conf for conf in all_conferences 
                if conf.get("members_introduction_url")
            ]
            
            if not conferences:
                ConferenceMemberCommands.echo_warning("議員紹介URLが設定されている会議体がありません")
                conf_repo.close()
                return

        ConferenceMemberCommands.echo_info(f"処理対象: {len(conferences)}件の会議体")

        # 抽出器を初期化
        extractor = ConferenceMemberExtractor()
        extracted_repo = ExtractedConferenceMemberRepository()

        # 各会議体を処理
        total_extracted = 0
        total_saved = 0

        with ProgressBar(total=len(conferences)) as progress:
            for conf in conferences:
                progress.update_task(
                    description=f"抽出中: {conf['name']}",
                    advance=0
                )

                # 既存データの処理
                if force:
                    deleted = extracted_repo.delete_extracted_members(conf["id"])
                    if deleted > 0:
                        ConferenceMemberCommands.echo_warning(
                            f"  既存の抽出データ{deleted}件を削除しました"
                        )

                try:
                    # 抽出実行
                    result = asyncio.run(
                        extractor.extract_and_save_members(
                            conference_id=conf["id"],
                            conference_name=conf["name"],
                            url=conf["members_introduction_url"],
                        )
                    )

                    if result.get("error"):
                        ConferenceMemberCommands.echo_error(
                            f"  ❌ エラー: {conf['name']} - {result['error']}"
                        )
                    else:
                        total_extracted += result["extracted_count"]
                        total_saved += result["saved_count"]
                        
                        ConferenceMemberCommands.echo_success(
                            f"  ✓ {conf['name']}: "
                            f"{result['extracted_count']}人を抽出、"
                            f"{result['saved_count']}人を保存"
                        )

                except Exception as e:
                    ConferenceMemberCommands.echo_error(f"  ❌ エラー: {conf['name']} - {str(e)}")
                    logger.exception(f"Error processing conference {conf['id']}")

                progress.update_task(advance=1)

        # 最終結果
        ConferenceMemberCommands.echo_info("\n=== 抽出完了 ===")
        ConferenceMemberCommands.echo_success(f"✅ 抽出総数: {total_extracted}人")
        ConferenceMemberCommands.echo_success(f"✅ 保存総数: {total_saved}人")
        
        # サマリー表示
        summary = extracted_repo.get_extraction_summary()
        ConferenceMemberCommands.echo_info(f"\n📊 ステータス別件数:")
        ConferenceMemberCommands.echo_info(f"  未処理: {summary['pending']}件")
        ConferenceMemberCommands.echo_info(f"  マッチ済: {summary['matched']}件")
        ConferenceMemberCommands.echo_info(f"  該当なし: {summary['no_match']}件")
        ConferenceMemberCommands.echo_info(f"  要確認: {summary['needs_review']}件")

        conf_repo.close()
        extractor.close()
        extracted_repo.close()

    @staticmethod
    @click.command("match-conference-members")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合は全ての未処理データを処理）",
    )
    def match_conference_members(conference_id: int = None):
        """抽出した議員情報を既存の政治家データとマッチング（ステップ2）"""
        
        ConferenceMemberCommands.echo_info("🔍 議員情報のマッチングを開始します（ステップ2/3）")

        # マッチングサービスを初期化
        matching_service = ConferenceMemberMatchingService()

        # 処理実行
        ConferenceMemberCommands.echo_info("LLMを使用して政治家データとマッチングします...")
        
        with ProgressBar() as progress:
            task = progress.add_task("マッチング処理中...", total=None)
            
            results = matching_service.process_pending_members(conference_id)
            
            progress.update(task, completed=True)

        # 結果表示
        ConferenceMemberCommands.echo_info("\n=== マッチング完了 ===")
        ConferenceMemberCommands.echo_info(f"処理総数: {results['total']}件")
        ConferenceMemberCommands.echo_success(f"✅ マッチ成功: {results['matched']}件")
        ConferenceMemberCommands.echo_warning(f"⚠️  要確認: {results['needs_review']}件")
        ConferenceMemberCommands.echo_error(f"❌ 該当なし: {results['no_match']}件")
        
        if results['error'] > 0:
            ConferenceMemberCommands.echo_error(f"❌ エラー: {results['error']}件")

        matching_service.close()

    @staticmethod
    @click.command("create-affiliations")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合は全てのマッチ済データを処理）",
    )
    @click.option(
        "--start-date",
        type=click.DateTime(formats=["%Y-%m-%d"]),
        help="所属開始日（デフォルト: 今日）",
    )
    def create_affiliations(conference_id: int = None, start_date = None):
        """マッチング済みデータから政治家所属情報を作成（ステップ3）"""
        
        ConferenceMemberCommands.echo_info("🏛️ 政治家所属情報の作成を開始します（ステップ3/3）")

        # 開始日の処理
        if start_date:
            start_date = start_date.date()
        else:
            start_date = date.today()

        ConferenceMemberCommands.echo_info(f"所属開始日: {start_date}")

        # マッチングサービスを初期化
        matching_service = ConferenceMemberMatchingService()

        # 処理実行
        with ProgressBar() as progress:
            task = progress.add_task("所属情報作成中...", total=None)
            
            results = matching_service.create_affiliations_from_matched(
                conference_id, start_date
            )
            
            progress.update(task, completed=True)

        # 結果表示
        ConferenceMemberCommands.echo_info("\n=== 所属情報作成完了 ===")
        ConferenceMemberCommands.echo_info(f"処理総数: {results['total']}件")
        ConferenceMemberCommands.echo_success(f"✅ 作成/更新: {results['created']}件")
        
        if results['failed'] > 0:
            ConferenceMemberCommands.echo_error(f"❌ 失敗: {results['failed']}件")

        matching_service.close()

    @staticmethod
    @click.command("member-status")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合は全体のステータスを表示）",
    )
    def member_status(conference_id: int = None):
        """抽出・マッチング状況を表示"""
        
        ConferenceMemberCommands.echo_info("📊 会議体メンバー抽出・マッチング状況")

        extracted_repo = ExtractedConferenceMemberRepository()

        # 全体サマリー
        summary = extracted_repo.get_extraction_summary()
        
        ConferenceMemberCommands.echo_info("\n=== 全体ステータス ===")
        ConferenceMemberCommands.echo_info(f"総件数: {summary['total']}件")
        ConferenceMemberCommands.echo_info(f"  📋 未処理: {summary['pending']}件")
        ConferenceMemberCommands.echo_success(f"  ✅ マッチ済: {summary['matched']}件")
        ConferenceMemberCommands.echo_warning(f"  ⚠️  要確認: {summary['needs_review']}件")
        ConferenceMemberCommands.echo_error(f"  ❌ 該当なし: {summary['no_match']}件")

        # 会議体別の詳細
        if conference_id:
            ConferenceMemberCommands.echo_info(f"\n=== 会議体ID {conference_id} の詳細 ===")
            
            # 未処理メンバー
            pending = extracted_repo.get_pending_members(conference_id)
            if pending:
                ConferenceMemberCommands.echo_info(f"\n📋 未処理メンバー ({len(pending)}人):")
                for member in pending[:10]:  # 最初の10件
                    role = f" ({member['extracted_role']})" if member.get('extracted_role') else ""
                    party = f" - {member['extracted_party_name']}" if member.get('extracted_party_name') else ""
                    ConferenceMemberCommands.echo_info(f"  • {member['extracted_name']}{role}{party}")
                if len(pending) > 10:
                    ConferenceMemberCommands.echo_info(f"  ... 他 {len(pending) - 10}人")

            # マッチ済みメンバー
            matched = extracted_repo.get_matched_members(conference_id)
            if matched:
                ConferenceMemberCommands.echo_success(f"\n✅ マッチ済みメンバー ({len(matched)}人):")
                for member in matched[:10]:  # 最初の10件
                    role = f" ({member['extracted_role']})" if member.get('extracted_role') else ""
                    ConferenceMemberCommands.echo_success(
                        f"  • {member['extracted_name']}{role} "
                        f"→ {member['politician_name']} "
                        f"(信頼度: {member['matching_confidence']:.2f})"
                    )
                if len(matched) > 10:
                    ConferenceMemberCommands.echo_success(f"  ... 他 {len(matched) - 10}人")

        extracted_repo.close()


def get_conference_member_commands():
    """Get conference member command group"""
    return ConferenceMemberCommands().get_commands()