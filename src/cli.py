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

if __name__ == '__main__':
    cli()