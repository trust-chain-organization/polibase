#!/usr/bin/env python
"""システムヘルスチェック"""

import os
import shutil
import subprocess
from datetime import datetime

from sqlalchemy import text

from src.config.database import get_db_engine


def check_database_health():
    """データベースヘルスチェック"""
    print("=" * 60)
    print("データベースヘルスチェック")
    print("=" * 60)

    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            # 接続数
            result = conn.execute(
                text("""
                SELECT count(*) as total,
                       count(*) FILTER (WHERE state = 'active') as active,
                       count(*) FILTER (WHERE state = 'idle') as idle
                FROM pg_stat_activity
                WHERE datname = 'polibase_db'
            """)
            )
            total, active, idle = result.fetchone()

            print("\n接続状態:")
            print(f"  総接続数: {total}")
            print(f"  アクティブ: {active}")
            print(f"  アイドル: {idle}")

            # 長時間実行クエリ
            result = conn.execute(
                text("""
                SELECT pid, usename,
                       age(clock_timestamp(), query_start) as runtime,
                       substr(query, 1, 60) as query_snippet
                FROM pg_stat_activity
                WHERE state = 'active'
                  AND query_start < clock_timestamp() - interval '1 minute'
                ORDER BY runtime DESC
                LIMIT 5
            """)
            )

            long_queries = result.fetchall()
            if long_queries:
                print("\n長時間実行クエリ:")
                for pid, user, runtime, query in long_queries:
                    print(f"  PID {pid} ({user}): {runtime} - {query}...")

            # デッドロック
            result = conn.execute(
                text("""
                SELECT count(*)
                FROM pg_stat_database
                WHERE datname = 'polibase_db'
                  AND deadlocks > 0
            """)
            )
            deadlock_count = result.fetchone()[0]

            if deadlock_count > 0:
                print(f"\n⚠️  デッドロック検出: {deadlock_count}件")
            else:
                print("\n✓ デッドロック: なし")

            return True

    except Exception as e:
        print(f"✗ エラー: {e}")
        return False


def check_docker_health():
    """Dockerコンテナヘルスチェック"""
    print(f"\n{'=' * 60}")
    print("Dockerコンテナヘルスチェック")
    print("=" * 60)

    # Dockerコンテナ内で実行されている場合はスキップ
    if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
        print("✓ Dockerコンテナ内で実行中")
        return True

    try:
        # docker compose ps の実行
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"✗ Docker Composeエラー: {result.stderr}")
            return False

        # 各コンテナの状態を解析
        containers = []
        for line in result.stdout.strip().split("\n"):
            if line:
                import json

                container = json.loads(line)
                containers.append(container)

        print(f"\nコンテナ数: {len(containers)}")

        all_healthy = True
        for container in containers:
            name = container.get("Name", "unknown")
            state = container.get("State", "unknown")
            health = container.get("Health", "none")

            if state == "running":
                status = "✓"
            else:
                status = "✗"
                all_healthy = False

            print(f"{status} {name}: {state} (health: {health})")

        return all_healthy

    except Exception as e:
        print(f"✗ エラー: {e}")
        return False


def check_disk_space():
    """ディスク容量チェック"""
    print(f"\n{'=' * 60}")
    print("ディスク容量チェック")
    print("=" * 60)

    # shutil.disk_usage を使用してディスク使用状況を取得
    try:
        disk_usage = shutil.disk_usage(".")

        total_gb = disk_usage.total / (1024**3)
        used_gb = disk_usage.used / (1024**3)
        free_gb = disk_usage.free / (1024**3)
        usage_percent = (disk_usage.used / disk_usage.total) * 100

        print("\nプロジェクトディレクトリ:")
        print(f"  総容量: {total_gb:.1f} GB")
        print(f"  使用量: {used_gb:.1f} GB")
        print(f"  空き容量: {free_gb:.1f} GB")
        print(f"  使用率: {usage_percent:.1f}%")

        if usage_percent > 90:
            print("\n⚠️  警告: ディスク使用率が90%を超えています")
            return False
        elif usage_percent > 80:
            print("\n⚠️  注意: ディスク使用率が80%を超えています")
        else:
            print("\n✓ ディスク容量: 十分な空きがあります")

        # 主要ディレクトリのサイズ
        print("\n主要ディレクトリサイズ:")
        directories = ["data", "database/backups", ".git"]

        for dir_name in directories:
            if os.path.exists(dir_name):
                size = get_directory_size(dir_name)
                print(f"  {dir_name}: {size / (1024**2):.1f} MB")

        return True

    except Exception as e:
        print(f"✗ ディスク容量の取得に失敗: {e}")
        return False


def get_directory_size(path):
    """ディレクトリサイズを取得"""
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total += os.path.getsize(filepath)
            except OSError:
                pass
    return total


def check_environment_variables():
    """環境変数チェック"""
    print(f"\n{'=' * 60}")
    print("環境変数チェック")
    print("=" * 60)

    required_vars = [
        "DATABASE_URL",
        "GOOGLE_API_KEY",
    ]

    optional_vars = [
        "GCS_BUCKET_NAME",
        "GCS_UPLOAD_ENABLED",
    ]

    all_required_present = True

    print("\n必須環境変数:")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 秘密情報は最初の数文字のみ表示
            if "KEY" in var or "PASSWORD" in var:
                display_value = value[:4] + "****"
            else:
                display_value = value[:20] + "..." if len(value) > 20 else value
            print(f"  ✓ {var}: {display_value}")
        else:
            print(f"  ✗ {var}: 未設定")
            all_required_present = False

    print("\nオプション環境変数:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✓ {var}: {value}")
        else:
            print(f"  - {var}: 未設定")

    return all_required_present


def generate_health_report():
    """ヘルスレポートの生成"""
    print("\n" + "=" * 80)
    print("システムヘルスレポート")
    print("=" * 80)
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    checks = [
        ("環境変数", check_environment_variables()),
        ("Docker", check_docker_health()),
        ("データベース", check_database_health()),
        ("ディスク容量", check_disk_space()),
    ]

    print("\n" + "=" * 80)
    print("総合判定")
    print("=" * 80)

    all_passed = all(result for _, result in checks)

    for check_name, result in checks:
        status = "✓" if result else "✗"
        print(f"{status} {check_name}")

    if all_passed:
        print("\n✓ システムは正常に動作しています")
        return 0
    else:
        print("\n✗ 一部のチェックで問題が検出されました")
        return 1


if __name__ == "__main__":
    import sys

    sys.exit(generate_health_report())
