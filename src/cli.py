"""Unified CLI for Polibase - Political Meeting Minutes Processing System"""
import click
import sys
import os

# Add parent directory to path to ensure imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@click.group()
def cli():
    """Polibase - 政治活動追跡アプリケーション
    
    A unified command-line interface for processing political meeting minutes,
    extracting politician information, and managing speaker data.
    """
    pass

@cli.command()
@click.option('--pdf', default='data/minutes.pdf', help='Path to the PDF file containing meeting minutes')
@click.option('--output', default='data/output/meeting_output.csv', help='Output CSV file path')
def process_minutes(pdf, output):
    """Process meeting minutes to extract conversations (議事録分割処理)
    
    This command reads a PDF file containing meeting minutes and extracts
    individual speeches/conversations using LLM processing.
    """
    from src.process_minutes import main
    click.echo(f"Processing minutes from: {pdf}")
    click.echo(f"Output will be saved to: {output}")
    main()

@cli.command()
@click.option('--pdf', default='data/minutes.pdf', help='Path to the PDF file containing meeting minutes')
@click.option('--output', default='data/output/politician_output.csv', help='Output CSV file path')
def extract_politicians(pdf, output):
    """Extract politician information from minutes (政治家抽出処理)
    
    This command processes meeting minutes to identify and extract
    information about politicians who spoke during the meetings.
    """
    from src.extract_politicians import main
    click.echo(f"Extracting politicians from: {pdf}")
    click.echo(f"Output will be saved to: {output}")
    main()

@cli.command()
@click.option('--use-llm', is_flag=True, help='Use LLM for fuzzy matching')
@click.option('--interactive/--no-interactive', default=True, help='Enable interactive confirmation')
def update_speakers(use_llm, interactive):
    """Update speaker links in database (発言者紐付け更新)
    
    This command links conversations to speaker records. Use --use-llm
    for advanced fuzzy matching with Google Gemini API.
    """
    if use_llm:
        click.echo("Using LLM-based speaker matching...")
        from update_speaker_links_llm import main
        main()
    else:
        click.echo("Using rule-based speaker matching...")
        from update_speaker_links import main
        main()

@cli.command()
def test_connection():
    """Test database connection (データベース接続テスト)"""
    from src.config.database import test_connection as test_db
    click.echo("Testing database connection...")
    try:
        test_db()
        click.echo("✓ Database connection successful!")
    except Exception as e:
        click.echo(f"✗ Database connection failed: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('action', type=click.Choice(['backup', 'restore', 'list']))
@click.argument('filename', required=False)
def database(action, filename):
    """Database management commands (データベース管理)
    
    Actions:
    - backup: Create a new backup
    - restore: Restore from a backup file
    - list: List available backups
    """
    import subprocess
    
    if action == 'backup':
        click.echo("Creating database backup...")
        subprocess.run(['./backup-database.sh', 'backup'])
    elif action == 'restore':
        if not filename:
            click.echo("Error: filename required for restore", err=True)
            sys.exit(1)
        click.echo(f"Restoring from backup: {filename}")
        subprocess.run(['./backup-database.sh', 'restore', filename])
    elif action == 'list':
        subprocess.run(['./backup-database.sh', 'list'])

@cli.command()
def reset_database():
    """Reset database to initial state (データベースリセット)
    
    WARNING: This will delete all data and restore to initial state!
    """
    if click.confirm('Are you sure you want to reset the database? This will delete all data!'):
        import subprocess
        subprocess.run(['./reset-database.sh'])
        click.echo("Database reset complete.")
    else:
        click.echo("Database reset cancelled.")

@cli.command()
@click.option('--port', default=8501, help='Port number for Streamlit app')
@click.option('--host', default='0.0.0.0', help='Host address')
def streamlit(port, host):
    """Launch Streamlit web interface for meeting management (会議管理Web UI)
    
    This command starts a web interface where you can:
    - View all registered meetings
    - Add new meetings with URLs and dates
    - Edit existing meeting information
    - Delete meetings
    - Manage political party member list URLs
    """
    import subprocess
    import os
    
    # Docker環境での実行を考慮
    if host == '0.0.0.0':
        access_url = f"http://localhost:{port}"
    else:
        access_url = f"http://{host}:{port}"
    
    click.echo(f"Starting Streamlit app...")
    click.echo(f"Access the app at: {access_url}")
    click.echo("Press Ctrl+C to stop the server")
    
    # Streamlitアプリケーションを起動
    subprocess.run([
        sys.executable, '-m', 'streamlit', 'run',
        'src/streamlit_app.py',
        '--server.port', str(port),
        '--server.address', host,
        '--server.headless', 'true'  # Dockerでの実行に必要
    ])

@cli.command()
@click.argument('url')
@click.option('--output-dir', default='data/scraped', help='Output directory for scraped content')
@click.option('--format', type=click.Choice(['txt', 'json', 'both']), default='both', help='Output format')
@click.option('--no-cache', is_flag=True, help='Ignore cache and force re-scraping')
@click.option('--upload-to-gcs', is_flag=True, help='Upload scraped files to Google Cloud Storage')
@click.option('--gcs-bucket', help='GCS bucket name (overrides environment variable)')
def scrape_minutes(url, output_dir, format, no_cache, upload_to_gcs, gcs_bucket):
    """Scrape meeting minutes from council website (議事録Web取得)
    
    This command fetches meeting minutes from supported council websites
    and saves them as text or JSON files.
    
    Example:
        polibase scrape-minutes "https://ssp.kaigiroku.net/tenant/kyoto/MinuteView.html?council_id=6030&schedule_id=1"
    """
    import asyncio
    from src.web_scraper.scraper_service import ScraperService
    from pathlib import Path
    
    click.echo(f"Scraping minutes from: {url}")
    
    # GCS設定の上書き
    if gcs_bucket:
        import os
        os.environ['GCS_BUCKET_NAME'] = gcs_bucket
    
    # サービス初期化
    service = ScraperService(enable_gcs=upload_to_gcs)
    
    # スクレイピング実行
    async def scrape():
        minutes = await service.fetch_from_url(url, use_cache=not no_cache)
        if not minutes:
            click.echo("Failed to scrape minutes", err=True)
            return False
        
        # 出力ディレクトリ作成
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # ファイル名生成
        base_name = f"{minutes.council_id}_{minutes.schedule_id}"
        
        # テキスト形式で保存
        if format in ['txt', 'both']:
            txt_path = output_path / f"{base_name}.txt"
            success, gcs_url = service.export_to_text(minutes, str(txt_path), upload_to_gcs=upload_to_gcs)
            if success:
                click.echo(f"Saved text to: {txt_path}")
                if gcs_url:
                    click.echo(f"Uploaded to GCS: {gcs_url}")
            else:
                click.echo("Failed to save text file", err=True)
        
        # JSON形式で保存
        if format in ['json', 'both']:
            json_path = output_path / f"{base_name}.json"
            success, gcs_url = service.export_to_json(minutes, str(json_path), upload_to_gcs=upload_to_gcs)
            if success:
                click.echo(f"Saved JSON to: {json_path}")
                if gcs_url:
                    click.echo(f"Uploaded to GCS: {gcs_url}")
            else:
                click.echo("Failed to save JSON file", err=True)
        
        # PDFをGCSにアップロード（PDFがローカルに保存されている場合）
        if upload_to_gcs and minutes.pdf_url:
            pdf_path = output_path / f"{base_name}.pdf"
            if pdf_path.exists():
                gcs_url = service.upload_pdf_to_gcs(str(pdf_path), minutes)
                if gcs_url:
                    click.echo(f"Uploaded PDF to GCS: {gcs_url}")
        
        # 基本情報を表示
        click.echo("\n--- Minutes Summary ---")
        click.echo(f"Title: {minutes.title}")
        click.echo(f"Date: {minutes.date.strftime('%Y年%m月%d日') if minutes.date else 'Unknown'}")
        click.echo(f"Speakers found: {len(minutes.speakers)}")
        click.echo(f"Content length: {len(minutes.content)} characters")
        if minutes.pdf_url:
            click.echo(f"PDF URL: {minutes.pdf_url}")
        
        return True
    
    # 非同期実行
    success = asyncio.run(scrape())
    sys.exit(0 if success else 1)

@cli.command()
@click.option('--tenant', required=True, help='Tenant name in kaigiroku.net (e.g., kyoto, osaka, kobe)')
@click.option('--start-id', default=6000, help='Start council ID')
@click.option('--end-id', default=6100, help='End council ID')
@click.option('--max-schedule', default=10, help='Maximum schedule ID to try')
@click.option('--output-dir', default='data/scraped/batch', help='Output directory')
@click.option('--concurrent', default=3, help='Number of concurrent requests')
@click.option('--upload-to-gcs', is_flag=True, help='Upload scraped files to Google Cloud Storage')
@click.option('--gcs-bucket', help='GCS bucket name (overrides environment variable)')
def batch_scrape(tenant, start_id, end_id, max_schedule, output_dir, concurrent, upload_to_gcs, gcs_bucket):
    """Batch scrape multiple meeting minutes from kaigiroku.net (議事録一括取得)
    
    This command tries to scrape multiple meeting minutes from kaigiroku.net
    by iterating through council and schedule IDs.
    
    Examples:
        polibase batch-scrape --tenant kyoto --start-id 6000 --end-id 6010
        polibase batch-scrape --tenant osaka --start-id 1000 --end-id 1100
    """
    import asyncio
    from src.web_scraper.scraper_service import ScraperService
    from pathlib import Path
    
    click.echo(f"Batch scraping from kaigiroku.net tenant: {tenant}")
    click.echo(f"Council IDs: {start_id} to {end_id}")
    click.echo(f"Schedule IDs: 1 to {max_schedule}")
    
    # URL生成
    base_url = f"https://ssp.kaigiroku.net/tenant/{tenant}/MinuteView.html"
    urls = []
    for council_id in range(start_id, end_id + 1):
        for schedule_id in range(1, max_schedule + 1):
            url = f"{base_url}?council_id={council_id}&schedule_id={schedule_id}"
            urls.append(url)
    
    click.echo(f"Total URLs to try: {len(urls)}")
    
    if not click.confirm('Do you want to continue?'):
        return
    
    # GCS設定の上書き
    if gcs_bucket:
        import os
        os.environ['GCS_BUCKET_NAME'] = gcs_bucket
    
    # サービス初期化
    service = ScraperService(enable_gcs=upload_to_gcs)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # バッチ処理実行
    async def batch_process():
        results = await service.fetch_multiple(urls, max_concurrent=concurrent)
        
        success_count = 0
        for minutes in results:
            if minutes:
                # テキストとJSONで保存
                base_name = f"{minutes.council_id}_{minutes.schedule_id}"
                txt_path = output_path / f"{base_name}.txt"
                json_path = output_path / f"{base_name}.json"
                
                # テキスト形式で保存（GCS対応）
                txt_success, txt_gcs_url = service.export_to_text(minutes, str(txt_path), upload_to_gcs=upload_to_gcs)
                
                # JSON形式で保存（GCS対応）
                json_success, json_gcs_url = service.export_to_json(minutes, str(json_path), upload_to_gcs=upload_to_gcs)
                
                if txt_success and json_success:
                    success_count += 1
                    if txt_gcs_url or json_gcs_url:
                        click.echo(f"Scraped and uploaded: {base_name}")
        
        click.echo(f"\nCompleted: {success_count}/{len(urls)} URLs successfully scraped")
        return success_count
    
    # 非同期実行
    success_count = asyncio.run(batch_process())
    click.echo(f"Saved {success_count} meeting minutes to {output_path}")

@cli.command()
@click.option('--party-id', type=int, help='Specific party ID to scrape')
@click.option('--all-parties', is_flag=True, help='Scrape all parties with member list URLs')
@click.option('--dry-run', is_flag=True, help='Show what would be scraped without saving')
@click.option('--max-pages', default=10, help='Maximum pages to fetch per party')
def scrape_politicians(party_id, all_parties, dry_run, max_pages):
    """Scrape politician data from party member list pages (政党議員一覧取得)
    
    This command fetches politician information from political party websites
    using LLM to extract structured data and saves them to the database.
    
    Examples:
        polibase scrape-politicians --party-id 1
        polibase scrape-politicians --all-parties
        polibase scrape-politicians --all-parties --dry-run
    """
    import asyncio
    from sqlalchemy import text
    from src.config.database import get_db_engine
    from src.party_member_extractor.html_fetcher import PartyMemberPageFetcher
    from src.party_member_extractor.extractor import PartyMemberExtractor
    from src.database.politician_repository import PoliticianRepository
    
    engine = get_db_engine()
    
    # 対象の政党を取得
    with engine.connect() as conn:
        if party_id:
            query = text("""
                SELECT id, name, members_list_url 
                FROM political_parties 
                WHERE id = :party_id AND members_list_url IS NOT NULL
            """)
            result = conn.execute(query, {"party_id": party_id})
        else:
            query = text("""
                SELECT id, name, members_list_url 
                FROM political_parties 
                WHERE members_list_url IS NOT NULL
                ORDER BY name
            """)
            result = conn.execute(query)
        
        parties = result.fetchall()
    
    if not parties:
        click.echo("No parties found with member list URLs", err=True)
        return
    
    click.echo(f"Found {len(parties)} parties to scrape:")
    for party in parties:
        click.echo(f"  - {party.name}: {party.members_list_url}")
    
    if not click.confirm('\nDo you want to continue?'):
        return
    
    # スクレイピング実行
    async def scrape_all():
        total_scraped = 0
        
        # HTMLフェッチャーとエクストラクターを初期化
        extractor = PartyMemberExtractor()
        
        async with PartyMemberPageFetcher() as fetcher:
            for party in parties:
                click.echo(f"\nProcessing {party.name}...")
                click.echo(f"  URL: {party.members_list_url}")
                
                # HTMLページを取得（ページネーション対応）
                click.echo(f"  Fetching pages (max: {max_pages})...")
                pages = await fetcher.fetch_all_pages(party.members_list_url, max_pages=max_pages)
                
                if not pages:
                    click.echo(f"  Failed to fetch pages for {party.name}")
                    continue
                
                click.echo(f"  Fetched {len(pages)} pages")
                
                # LLMで議員情報を抽出
                click.echo("  Extracting member information using LLM...")
                result = extractor.extract_from_pages(pages, party.name)
                
                if not result or not result.members:
                    click.echo(f"  No members found for {party.name}")
                    continue
                
                click.echo(f"  Extracted {len(result.members)} members")
                
                if dry_run:
                    # ドライランモード：データを表示するだけ
                    for member in result.members[:5]:  # 最初の5件を表示
                        click.echo(f"    - {member.name}")
                        if member.position:
                            click.echo(f"      Position: {member.position}")
                        if member.electoral_district:
                            click.echo(f"      District: {member.electoral_district}")
                        if member.prefecture:
                            click.echo(f"      Prefecture: {member.prefecture}")
                        if member.party_position:
                            click.echo(f"      Party Role: {member.party_position}")
                    if len(result.members) > 5:
                        click.echo(f"    ... and {len(result.members) - 5} more")
                else:
                    # データベースに保存
                    repo = PoliticianRepository()
                    
                    # Pydanticモデルを辞書に変換してpolitical_party_idを追加
                    members_data = []
                    for member in result.members:
                        member_dict = member.model_dump()
                        member_dict['political_party_id'] = party.id
                        members_data.append(member_dict)
                    
                    created_ids = repo.bulk_create_politicians(members_data)
                    repo.close()
                    
                    click.echo(f"  Saved {len(created_ids)} politicians to database")
                    total_scraped += len(created_ids)
        
        return total_scraped
    
    # 非同期実行
    total = asyncio.run(scrape_all())
    
    if not dry_run:
        click.echo(f"\nTotal politicians saved: {total}")
    
    engine.dispose()


if __name__ == '__main__':
    cli()