"""Commands for managing politician affiliations"""

import asyncio
import logging

import click

from src.cli_package.base import CLIBase
from src.cli_package.progress import ProgressBar
from src.conference_member_scraper.affiliation_service import AffiliationService
from src.conference_member_scraper.scraper import ConferenceMemberScraper
from src.database.conference_repository import ConferenceRepository

logger = logging.getLogger(__name__)


class AffiliationCommands(CLIBase):
    """Commands for managing politician affiliations"""

    def get_commands(self) -> list[click.Command]:
        """Get list of affiliation commands"""
        return [self.scrape_conference_members]

    @click.command("scrape-conference-members")
    @click.option(
        "--conference-id",
        type=int,
        help="会議体ID（指定しない場合はURLが設定されている全会議体を処理）",
    )
    @click.option(
        "--dry-run",
        is_flag=True,
        help="実際にはデータベースに保存せず、抽出結果のみ表示",
    )
    @click.pass_context
    def scrape_conference_members(ctx, conference_id: int = None, dry_run: bool = False):
        """会議体の議員紹介URLから所属情報を抽出してデータベースに保存"""
        
        self = ctx.obj
        self.echo_info("🏛️ 会議体メンバー情報の抽出を開始します")

        # 対象の会議体を取得
        conf_repo = ConferenceRepository()
        
        if conference_id:
            # 特定の会議体のみ
            conferences = [conf_repo.get_conference_by_id(conference_id)]
            if not conferences[0]:
                self.echo_error(f"会議体ID {conference_id} が見つかりません")
                return
        else:
            # URLが設定されている全会議体
            all_conferences = conf_repo.get_all_conferences()
            conferences = [
                conf for conf in all_conferences 
                if conf.get("members_introduction_url")
            ]
            
            if not conferences:
                self.echo_warning("議員紹介URLが設定されている会議体がありません")
                return

        self.echo_info(f"処理対象: {len(conferences)}件の会議体")

        # ドライランモード
        if dry_run:
            self.echo_warning("ドライランモード: データベースには保存されません")

        # 各会議体を処理
        total_results = {
            "created": 0,
            "updated": 0,
            "failed": 0,
            "not_found": 0,
        }

        scraper = ConferenceMemberScraper()
        service = AffiliationService()

        with ProgressBar(total=len(conferences)) as progress:
            for conf in conferences:
                progress.update_task(
                    description=f"処理中: {conf['name']}",
                    advance=0
                )

                try:
                    # スクレイピング実行
                    member_list = asyncio.run(
                        scraper.scrape_conference_members(
                            conference_id=conf["id"],
                            conference_name=conf["name"],
                            url=conf["members_introduction_url"],
                        )
                    )

                    self.echo_info(
                        f"\n{conf['name']}から{len(member_list.members)}人の"
                        f"メンバーを抽出しました"
                    )

                    # 抽出結果を表示
                    for member in member_list.members:
                        role_str = f" ({member.role})" if member.role else ""
                        party_str = f" - {member.party_name}" if member.party_name else ""
                        self.echo_success(f"  ✓ {member.name}{role_str}{party_str}")

                    # ドライランでなければDBに保存
                    if not dry_run:
                        results = service.create_affiliations_from_members(member_list)
                        
                        # 結果を集計
                        for key in total_results:
                            total_results[key] += results[key]

                        # 結果を表示
                        self.echo_info(
                            f"  → 作成: {results['created']}, "
                            f"更新: {results['updated']}, "
                            f"失敗: {results['failed']}, "
                            f"政治家未登録: {results['not_found']}"
                        )

                except Exception as e:
                    self.echo_error(f"エラー: {conf['name']} - {str(e)}")
                    logger.exception(f"Error processing conference {conf['id']}")
                    total_results["failed"] += 1

                progress.update_task(advance=1)

        # 最終結果
        self.echo_info("\n=== 処理完了 ===")
        if not dry_run:
            self.echo_success(f"✅ 作成: {total_results['created']}件")
            self.echo_warning(f"⚠️  更新: {total_results['updated']}件")
            self.echo_error(f"❌ 失敗: {total_results['failed']}件")
            self.echo_warning(f"❓ 政治家未登録: {total_results['not_found']}件")

        conf_repo.close()


def get_affiliation_commands():
    """Get affiliation command group"""
    return AffiliationCommands().get_commands()