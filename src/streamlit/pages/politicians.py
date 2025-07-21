"""政治家管理ページ"""

import pandas as pd

import streamlit as st
from src.common.logging import get_logger
from src.database.politician_repository import PoliticianRepository
from src.models.politician import Politician

logger = get_logger(__name__)


def manage_politicians():
    """政治家管理（一覧・詳細）"""
    st.header("政治家管理")
    st.markdown("収集された政治家情報の一覧と関連データを表示します")

    # 政治家管理用のタブを作成
    politician_tab1, politician_tab2 = st.tabs(["政治家一覧", "詳細検索"])

    with politician_tab1:
        show_politicians_list()

    with politician_tab2:
        show_politician_details()


def show_politicians_list():
    """政治家一覧の表示"""
    pol_repo = PoliticianRepository()

    try:
        # 政治家データを関連情報と共に取得
        query = """
        SELECT
            p.id,
            p.name,
            p.position,
            p.prefecture,
            p.electoral_district,
            pp.name as party_name,
            pp.id as party_id,
            CASE WHEN p.speaker_id IS NOT NULL THEN '✅' ELSE '❌' END as has_speaker,
            COUNT(DISTINCT pa.conference_id) as conference_count,
            COUNT(DISTINCT c.id) as conversation_count
        FROM politicians p
        LEFT JOIN political_parties pp ON p.political_party_id = pp.id
        LEFT JOIN politician_affiliations pa ON p.id = pa.politician_id
        LEFT JOIN speakers s ON p.speaker_id = s.id
        LEFT JOIN conversations c ON s.id = c.speaker_id
        GROUP BY p.id, p.name, p.position, p.prefecture, p.electoral_district,
                 pp.name, pp.id, p.speaker_id
        ORDER BY p.name
        """

        politicians_data = pol_repo.fetch_as_dict(query)

        if not politicians_data:
            st.info("政治家データがまだ登録されていません")
            return

        # DataFrameに変換
        df = pd.DataFrame(politicians_data)

        # 統計情報の表示
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("総政治家数", len(df))
        with col2:
            speaker_linked = len(df[df["has_speaker"] == "✅"])  # type: ignore[arg-type,index]
            st.metric("発言者リンク済み", f"{speaker_linked} / {len(df)}")
        with col3:
            parties_count = df["party_id"].nunique()
            st.metric("政党数", parties_count)
        with col4:
            avg_conferences = df["conference_count"].mean()
            st.metric("平均所属会議体数", f"{avg_conferences:.1f}")

        # フィルタリング機能
        st.markdown("### フィルタリング")
        col1, col2, col3 = st.columns(3)

        with col1:
            # 政党フィルタ
            party_options = ["すべて"] + sorted(
                df["party_name"].dropna().unique().tolist()  # type: ignore[union-attr]
            )
            selected_party = st.selectbox("政党", party_options)

        with col2:
            # 発言者リンクフィルタ
            speaker_options = ["すべて", "リンク済み", "未リンク"]
            selected_speaker = st.selectbox("発言者リンク状態", speaker_options)

        with col3:
            # 名前検索
            search_name = st.text_input("名前検索", placeholder="政治家名を入力")

        # フィルタリング適用
        filtered_df = df.copy()

        if selected_party != "すべて":
            filtered_df = filtered_df[filtered_df["party_name"] == selected_party]

        if selected_speaker == "リンク済み":
            filtered_df = filtered_df[filtered_df["has_speaker"] == "✅"]
        elif selected_speaker == "未リンク":
            filtered_df = filtered_df[filtered_df["has_speaker"] == "❌"]

        if search_name:
            filtered_df = filtered_df[
                filtered_df["name"].str.contains(search_name, na=False)
            ]

        # 表示カラムの選択
        display_columns = {
            "name": "名前",
            "party_name": "政党",
            "position": "役職",
            "prefecture": "都道府県",
            "electoral_district": "選挙区",
            "has_speaker": "発言者リンク",
            "conference_count": "所属会議体数",
            "conversation_count": "発言数",
        }

        # データ表示
        st.markdown(f"### 政治家一覧 ({len(filtered_df)}名)")  # type: ignore[arg-type]

        # カラム名を日本語に変換
        display_df = filtered_df[list(display_columns.keys())].rename(  # type: ignore[index,union-attr]
            columns=display_columns
        )

        # データテーブル表示
        st.dataframe(  # type: ignore[call-arg]
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "発言者リンク": st.column_config.TextColumn(
                    help="発言者（Speaker）とのリンク状態"
                ),
                "所属会議体数": st.column_config.NumberColumn(
                    format="%d", help="所属している会議体の数"
                ),
                "発言数": st.column_config.NumberColumn(
                    format="%d", help="記録されている発言の総数"
                ),
            },
        )

        # エクスポート機能
        if st.button("CSVエクスポート", type="secondary"):
            from datetime import datetime

            csv = display_df.to_csv(index=False, encoding="utf-8-sig")  # type: ignore[union-attr]
            st.download_button(
                label="ダウンロード",
                data=csv,  # type: ignore[arg-type]
                file_name=f"politicians_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    except Exception as e:
        st.error(f"データ取得中にエラーが発生しました: {str(e)}")
        logger.error(f"Error fetching politicians data: {str(e)}", exc_info=True)
    finally:
        pol_repo.close()


def show_politician_details():
    """政治家詳細検索・表示"""
    pol_repo = PoliticianRepository()

    try:
        # 政治家リストを取得
        politicians = pol_repo.fetch_all_as_models(
            Politician, "SELECT * FROM politicians ORDER BY name"
        )

        if not politicians:
            st.info("政治家データがまだ登録されていません")
            return

        # 政治家選択
        politician_options = {f"{p.name} ({p.id})": p for p in politicians}
        selected_option = st.selectbox(
            "政治家を選択",
            options=list(politician_options.keys()),
            help="詳細を表示する政治家を選択してください",
        )

        if selected_option:
            selected_politician = politician_options[selected_option]

            # 詳細情報の取得
            detail_query = """
            SELECT
                p.*,
                pp.name as party_name,
                s.name as speaker_name,
                s.id as speaker_id
            FROM politicians p
            LEFT JOIN political_parties pp ON p.political_party_id = pp.id
            LEFT JOIN speakers s ON p.speaker_id = s.id
            WHERE p.id = :politician_id
            """

            detail_result = pol_repo.fetch_as_dict(
                detail_query, {"politician_id": selected_politician.id}
            )

            if detail_result:
                detail = detail_result[0]

                # 基本情報の表示
                st.markdown("### 基本情報")
                col1, col2 = st.columns(2)

                with col1:
                    st.markdown(f"**名前**: {detail['name']}")
                    st.markdown(f"**政党**: {detail['party_name'] or '無所属'}")
                    st.markdown(f"**役職**: {detail['position'] or '-'}")

                with col2:
                    st.markdown(f"**都道府県**: {detail['prefecture'] or '-'}")
                    st.markdown(f"**選挙区**: {detail['electoral_district'] or '-'}")
                    speaker_status = "✅ あり" if detail["speaker_id"] else "❌ なし"
                    st.markdown(f"**発言者リンク**: {speaker_status}")
                    if detail["profile_url"]:
                        st.markdown(f"**[プロフィールURL]({detail['profile_url']})**")

                # 所属会議体情報
                st.markdown("### 所属会議体")
                affiliation_query = """
                SELECT
                    c.name as conference_name,
                    gb.name as governing_body_name,
                    pa.start_date,
                    pa.end_date,
                    pa.role
                FROM politician_affiliations pa
                JOIN conferences c ON pa.conference_id = c.id
                JOIN governing_bodies gb ON c.governing_body_id = gb.id
                WHERE pa.politician_id = :politician_id
                ORDER BY pa.start_date DESC
                """

                affiliations = pol_repo.fetch_as_dict(
                    affiliation_query, {"politician_id": selected_politician.id}
                )

                if affiliations:
                    aff_df = pd.DataFrame(affiliations)
                    aff_df["期間"] = aff_df.apply(
                        lambda x: f"{x['start_date']} ～ {x['end_date'] or '現在'}",
                        axis=1,
                    )
                    display_aff_df = aff_df[
                        ["conference_name", "governing_body_name", "role", "期間"]
                    ].rename(
                        columns={
                            "conference_name": "会議体",
                            "governing_body_name": "開催主体",
                            "role": "役職",
                        }
                    )
                    st.dataframe(
                        display_aff_df, use_container_width=True, hide_index=True
                    )
                else:
                    st.info("所属会議体情報がありません")

                # 発言情報（発言者リンクがある場合）
                if detail["speaker_id"]:
                    st.markdown("### 発言統計")
                    conversation_query = """
                    SELECT
                        COUNT(*) as total_conversations,
                        COUNT(DISTINCT m.id) as meeting_count,
                        MIN(m.date) as first_speech_date,
                        MAX(m.date) as last_speech_date
                    FROM conversations c
                    JOIN minutes min ON c.minute_id = min.id
                    JOIN meetings m ON min.meeting_id = m.id
                    WHERE c.speaker_id = :speaker_id
                    """

                    conv_stats = pol_repo.fetch_as_dict(
                        conversation_query, {"speaker_id": detail["speaker_id"]}
                    )

                    if conv_stats and conv_stats[0]["total_conversations"] > 0:
                        stats = conv_stats[0]
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("総発言数", stats["total_conversations"])
                        with col2:
                            st.metric("会議出席数", stats["meeting_count"])
                        with col3:
                            st.metric("初発言日", stats["first_speech_date"])
                        with col4:
                            st.metric("最終発言日", stats["last_speech_date"])

    except Exception as e:
        st.error(f"詳細データ取得中にエラーが発生しました: {str(e)}")
        logger.error(f"Error fetching politician details: {str(e)}", exc_info=True)
    finally:
        pol_repo.close()
