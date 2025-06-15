#!/usr/bin/env python
"""データベース管理機能の詳細テスト"""

import subprocess
from datetime import datetime
from pathlib import Path

from src.config.database import get_connection


def test_connection():
    """データベース接続テスト"""
    print("=" * 60)
    print("データベース接続テスト")
    print("=" * 60)

    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            print("✓ 接続成功")
            print(f"PostgreSQL バージョン: {version}")

            # 現在のデータベース情報
            cursor.execute("SELECT current_database(), current_user")
            db_name, user = cursor.fetchone()
            print(f"データベース: {db_name}")
            print(f"ユーザー: {user}")

        return True
    except Exception as e:
        print(f"✗ 接続失敗: {e}")
        return False


def test_table_structure():
    """テーブル構造の確認"""
    print(f"\n{'=' * 60}")
    print("テーブル構造の確認")
    print("=" * 60)

    with get_connection() as conn:
        cursor = conn.cursor()

        # テーブル一覧
        cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]

        print(f"\nテーブル数: {len(tables)}")

        # 各テーブルの情報
        for table in tables:
            cursor.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """,
                (table,),
            )

            columns = cursor.fetchall()

            # レコード数
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]

            print(f"\n{table} ({count:,} records):")
            for col_name, data_type, nullable, _default in columns[
                :3
            ]:  # 最初の3カラムのみ表示
                null_str = "NULL" if nullable == "YES" else "NOT NULL"
                print(f"  - {col_name}: {data_type} {null_str}")
            if len(columns) > 3:
                print(f"  ... 他 {len(columns) - 3} カラム")


def test_data_statistics():
    """データ統計の確認"""
    print(f"\n{'=' * 60}")
    print("データ統計")
    print("=" * 60)

    with get_connection() as conn:
        cursor = conn.cursor()

        # 主要テーブルの統計

        # 政治家統計
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT political_party_id) as parties,
                   COUNT(DISTINCT prefecture) as prefectures
            FROM politicians
        """)
        pol_total, pol_parties, pol_prefectures = cursor.fetchone()

        print("\n政治家データ:")
        print(f"  総数: {pol_total:,}名")
        print(f"  政党数: {pol_parties}")
        print(f"  都道府県数: {pol_prefectures}")

        # 会議統計
        cursor.execute("""
            SELECT COUNT(*) as total,
                   MIN(date) as oldest,
                   MAX(date) as newest,
                   COUNT(DISTINCT conference_id) as conferences
            FROM meetings
        """)
        meet_total, oldest, newest, conferences = cursor.fetchone()

        print("\n会議データ:")
        print(f"  総数: {meet_total:,}件")
        if oldest:
            print(f"  期間: {oldest} 〜 {newest}")
            print(f"  会議体数: {conferences}")

        # 発言統計
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT meeting_id) as meetings,
                   COUNT(DISTINCT speaker_id) as speakers
            FROM conversations
        """)
        conv_total, conv_meetings, conv_speakers = cursor.fetchone()

        print("\n発言データ:")
        print(f"  総数: {conv_total:,}件")
        print(f"  会議数: {conv_meetings}")
        print(f"  発言者数: {conv_speakers}")

        # データ成長率（過去30日）
        cursor.execute("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as count
            FROM meetings
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date
        """)

        growth_data = cursor.fetchall()
        if growth_data:
            print("\n過去30日のデータ増加:")
            total_new = sum(row[1] for row in growth_data)
            print(f"  新規会議: {total_new}件")
            print(f"  日平均: {total_new / 30:.1f}件")


def test_backup_operations():
    """バックアップ操作のテスト"""
    print(f"\n{'=' * 60}")
    print("バックアップ操作テスト")
    print("=" * 60)

    backup_dir = Path("database/backups")
    backup_dir.mkdir(parents=True, exist_ok=True)

    # テストバックアップの作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    test_backup_name = f"test_backup_{timestamp}.sql"

    print(f"\nテストバックアップを作成: {test_backup_name}")

    try:
        # pg_dumpコマンドの実行
        result = subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "postgres",
                "pg_dump",
                "-U",
                "polibase_user",
                "-d",
                "polibase_db",
                "--no-owner",
                "--no-acl",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # バックアップファイルに保存
            backup_path = backup_dir / test_backup_name
            with open(backup_path, "w") as f:
                f.write(result.stdout)

            file_size = backup_path.stat().st_size
            print("✓ バックアップ作成成功")
            print(f"  ファイルサイズ: {file_size / 1024 / 1024:.1f} MB")

            # バックアップの検証
            with open(backup_path) as f:
                content = f.read()
                table_count = content.count("CREATE TABLE")
                print(f"  テーブル数: {table_count}")

            # クリーンアップ
            backup_path.unlink()
            print("  テストファイルを削除しました")

        else:
            print(f"✗ バックアップ失敗: {result.stderr}")

    except Exception as e:
        print(f"✗ エラー: {e}")


def test_migration_status():
    """マイグレーション状態の確認"""
    print(f"\n{'=' * 60}")
    print("マイグレーション状態")
    print("=" * 60)

    migrations_dir = Path("database/migrations")

    # マイグレーションファイル一覧
    migration_files = sorted(migrations_dir.glob("*.sql"))
    print(f"\nマイグレーションファイル数: {len(migration_files)}")

    with get_connection() as conn:
        cursor = conn.cursor()

        for migration_file in migration_files:
            filename = migration_file.name

            # マイグレーションが適用されているかの簡易チェック
            # （実際にはマイグレーション管理テーブルが必要）
            if "create_parliamentary_groups" in filename:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables
                        WHERE table_name = 'parliamentary_groups'
                    )
                """)
                exists = cursor.fetchone()[0]
                status = "✓" if exists else "✗"
            elif "add_gcs_uri" in filename:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'meetings'
                        AND column_name = 'gcs_pdf_uri'
                    )
                """)
                exists = cursor.fetchone()[0]
                status = "✓" if exists else "✗"
            else:
                status = "?"

            print(f"{status} {filename}")


def test_data_integrity():
    """データ整合性チェック"""
    print(f"\n{'=' * 60}")
    print("データ整合性チェック")
    print("=" * 60)

    with get_connection() as conn:
        cursor = conn.cursor()

        integrity_issues = []

        # 1. 孤立レコードのチェック
        print("\n1. 孤立レコードチェック:")

        # speaker_idが存在しない会話
        cursor.execute("""
            SELECT COUNT(*)
            FROM conversations c
            WHERE c.speaker_id IS NOT NULL
              AND NOT EXISTS (
                  SELECT 1 FROM speakers s
                  WHERE s.id = c.speaker_id
              )
        """)
        orphaned_conversations = cursor.fetchone()[0]

        if orphaned_conversations > 0:
            print(f"  ✗ 孤立した会話: {orphaned_conversations}件")
            integrity_issues.append("orphaned_conversations")
        else:
            print("  ✓ 孤立した会話: なし")

        # 2. 必須フィールドのNULLチェック
        print("\n2. 必須フィールドチェック:")

        null_checks = [
            ("politicians", "name"),
            ("meetings", "date"),
            ("conferences", "name"),
            ("political_parties", "name"),
        ]

        for table, column in null_checks:
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM {table}
                WHERE {column} IS NULL
            """)
            null_count = cursor.fetchone()[0]

            if null_count > 0:
                print(f"  ✗ {table}.{column}: {null_count}件のNULL")
                integrity_issues.append(f"{table}.{column}_null")
            else:
                print(f"  ✓ {table}.{column}: NULLなし")

        # 3. 日付の妥当性チェック
        print("\n3. 日付妥当性チェック:")

        cursor.execute("""
            SELECT COUNT(*)
            FROM meetings
            WHERE date > CURRENT_DATE + INTERVAL '1 year'
               OR date < '1900-01-01'
        """)
        invalid_dates = cursor.fetchone()[0]

        if invalid_dates > 0:
            print(f"  ✗ 無効な日付: {invalid_dates}件")
            integrity_issues.append("invalid_dates")
        else:
            print("  ✓ 日付: すべて有効")

        # 総合判定
        print("\n総合判定:")
        if not integrity_issues:
            print("✓ データ整合性: 問題なし")
        else:
            print(f"✗ {len(integrity_issues)}件の問題が検出されました")


def test_performance_metrics():
    """パフォーマンスメトリクス"""
    print(f"\n{'=' * 60}")
    print("パフォーマンスメトリクス")
    print("=" * 60)

    with get_connection() as conn:
        cursor = conn.cursor()

        # データベースサイズ
        cursor.execute("""
            SELECT
                pg_database_size('polibase_db') as total_size,
                pg_size_pretty(pg_database_size('polibase_db')) as pretty_size
        """)
        total_size, pretty_size = cursor.fetchone()

        print(f"\nデータベースサイズ: {pretty_size}")

        # テーブル別サイズ
        cursor.execute("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(
                    pg_total_relation_size(schemaname||'.'||tablename)
                ) as size,
                pg_total_relation_size(schemaname||'.'||tablename) as bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 5
        """)

        print("\nテーブルサイズ（上位5件）:")
        for _schema, table, size, bytes in cursor.fetchall():
            percentage = bytes / total_size * 100 if total_size > 0 else 0
            print(f"  {table}: {size} ({percentage:.1f}%)")

        # インデックス使用状況
        cursor.execute("""
            SELECT
                schemaname,
                tablename,
                indexname,
                idx_scan,
                idx_tup_read,
                idx_tup_fetch
            FROM pg_stat_user_indexes
            WHERE idx_scan > 0
            ORDER BY idx_scan DESC
            LIMIT 5
        """)

        print("\nインデックス使用状況（上位5件）:")
        indexes = cursor.fetchall()
        for _schema, table, index, scans, _read, _fetch in indexes:
            print(f"  {index} ({table}): {scans:,} scans")


def run_full_test():
    """完全なテストの実行"""
    print("=" * 80)
    print("データベース管理機能 - 完全テスト")
    print("=" * 80)

    # 1. 接続テスト
    if not test_connection():
        print("\n接続に失敗したため、テストを中止します")
        return

    # 2. テーブル構造
    test_table_structure()

    # 3. データ統計
    test_data_statistics()

    # 4. バックアップ操作
    test_backup_operations()

    # 5. マイグレーション状態
    test_migration_status()

    # 6. データ整合性
    test_data_integrity()

    # 7. パフォーマンス
    test_performance_metrics()

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == "__main__":
    run_full_test()
