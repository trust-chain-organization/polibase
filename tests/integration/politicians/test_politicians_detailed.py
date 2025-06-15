#!/usr/bin/env python
"""政治家情報抽出機能の詳細テスト"""

import asyncio
import time

from src.config.database import get_connection
from src.database.politician_repository import PoliticianRepository
from src.party_member_extractor.extractor import PartyMemberExtractor
from src.party_member_extractor.html_fetcher import HTMLFetcher


def test_party_urls():
    """政党URL設定の確認"""
    print("=" * 60)
    print("政党URL設定の確認")
    print("=" * 60)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, members_list_url
            FROM political_parties
            ORDER BY id
        """)
        parties = cursor.fetchall()

    print(f"\n設定済み政党数: {len([p for p in parties if p[2]])}/{len(parties)}")
    print("\n詳細:")
    for party_id, name, url in parties:
        status = "✓" if url else "✗"
        print(f"{status} [{party_id}] {name}")
        if url:
            print(f"   URL: {url}")
        else:
            print("   URL: 未設定")

    return [p for p in parties if p[2]]


def test_html_fetching(party_id: int, url: str):
    """HTML取得のテスト"""
    print(f"\n{'=' * 60}")
    print(f"HTML取得テスト - Party ID: {party_id}")
    print("=" * 60)

    fetcher = HTMLFetcher()

    try:
        print(f"URL: {url}")
        print("Playwrightでページを取得中...")

        start_time = time.time()
        html_content = asyncio.run(fetcher.fetch_with_playwright(url))
        elapsed_time = time.time() - start_time

        print(f"✓ 取得成功 ({elapsed_time:.2f}秒)")
        print(f"HTMLサイズ: {len(html_content):,} bytes")

        # ページネーションリンクの検出
        pagination_links = fetcher.find_pagination_links(html_content)
        print(f"ページネーションリンク: {len(pagination_links)}個")
        if pagination_links:
            print("検出されたリンク:")
            for i, link in enumerate(pagination_links[:5]):
                print(f"  [{i+1}] {link}")
            if len(pagination_links) > 5:
                print(f"  ... 他 {len(pagination_links) - 5} 個")

        return html_content

    except Exception as e:
        print(f"✗ エラー: {e}")
        return None


def test_politician_extraction(party_id: int, html_content: str):
    """政治家情報抽出のテスト"""
    print(f"\n{'=' * 60}")
    print(f"政治家情報抽出テスト - Party ID: {party_id}")
    print("=" * 60)

    extractor = PartyMemberExtractor()

    try:
        print("LLMで政治家情報を抽出中...")
        start_time = time.time()

        politicians = asyncio.run(extractor.extract_politicians_from_html(html_content))
        elapsed_time = time.time() - start_time

        print(f"✓ 抽出完了 ({elapsed_time:.2f}秒)")
        print(f"抽出された政治家数: {len(politicians)}名")

        if politicians:
            print("\nサンプル（最初の5名）:")
            for i, pol in enumerate(politicians[:5]):
                print(f"\n[{i+1}] {pol.name}")
                if pol.position:
                    print(f"   役職: {pol.position}")
                if pol.prefecture:
                    print(f"   都道府県: {pol.prefecture}")
                if pol.electoral_district:
                    print(f"   選挙区: {pol.electoral_district}")
                if pol.profile_url:
                    print(f"   プロフィール: {pol.profile_url}")

        return politicians

    except Exception as e:
        print(f"✗ エラー: {e}")
        return []


def test_duplicate_checking(party_id: int, politicians: list):
    """重複チェックのテスト"""
    print(f"\n{'=' * 60}")
    print("重複チェックテスト")
    print("=" * 60)

    politician_repo = PoliticianRepository(get_connection())

    new_count = 0
    existing_count = 0

    print(f"チェック対象: {len(politicians)}名")

    for pol in politicians:
        existing = politician_repo.find_by_name_and_party(pol.name, party_id)
        if existing:
            existing_count += 1
        else:
            new_count += 1

    print("\n結果:")
    print(f"  新規: {new_count}名")
    print(f"  既存: {existing_count}名")

    if existing_count > 0:
        print("\n既存政治家の例（最大5名）:")
        shown = 0
        for pol in politicians:
            if shown >= 5:
                break
            existing = politician_repo.find_by_name_and_party(pol.name, party_id)
            if existing:
                print(f"  - {pol.name}")
                shown += 1

    return new_count, existing_count


def test_performance_metrics():
    """パフォーマンス測定"""
    print(f"\n{'=' * 60}")
    print("パフォーマンス測定")
    print("=" * 60)

    PoliticianRepository(get_connection())

    # 各政党の議員数
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pp.name, COUNT(p.id) as count,
                   MIN(p.created_at) as first_added,
                   MAX(p.created_at) as last_added
            FROM political_parties pp
            LEFT JOIN politicians p ON pp.id = p.political_party_id
            GROUP BY pp.id, pp.name
            HAVING COUNT(p.id) > 0
            ORDER BY count DESC
        """)
        party_stats = cursor.fetchall()

    print("\n政党別議員数:")
    total_politicians = 0
    for name, count, first_added, last_added in party_stats:
        total_politicians += count
        print(f"  {name}: {count}名")
        if first_added:
            print(f"    初回追加: {first_added}")
            print(f"    最終更新: {last_added}")

    print(f"\n合計: {total_politicians}名")

    # データベースサイズ
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pg_size_pretty(pg_total_relation_size('politicians'))
        """)
        size = cursor.fetchone()[0]

    print(f"\npoliticiansテーブルサイズ: {size}")


def run_full_test(party_id: int = None):
    """完全なテストの実行"""
    print("=" * 80)
    print("政治家情報抽出機能 - 完全テスト")
    print("=" * 80)

    # 1. URL設定確認
    parties_with_url = test_party_urls()

    if not parties_with_url:
        print("\n✗ URLが設定された政党がありません")
        return

    # テスト対象の選択
    if party_id:
        test_party = next((p for p in parties_with_url if p[0] == party_id), None)
        if not test_party:
            print(f"\n✗ Party ID {party_id} にはURLが設定されていません")
            return
        test_parties = [test_party]
    else:
        # 最初の政党をテスト
        test_parties = parties_with_url[:1]

    for party_id, party_name, url in test_parties:
        print(f"\n{'#' * 80}")
        print(f"テスト対象: {party_name} (ID: {party_id})")
        print("#" * 80)

        # 2. HTML取得
        html_content = test_html_fetching(party_id, url)
        if not html_content:
            continue

        # 3. 政治家抽出
        politicians = test_politician_extraction(party_id, html_content)
        if not politicians:
            continue

        # 4. 重複チェック
        new_count, existing_count = test_duplicate_checking(party_id, politicians)

    # 5. パフォーマンス測定
    test_performance_metrics()

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    party_id = None
    if len(sys.argv) > 2 and sys.argv[1] == "--party-id":
        party_id = int(sys.argv[2])

    run_full_test(party_id)
