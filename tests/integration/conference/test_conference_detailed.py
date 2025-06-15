#!/usr/bin/env python
"""会議体メンバー管理機能の詳細テスト"""

import asyncio
from datetime import date

from src.conference_member_extractor.membership_service import (
    ConferenceMembershipService,
)
from src.config.database import get_connection
from src.database.conference_repository import ConferenceRepository
from src.database.extracted_conference_member_repository import (
    ExtractedConferenceMemberRepository,
)


def test_conference_urls():
    """会議体URL設定の確認"""
    print("=" * 60)
    print("会議体URL設定の確認")
    print("=" * 60)

    conference_repo = ConferenceRepository(get_connection())

    # URL設定済みの会議体を取得
    conferences_with_url = conference_repo.get_conferences_with_member_url()

    print(f"\nURL設定済み会議体数: {len(conferences_with_url)}")
    print("\n詳細:")
    for conf in conferences_with_url[:10]:  # 最初の10件
        print(f"\n[{conf['id']}] {conf['name']}")
        print(f"   自治体: {conf['governing_body_name']}")
        print(f"   URL: {conf['members_introduction_url']}")

    if len(conferences_with_url) > 10:
        print(f"\n... 他 {len(conferences_with_url) - 10} 件")

    return conferences_with_url


def test_extraction_process(conference_id: int):
    """メンバー抽出プロセスのテスト"""
    print(f"\n{'=' * 60}")
    print(f"メンバー抽出テスト - Conference ID: {conference_id}")
    print("=" * 60)

    service = ConferenceMembershipService()
    conference_repo = ConferenceRepository(get_connection())
    extracted_repo = ExtractedConferenceMemberRepository(get_connection())

    # 会議体情報を取得
    conference = conference_repo.get_by_id(conference_id)
    if not conference:
        print(f"✗ Conference ID {conference_id} が見つかりません")
        return None

    print(f"\n会議体: {conference['name']}")
    print(f"URL: {conference.get('members_introduction_url', 'なし')}")

    if not conference.get("members_introduction_url"):
        print("✗ URLが設定されていません")
        return None

    # 既存データの確認
    existing = extracted_repo.get_by_conference_id(conference_id)
    if existing:
        print(f"\n既存データ: {len(existing)}件")
        print("ステータス別:")
        status_counts = {}
        for member in existing:
            status = member["matching_status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in status_counts.items():
            print(f"  {status}: {count}件")

    # 抽出実行
    print("\n抽出を開始...")
    try:
        extracted_count = asyncio.run(service.extract_members(conference_id))
        print(f"✓ 抽出完了: {extracted_count}名")

        # 抽出結果の確認
        new_extracted = extracted_repo.get_by_conference_id(conference_id)
        print("\n抽出結果（最初の5名）:")
        for member in new_extracted[:5]:
            print(f"\n- {member['extracted_name']}")
            if member["extracted_role"]:
                print(f"  役職: {member['extracted_role']}")
            if member["extracted_party_name"]:
                print(f"  政党: {member['extracted_party_name']}")

        return extracted_count

    except Exception as e:
        print(f"✗ エラー: {e}")
        return None


def test_matching_process(conference_id: int):
    """マッチングプロセスのテスト"""
    print(f"\n{'=' * 60}")
    print(f"マッチングテスト - Conference ID: {conference_id}")
    print("=" * 60)

    service = ConferenceMembershipService()
    extracted_repo = ExtractedConferenceMemberRepository(get_connection())

    # 未処理のメンバーを確認
    pending_members = extracted_repo.get_pending_members(conference_id)
    print(f"\n未処理メンバー: {len(pending_members)}名")

    if not pending_members:
        print("処理対象がありません")
        return

    # マッチング実行
    print("\nマッチングを開始...")
    try:
        results = asyncio.run(service.match_members(conference_id))

        print("\n✓ マッチング完了")
        print(f"処理件数: {len(results)}")

        # 結果の集計
        status_counts = {"matched": 0, "needs_review": 0, "no_match": 0}
        confidence_sum = 0
        confidence_count = 0

        for result in results:
            status_counts[result["status"]] += 1
            if result["confidence"] is not None:
                confidence_sum += result["confidence"]
                confidence_count += 1

        print("\nマッチング結果:")
        print(f"  matched (≥0.7): {status_counts['matched']}件")
        print(f"  needs_review (0.5-0.7): {status_counts['needs_review']}件")
        print(f"  no_match (<0.5): {status_counts['no_match']}件")

        if confidence_count > 0:
            avg_confidence = confidence_sum / confidence_count
            print(f"  平均信頼度: {avg_confidence:.2f}")

        # マッチング例を表示
        print("\nマッチング例（matched）:")
        for result in results[:5]:
            if result["status"] == "matched":
                member = extracted_repo.get_by_id(result["member_id"])
                matched_name = result.get("matched_name", "N/A")
                confidence = result["confidence"]
                print(
                    f"  {member['extracted_name']} → {matched_name} "
                    f"(信頼度: {confidence:.2f})"
                )

        return results

    except Exception as e:
        print(f"✗ エラー: {e}")
        return None


def test_affiliation_creation(conference_id: int):
    """所属作成プロセスのテスト"""
    print(f"\n{'=' * 60}")
    print(f"所属作成テスト - Conference ID: {conference_id}")
    print("=" * 60)

    service = ConferenceMembershipService()
    extracted_repo = ExtractedConferenceMemberRepository(get_connection())

    # マッチング済みメンバーを確認
    matched_members = extracted_repo.get_matched_members(conference_id)
    print(f"\nマッチング済みメンバー: {len(matched_members)}名")

    if not matched_members:
        print("作成対象がありません")
        return

    # 所属作成
    print("\n所属作成を開始...")
    start_date = date(2024, 1, 1)

    try:
        created_count = asyncio.run(
            service.create_memberships_from_matched(conference_id, start_date)
        )

        print(f"✓ 所属作成完了: {created_count}件")

        # 作成された所属を確認
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.name, pa.role, pa.start_date
                FROM politician_affiliations pa
                JOIN politicians p ON pa.politician_id = p.id
                WHERE pa.conference_id = %s
                  AND pa.start_date = %s
                ORDER BY pa.role, p.name
                LIMIT 10
            """,
                (conference_id, start_date),
            )

            affiliations = cursor.fetchall()

            if affiliations:
                print("\n作成された所属（最初の10件）:")
                for name, role, start in affiliations:
                    print(f"  {name} - {role or '一般'} (開始日: {start})")

        return created_count

    except Exception as e:
        print(f"✗ エラー: {e}")
        return None


def test_matching_accuracy():
    """マッチング精度の分析"""
    print(f"\n{'=' * 60}")
    print("マッチング精度分析")
    print("=" * 60)

    extracted_repo = ExtractedConferenceMemberRepository(get_connection())

    # 全体のマッチング統計
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                matching_status,
                COUNT(*) as count,
                AVG(matching_confidence)::numeric(3,2) as avg_confidence,
                MIN(matching_confidence)::numeric(3,2) as min_confidence,
                MAX(matching_confidence)::numeric(3,2) as max_confidence
            FROM extracted_conference_members
            WHERE matching_status != 'pending'
            GROUP BY matching_status
            ORDER BY matching_status
        """)

        stats = cursor.fetchall()

    print("\n全体統計:")
    total_count = 0
    for status, count, avg_conf, min_conf, max_conf in stats:
        total_count += count
        print(f"\n{status}:")
        print(f"  件数: {count}")
        if avg_conf is not None:
            print(f"  平均信頼度: {avg_conf}")
            print(f"  最小/最大: {min_conf} / {max_conf}")

    if total_count > 0:
        matched_count = next((s[1] for s in stats if s[0] == "matched"), 0)
        match_rate = matched_count / total_count * 100
        print(f"\n全体マッチング率: {match_rate:.1f}%")

    # 信頼度の分布
    print("\n信頼度分布:")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                CASE
                    WHEN matching_confidence >= 0.9 THEN '0.9-1.0'
                    WHEN matching_confidence >= 0.8 THEN '0.8-0.9'
                    WHEN matching_confidence >= 0.7 THEN '0.7-0.8'
                    WHEN matching_confidence >= 0.6 THEN '0.6-0.7'
                    WHEN matching_confidence >= 0.5 THEN '0.5-0.6'
                    ELSE '0.0-0.5'
                END as confidence_range,
                COUNT(*) as count
            FROM extracted_conference_members
            WHERE matching_confidence IS NOT NULL
            GROUP BY confidence_range
            ORDER BY confidence_range DESC
        """)

        distribution = cursor.fetchall()

        for range_str, count in distribution:
            bar = "█" * int(count / 10) or "▏"
            print(f"  {range_str}: {bar} {count}")

    # 要確認のケース
    print("\n要確認ケース（needs_review）のサンプル:")
    needs_review = extracted_repo.get_needs_review_members()[:5]
    for member in needs_review:
        confidence = member["matching_confidence"]
        print(f"\n- {member['extracted_name']} (信頼度: {confidence:.2f})")
        if member["matching_notes"]:
            print(f"  備考: {member['matching_notes']}")


def run_full_test(conference_id: int | None = None):
    """完全なテストの実行"""
    print("=" * 80)
    print("会議体メンバー管理機能 - 完全テスト")
    print("=" * 80)

    # 1. URL設定確認
    conferences = test_conference_urls()

    if not conferences:
        print("\n✗ URLが設定された会議体がありません")
        return

    # テスト対象の選択
    if conference_id:
        test_conference = next(
            (c for c in conferences if c["id"] == conference_id), None
        )
        if not test_conference:
            print(f"\n✗ Conference ID {conference_id} にはURLが設定されていません")
            return
    else:
        # 最初の会議体をテスト
        test_conference = conferences[0]
        conference_id = test_conference["id"]

    print(f"\n{'#' * 80}")
    print(f"テスト対象: {test_conference['name']} (ID: {conference_id})")
    print("#" * 80)

    # 2. メンバー抽出
    extracted_count = test_extraction_process(conference_id)

    # 3. マッチング
    if extracted_count:
        test_matching_process(conference_id)

    # 4. 所属作成
    test_affiliation_creation(conference_id)

    # 5. 精度分析
    test_matching_accuracy()

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    conference_id = None
    if len(sys.argv) > 2 and sys.argv[1] == "--conference-id":
        conference_id = int(sys.argv[2])

    run_full_test(conference_id)
