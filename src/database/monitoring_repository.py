"""Repository for monitoring data coverage and statistics"""

from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from src.database.base_repository import BaseRepository


class MonitoringRepository(BaseRepository):
    """監視ダッシュボード用のデータアクセスリポジトリ"""

    def __init__(self, session=None):
        """Initialize repository with optional session"""
        if session:
            super().__init__(use_session=True)
            self._session = session
        else:
            super().__init__(use_session=False)

    def get_overall_metrics(self) -> dict[str, Any]:
        """全体的なメトリクスを取得"""
        # 基本的な統計情報を取得
        query = """
            WITH stats AS (
                SELECT
                    -- 議会統計
                    (SELECT COUNT(*) FROM conferences) as total_conferences,
                    (SELECT COUNT(DISTINCT conference_id) FROM meetings)
                        as conferences_with_data,

                    -- 会議統計
                    (SELECT COUNT(*) FROM meetings) as total_meetings,
                    (SELECT COUNT(*) FROM meetings
                     WHERE id IN (SELECT meeting_id FROM minutes))
                        as meetings_with_minutes,

                    -- 議事録統計
                    (SELECT COUNT(*) FROM minutes) as total_minutes,
                    (SELECT COUNT(*) FROM minutes) as processed_minutes,

                    -- 発言者統計
                    (SELECT COUNT(*) FROM speakers) as total_speakers,
                    (SELECT COUNT(*) FROM speakers
                     WHERE id IN (SELECT speaker_id FROM politicians))
                        as linked_speakers,

                    -- 政治家統計
                    (SELECT COUNT(*) FROM politicians) as total_politicians,
                    (SELECT COUNT(DISTINCT p.id) FROM politicians p
                     WHERE EXISTS (SELECT 1 FROM conversations c
                                  WHERE c.speaker_id = p.speaker_id))
                        as active_politicians
            )
            SELECT
                total_conferences,
                conferences_with_data,
                CASE WHEN total_conferences > 0
                    THEN ROUND(100.0 * conferences_with_data / total_conferences, 1)
                    ELSE 0 END as conferences_coverage,

                total_meetings,
                meetings_with_minutes,
                CASE WHEN total_meetings > 0
                    THEN ROUND(100.0 * meetings_with_minutes / total_meetings, 1)
                    ELSE 0 END as meetings_coverage,

                total_minutes,
                processed_minutes,
                CASE WHEN total_minutes > 0
                    THEN ROUND(100.0 * processed_minutes / total_minutes, 1)
                    ELSE 0 END as minutes_coverage,

                total_speakers,
                linked_speakers,
                CASE WHEN total_speakers > 0
                    THEN ROUND(100.0 * linked_speakers / total_speakers, 1)
                    ELSE 0 END as speakers_coverage,

                total_politicians,
                active_politicians,
                CASE WHEN total_politicians > 0
                    THEN ROUND(100.0 * active_politicians / total_politicians, 1)
                    ELSE 0 END as politicians_coverage
            FROM stats
        """

        result = self.fetch_one(query)
        return dict(result._mapping) if result else {}

    def get_recent_activities(self, days: int = 7) -> pd.DataFrame:
        """最近のデータ入力活動を取得"""
        query = """
            WITH recent_activities AS (
                -- 最近追加された会議
                SELECT
                    'Meeting' as activity_type,
                    m.name as item_name,
                    m.date as activity_date,
                    m.created_at,
                    c.name as conference_name
                FROM meetings m
                JOIN conferences c ON m.conference_id = c.id
                WHERE m.created_at >= :start_date

                UNION ALL

                -- 最近追加された議事録
                SELECT
                    'Minutes' as activity_type,
                    COALESCE(m.name, 'Minutes #' || min.id) as item_name,
                    min.created_at::date as activity_date,
                    min.created_at as created_at,
                    c.name as conference_name
                FROM minutes min
                LEFT JOIN meetings m ON min.meeting_id = m.id
                LEFT JOIN conferences c ON m.conference_id = c.id
                WHERE min.created_at >= :start_date

                UNION ALL

                -- 最近追加された政治家
                SELECT
                    'Politician' as activity_type,
                    p.name as item_name,
                    p.created_at::date as activity_date,
                    p.created_at,
                    pp.name as conference_name
                FROM politicians p
                LEFT JOIN political_parties pp ON p.political_party_id = pp.id
                WHERE p.created_at >= :start_date
            )
            SELECT
                activity_type as "タイプ",
                item_name as "項目名",
                conference_name as "関連組織",
                activity_date as "日付",
                created_at as "作成日時"
            FROM recent_activities
            ORDER BY created_at DESC
            LIMIT 100
        """

        start_date = datetime.now() - timedelta(days=days)
        result = self.fetch_all(query, {"start_date": start_date.isoformat()})

        return pd.DataFrame(result)

    def get_conference_coverage(
        self, governing_body_type: str | None = None, min_coverage: float = 0
    ) -> pd.DataFrame:
        """議会別のカバレッジ情報を取得"""
        where_clause = ""
        params = {"min_coverage": min_coverage}

        if governing_body_type:
            where_clause = "WHERE gb.type = :gov_type"
            params["gov_type"] = governing_body_type

        query = f"""
            WITH conference_stats AS (
                SELECT
                    c.id as conference_id,
                    c.name as conference_name,
                    gb.name as governing_body_name,
                    gb.type as governing_body_type,
                    COUNT(DISTINCT m.id) as total_meetings,
                    COUNT(DISTINCT CASE WHEN EXISTS
                        (SELECT 1 FROM minutes WHERE meeting_id = m.id)
                        THEN m.id END) as processed_meetings,
                    MAX(m.created_at) as last_updated
                FROM conferences c
                JOIN governing_bodies gb ON c.governing_body_id = gb.id
                LEFT JOIN meetings m ON c.id = m.conference_id
                {where_clause}
                GROUP BY c.id, c.name, gb.name, gb.type
            )
            SELECT
                conference_id,
                conference_name,
                governing_body_name,
                governing_body_type,
                total_meetings,
                processed_meetings,
                CASE WHEN total_meetings > 0
                    THEN ROUND(100.0 * processed_meetings / total_meetings, 1)
                    ELSE 0 END as coverage_rate,
                last_updated
            FROM conference_stats
            WHERE CASE WHEN total_meetings > 0
                THEN (100.0 * processed_meetings / total_meetings)
                ELSE 0 END >= :min_coverage
            ORDER BY coverage_rate DESC, total_meetings DESC
        """

        result = self.fetch_all(query, params)
        return pd.DataFrame(result)

    def get_timeline_data(
        self, time_range: str = "過去30日", data_type: str = "すべて"
    ) -> pd.DataFrame:
        """時系列データを取得"""
        # 期間の計算
        end_date = datetime.now()
        if time_range == "過去7日":
            start_date = end_date - timedelta(days=7)
        elif time_range == "過去30日":
            start_date = end_date - timedelta(days=30)
        elif time_range == "過去3ヶ月":
            start_date = end_date - timedelta(days=90)
        elif time_range == "過去1年":
            start_date = end_date - timedelta(days=365)
        else:  # 全期間
            start_date = datetime(2000, 1, 1)

        queries = []

        if data_type in ["会議数", "すべて"]:
            queries.append("""
                SELECT
                    DATE(created_at) as date,
                    '会議' as data_type,
                    COUNT(*) as count
                FROM meetings
                WHERE created_at >= :start_date
                GROUP BY DATE(created_at)
            """)

        if data_type in ["議事録数", "すべて"]:
            queries.append("""
                SELECT
                    DATE(created_at) as date,
                    '議事録' as data_type,
                    COUNT(*) as count
                FROM minutes
                WHERE created_at >= :start_date
                GROUP BY DATE(created_at)
            """)

        if data_type in ["発言数", "すべて"]:
            queries.append("""
                SELECT
                    DATE(created_at) as date,
                    '発言' as data_type,
                    COUNT(*) as count
                FROM conversations
                WHERE created_at >= :start_date
                GROUP BY DATE(created_at)
            """)

        if queries:
            union_query = " UNION ALL ".join(queries)
            final_query = f"""
                WITH timeline AS ({union_query})
                SELECT date, data_type, count
                FROM timeline
                WHERE date IS NOT NULL
                ORDER BY date, data_type
            """

            result = self.fetch_all(final_query, {"start_date": start_date.isoformat()})
            return pd.DataFrame(result)

        return pd.DataFrame()

    def get_party_coverage(self) -> pd.DataFrame:
        """政党別カバレッジを取得"""
        query = """
            SELECT
                pp.name as party_name,
                COUNT(DISTINCT p.id) as politician_count,
                COUNT(DISTINCT CASE WHEN EXISTS
                    (SELECT 1 FROM conversations c
                     WHERE c.speaker_id = p.speaker_id) THEN p.id END) as active_count,
                CASE WHEN COUNT(DISTINCT p.id) > 0
                    THEN ROUND(100.0 * COUNT(DISTINCT CASE WHEN EXISTS
                        (SELECT 1 FROM conversations c
                         WHERE c.speaker_id = p.speaker_id) THEN p.id END)
                        / COUNT(DISTINCT p.id), 1)
                    ELSE 0 END as coverage_rate
            FROM political_parties pp
            LEFT JOIN politicians p ON pp.id = p.political_party_id
            GROUP BY pp.id, pp.name
            ORDER BY politician_count DESC
        """

        result = self.fetch_all(query)
        return pd.DataFrame(result)

    def get_prefecture_detailed_coverage(self) -> pd.DataFrame:
        """都道府県別の詳細カバレッジ情報を取得（地図表示用）"""
        query = """
            WITH prefecture_stats AS (
                SELECT
                    gb.name as prefecture_name,
                    gb.id as governing_body_id,

                    -- 議会統計
                    COUNT(DISTINCT c.id) as conference_count,

                    -- 会議統計
                    COUNT(DISTINCT m.id) as meetings_count,
                    COUNT(DISTINCT CASE WHEN EXISTS
                        (SELECT 1 FROM minutes WHERE meeting_id = m.id)
                        THEN m.id END) as processed_meetings_count,

                    -- 議事録統計
                    COUNT(DISTINCT min.id) as minutes_count,

                    -- 議員統計（都道府県に属する議会の議員）
                    COUNT(DISTINCT pa.politician_id) as politicians_count,

                    -- 議員団統計
                    COUNT(DISTINCT pg.id) as groups_count

                FROM governing_bodies gb
                LEFT JOIN conferences c ON gb.id = c.governing_body_id
                LEFT JOIN meetings m ON c.id = m.conference_id
                LEFT JOIN minutes min ON m.id = min.meeting_id
                LEFT JOIN politician_affiliations pa ON c.id = pa.conference_id
                    AND pa.end_date IS NULL  -- 現職のみ
                LEFT JOIN parliamentary_groups pg ON c.id = pg.conference_id
                    AND pg.is_active = TRUE  -- 現在の議員団のみ
                WHERE gb.type = '都道府県'
                GROUP BY gb.id, gb.name
            )
            SELECT
                prefecture_name,
                conference_count,
                meetings_count,
                processed_meetings_count,
                minutes_count,
                politicians_count,
                groups_count,

                -- 総合充実度の計算（各指標の平均）
                CASE
                    WHEN meetings_count > 0 THEN
                        ROUND(
                            (
                                -- 会議処理率
                                (100.0 * processed_meetings_count / meetings_count) +
                                -- 議会あたり議員数（最大50人で正規化）
                                LEAST(100.0,
                                    CASE WHEN conference_count > 0
                                    THEN 100.0 * politicians_count /
                                        (conference_count * 50)
                                    ELSE 0 END
                                ) +
                                -- 議会あたり議員団数（最大10団体で正規化）
                                LEAST(100.0,
                                    CASE WHEN conference_count > 0
                                    THEN 100.0 * groups_count / (conference_count * 10)
                                    ELSE 0 END
                                )
                            ) / 3.0, 1
                        )
                    ELSE 0
                END as total_value

            FROM prefecture_stats
            ORDER BY total_value DESC, meetings_count DESC
        """

        result = self.fetch_all(query)
        return pd.DataFrame(result)

    def get_prefecture_coverage(self) -> pd.DataFrame:
        """都道府県別カバレッジを取得"""
        query = """
            WITH prefecture_stats AS (
                SELECT
                    gb.name as prefecture_name,
                    COUNT(DISTINCT c.id) as conference_count,
                    COUNT(DISTINCT m.id) as meeting_count,
                    COUNT(DISTINCT CASE WHEN EXISTS
                    (SELECT 1 FROM minutes WHERE meeting_id = m.id)
                    THEN m.id END) as processed_count
                FROM governing_bodies gb
                LEFT JOIN conferences c ON gb.id = c.governing_body_id
                LEFT JOIN meetings m ON c.id = m.conference_id
                WHERE gb.type = '都道府県'
                GROUP BY gb.id, gb.name
            )
            SELECT
                prefecture_name,
                conference_count,
                meeting_count,
                processed_count,
                CASE WHEN meeting_count > 0
                    THEN ROUND(100.0 * processed_count / meeting_count, 1)
                    ELSE 0 END as coverage_rate
            FROM prefecture_stats
            ORDER BY coverage_rate DESC, meeting_count DESC
        """

        result = self.fetch_all(query)
        return pd.DataFrame(result)

    def get_committee_type_coverage(self) -> pd.DataFrame:
        """委員会タイプ別カバレッジを取得"""
        query = """
            SELECT
                gb.type as governing_body_type,
                CASE
                    WHEN c.name LIKE '%本会議%' THEN '本会議'
                    WHEN c.name LIKE '%委員会%' THEN '委員会'
                    WHEN c.name LIKE '%審議会%' THEN '審議会'
                    ELSE 'その他'
                END as committee_type,
                COUNT(DISTINCT m.id) as meeting_count,
                COUNT(DISTINCT CASE WHEN EXISTS
                    (SELECT 1 FROM minutes WHERE meeting_id = m.id)
                    THEN m.id END) as processed_count
            FROM conferences c
            JOIN governing_bodies gb ON c.governing_body_id = gb.id
            LEFT JOIN meetings m ON c.id = m.conference_id
            GROUP BY gb.type, committee_type
            ORDER BY gb.type, meeting_count DESC
        """

        result = self.fetch_all(query)
        return pd.DataFrame(result)
