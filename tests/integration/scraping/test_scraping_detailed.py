#!/usr/bin/env python
"""スクレイピング機能の詳細テスト"""

import asyncio
import os
import time
from datetime import datetime

from src.config.database import get_db_engine
from src.utils.gcs_storage import GCSStorage
from src.web_scraper.kaigiroku_net_scraper import KaigirokuNetScraper
from src.web_scraper.kokkai_scraper import KokkaiScraper
from src.web_scraper.scraper_service import ScraperService


def test_kaigiroku_scraping():
    """kaigiroku.netスクレイピングのテスト"""
    print("=" * 60)
    print("kaigiroku.net スクレイピングテスト")
    print("=" * 60)

    # テストURL
    test_urls = [
        "https://ssp.kaigiroku.net/tenant/kyoto/SpMinuteView.html?council_id=1&schedule_id=1",
        # 他のテストURLを追加
    ]

    scraper = KaigirokuNetScraper()

    for url in test_urls:
        print(f"\nテストURL: {url}")

        try:
            print("スクレイピング開始...")
            start_time = time.time()

            result = asyncio.run(scraper.scrape(url))
            elapsed_time = time.time() - start_time

            print(f"✓ スクレイピング完了 ({elapsed_time:.2f}秒)")

            # 結果の確認
            print("\n取得データ:")
            print(f"  会議日: {result.metadata.get('date', 'なし')}")
            print(f"  会議体: {result.metadata.get('conference_name', '不明')}")
            print(f"  自治体: {result.metadata.get('governing_body_name', '不明')}")
            print(f"  テキストサイズ: {len(result.text):,} 文字")

            if result.pdf_content:
                print(f"  PDFサイズ: {len(result.pdf_content):,} bytes")
            else:
                print("  PDF: 取得なし")

            # テキストのサンプル表示
            if result.text:
                print("\nテキストサンプル（最初の200文字）:")
                print(result.text[:200] + "...")

        except Exception as e:
            print(f"✗ エラー: {e}")


def test_kokkai_scraping():
    """国会議事録スクレイピングのテスト"""
    print(f"\n{'=' * 60}")
    print("国会議事録 スクレイピングテスト")
    print("=" * 60)

    # テストURL（実際のURLに置き換えてください）
    test_urls = [
        "https://kokkai.ndl.go.jp/minutes/api/v1/detailPDF?minId=120504889X00120220314",
    ]

    scraper = KokkaiScraper()

    for url in test_urls:
        print(f"\nテストURL: {url}")

        try:
            print("スクレイピング開始...")
            start_time = time.time()

            result = asyncio.run(scraper.scrape(url))
            elapsed_time = time.time() - start_time

            print(f"✓ スクレイピング完了 ({elapsed_time:.2f}秒)")

            # 結果の確認
            print("\n取得データ:")
            print(f"  会議日: {result.metadata.get('date', 'なし')}")
            print(f"  会議名: {result.metadata.get('conference_name', '不明')}")
            print(f"  テキストサイズ: {len(result.text):,} 文字")

        except Exception as e:
            print(f"✗ エラー: {e}")


def test_gcs_integration():
    """GCS統合のテスト"""
    print(f"\n{'=' * 60}")
    print("GCS統合テスト")
    print("=" * 60)

    # GCS設定確認
    bucket_name = os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        print("✗ GCS_BUCKET_NAME が設定されていません")
        return

    print(f"バケット名: {bucket_name}")

    try:
        storage = GCSStorage(bucket_name)

        # テストファイルのアップロード
        test_content = (
            "これはテストコンテンツです。\n日時: " + datetime.now().isoformat()
        )
        test_path = f"scraped/test/test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        print(f"\nテストファイルをアップロード: {test_path}")
        uri = storage.upload_text(test_content, test_path)
        print(f"✓ アップロード成功: {uri}")

        # ダウンロードテスト
        print("\nダウンロードテスト...")
        downloaded_content = storage.download_text(uri)

        if downloaded_content == test_content:
            print("✓ ダウンロード成功: コンテンツが一致")
        else:
            print("✗ ダウンロード失敗: コンテンツが不一致")

        # ファイル一覧取得
        print("\n最近のファイル一覧:")
        today = datetime.now()
        prefix = f"scraped/{today.year}/{today.month:02d}/"

        blobs = storage.list_files(prefix, limit=10)
        for blob in blobs:
            print(f"  - {blob.name} ({blob.size:,} bytes)")

    except Exception as e:
        print(f"✗ エラー: {e}")


def test_batch_scraping():
    """バッチスクレイピングのテスト"""
    print(f"\n{'=' * 60}")
    print("バッチスクレイピングテスト")
    print("=" * 60)

    ScraperService()

    # 対応している自治体
    supported_tenants = ["kyoto", "osaka"]  # 実際の対応リストに合わせる

    for tenant in supported_tenants[:1]:  # 最初の1つだけテスト
        print(f"\n自治体: {tenant}")

        try:
            print("最新の会議一覧を取得...")
            # TODO: 実際のバッチスクレイピング実装
            print("（バッチスクレイピングは別途実装）")

        except Exception as e:
            print(f"✗ エラー: {e}")


def test_performance_metrics():
    """パフォーマンス測定"""
    print(f"\n{'=' * 60}")
    print("パフォーマンス測定")
    print("=" * 60)

    # 最近のスクレイピング実績
    engine = get_db_engine()
    with engine.connect() as conn:
        from sqlalchemy import text

        # 日別の統計
        query = text("""
            SELECT
                DATE(created_at) as date,
                COUNT(*) as total_count,
                COUNT(gcs_pdf_uri) as pdf_count,
                COUNT(gcs_text_uri) as text_count,
                AVG(CASE
                    WHEN gcs_pdf_uri IS NOT NULL OR gcs_text_uri IS NOT NULL
                    THEN 1 ELSE 0
                END) as success_rate
            FROM meetings
            WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
            GROUP BY DATE(created_at)
            ORDER BY date DESC
        """)

        result = conn.execute(query)
        daily_stats = result.fetchall()

        print("\n過去7日間の統計:")
        for date, total, pdf, text_count, success_rate in daily_stats:
            print(f"\n{date}:")
            print(f"  総数: {total}")
            print(f"  PDF: {pdf}")
            print(f"  テキスト: {text_count}")
            print(f"  成功率: {success_rate * 100:.1f}%")

        # ソース別の統計
        query = text("""
            SELECT
                CASE
                    WHEN url LIKE '%kaigiroku.net%' THEN 'kaigiroku.net'
                    WHEN url LIKE '%kokkai.ndl.go.jp%' THEN '国会議事録'
                    ELSE 'その他'
                END as source,
                COUNT(*) as count
            FROM meetings
            WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
            GROUP BY source
            ORDER BY count DESC
        """)

        result = conn.execute(query)
        source_stats = result.fetchall()

        print("\nソース別統計（過去30日）:")
        for source, count in source_stats:
            print(f"  {source}: {count}件")

    # ローカルファイルの統計
    if os.path.exists("data/scraped"):
        print("\nローカルファイル統計:")

        total_size = 0
        file_count = 0
        file_types = {}

        for root, _dirs, files in os.walk("data/scraped"):
            for file in files:
                file_path = os.path.join(root, file)
                file_count += 1
                total_size += os.path.getsize(file_path)

                ext = os.path.splitext(file)[1].lower()
                file_types[ext] = file_types.get(ext, 0) + 1

        print(f"  ファイル数: {file_count:,}")
        print(f"  合計サイズ: {total_size / 1024 / 1024:.1f} MB")
        print("  ファイルタイプ:")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    {ext or '(なし)'}: {count}件")


def test_error_handling():
    """エラーハンドリングのテスト"""
    print(f"\n{'=' * 60}")
    print("エラーハンドリングテスト")
    print("=" * 60)

    service = ScraperService()

    # 無効なURLのテスト
    invalid_urls = [
        "https://invalid-url.example.com",
        "not-a-url",
        "",
    ]

    for url in invalid_urls:
        print(f"\n無効なURL: '{url}'")
        try:
            asyncio.run(service.scrape_and_save(url))
            print("✗ エラーが発生しませんでした")
        except Exception as e:
            print(f"✓ 期待通りのエラー: {type(e).__name__}: {e}")

    # タイムアウトテスト
    print("\nタイムアウトテスト（実装による）")
    # TODO: タイムアウトのテスト実装


def run_full_test():
    """完全なテストの実行"""
    print("=" * 80)
    print("スクレイピング機能 - 完全テスト")
    print("=" * 80)

    # 1. kaigiroku.netテスト
    test_kaigiroku_scraping()

    # 2. 国会議事録テスト
    test_kokkai_scraping()

    # 3. GCS統合テスト
    test_gcs_integration()

    # 4. バッチスクレイピング
    test_batch_scraping()

    # 5. パフォーマンス測定
    test_performance_metrics()

    # 6. エラーハンドリング
    test_error_handling()

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--kaigiroku":
            test_kaigiroku_scraping()
        elif sys.argv[1] == "--kokkai":
            test_kokkai_scraping()
        elif sys.argv[1] == "--gcs":
            test_gcs_integration()
        elif sys.argv[1] == "--batch":
            test_batch_scraping()
        elif sys.argv[1] == "--performance":
            test_performance_metrics()
        elif sys.argv[1] == "--errors":
            test_error_handling()
    else:
        run_full_test()
