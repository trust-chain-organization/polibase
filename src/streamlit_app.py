"""Streamlit app for managing meetings"""

import subprocess
from datetime import date, datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text

# Initialize logging and Sentry before other imports
from src.common.logging import get_logger, setup_logging
from src.config.sentry import init_sentry
from src.config.settings import get_settings

# Initialize settings
settings = get_settings()

# Initialize structured logging with Sentry integration
setup_logging(
    log_level=settings.log_level, json_format=settings.is_production, enable_sentry=True
)

# Initialize Sentry SDK
init_sentry()

# Get logger
logger = get_logger(__name__)

from src.config.database import get_db_engine  # noqa: E402
from src.database.conference_repository import ConferenceRepository  # noqa: E402
from src.database.governing_body_repository import GoverningBodyRepository  # noqa: E402
from src.database.meeting_repository import MeetingRepository  # noqa: E402
from src.database.parliamentary_group_repository import (  # noqa: E402
    ParliamentaryGroupMembershipRepository,
    ParliamentaryGroupRepository,
)
from src.database.politician_repository import PoliticianRepository  # noqa: E402
from src.exceptions import (  # noqa: E402
    DatabaseError,
    ProcessingError,
    RecordNotFoundError,
    SaveError,
    ScrapingError,
    UpdateError,
)
from src.models.politician import Politician  # noqa: E402
from src.seed_generator import SeedGenerator  # noqa: E402

# ページ設定
st.set_page_config(page_title="Polibase - 会議管理", page_icon="🏛️", layout="wide")

# セッション状態の初期化
if "selected_governing_body" not in st.session_state:
    st.session_state.selected_governing_body = None
if "selected_conference" not in st.session_state:
    st.session_state.selected_conference = None
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "edit_meeting_id" not in st.session_state:
    st.session_state.edit_meeting_id = None
if "process_status" not in st.session_state:
    st.session_state.process_status = {}
if "process_output" not in st.session_state:
    st.session_state.process_output = {}
if "success_message" not in st.session_state:
    st.session_state.success_message = None
if "error_message" not in st.session_state:
    st.session_state.error_message = None
if "message_details" not in st.session_state:
    st.session_state.message_details = None
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "会議一覧"
if "created_parliamentary_groups" not in st.session_state:
    st.session_state.created_parliamentary_groups = []


def display_messages():
    """セッション状態のメッセージを表示"""
    # メッセージクリアフラグをチェック
    if "clear_messages" in st.session_state and st.session_state.clear_messages:
        st.session_state.success_message = None
        st.session_state.error_message = None
        st.session_state.message_details = None
        st.session_state.clear_messages = False
        return

    # 成功メッセージの表示
    if st.session_state.success_message:
        with st.container():
            col1, col2 = st.columns([10, 1])
            with col1:
                st.success(st.session_state.success_message)
            with col2:
                if st.button("✖", key="clear_success", help="メッセージを閉じる"):
                    st.session_state.clear_messages = True
                    st.rerun()

            # 詳細情報があれば表示
            if st.session_state.message_details:
                with st.expander("詳細を表示", expanded=True):
                    st.markdown(st.session_state.message_details)

    # エラーメッセージの表示
    if st.session_state.error_message:
        with st.container():
            col1, col2 = st.columns([10, 1])
            with col1:
                st.error(st.session_state.error_message)
            with col2:
                if st.button("✖", key="clear_error", help="メッセージを閉じる"):
                    st.session_state.clear_messages = True
                    st.rerun()


def main():
    st.title("🏛️ Polibase - 会議管理システム")
    st.markdown("議事録の会議情報（URL、日付）を管理します")

    # グローバルメッセージを表示（会議体管理以外で使用）
    # display_messages()

    # タブ作成
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
        [
            "会議管理",
            "政党管理",
            "会議体管理",
            "開催主体管理",
            "議員団管理",
            "処理実行",
            "政治家管理",
        ]
    )

    with tab1:
        manage_meetings()

    with tab2:
        manage_political_parties()

    with tab3:
        manage_conferences()

    with tab4:
        manage_governing_bodies()

    with tab5:
        manage_parliamentary_groups()

    with tab6:
        execute_processes()

    with tab7:
        manage_politicians()


def manage_meetings():
    """会議管理（一覧・新規登録・編集）"""
    st.header("会議管理")
    st.markdown("議事録の会議情報を管理します")

    # 会議管理用のタブを作成
    meeting_tab1, meeting_tab2, meeting_tab3 = st.tabs(
        ["会議一覧", "新規会議登録", "会議編集"]
    )

    with meeting_tab1:
        show_meetings_list()

    with meeting_tab2:
        add_new_meeting()

    with meeting_tab3:
        edit_meeting()


def show_meetings_list():
    """会議一覧を表示"""
    st.subheader("会議一覧")

    repo = MeetingRepository()

    # フィルター
    col1, col2 = st.columns(2)

    with col1:
        governing_bodies = repo.get_governing_bodies()
        gb_options = ["すべて"] + [
            f"{gb['name']} ({gb['type']})" for gb in governing_bodies
        ]
        gb_selected = st.selectbox("開催主体", gb_options, key="list_gb")

        if gb_selected != "すべて":
            # 選択されたオプションから対応するgoverning_bodyを探す
            for _i, gb in enumerate(governing_bodies):
                if f"{gb['name']} ({gb['type']})" == gb_selected:
                    selected_gb = gb
                    break
            conferences = repo.get_conferences_by_governing_body(selected_gb["id"])
        else:
            conferences = []

    with col2:
        if conferences:
            conf_options = ["すべて"] + [conf["name"] for conf in conferences]
            conf_selected = st.selectbox("会議体", conf_options, key="list_conf")

            if conf_selected != "すべて":
                # 選択されたオプションから対応するconferenceを探す
                for conf in conferences:
                    if conf["name"] == conf_selected:
                        selected_conf_id = conf["id"]
                        break
            else:
                selected_conf_id = None
        else:
            selected_conf_id = None
            if gb_selected != "すべて":
                st.info("会議体を選択してください")

    # 会議一覧取得
    meetings = repo.get_meetings(conference_id=selected_conf_id)

    if meetings:
        # DataFrameに変換
        df = pd.DataFrame(meetings)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date", ascending=False)

        # 表示用のカラムを整形
        df["開催日"] = df["date"].dt.strftime("%Y年%m月%d日")
        df["開催主体・会議体"] = (
            df["governing_body_name"] + " - " + df["conference_name"]
        )

        # 編集・削除ボタン用のカラム
        for _idx, row in df.iterrows():
            col1, col2, col3 = st.columns([6, 1, 1])

            with col1:
                # URLを表示
                url_display = row["url"] if row["url"] else "URLなし"
                st.markdown(
                    f"**{row['開催日']}** - {row['開催主体・会議体']}",
                    unsafe_allow_html=True,
                )
                if row["url"]:
                    st.markdown(f"URL: [{url_display}]({row['url']})")
                else:
                    st.markdown(f"URL: {url_display}")

            with col2:
                if st.button("編集", key=f"edit_{row['id']}"):
                    st.session_state.edit_mode = True
                    st.session_state.edit_meeting_id = row["id"]
                    st.rerun()

            with col3:
                if st.button("削除", key=f"delete_{row['id']}"):
                    if repo.delete_meeting(row["id"]):
                        st.success("会議を削除しました")
                        st.rerun()
                    else:
                        st.error(
                            "会議を削除できませんでした"
                            "（関連する議事録が存在する可能性があります）"
                        )

            st.divider()
    else:
        st.info("会議が登録されていません")

    repo.close()


def add_new_meeting():
    """新規会議登録フォーム"""
    st.subheader("新規会議登録")

    repo = MeetingRepository()

    # 開催主体選択（フォームの外）
    governing_bodies = repo.get_governing_bodies()
    if not governing_bodies:
        st.error("開催主体が登録されていません。先にマスターデータを登録してください。")
        repo.close()
        return

    gb_options = [f"{gb['name']} ({gb['type']})" for gb in governing_bodies]
    gb_selected = st.selectbox("開催主体を選択", gb_options, key="new_meeting_gb")

    # 選択されたgoverning_bodyを取得
    selected_gb = None
    for gb in governing_bodies:
        if f"{gb['name']} ({gb['type']})" == gb_selected:
            selected_gb = gb
            break

    # 会議体選択（選択された開催主体に紐づくもののみ表示）
    conferences = []
    if selected_gb:
        conferences = repo.get_conferences_by_governing_body(selected_gb["id"])
        if not conferences:
            st.error("選択された開催主体に会議体が登録されていません")
            repo.close()
            return

    conf_options = []
    for conf in conferences:
        conf_display = f"{conf['name']}"
        if conf.get("type"):
            conf_display += f" ({conf['type']})"
        conf_options.append(conf_display)

    conf_selected = st.selectbox("会議体を選択", conf_options, key="new_meeting_conf")

    # 選択されたconferenceを取得
    selected_conf = None
    for i, conf in enumerate(conferences):
        if conf_options[i] == conf_selected:
            selected_conf = conf
            break

    # フォーム部分
    with st.form("new_meeting_form"):
        # 選択された内容を表示（読み取り専用）
        st.info(f"開催主体: {gb_selected} / 会議体: {conf_selected}")

        # 日付入力
        meeting_date = st.date_input("開催日", value=date.today())

        # URL入力
        url = st.text_input(
            "会議URL（議事録PDFのURLなど）",
            placeholder="https://example.com/minutes.pdf",
        )

        # 送信ボタン
        submitted = st.form_submit_button("登録")

        if submitted and selected_conf:
            if not url:
                st.error("URLを入力してください")
            else:
                try:
                    meeting_id = repo.create_meeting(
                        conference_id=selected_conf["id"],
                        meeting_date=meeting_date,
                        url=url,
                    )
                    st.success(f"会議を登録しました (ID: {meeting_id})")

                    # フォームをリセット
                    st.rerun()
                except (SaveError, DatabaseError) as e:
                    st.error(f"会議の登録に失敗しました: {str(e)}")
                except Exception as e:
                    st.error(f"予期しないエラーが発生しました: {str(e)}")

    # 登録済み会議体の確認セクション
    with st.expander("登録済み会議体一覧", expanded=False):
        all_conferences = repo.get_all_conferences()
        if all_conferences:
            # 開催主体ごとにグループ化して表示
            conf_df = pd.DataFrame(all_conferences)

            for gb_name in conf_df["governing_body_name"].unique():
                gb_conf_df = conf_df[conf_df["governing_body_name"] == gb_name]
                st.markdown(f"**{gb_name}**")
                display_df = gb_conf_df[["name", "type"]].copy()
                display_df.columns = ["会議体名", "会議体種別"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("会議体が登録されていません")

    repo.close()


def edit_meeting():
    """会議編集フォーム"""
    st.subheader("会議編集")

    if not st.session_state.edit_mode or not st.session_state.edit_meeting_id:
        st.info(
            "編集する会議を選択してください（会議一覧タブから編集ボタンをクリック）"
        )
        return

    repo = MeetingRepository()

    # 編集対象の会議情報を取得
    meeting = repo.get_meeting_by_id(st.session_state.edit_meeting_id)
    if not meeting:
        st.error("会議が見つかりません")
        st.session_state.edit_mode = False
        st.session_state.edit_meeting_id = None
        return

    st.info(f"編集中: {meeting['governing_body_name']} - {meeting['conference_name']}")

    with st.form("edit_meeting_form"):
        # 日付入力
        current_date = meeting["date"] if meeting["date"] else date.today()
        meeting_date = st.date_input("開催日", value=current_date)

        # URL入力
        url = st.text_input(
            "会議URL（議事録PDFのURLなど）",
            value=meeting["url"] or "",
            placeholder="https://example.com/minutes.pdf",
        )

        # ボタン
        col1, col2 = st.columns(2)

        with col1:
            submitted = st.form_submit_button("更新")

        with col2:
            cancelled = st.form_submit_button("キャンセル")

        if submitted:
            if not url:
                st.error("URLを入力してください")
            else:
                try:
                    if repo.update_meeting(
                        meeting_id=st.session_state.edit_meeting_id,
                        meeting_date=meeting_date,
                        url=url,
                    ):
                        st.success("会議を更新しました")
                        st.session_state.edit_mode = False
                        st.session_state.edit_meeting_id = None
                        st.rerun()
                    else:
                        st.error("会議の更新に失敗しました")
                except (UpdateError, RecordNotFoundError, DatabaseError) as e:
                    st.error(f"会議の更新に失敗しました: {str(e)}")
                except Exception as e:
                    st.error(f"予期しないエラーが発生しました: {str(e)}")

        if cancelled:
            st.session_state.edit_mode = False
            st.session_state.edit_meeting_id = None
            st.rerun()

    repo.close()


def manage_political_parties():
    """政党管理（議員一覧ページURL）"""
    st.header("政党管理")
    st.markdown("各政党の議員一覧ページURLを管理します")

    engine = get_db_engine()
    conn = engine.connect()

    try:
        # 政党一覧を取得
        query = text("""
            SELECT id, name, members_list_url
            FROM political_parties
            ORDER BY name
        """)
        result = conn.execute(query)
        parties = result.fetchall()

        if not parties:
            st.info("政党が登録されていません")
            return

        # SEEDファイル生成セクション（一番上に配置）
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### SEEDファイル生成")
                st.markdown("現在登録されている政党データからSEEDファイルを生成します")
            with col2:
                if st.button(
                    "SEEDファイル生成",
                    key="generate_political_parties_seed",
                    type="primary",
                ):
                    with st.spinner("SEEDファイルを生成中..."):
                        try:
                            generator = SeedGenerator()
                            seed_content = generator.generate_political_parties_seed()

                            # ファイルに保存
                            output_path = (
                                "database/seed_political_parties_generated.sql"
                            )
                            with open(output_path, "w") as f:
                                f.write(seed_content)

                            st.success(f"✅ SEEDファイルを生成しました: {output_path}")

                            # 生成内容をプレビュー表示
                            with st.expander("生成されたSEEDファイル", expanded=False):
                                st.code(seed_content, language="sql")
                        except Exception as e:
                            st.error(
                                f"❌ SEEDファイル生成中にエラーが発生しました: {str(e)}"
                            )

        st.markdown("---")

        # フィルター設定と統計情報
        col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 6])
        with col_filter1:
            url_filter = st.selectbox(
                "議員一覧URL",
                ["すべて", "設定済み", "未設定"],
                key="party_url_filter",
            )

        # フィルタリング適用
        filtered_parties = parties
        if url_filter == "設定済み":
            filtered_parties = [party for party in parties if party.members_list_url]
        elif url_filter == "未設定":
            filtered_parties = [
                party for party in parties if not party.members_list_url
            ]

        # 統計情報を表示
        total_count = len(parties)
        with_url_count = len([p for p in parties if p.members_list_url])
        without_url_count = total_count - with_url_count

        with col_filter2:
            st.metric(
                "設定済み",
                f"{with_url_count}/{total_count}",
                (
                    f"{with_url_count / total_count * 100:.0f}%"
                    if total_count > 0
                    else "0%"
                ),
            )

        with col_filter3:
            st.metric(
                "未設定",
                f"{without_url_count}/{total_count}",
                (
                    f"{without_url_count / total_count * 100:.0f}%"
                    if total_count > 0
                    else "0%"
                ),
            )

        st.markdown("---")

        # フィルター後の政党が存在するかチェック
        if filtered_parties:
            # 政党ごとにURL編集フォームを表示
            for idx, party in enumerate(filtered_parties):
                # 各政党を個別に表示
                col1, col2, col3, col4 = st.columns([3, 2, 3, 1])

                with col1:
                    st.markdown(f"**{party.name}**")

                with col2:
                    if party.members_list_url:
                        st.success("✅ URL設定済み")
                    else:
                        st.error("❌ URL未設定")

                with col3:
                    # 編集状態の管理
                    edit_key = f"edit_party_{party.id}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    # 現在のURLを表示（編集モードでない場合）
                    if not st.session_state[edit_key] and party.members_list_url:
                        url = party.members_list_url
                        display_url = url[:30] + "..." if len(url) > 30 else url
                        st.caption(f"🔗 {display_url}")

                with col4:
                    if st.button("✏️ 編集", key=f"edit_party_btn_{party.id}"):
                        st.session_state[edit_key] = not st.session_state[edit_key]
                        st.rerun()

                # 編集モード
                if st.session_state[edit_key]:
                    with st.container():
                        st.markdown("---")
                        col_input, col_save, col_cancel = st.columns([6, 1, 1])

                        with col_input:
                            new_url = st.text_input(
                                "議員一覧ページURL",
                                value=party.members_list_url or "",
                                key=f"party_url_input_{party.id}",
                                placeholder="https://example.com/members",
                                help="この政党の議員一覧が掲載されているWebページのURL",
                            )

                        with col_save:
                            if st.button("💾 保存", key=f"save_party_btn_{party.id}"):
                                # URLを更新
                                update_query = text("""
                                    UPDATE political_parties
                                    SET members_list_url = :url
                                    WHERE id = :party_id
                                """)
                                conn.execute(
                                    update_query,
                                    {
                                        "url": new_url if new_url else None,
                                        "party_id": party.id,
                                    },
                                )
                                conn.commit()
                                st.session_state[edit_key] = False
                                st.success(
                                    f"✅ {party.name}の議員一覧URLを更新しました"
                                )
                                st.rerun()

                        with col_cancel:
                            if st.button(
                                "❌ キャンセル", key=f"cancel_party_btn_{party.id}"
                            ):
                                st.session_state[edit_key] = False
                                st.rerun()

                # 区切り線（最後の項目以外）
                if idx < len(filtered_parties) - 1:
                    st.markdown("---")
        else:
            # フィルター結果が空の場合
            if url_filter == "設定済み":
                st.info("議員一覧URLが設定されている政党はありません")
            elif url_filter == "未設定":
                st.info("すべての政党で議員一覧URLが設定されています")

        # 一括確認セクション
        with st.expander("登録済みURL一覧", expanded=False):
            df_data = []
            for party in parties:
                df_data.append(
                    {
                        "政党名": party.name,
                        "議員一覧URL": party.members_list_url or "未設定",
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)

    finally:
        conn.close()


def manage_conferences():
    """会議体管理（登録・編集・削除）"""
    st.header("会議体管理")
    st.markdown("会議体（議会・委員会など）を管理します")

    conf_repo = ConferenceRepository()

    # 会議体管理用のメッセージを表示
    if (
        "conf_success_message" in st.session_state
        and st.session_state.conf_success_message
    ):
        col1, col2 = st.columns([10, 1])
        with col1:
            st.success(st.session_state.conf_success_message)
        with col2:
            if st.button("✖", key="clear_conf_success", help="メッセージを閉じる"):
                st.session_state.conf_success_message = None
                st.session_state.conf_message_details = None
                st.rerun()

        # 詳細情報があれば表示
        if (
            "conf_message_details" in st.session_state
            and st.session_state.conf_message_details
        ):
            with st.expander("詳細を表示", expanded=True):
                st.markdown(st.session_state.conf_message_details)

    if "conf_error_message" in st.session_state and st.session_state.conf_error_message:
        col1, col2 = st.columns([10, 1])
        with col1:
            st.error(st.session_state.conf_error_message)
        with col2:
            if st.button("✖", key="clear_conf_error", help="メッセージを閉じる"):
                st.session_state.conf_error_message = None
                st.rerun()

    # サブタブを作成
    conf_tab1, conf_tab2, conf_tab3 = st.tabs(["会議体一覧", "新規登録", "編集・削除"])

    with conf_tab1:
        # 会議体一覧
        st.subheader("登録済み会議体一覧")

        conferences = conf_repo.get_all_conferences()
        if conferences:
            # SEEDファイル生成セクション（一番上に配置）
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### SEEDファイル生成")
                    st.markdown(
                        "現在登録されている会議体データからSEEDファイルを生成します"
                    )
                with col2:
                    if st.button(
                        "SEEDファイル生成",
                        key="generate_conferences_seed",
                        type="primary",
                    ):
                        with st.spinner("SEEDファイルを生成中..."):
                            try:
                                generator = SeedGenerator()
                                seed_content = generator.generate_conferences_seed()

                                # ファイルに保存
                                output_path = "database/seed_conferences_generated.sql"
                                with open(output_path, "w") as f:
                                    f.write(seed_content)

                                st.success(
                                    f"✅ SEEDファイルを生成しました: {output_path}"
                                )

                                # 生成内容をプレビュー表示
                                with st.expander(
                                    "生成されたSEEDファイル", expanded=False
                                ):
                                    st.code(seed_content, language="sql")
                            except Exception as e:
                                st.error(
                                    f"❌ SEEDファイル生成中にエラーが"
                                    f"発生しました: {str(e)}"
                                )

            st.markdown("---")
            # フィルター設定
            col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 6])
            with col_filter1:
                url_filter = st.selectbox(
                    "議員紹介URL",
                    ["すべて", "設定済み", "未設定"],
                    key="conf_url_filter",
                )

            # フィルタリング適用
            filtered_conferences = conferences
            if url_filter == "設定済み":
                filtered_conferences = [
                    conf for conf in conferences if conf.get("members_introduction_url")
                ]
            elif url_filter == "未設定":
                filtered_conferences = [
                    conf
                    for conf in conferences
                    if not conf.get("members_introduction_url")
                ]

            # 統計情報を表示
            total_count = len(conferences)
            with_url_count = len(
                [c for c in conferences if c.get("members_introduction_url")]
            )
            without_url_count = total_count - with_url_count

            with col_filter2:
                st.metric(
                    "設定済み",
                    f"{with_url_count}/{total_count}",
                    (
                        f"{with_url_count / total_count * 100:.0f}%"
                        if total_count > 0
                        else "0%"
                    ),
                )

            with col_filter3:
                st.metric(
                    "未設定",
                    f"{without_url_count}/{total_count}",
                    (
                        f"{without_url_count / total_count * 100:.0f}%"
                        if total_count > 0
                        else "0%"
                    ),
                )

            st.markdown("---")

            # フィルター後の会議体が存在するかチェック
            if filtered_conferences:
                # 開催主体でグループ化
                grouped_conferences = {}
                for conf in filtered_conferences:
                    gb_name = conf["governing_body_name"] or "未設定"
                    if gb_name not in grouped_conferences:
                        grouped_conferences[gb_name] = []
                    grouped_conferences[gb_name].append(conf)

                # 開催主体ごとに表示（未設定を最後に）
                sorted_gb_names = sorted(
                    grouped_conferences.keys(),
                    key=lambda x: (x == "未設定", x),  # 未設定を最後に
                )
                for gb_name in sorted_gb_names:
                    gb_conferences = grouped_conferences[gb_name]
                    with st.expander(f"📂 {gb_name}", expanded=True):
                        for idx, conf in enumerate(gb_conferences):
                            # 各会議体を個別に表示
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                            with col1:
                                st.markdown(f"**{conf['name']}**")
                                if conf.get("type"):
                                    st.caption(f"種別: {conf['type']}")

                            with col2:
                                if conf.get("members_introduction_url"):
                                    st.success("✅ URL設定済み")
                                else:
                                    st.error("❌ URL未設定")

                            with col3:
                                # 編集状態の管理
                                edit_key = f"edit_conf_{conf['id']}"
                                if edit_key not in st.session_state:
                                    st.session_state[edit_key] = False

                                # 現在のURLを表示（編集モードでない場合）
                                if not st.session_state[edit_key] and conf.get(
                                    "members_introduction_url"
                                ):
                                    url = conf["members_introduction_url"]
                                    display_url = (
                                        url[:30] + "..." if len(url) > 30 else url
                                    )
                                    st.caption(f"🔗 {display_url}")

                            with col4:
                                if st.button("✏️ 編集", key=f"edit_btn_{conf['id']}"):
                                    st.session_state[edit_key] = not st.session_state[
                                        edit_key
                                    ]
                                    st.rerun()

                            # 編集モード
                            if st.session_state[edit_key]:
                                with st.container():
                                    st.markdown("---")

                                    # 開催主体の選択
                                    governing_bodies = conf_repo.get_governing_bodies()
                                    gb_options = ["なし"] + [
                                        f"{gb['name']} ({gb['type']})"
                                        for gb in governing_bodies
                                    ]

                                    # 現在の開催主体を選択状態にする
                                    current_gb_index = 0
                                    if conf.get("governing_body_id"):
                                        for i, gb in enumerate(governing_bodies):
                                            if gb["id"] == conf["governing_body_id"]:
                                                current_gb_index = (
                                                    i + 1
                                                )  # "なし"の分を加算
                                                break

                                    selected_gb = st.selectbox(
                                        "開催主体",
                                        gb_options,
                                        index=current_gb_index,
                                        key=f"gb_select_{conf['id']}",
                                    )

                                    # URLの入力
                                    new_url = st.text_input(
                                        "議員紹介URL",
                                        value=conf.get("members_introduction_url", ""),
                                        key=f"url_input_{conf['id']}",
                                        placeholder="https://example.com/members",
                                    )

                                    col_save, col_cancel = st.columns([1, 1])

                                with col_save:
                                    if st.button(
                                        "💾 保存", key=f"save_btn_{conf['id']}"
                                    ):
                                        # 選択された開催主体のIDを取得
                                        selected_gb_id = None
                                        if selected_gb != "なし":
                                            for gb in governing_bodies:
                                                if (
                                                    f"{gb['name']} ({gb['type']})"
                                                    == selected_gb
                                                ):
                                                    selected_gb_id = gb["id"]
                                                    break

                                        # URLと開催主体を更新
                                        conf_repo.update_conference(
                                            conference_id=conf["id"],
                                            governing_body_id=selected_gb_id,
                                            members_introduction_url=(
                                                new_url if new_url else None
                                            ),
                                        )
                                        st.session_state[edit_key] = False
                                        st.session_state.conf_success_message = (
                                            f"✅ {conf['name']}を更新しました"
                                        )
                                        st.rerun()

                                with col_cancel:
                                    if st.button(
                                        "❌ キャンセル",
                                        key=f"cancel_btn_{conf['id']}",
                                    ):
                                        st.session_state[edit_key] = False
                                        st.rerun()

                            # 区切り線（最後の項目以外）
                            if idx < len(gb_conferences) - 1:
                                st.markdown("---")
            else:
                # フィルター結果が空の場合
                if url_filter == "設定済み":
                    st.info("議員紹介URLが設定済みの会議体はありません")
                elif url_filter == "未設定":
                    st.info("議員紹介URLが未設定の会議体はありません")
        else:
            st.info("会議体が登録されていません")

    with conf_tab2:
        # 新規登録
        st.subheader("新規会議体登録")

        with st.form("new_conference_form"):
            # 開催主体選択
            governing_bodies = conf_repo.get_governing_bodies()
            gb_options = ["なし"] + [
                f"{gb['name']} ({gb['type']})" for gb in governing_bodies
            ]
            gb_selected = st.selectbox("開催主体（任意）", gb_options)

            # 選択された開催主体のIDを取得
            selected_gb_id = None
            if gb_selected != "なし":
                for gb in governing_bodies:
                    if f"{gb['name']} ({gb['type']})" == gb_selected:
                        selected_gb_id = gb["id"]
                        break

            # 会議体情報入力
            conf_name = st.text_input("会議体名", placeholder="例: 本会議、予算委員会")
            conf_type = st.text_input(
                "会議体種別（任意）",
                placeholder="例: 本会議、常任委員会、特別委員会",
            )
            members_url = st.text_input(
                "議員紹介URL（任意）",
                placeholder="https://example.com/members",
                help="会議体の議員一覧が掲載されているページのURL",
            )

            submitted = st.form_submit_button("登録")

            if submitted:
                if not conf_name:
                    st.session_state.conf_error_message = "会議体名を入力してください"
                    st.rerun()
                else:
                    conf_id = conf_repo.create_conference(
                        name=conf_name,
                        governing_body_id=selected_gb_id,  # Noneでも可
                        type=conf_type if conf_type else None,
                    )
                    if conf_id:
                        # 議員紹介URLが入力されていれば更新
                        if members_url:
                            conf_repo.update_conference_members_url(
                                conference_id=conf_id,
                                members_introduction_url=members_url,
                            )

                        # 成功メッセージと詳細をセッション状態に保存
                        st.session_state.conf_success_message = (
                            "✅ 会議体を登録しました"
                        )
                        st.session_state.conf_message_details = f"""
                        **会議体ID:** {conf_id}

                        **開催主体:** {gb_selected}

                        **会議体名:** {conf_name}

                        **会議体種別:** {conf_type if conf_type else "未設定"}

                        **議員紹介URL:** {"✅ 設定済み" if members_url else "❌ 未設定"}
                        {f"\\n- {members_url}" if members_url else ""}
                        """

                        st.rerun()
                    else:
                        st.session_state.conf_error_message = (
                            "会議体の登録に失敗しました"
                            "（同じ名前の会議体が既に存在する可能性があります）"
                        )
                        st.rerun()

    with conf_tab3:
        # 編集・削除
        st.subheader("会議体の編集・削除")

        conferences = conf_repo.get_all_conferences()
        if not conferences:
            st.info("編集する会議体がありません")
        else:
            # 会議体選択
            conf_options = []
            conf_map = {}
            for conf in conferences:
                display_name = f"{conf['governing_body_name']} - {conf['name']}"
                if conf.get("type"):
                    display_name += f" ({conf['type']})"
                # URL設定状態を追加
                url_status = "✅" if conf.get("members_introduction_url") else "❌"
                display_name = f"{url_status} {display_name}"
                conf_options.append(display_name)
                conf_map[display_name] = conf

            selected_conf_display = st.selectbox("編集する会議体を選択", conf_options)

            selected_conf = conf_map[selected_conf_display]

            # 現在の議員紹介URLの状態を表示
            if selected_conf.get("members_introduction_url"):
                st.info(f"🔗 現在のURL: {selected_conf['members_introduction_url']}")
            else:
                st.warning("❌ 議員紹介URLが未設定です")

            # 編集フォーム
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 編集")
                with st.form("edit_conference_form"):
                    new_name = st.text_input("会議体名", value=selected_conf["name"])
                    new_type = st.text_input(
                        "会議体種別", value=selected_conf.get("type", "")
                    )
                    new_members_url = st.text_input(
                        "議員紹介URL",
                        value=selected_conf.get("members_introduction_url", "") or "",
                        placeholder="https://example.com/members",
                        help="会議体の議員一覧が掲載されているページのURL",
                    )

                    submitted = st.form_submit_button("更新")

                    if submitted:
                        if not new_name:
                            st.error("会議体名を入力してください")
                        else:
                            # 基本情報を更新
                            if conf_repo.update_conference(
                                conference_id=selected_conf["id"],
                                name=new_name,
                                type=new_type if new_type else None,
                            ):
                                # 議員紹介URLを更新
                                conf_repo.update_conference_members_url(
                                    conference_id=selected_conf["id"],
                                    members_introduction_url=new_members_url
                                    if new_members_url
                                    else None,
                                )
                                st.success("会議体を更新しました")
                                st.rerun()
                            else:
                                st.error("会議体の更新に失敗しました")

            with col2:
                st.markdown("#### 削除")
                st.warning(
                    "⚠️ 会議体を削除すると、関連するデータも削除される可能性があります"
                )

                if st.button("🗑️ この会議体を削除", type="secondary"):
                    if conf_repo.delete_conference(selected_conf["id"]):
                        st.success("会議体を削除しました")
                        st.rerun()
                    else:
                        st.error(
                            "会議体を削除できませんでした"
                            "（関連する会議が存在する可能性があります）"
                        )

    conf_repo.close()


def execute_processes():
    """処理実行タブ"""
    st.header("処理実行")
    st.markdown("各種処理をWebUIから実行できます")

    # 処理カテゴリ選択
    process_category = st.selectbox(
        "処理カテゴリを選択",
        [
            "議事録処理",
            "政治家情報抽出",
            "会議体メンバー管理",
            "スクレイピング",
            "その他",
        ],
    )

    if process_category == "議事録処理":
        execute_minutes_processes()
    elif process_category == "政治家情報抽出":
        execute_politician_processes()
    elif process_category == "会議体メンバー管理":
        execute_conference_member_processes()
    elif process_category == "スクレイピング":
        execute_scraping_processes()
    else:
        execute_other_processes()


def run_command_with_progress(command, process_name):
    """コマンドをバックグラウンドで実行し、進捗を管理"""
    # セッション状態の初期化を確認
    if "process_status" not in st.session_state:
        st.session_state.process_status = {}
    if "process_output" not in st.session_state:
        st.session_state.process_output = {}

    st.session_state.process_status[process_name] = "running"
    st.session_state.process_output[process_name] = []

    # プレースホルダーを作成して、後で更新できるようにする
    status_placeholder = st.empty()
    output_placeholder = st.empty()

    # コンテナ内で直接コマンドを実行
    try:
        # Streamlitから実行されていることを示す環境変数を設定
        import os
        import shlex

        env = os.environ.copy()
        env["STREAMLIT_RUNNING"] = "true"

        # コマンドを安全に分割（文字列の場合）
        if isinstance(command, str):
            command_list = shlex.split(command)
        else:
            command_list = command

        # プロセスを開始（shell=Falseで安全に実行）
        process = subprocess.Popen(
            command_list,
            shell=False,  # セキュリティ向上のためshell=False
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        # 出力を収集するリスト
        output_lines = []

        # 出力をリアルタイムで収集
        with status_placeholder.container():
            st.info("🔄 処理実行中...")

        for line in iter(process.stdout.readline, ""):
            if line:
                output_lines.append(line.strip())
                # 出力をリアルタイムで更新
                with output_placeholder.container():
                    with st.expander("実行ログ", expanded=True):
                        # 最新の10行のみ表示
                        recent_lines = output_lines[-10:]
                        st.code("\n".join(recent_lines), language="text")

        process.wait()

        # 結果をセッション状態に保存
        st.session_state.process_output[process_name] = output_lines

        if process.returncode == 0:
            st.session_state.process_status[process_name] = "completed"
            with status_placeholder.container():
                st.success("✅ 処理が完了しました")
        else:
            st.session_state.process_status[process_name] = "failed"
            with status_placeholder.container():
                st.error("❌ 処理が失敗しました")

        # 最終的な出力を表示（全ログを表示）
        with output_placeholder.container():
            with st.expander("実行ログ", expanded=False):
                st.code("\n".join(output_lines), language="text")

    except subprocess.TimeoutExpired:
        st.session_state.process_status[process_name] = "timeout"
        st.session_state.process_output[process_name] = ["処理がタイムアウトしました"]
        with status_placeholder.container():
            st.error("❌ 処理がタイムアウトしました")
        with output_placeholder.container():
            st.code("処理がタイムアウトしました", language="text")
    except ProcessingError as e:
        st.session_state.process_status[process_name] = "error"
        st.session_state.process_output[process_name] = [f"処理エラー: {str(e)}"]
        with status_placeholder.container():
            st.error("❌ 処理エラーが発生しました")
        with output_placeholder.container():
            st.code(f"処理エラー: {str(e)}", language="text")
    except Exception as e:
        st.session_state.process_status[process_name] = "error"
        st.session_state.process_output[process_name] = [f"予期しないエラー: {str(e)}"]
        with status_placeholder.container():
            st.error("❌ 予期しないエラーが発生しました")
        with output_placeholder.container():
            st.code(f"予期しないエラー: {str(e)}", language="text")


def execute_minutes_processes():
    """議事録処理の実行"""
    st.subheader("議事録処理")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 議事録分割処理")
        st.markdown("PDFから議事録を読み込み、発言ごとに分割します")

        # 会議情報の表示用にリポジトリを作成
        repo = MeetingRepository()

        # すべての会議を取得してセレクトボックスの選択肢を作成
        all_meetings = repo.get_meetings()

        if not all_meetings:
            st.warning("登録されている会議がありません")
            meeting_id = None
        else:
            # 会議を日付順（新しい順）にソート
            all_meetings.sort(key=lambda x: x["date"], reverse=True)

            # セレクトボックスの選択肢を作成
            meeting_options = ["なし（全体処理）"] + [
                (
                    f"ID:{m['id']} - {m['date'].strftime('%Y/%m/%d')} "
                    f"{m['governing_body_name']} {m['conference_name']}"
                )
                for m in all_meetings
            ]

            selected_meeting = st.selectbox(
                "処理する会議を選択（GCSから処理する場合）",
                meeting_options,
                help="会議を選択するとGCSから議事録を取得して処理します",
            )

            # 選択された会議のIDを取得
            if selected_meeting == "なし（全体処理）":
                meeting_id = None
            else:
                # "ID:123 - ..." の形式からIDを抽出
                meeting_id = int(selected_meeting.split(" - ")[0].replace("ID:", ""))

                # 選択された会議の詳細情報を表示
                selected_meeting_info = next(
                    m for m in all_meetings if m["id"] == meeting_id
                )
                meeting_date_str = selected_meeting_info["date"].strftime(
                    "%Y年%m月%d日"
                )
                meeting_url = (
                    selected_meeting_info["url"]
                    if selected_meeting_info["url"]
                    else "URLなし"
                )
                st.info(
                    f"**選択された会議の詳細:**\n"
                    f"- 開催主体: {selected_meeting_info['governing_body_name']}\n"
                    f"- 会議体: {selected_meeting_info['conference_name']}\n"
                    f"- 開催日: {meeting_date_str}\n"
                    f"- URL: {meeting_url}"
                )

        repo.close()

        if st.button("議事録分割を実行", key="process_minutes"):
            command = "uv run polibase process-minutes"
            if meeting_id:
                command = (
                    f"uv run python -m src.process_minutes --meeting-id {meeting_id}"
                )

            run_command_with_progress(command, "process_minutes")

            # 処理完了後、作成されたレコードを表示
            if (
                "process_minutes" in st.session_state.process_status
                and st.session_state.process_status["process_minutes"] == "completed"
            ):
                # データベースから処理結果を取得
                engine = get_db_engine()
                with engine.connect() as conn:
                    if meeting_id:
                        # 特定の会議の議事録を取得
                        result = conn.execute(
                            text("""
                            SELECT m.id, m.url, m.created_at,
                                   mt.url as meeting_url, mt.date as meeting_date,
                                   gb.name as governing_body_name,
                                   conf.name as conference_name,
                                   COUNT(c.id) as conversation_count
                            FROM minutes m
                            LEFT JOIN conversations c ON m.id = c.minutes_id
                            LEFT JOIN meetings mt ON m.meeting_id = mt.id
                            LEFT JOIN conferences conf ON mt.conference_id = conf.id
                            LEFT JOIN governing_bodies gb
                                ON conf.governing_body_id = gb.id
                            WHERE m.meeting_id = :meeting_id
                            GROUP BY m.id, m.url, m.created_at, mt.url, mt.date,
                                     gb.name, conf.name
                            ORDER BY m.created_at DESC
                            LIMIT 10
                        """),
                            {"meeting_id": meeting_id},
                        )
                    else:
                        # 最新の議事録を取得
                        result = conn.execute(
                            text("""
                            SELECT m.id, m.url, m.created_at,
                                   mt.url as meeting_url, mt.date as meeting_date,
                                   gb.name as governing_body_name,
                                   conf.name as conference_name,
                                   COUNT(c.id) as conversation_count
                            FROM minutes m
                            LEFT JOIN conversations c ON m.id = c.minutes_id
                            LEFT JOIN meetings mt ON m.meeting_id = mt.id
                            LEFT JOIN conferences conf ON mt.conference_id = conf.id
                            LEFT JOIN governing_bodies gb
                                ON conf.governing_body_id = gb.id
                            WHERE m.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                            GROUP BY m.id, m.url, m.created_at, mt.url, mt.date,
                                     gb.name, conf.name
                            ORDER BY m.created_at DESC
                            LIMIT 10
                        """)
                        )

                    minutes_records = result.fetchall()

                    if minutes_records:
                        st.success(
                            f"✅ {len(minutes_records)}件の議事録が作成されました"
                        )

                        # 作成されたレコードの詳細を表示
                        with st.expander("作成されたレコード詳細", expanded=True):
                            for record in minutes_records:
                                # タイトルを生成（会議情報から）
                                title = (
                                    f"{record.governing_body_name} "
                                    f"{record.conference_name}"
                                )
                                if record.meeting_date:
                                    date_str = record.meeting_date.strftime(
                                        "%Y年%m月%d日"
                                    )
                                    title += f" ({date_str})"

                                created_at_str = record.created_at.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )
                                st.markdown(f"""
                                **議事録ID: {record.id}**
                                - 会議: {title}
                                - 発言数: {record.conversation_count}件
                                - 議事録URL: {record.url if record.url else "未設定"}
                                - 作成日時: {created_at_str}
                                """)

                                # この議事録に含まれる発言（conversations）を取得
                                if record.conversation_count > 0:
                                    conv_result = conn.execute(
                                        text("""
                                        SELECT c.id, c.speaker_name, c.comment,
                                               c.speaker_id,
                                               s.name as linked_speaker_name
                                        FROM conversations c
                                        LEFT JOIN speakers s ON c.speaker_id = s.id
                                        WHERE c.minutes_id = :minutes_id
                                        ORDER BY c.id
                                        LIMIT 5
                                    """),
                                        {"minutes_id": record.id},
                                    )

                                    conversations = conv_result.fetchall()

                                    st.markdown("**含まれる発言（最初の5件）:**")
                                    for conv in conversations:
                                        speaker_info = f"発言者: {conv.speaker_name}"
                                        if conv.speaker_id:
                                            speaker_info += (
                                                f" → 紐付け済み: "
                                                f"{conv.linked_speaker_name}"
                                            )

                                        # 発言内容を短く表示（最初の100文字）
                                        content_preview = (
                                            conv.comment[:100] + "..."
                                            if len(conv.comment) > 100
                                            else conv.comment
                                        )

                                        st.markdown(f"""
                                        - **ID: {conv.id}** - {speaker_info}
                                          - 内容: {content_preview}
                                        """)

                                    if record.conversation_count > 5:
                                        remaining = record.conversation_count - 5
                                        st.markdown(f"*...他{remaining}件の発言*")

                                st.divider()

    with col2:
        st.markdown("### 発言者抽出処理")
        st.markdown("議事録から発言者を抽出し、speaker/politicianと紐付けます")

        if st.button("発言者抽出を実行", key="extract_speakers"):
            command = "uv run python -m src.extract_speakers_from_minutes"

            run_command_with_progress(command, "extract_speakers")

            # 処理完了後、作成されたレコードを表示
            if (
                "extract_speakers" in st.session_state.process_status
                and st.session_state.process_status["extract_speakers"] == "completed"
            ):
                # データベースから処理結果を取得
                engine = get_db_engine()
                with engine.connect() as conn:
                    # 最新作成されたspeakersを取得
                    speakers_result = conn.execute(
                        text("""
                        SELECT s.id, s.name, s.type, s.is_politician,
                               s.political_party_name, s.created_at,
                               COUNT(c.id) as conversation_count
                        FROM speakers s
                        LEFT JOIN conversations c ON s.id = c.speaker_id
                        WHERE s.created_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                        GROUP BY s.id, s.name, s.type, s.is_politician,
                                 s.political_party_name, s.created_at
                        ORDER BY s.created_at DESC
                        LIMIT 20
                    """)
                    )

                    speakers_records = speakers_result.fetchall()

                    # 紐付けられた発言数を取得
                    linked_result = conn.execute(
                        text("""
                        SELECT COUNT(*) as count
                        FROM conversations
                        WHERE speaker_id IS NOT NULL
                        AND updated_at >= CURRENT_TIMESTAMP - INTERVAL '1 hour'
                    """)
                    )
                    linked_count = linked_result.fetchone().count

                    if speakers_records or linked_count > 0:
                        st.success("✅ 発言者抽出処理が完了しました")

                        # 作成されたレコードの詳細を表示
                        with st.expander("処理結果詳細", expanded=True):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.metric(
                                    "新規作成された発言者", f"{len(speakers_records)}人"
                                )
                            with col2:
                                st.metric("紐付けられた発言数", f"{linked_count}件")

                            if speakers_records:
                                st.markdown("#### 新規作成された発言者")
                                for speaker in speakers_records:
                                    politician_badge = (
                                        "✅ 政治家"
                                        if speaker.is_politician
                                        else "❌ 非政治家"
                                    )
                                    party_info = (
                                        f" ({speaker.political_party_name})"
                                        if speaker.political_party_name
                                        else ""
                                    )

                                    st.markdown(f"""
                                    **{speaker.name}{party_info}** {politician_badge}
                                    - ID: {speaker.id}
                                    - タイプ: {speaker.type}
                                    - 紐付け発言数: {speaker.conversation_count}件
                                    """)


def execute_politician_processes():
    """政治家情報抽出処理の実行"""
    st.subheader("政治家情報抽出")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 政治家情報取得処理")
        st.markdown("政党のWebサイトから政治家情報を取得します")

        # データベースから政党リストを取得
        engine = get_db_engine()
        with engine.connect() as conn:
            parties_result = conn.execute(
                text("""
                SELECT id, name, members_list_url
                FROM political_parties
                WHERE members_list_url IS NOT NULL
                ORDER BY name
            """)
            )
            parties = parties_result.fetchall()

        if not parties:
            st.warning(
                "議員一覧URLが設定されている政党がありません。政党管理タブでURLを設定してください。"
            )
        else:
            # 政党選択オプション
            party_options = ["すべての政党"] + [
                f"{party.name} (ID: {party.id})" for party in parties
            ]
            selected_party = st.selectbox("取得対象の政党を選択", party_options)

            # 選択された政党の情報を表示
            if selected_party != "すべての政党":
                # 選択された政党の情報を取得
                party_id = int(selected_party.split("ID: ")[1].rstrip(")"))
                selected_party_info = next(p for p in parties if p.id == party_id)
                st.info(f"**取得元URL:** {selected_party_info.members_list_url}")
            else:
                st.info(f"**対象政党数:** {len(parties)}党")
                with st.expander("対象政党一覧", expanded=False):
                    for party in parties:
                        st.markdown(f"- **{party.name}**: {party.members_list_url}")

            # ドライラン（実際には保存しない）オプション
            dry_run = st.checkbox(
                "ドライラン（実際には保存しない）",
                value=False,
                help="データを実際に保存せず、取得できる情報を確認します",
            )

            if st.button("政治家情報取得を実行", key="extract_politicians"):
                # Playwrightの依存関係とブラウザをインストール
                install_command = (
                    "uv run playwright install-deps && "
                    "uv run playwright install chromium"
                )

                # スクレイピングコマンドを構築
                if selected_party == "すべての政党":
                    scrape_command = "uv run polibase scrape-politicians --all-parties"
                else:
                    # "党名 (ID: 123)" の形式からIDを抽出
                    party_id = int(selected_party.split("ID: ")[1].rstrip(")"))
                    scrape_command = (
                        f"uv run polibase scrape-politicians --party-id {party_id}"
                    )

                if dry_run:
                    scrape_command += " --dry-run"

                command = f"{install_command} && {scrape_command}"

                with st.spinner("政治家情報取得処理を実行中..."):
                    run_command_with_progress(command, "extract_politicians")

        # 進捗表示
        if "extract_politicians" in st.session_state.process_status:
            status = st.session_state.process_status["extract_politicians"]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if "extract_politicians" in st.session_state.process_output:
                with st.expander("実行ログ", expanded=False):
                    output = "\n".join(
                        st.session_state.process_output["extract_politicians"]
                    )
                    st.code(output, language="text")

    with col2:
        st.markdown("### 紐付け処理")

        # 処理タイプの選択
        link_type = st.radio(
            "紐付け処理の種類",
            ["発言-発言者紐付け", "発言者-政治家紐付け"],
            help="どの紐付け処理を実行するか選択してください",
        )

        if link_type == "発言-発言者紐付け":
            st.markdown("議事録の発言を発言者（speakers）に紐付けます")
            use_llm = st.checkbox("LLMを使用する", value=True)

            if st.button("発言-発言者紐付けを実行", key="update_speakers"):
                command = "uv run polibase update-speakers"
                if use_llm:
                    command += " --use-llm"

                with st.spinner("発言-発言者紐付け処理を実行中..."):
                    run_command_with_progress(command, "update_speakers")

        else:  # 発言者-政治家紐付け
            st.markdown("発言者（speakers）を政治家（politicians）に紐付けます")
            use_llm_politician = st.checkbox(
                "LLMを使用する",
                value=True,
                key="use_llm_politician",
                help="LLMを使用して表記ゆれや敬称の違いも考慮した高度なマッチングを行います",
            )

            if use_llm_politician:
                st.info("LLMを使用した高度なマッチング（表記ゆれ・敬称対応）")
            else:
                st.info("名前の完全一致による自動紐付けを行います")

            if st.button(
                "発言者-政治家紐付けを実行", key="link_speakers_to_politicians"
            ):
                # extract-speakers で --skip-extraction と
                # --skip-conversation-link を指定
                command = (
                    "uv run polibase extract-speakers "
                    "--skip-extraction --skip-conversation-link"
                )
                if use_llm_politician:
                    command += " --use-llm"

                with st.spinner("発言者-政治家紐付け処理を実行中..."):
                    run_command_with_progress(command, "link_speakers_to_politicians")

        # 進捗表示 - 選択された処理タイプに応じて表示
        process_key = (
            "update_speakers"
            if link_type == "発言-発言者紐付け"
            else "link_speakers_to_politicians"
        )

        if process_key in st.session_state.process_status:
            status = st.session_state.process_status[process_key]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if process_key in st.session_state.process_output:
                with st.expander("実行ログ", expanded=False):
                    output = "\n".join(st.session_state.process_output[process_key])
                    st.code(output, language="text")


def execute_conference_member_processes():
    """会議体メンバー管理処理の実行"""
    st.subheader("会議体メンバー管理")
    st.markdown("会議体の議員メンバー情報を抽出・マッチング・管理します")

    # 会議体選択
    conf_repo = ConferenceRepository()

    # members_introduction_urlが設定されている会議体のみ取得
    engine = get_db_engine()
    with engine.connect() as conn:
        conf_result = conn.execute(
            text("""
                SELECT c.id, c.name, c.members_introduction_url,
                       gb.name as governing_body_name,
                       COUNT(ecm.id) as extracted_count,
                       COUNT(CASE WHEN ecm.matching_status = 'matched' THEN 1 END)
                            as matched_count,
                       COUNT(CASE WHEN ecm.matching_status = 'pending' THEN 1 END)
                            as pending_count,
                       COUNT(CASE WHEN ecm.matching_status = 'needs_review' THEN 1 END)
                            as needs_review_count,
                       COUNT(CASE WHEN ecm.matching_status = 'no_match' THEN 1 END)
                            as no_match_count
                FROM conferences c
                JOIN governing_bodies gb ON c.governing_body_id = gb.id
                LEFT JOIN extracted_conference_members ecm
                    ON c.id = ecm.conference_id
                WHERE c.members_introduction_url IS NOT NULL
                GROUP BY c.id, c.name, c.members_introduction_url,
                         gb.name
                ORDER BY gb.name, c.name
            """)
        )
        conferences = conf_result.fetchall()

    if not conferences:
        st.warning("議員紹介URLが設定されている会議体がありません。")
        st.info("会議体管理タブの「編集・削除」から議員紹介URLを設定してください。")
        conf_repo.close()
        return

    # 会議体選択
    conference_options = []
    conf_map = {}
    for conf in conferences:
        status_str = f"（抽出: {conf.extracted_count}人"
        if conf.matched_count > 0:
            status_str += f", マッチ: {conf.matched_count}人"
        if conf.pending_count > 0:
            status_str += f", 未処理: {conf.pending_count}人"
        status_str += "）"

        display_name = f"{conf.governing_body_name} - {conf.name} {status_str}"
        conference_options.append(display_name)
        conf_map[display_name] = conf

    selected_conf_display = st.selectbox(
        "処理対象の会議体を選択",
        conference_options,
        help="議員紹介URLが設定されている会議体のみ表示されます",
    )

    selected_conf = conf_map[selected_conf_display]
    conference_id = selected_conf.id

    # 選択された会議体の情報を表示
    col1, col2 = st.columns([2, 1])

    with col1:
        st.info(
            f"**会議体情報:**\n"
            f"- 開催主体: {selected_conf.governing_body_name}\n"
            f"- 会議体名: {selected_conf.name}\n"
            f"- 議員紹介URL: {selected_conf.members_introduction_url}"
        )

    with col2:
        # ステータスメトリクス
        if selected_conf.extracted_count > 0:
            st.metric("抽出済み", f"{selected_conf.extracted_count}人")
            progress = selected_conf.matched_count / selected_conf.extracted_count
            st.progress(progress, text=f"マッチ率: {progress * 100:.0f}%")

    # 処理ボタン
    st.markdown("### 処理実行")

    # 3ステップを個別に実行
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### ステップ1: 議員抽出")
        st.markdown("WebページからLLMで議員情報を抽出")

        force_extract = st.checkbox(
            "既存データを削除して再抽出",
            value=False,
            key="force_extract",
            help="既に抽出済みのデータがある場合、削除してから再度抽出します",
        )

        if st.button("🔍 議員情報を抽出", key="extract_members", type="primary"):
            command = (
                f"uv run polibase extract-conference-members "
                f"--conference-id {conference_id}"
            )
            if force_extract:
                command += " --force"

            with st.spinner("議員情報を抽出中..."):
                run_command_with_progress(command, "extract_members")

    with col2:
        st.markdown("#### ステップ2: マッチング")
        st.markdown("抽出データを既存政治家とLLMマッチング")

        if selected_conf.pending_count == 0 and selected_conf.extracted_count > 0:
            st.info("✅ 全員マッチング済み")
        else:
            if st.button("🔗 政治家とマッチング", key="match_members", type="primary"):
                command = (
                    f"uv run polibase match-conference-members "
                    f"--conference-id {conference_id}"
                )

                with st.spinner("政治家とマッチング中..."):
                    run_command_with_progress(command, "match_members")

    with col3:
        st.markdown("#### ステップ3: 所属作成")
        st.markdown("マッチング結果から所属情報を作成")

        # 開始日の選択
        start_date = st.date_input(
            "所属開始日",
            value=date.today(),
            key="affiliation_start_date",
            help="政治家と会議体の所属関係の開始日",
        )

        if selected_conf.matched_count == 0:
            st.warning("マッチング済みデータなし")
        else:
            if st.button(
                f"📋 所属情報を作成 ({selected_conf.matched_count}人)",
                key="create_affiliations",
                type="primary",
            ):
                command = (
                    f"uv run polibase create-affiliations "
                    f"--conference-id {conference_id} "
                    f"--start-date {start_date.strftime('%Y-%m-%d')}"
                )

                with st.spinner("所属情報を作成中..."):
                    run_command_with_progress(command, "create_affiliations")

    # 一括実行オプション
    st.markdown("### 一括実行")
    with st.expander("3ステップを一括実行", expanded=False):
        st.warning("⚠️ この操作は既存データを上書きする可能性があります")

        batch_force = st.checkbox("強制的に再抽出", value=False, key="batch_force")
        batch_start_date = st.date_input(
            "所属開始日", value=date.today(), key="batch_start_date"
        )

        if st.button("🚀 全ステップを一括実行", key="batch_execute", type="secondary"):
            # 3つのコマンドを順番に実行
            commands = [
                (
                    f"uv run polibase extract-conference-members "
                    f"--conference-id {conference_id}"
                    + (" --force" if batch_force else "")
                ),
                (
                    f"uv run polibase match-conference-members "
                    f"--conference-id {conference_id}"
                ),
                (
                    f"uv run polibase create-affiliations "
                    f"--conference-id {conference_id} "
                    f"--start-date {batch_start_date.strftime('%Y-%m-%d')}"
                ),
            ]

            full_command = " && ".join(commands)

            with st.spinner("全ステップを実行中..."):
                run_command_with_progress(full_command, "batch_conference_members")

    # ステータス確認
    st.markdown("### 処理状況確認")
    if st.button("📊 最新の状況を確認", key="check_status"):
        command = f"uv run polibase member-status --conference-id {conference_id}"

        with st.spinner("状況を確認中..."):
            run_command_with_progress(command, "member_status")

    # 進捗表示（全プロセス）
    process_keys = [
        "extract_members",
        "match_members",
        "create_affiliations",
        "batch_conference_members",
        "member_status",
    ]

    for process_key in process_keys:
        if process_key in st.session_state.process_status:
            status = st.session_state.process_status[process_key]

            # プロセス名の表示名を設定
            display_names = {
                "extract_members": "議員情報抽出",
                "match_members": "政治家マッチング",
                "create_affiliations": "所属情報作成",
                "batch_conference_members": "一括処理",
                "member_status": "状況確認",
            }

            process_display_name = display_names.get(process_key, process_key)

            # ステータス表示
            if status == "running":
                st.info(f"🔄 {process_display_name}を実行中...")
            elif status == "completed":
                st.success(f"✅ {process_display_name}が完了しました")

                # 処理結果のサマリーを表示（出力から抽出）
                if process_key in st.session_state.process_output:
                    output_lines = st.session_state.process_output[process_key]

                    # 結果サマリーを抽出
                    if process_key == "extract_members":
                        for line in output_lines:
                            if "抽出総数:" in line or "保存総数:" in line:
                                st.info(line.strip())
                    elif process_key == "match_members":
                        for line in output_lines:
                            if "処理総数:" in line or "マッチ成功:" in line:
                                st.info(line.strip())
                    elif process_key == "create_affiliations":
                        for line in output_lines:
                            if "処理総数:" in line or "作成/更新:" in line:
                                st.info(line.strip())

            elif status == "failed":
                st.error(f"❌ {process_display_name}が失敗しました")
            elif status == "error":
                st.error(f"❌ {process_display_name}でエラーが発生しました")

            # 出力表示
            if process_key in st.session_state.process_output:
                with st.expander(f"{process_display_name}の実行ログ", expanded=False):
                    output = "\n".join(st.session_state.process_output[process_key])
                    st.code(output, language="text")

    # 抽出済みデータの詳細表示
    with st.expander("抽出済みメンバー詳細", expanded=False):
        # 抽出済みメンバーを取得
        with engine.connect() as conn:
            members_result = conn.execute(
                text("""
                    SELECT ecm.*, p.name as politician_name
                    FROM extracted_conference_members ecm
                    LEFT JOIN politicians p ON ecm.matched_politician_id = p.id
                    WHERE ecm.conference_id = :conference_id
                    ORDER BY
                        CASE ecm.matching_status
                            WHEN 'matched' THEN 1
                            WHEN 'needs_review' THEN 2
                            WHEN 'pending' THEN 3
                            WHEN 'no_match' THEN 4
                        END,
                        ecm.extracted_name
                """),
                {"conference_id": conference_id},
            )

            members = members_result.fetchall()

            if members:
                # ステータス別にグループ化して表示
                status_groups = {
                    "matched": [],
                    "needs_review": [],
                    "pending": [],
                    "no_match": [],
                }

                for member in members:
                    status_groups[member.matching_status].append(member)

                # マッチ済み
                if status_groups["matched"]:
                    st.markdown("#### ✅ マッチ済み")
                    for member in status_groups["matched"]:
                        confidence_text = (
                            f"（信頼度: {member.matching_confidence:.0%}）"
                            if member.matching_confidence
                            else ""
                        )
                        role = member.extracted_role or "委員"
                        st.success(
                            f"{member.extracted_name} ({role}) "
                            f"→ {member.politician_name} {confidence_text}"
                        )

                # 要確認
                if status_groups["needs_review"]:
                    st.markdown("#### ⚠️ 要確認")
                    for member in status_groups["needs_review"]:
                        confidence_text = (
                            f"（信頼度: {member.matching_confidence:.0%}）"
                            if member.matching_confidence
                            else ""
                        )
                        role = member.extracted_role or "委員"
                        st.warning(
                            f"{member.extracted_name} ({role}) "
                            f"→ {member.politician_name} {confidence_text}"
                        )

                # 未処理
                if status_groups["pending"]:
                    st.markdown("#### 📋 未処理")
                    for member in status_groups["pending"]:
                        party_text = (
                            f"（{member.extracted_party_name}）"
                            if member.extracted_party_name
                            else ""
                        )
                        role = member.extracted_role or "委員"
                        st.info(f"{member.extracted_name} ({role}) {party_text}")

                # 該当なし
                if status_groups["no_match"]:
                    st.markdown("#### ❌ 該当なし")
                    for member in status_groups["no_match"]:
                        party_text = (
                            f"（{member.extracted_party_name}）"
                            if member.extracted_party_name
                            else ""
                        )
                        role = member.extracted_role or "委員"
                        st.error(f"{member.extracted_name} ({role}) {party_text}")
            else:
                st.info("抽出されたメンバーはありません")

    conf_repo.close()


def execute_scraping_processes():
    """スクレイピング処理の実行"""
    st.subheader("スクレイピング処理")

    # 議事録スクレイピング
    st.markdown("### 議事録スクレイピング")

    col1, col2 = st.columns(2)

    with col1:
        scrape_url = st.text_input(
            "議事録URL",
            placeholder="https://example.com/minutes.html",
            help="スクレイピングする議事録のURL",
        )

        upload_to_gcs = st.checkbox("GCSにアップロード", value=False)
        gcs_bucket = ""
        if upload_to_gcs:
            gcs_bucket = st.text_input(
                "GCSバケット名（オプション）",
                placeholder="my-bucket",
                help="空欄の場合は環境変数のGCS_BUCKET_NAMEを使用",
            )

    with col2:
        if st.button(
            "議事録をスクレイピング", key="scrape_minutes", disabled=not scrape_url
        ):
            command = f"uv run polibase scrape-minutes '{scrape_url}'"
            if upload_to_gcs:
                command += " --upload-to-gcs"
                if gcs_bucket:
                    command += f" --gcs-bucket {gcs_bucket}"

            with st.spinner("議事録をスクレイピング中..."):
                run_command_with_progress(command, "scrape_minutes")

        # 進捗表示
        if "scrape_minutes" in st.session_state.process_status:
            status = st.session_state.process_status["scrape_minutes"]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if "scrape_minutes" in st.session_state.process_output:
                with st.expander("実行ログ", expanded=False):
                    output = "\n".join(
                        st.session_state.process_output["scrape_minutes"]
                    )
                    st.code(output, language="text")

    # バッチスクレイピング
    st.markdown("### バッチスクレイピング")
    st.markdown("kaigiroku.netから複数の議事録を一括取得")

    col3, col4 = st.columns(2)

    with col3:
        tenant = st.selectbox("自治体を選択", ["kyoto", "osaka"])
        batch_upload_to_gcs = st.checkbox(
            "GCSにアップロード", value=False, key="batch_gcs"
        )

    with col4:
        if st.button("バッチスクレイピングを実行", key="batch_scrape"):
            command = f"uv run polibase batch-scrape --tenant {tenant}"
            if batch_upload_to_gcs:
                command += " --upload-to-gcs"

            with st.spinner(f"{tenant}の議事録を一括取得中..."):
                run_command_with_progress(command, "batch_scrape")

        # 進捗表示
        if "batch_scrape" in st.session_state.process_status:
            status = st.session_state.process_status["batch_scrape"]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if "batch_scrape" in st.session_state.process_output:
                with st.expander("実行ログ", expanded=False):
                    output = "\n".join(st.session_state.process_output["batch_scrape"])
                    st.code(output, language="text")

    # 政治家情報スクレイピング
    st.markdown("### 政治家情報スクレイピング")
    st.markdown("政党ウェブサイトから議員情報を取得")

    col5, col6 = st.columns(2)

    with col5:
        scrape_all_parties = st.checkbox("すべての政党から取得", value=True)
        party_id = None
        if not scrape_all_parties:
            party_id = st.number_input("政党ID", min_value=1, step=1)

        dry_run = st.checkbox("ドライラン（実際には登録しない）", value=False)

    with col6:
        if st.button("政治家情報をスクレイピング", key="scrape_politicians"):
            command = "uv run polibase scrape-politicians"
            if scrape_all_parties:
                command += " --all-parties"
            elif party_id:
                command += f" --party-id {party_id}"
            if dry_run:
                command += " --dry-run"

            with st.spinner("政治家情報をスクレイピング中..."):
                run_command_with_progress(command, "scrape_politicians")

        # 進捗表示
        if "scrape_politicians" in st.session_state.process_status:
            status = st.session_state.process_status["scrape_politicians"]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if "scrape_politicians" in st.session_state.process_output:
                with st.expander("実行ログ", expanded=False):
                    output = "\n".join(
                        st.session_state.process_output["scrape_politicians"]
                    )
                    st.code(output, language="text")


def execute_other_processes():
    """その他の処理の実行"""
    st.subheader("その他の処理")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### データベース接続テスト")
        if st.button("接続テスト実行", key="test_connection"):
            command = (
                "uv run python -c "
                '"from src.config.database import test_connection; test_connection()"'
            )

            with st.spinner("データベース接続をテスト中..."):
                run_command_with_progress(command, "test_connection")

        # 進捗表示
        if "test_connection" in st.session_state.process_status:
            status = st.session_state.process_status["test_connection"]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if "test_connection" in st.session_state.process_output:
                with st.expander("実行ログ", expanded=False):
                    output = "\n".join(
                        st.session_state.process_output["test_connection"]
                    )
                    st.code(output, language="text")

    with col2:
        st.markdown("### コマンドヘルプ")
        if st.button("ヘルプ表示", key="show_help"):
            command = "uv run polibase --help"

            with st.spinner("ヘルプを取得中..."):
                run_command_with_progress(command, "show_help")

        # 進捗表示
        if "show_help" in st.session_state.process_status:
            status = st.session_state.process_status["show_help"]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if "show_help" in st.session_state.process_output:
                with st.expander("実行ログ", expanded=True):
                    output = "\n".join(st.session_state.process_output["show_help"])
                    st.code(output, language="text")

    # 処理ステータス一覧
    st.markdown("### 実行中の処理")
    if st.session_state.process_status:
        status_df = pd.DataFrame(
            [
                {
                    "処理名": name,
                    "状態": status,
                    "最終更新": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
                for name, status in st.session_state.process_status.items()
            ]
        )
        st.dataframe(status_df, use_container_width=True)

        if st.button("ステータスをクリア"):
            st.session_state.process_status = {}
            st.session_state.process_output = {}
            st.rerun()
    else:
        st.info("実行中の処理はありません")


def manage_governing_bodies():
    """開催主体管理（CRUD）"""
    st.header("開催主体管理")
    st.markdown("開催主体（国、都道府県、市町村）の情報を管理します")

    # サブタブの作成
    gb_tab1, gb_tab2, gb_tab3 = st.tabs(["開催主体一覧", "新規登録", "編集・削除"])

    gb_repo = GoverningBodyRepository()

    with gb_tab1:
        # 開催主体一覧
        st.subheader("開催主体一覧")

        # フィルタリングオプション
        col1, col2 = st.columns(2)

        with col1:
            # 種別でフィルタリング
            type_options = ["すべて"] + gb_repo.get_type_options()
            selected_type = st.selectbox(
                "種別でフィルタ", type_options, key="gb_type_filter"
            )

        with col2:
            # 会議体の有無でフィルタリング
            conference_filter = st.selectbox(
                "会議体でフィルタ",
                ["すべて", "会議体あり", "会議体なし"],
                key="gb_conference_filter",
            )

        # 開催主体取得
        if selected_type == "すべて":
            governing_bodies = gb_repo.get_all_governing_bodies()
        else:
            governing_bodies = gb_repo.get_governing_bodies_by_type(selected_type)

        # 会議体フィルタの適用
        if conference_filter == "会議体あり":
            governing_bodies = [
                gb for gb in governing_bodies if gb.get("conference_count", 0) > 0
            ]
        elif conference_filter == "会議体なし":
            governing_bodies = [
                gb for gb in governing_bodies if gb.get("conference_count", 0) == 0
            ]

        if governing_bodies:
            # SEEDファイル生成セクション（一番上に配置）
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### SEEDファイル生成")
                    st.markdown(
                        "現在登録されている開催主体データからSEEDファイルを生成します"
                    )
                with col2:
                    if st.button(
                        "SEEDファイル生成",
                        key="generate_governing_bodies_seed",
                        type="primary",
                    ):
                        with st.spinner("SEEDファイルを生成中..."):
                            try:
                                generator = SeedGenerator()
                                seed_content = (
                                    generator.generate_governing_bodies_seed()
                                )

                                # ファイルに保存
                                output_path = (
                                    "database/seed_governing_bodies_generated.sql"
                                )
                                with open(output_path, "w") as f:
                                    f.write(seed_content)

                                st.success(
                                    f"✅ SEEDファイルを生成しました: {output_path}"
                                )

                                # 生成内容をプレビュー表示
                                with st.expander(
                                    "生成されたSEEDファイル", expanded=False
                                ):
                                    st.code(seed_content, language="sql")
                            except Exception as e:
                                st.error(
                                    f"❌ SEEDファイル生成中にエラーが"
                                    f"発生しました: {str(e)}"
                                )

            st.markdown("---")
            # データフレームで表示
            df_data = []
            for gb in governing_bodies:
                df_data.append(
                    {
                        "ID": gb["id"],
                        "名称": gb["name"],
                        "種別": gb["type"],
                        "会議体数": gb.get("conference_count", 0),
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # 統計情報
            st.markdown("### 統計情報")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総数", f"{len(governing_bodies)}件")
            with col2:
                country_count = len(
                    [gb for gb in governing_bodies if gb["type"] == "国"]
                )
                st.metric("国", f"{country_count}件")
            with col3:
                pref_count = len(
                    [gb for gb in governing_bodies if gb["type"] == "都道府県"]
                )
                st.metric("都道府県", f"{pref_count}件")
            with col4:
                city_count = len(
                    [gb for gb in governing_bodies if gb["type"] == "市町村"]
                )
                st.metric("市町村", f"{city_count}件")

            # 会議体の有無の統計
            col1, col2 = st.columns(2)
            with col1:
                with_conf_count = len(
                    [gb for gb in governing_bodies if gb.get("conference_count", 0) > 0]
                )
                st.metric("会議体あり", f"{with_conf_count}件")
            with col2:
                without_conf_count = len(
                    [
                        gb
                        for gb in governing_bodies
                        if gb.get("conference_count", 0) == 0
                    ]
                )
                st.metric("会議体なし", f"{without_conf_count}件")
        else:
            st.info("開催主体が登録されていません")

    with gb_tab2:
        # 新規登録
        st.subheader("新規開催主体登録")

        with st.form("new_governing_body_form"):
            gb_name = st.text_input("開催主体名", key="new_gb_name")
            gb_type = st.selectbox(
                "種別", gb_repo.get_type_options(), key="new_gb_type"
            )

            submitted = st.form_submit_button("登録")

            if submitted:
                if not gb_name:
                    st.error("開催主体名を入力してください")
                else:
                    # 登録処理
                    new_id = gb_repo.create_governing_body(gb_name, gb_type)
                    if new_id:
                        st.success(
                            f"開催主体「{gb_name}」を登録しました（ID: {new_id}）"
                        )
                        st.rerun()
                    else:
                        st.error(
                            "登録に失敗しました。同じ名前と種別の開催主体が既に存在する可能性があります。"
                        )

    with gb_tab3:
        # 編集・削除
        st.subheader("開催主体の編集・削除")

        # 開催主体選択
        governing_bodies = gb_repo.get_all_governing_bodies()
        if governing_bodies:
            gb_options = [
                f"{gb['name']} ({gb['type']}) - ID: {gb['id']}"
                for gb in governing_bodies
            ]
            selected_gb_option = st.selectbox(
                "編集する開催主体を選択", gb_options, key="edit_gb_select"
            )

            # 選択された開催主体のIDを取得
            selected_gb_id = int(selected_gb_option.split("ID: ")[1])
            selected_gb = next(
                gb for gb in governing_bodies if gb["id"] == selected_gb_id
            )

            # 編集フォーム
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 編集")
                with st.form("edit_governing_body_form"):
                    edit_gb_name = st.text_input(
                        "開催主体名", value=selected_gb["name"], key="edit_gb_name"
                    )
                    edit_gb_type = st.selectbox(
                        "種別",
                        gb_repo.get_type_options(),
                        index=gb_repo.get_type_options().index(selected_gb["type"]),
                        key="edit_gb_type",
                    )

                    update_submitted = st.form_submit_button("更新")

                    if update_submitted:
                        if not edit_gb_name:
                            st.error("開催主体名を入力してください")
                        else:
                            # 更新処理
                            success = gb_repo.update_governing_body(
                                selected_gb_id, edit_gb_name, edit_gb_type
                            )
                            if success:
                                st.success(f"開催主体「{edit_gb_name}」を更新しました")
                                st.rerun()
                            else:
                                st.error(
                                    "更新に失敗しました。同じ名前と種別の開催主体が既に存在する可能性があります。"
                                )

            with col2:
                st.markdown("### 削除")

                # 会議体数を表示
                conference_count = selected_gb.get("conference_count", 0)
                if conference_count > 0:
                    st.warning(
                        f"この開催主体には{conference_count}件の会議体が関連付けられています。"
                        "削除するには、先に関連する会議体を削除する必要があります。"
                    )
                else:
                    st.info("この開催主体に関連する会議体はありません。")

                    if st.button(
                        "削除",
                        key="delete_gb_button",
                        type="secondary",
                        disabled=conference_count > 0,
                    ):
                        # 削除確認
                        if st.checkbox(
                            f"「{selected_gb['name']}」を本当に削除しますか？",
                            key="confirm_delete_gb",
                        ):
                            if st.button(
                                "削除を実行", key="execute_delete_gb", type="primary"
                            ):
                                success = gb_repo.delete_governing_body(selected_gb_id)
                                if success:
                                    st.success(
                                        f"開催主体「{selected_gb['name']}」を削除しました"
                                    )
                                    st.rerun()
                                else:
                                    st.error("削除に失敗しました")
        else:
            st.info("編集する開催主体がありません")

    # リポジトリのクローズ
    gb_repo.close()


def manage_parliamentary_groups():
    """議員団管理（CRUD）"""
    st.header("議員団管理")
    st.markdown("議員団（会派）の情報を管理します")

    # サブタブの作成
    group_tab1, group_tab2, group_tab3, group_tab4 = st.tabs(
        ["議員団一覧", "新規登録", "編集・削除", "メンバー抽出"]
    )

    pg_repo = ParliamentaryGroupRepository()
    conf_repo = ConferenceRepository()

    with group_tab1:
        # 議員団一覧
        st.subheader("議員団一覧")

        # 会議体でフィルタリング
        conferences = conf_repo.get_all_conferences()
        conf_options = ["すべて"] + [
            f"{c['governing_body_name']} - {c['name']}" for c in conferences
        ]
        conf_map = {
            f"{c['governing_body_name']} - {c['name']}": c["id"] for c in conferences
        }

        selected_conf_filter = st.selectbox(
            "会議体でフィルタ", conf_options, key="conf_filter"
        )

        # 議員団取得
        if selected_conf_filter == "すべて":
            groups = pg_repo.search_parliamentary_groups()
        else:
            conf_id = conf_map[selected_conf_filter]
            groups = pg_repo.get_parliamentary_groups_by_conference(
                conf_id, active_only=False
            )

        if groups:
            # SEEDファイル生成セクション（一番上に配置）
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### SEEDファイル生成")
                    st.markdown(
                        "現在登録されている議員団データからSEEDファイルを生成します"
                    )
                with col2:
                    if st.button(
                        "SEEDファイル生成",
                        key="generate_parliamentary_groups_seed",
                        type="primary",
                    ):
                        with st.spinner("SEEDファイルを生成中..."):
                            try:
                                generator = SeedGenerator()
                                seed_content = (
                                    generator.generate_parliamentary_groups_seed()
                                )

                                # ファイルに保存
                                output_path = (
                                    "database/seed_parliamentary_groups_generated.sql"
                                )
                                with open(output_path, "w") as f:
                                    f.write(seed_content)

                                st.success(
                                    f"✅ SEEDファイルを生成しました: {output_path}"
                                )

                                # 生成内容をプレビュー表示
                                with st.expander(
                                    "生成されたSEEDファイル", expanded=False
                                ):
                                    st.code(seed_content, language="sql")
                            except Exception as e:
                                st.error(
                                    f"❌ SEEDファイル生成中にエラーが"
                                    f"発生しました: {str(e)}"
                                )

            st.markdown("---")

            # データフレームで表示
            df_data = []
            for group in groups:
                # 会議体名を取得
                conf = next(
                    (c for c in conferences if c["id"] == group["conference_id"]), None
                )
                conf_name = (
                    f"{conf['governing_body_name']} - {conf['name']}"
                    if conf
                    else "不明"
                )

                df_data.append(
                    {
                        "ID": group["id"],
                        "議員団名": group["name"],
                        "会議体": conf_name,
                        "URL": group.get("url", "") or "未設定",
                        "説明": group.get("description", "") or "",
                        "状態": "活動中" if group.get("is_active", True) else "非活動",
                        "作成日": group["created_at"],
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)

            # メンバー数の表示
            st.markdown("### メンバー数")
            pgm_repo = ParliamentaryGroupMembershipRepository()
            member_counts = []
            for group in groups:
                current_members = pgm_repo.get_current_members(group["id"])
                member_counts.append(
                    {
                        "議員団名": group["name"],
                        "現在のメンバー数": len(current_members),
                    }
                )

            member_df = pd.DataFrame(member_counts)
            st.dataframe(member_df, use_container_width=True, hide_index=True)
        else:
            st.info("議員団が登録されていません")

    with group_tab2:
        # 新規登録
        st.subheader("議員団の新規登録")

        # フォームの外で会議体を取得
        conferences = conf_repo.get_all_conferences()
        if not conferences:
            st.error("会議体が登録されていません。先に会議体を登録してください。")
            st.stop()

        conf_options = [
            f"{c['governing_body_name']} - {c['name']}" for c in conferences
        ]
        conf_map = {
            f"{c['governing_body_name']} - {c['name']}": c["id"] for c in conferences
        }

        with st.form("new_parliamentary_group_form", clear_on_submit=False):
            selected_conf = st.selectbox("所属会議体", conf_options)

            # 議員団情報入力
            group_name = st.text_input("議員団名", placeholder="例: 自民党市議団")
            group_url = st.text_input(
                "議員団URL（任意）",
                placeholder="https://example.com/parliamentary-group",
                help="議員団の公式ページやプロフィールページのURL",
            )
            group_description = st.text_area(
                "説明（任意）", placeholder="議員団の説明や特徴を入力"
            )
            is_active = st.checkbox("活動中", value=True)

            submitted = st.form_submit_button("登録")

        if submitted:
            conf_id = conf_map[selected_conf]
            if not group_name:
                st.error("議員団名を入力してください")
            else:
                try:
                    result = pg_repo.create_parliamentary_group(
                        name=group_name,
                        conference_id=conf_id,
                        url=group_url if group_url else None,
                        description=group_description if group_description else None,
                        is_active=is_active,
                    )
                    if result:
                        # 作成結果をセッション状態に保存
                        created_group = {
                            "id": result["id"],
                            "name": result["name"],
                            "conference_id": result["conference_id"],
                            "conference_name": selected_conf,
                            "url": result.get("url", ""),
                            "description": result.get("description", ""),
                            "is_active": result.get("is_active", True),
                            "created_at": result.get("created_at", ""),
                        }
                        st.session_state.created_parliamentary_groups.append(
                            created_group
                        )
                    else:
                        st.error(
                            "議員団の登録に失敗しました"
                            "（同じ名前の議員団が既に存在する可能性があります）"
                        )
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    import traceback

                    st.text(traceback.format_exc())

        # 作成済み議員団の表示
        if st.session_state.created_parliamentary_groups:
            st.divider()
            st.subheader("作成済み議員団")

            for i, group in enumerate(st.session_state.created_parliamentary_groups):
                with st.expander(
                    f"✅ {group['name']} (ID: {group['id']})", expanded=True
                ):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.write(f"**議員団名**: {group['name']}")
                        st.write(f"**議員団ID**: {group['id']}")
                        st.write(f"**所属会議体**: {group['conference_name']}")
                        if group["url"]:
                            st.write(f"**URL**: {group['url']}")
                        if group["description"]:
                            st.write(f"**説明**: {group['description']}")
                        active_status = "活動中" if group["is_active"] else "非活動"
                        st.write(f"**活動状態**: {active_status}")
                        if group["created_at"]:
                            st.write(f"**作成日時**: {group['created_at']}")
                    with col2:
                        if st.button("削除", key=f"remove_created_{i}"):
                            st.session_state.created_parliamentary_groups.pop(i)
                            st.rerun()

    with group_tab3:
        # 編集・削除
        st.subheader("議員団の編集・削除")

        groups = pg_repo.search_parliamentary_groups()
        if not groups:
            st.info("編集する議員団がありません")
        else:
            # 議員団選択
            conferences = conf_repo.get_all_conferences()
            group_options = []
            group_map = {}
            for group in groups:
                conf = next(
                    (c for c in conferences if c["id"] == group["conference_id"]), None
                )
                conf_name = conf["name"] if conf else "不明"
                display_name = f"{group['name']} ({conf_name})"
                group_options.append(display_name)
                group_map[display_name] = group

            selected_group_display = st.selectbox("編集する議員団を選択", group_options)
            selected_group = group_map[selected_group_display]

            # 編集フォーム
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 編集")
                with st.form("edit_parliamentary_group_form"):
                    new_name = st.text_input("議員団名", value=selected_group["name"])
                    new_url = st.text_input(
                        "議員団URL", value=selected_group.get("url", "") or ""
                    )
                    new_description = st.text_area(
                        "説明", value=selected_group.get("description", "") or ""
                    )
                    new_is_active = st.checkbox(
                        "活動中", value=selected_group.get("is_active", True)
                    )

                    submitted = st.form_submit_button("更新")

                    if submitted:
                        if not new_name:
                            st.error("議員団名を入力してください")
                        else:
                            if pg_repo.update_parliamentary_group(
                                group_id=selected_group["id"],
                                name=new_name,
                                url=new_url if new_url else None,
                                description=new_description
                                if new_description
                                else None,
                                is_active=new_is_active,
                            ):
                                st.success("議員団を更新しました")
                                st.rerun()
                            else:
                                st.error("議員団の更新に失敗しました")

            with col2:
                st.markdown("#### メンバー情報")
                pgm_repo = ParliamentaryGroupMembershipRepository()
                current_members = pgm_repo.get_current_members(selected_group["id"])

                if current_members:
                    st.write(f"現在のメンバー数: {len(current_members)}名")
                    member_names = [m["politician_name"] for m in current_members]
                    st.write("メンバー: " + ", ".join(member_names[:5]))
                    if len(member_names) > 5:
                        st.write(f"... 他 {len(member_names) - 5}名")
                else:
                    st.write("メンバーなし")

                st.markdown("#### 削除")
                st.warning("⚠️ 議員団を削除すると、所属履歴も削除されます")

                # 削除は活動中でない議員団のみ可能
                if selected_group.get("is_active", True):
                    st.info(
                        "活動中の議員団は削除できません。先に非活動にしてください。"
                    )
                elif current_members:
                    st.info("メンバーがいる議員団は削除できません。")
                else:
                    if st.button("🗑️ この議員団を削除", type="secondary"):
                        # Note: 削除機能は未実装のため、将来的に実装予定
                        st.error("削除機能は現在実装されていません")

    with group_tab4:
        # メンバー抽出
        st.subheader("議員団メンバーの抽出")
        st.markdown(
            "議員団のURLから所属議員を自動的に抽出し、メンバーシップを作成します"
        )

        # URLが設定されている議員団を取得
        groups_with_url = [
            g for g in pg_repo.search_parliamentary_groups() if g.get("url")
        ]

        if not groups_with_url:
            st.info(
                "URLが設定されている議員団がありません。先に議員団のURLを設定してください。"
            )
        else:
            # 議員団選択
            conferences = conf_repo.get_all_conferences()
            group_options = []
            group_map = {}
            for group in groups_with_url:
                conf = next(
                    (c for c in conferences if c["id"] == group["conference_id"]), None
                )
                conf_name = (
                    f"{conf['governing_body_name']} - {conf['name']}"
                    if conf
                    else "不明"
                )
                display_name = f"{group['name']} ({conf_name})"
                group_options.append(display_name)
                group_map[display_name] = group

            selected_group_display = st.selectbox(
                "抽出対象の議員団を選択", group_options, key="extract_group_select"
            )
            selected_group = group_map[selected_group_display]

            # 現在のメンバー数を表示
            pgm_repo = ParliamentaryGroupMembershipRepository()
            current_members = pgm_repo.get_current_members(selected_group["id"])

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**議員団URL:** {selected_group['url']}")
            with col2:
                st.info(f"**現在のメンバー数:** {len(current_members)}名")

            # 抽出設定
            st.markdown("### 抽出設定")

            col1, col2 = st.columns(2)
            with col1:
                confidence_threshold = st.slider(
                    "マッチング信頼度の閾値",
                    min_value=0.5,
                    max_value=1.0,
                    value=0.7,
                    step=0.05,
                    help="この値以上の信頼度でマッチングされた政治家のみメンバーシップを作成します",
                )

            with col2:
                start_date = st.date_input(
                    "所属開始日",
                    value=date.today(),
                    help="作成されるメンバーシップの所属開始日",
                )

            dry_run = st.checkbox(
                "ドライラン（実際にはメンバーシップを作成しない）",
                value=True,
                help="チェックすると、抽出結果の確認のみ行い、実際のメンバーシップは作成しません",
            )

            # 実行ボタン
            if st.button("🔍 メンバー抽出を実行", type="primary"):
                with st.spinner("メンバー情報を抽出中..."):
                    try:
                        from src.parliamentary_group_member_extractor import (
                            ParliamentaryGroupMemberExtractor,
                            ParliamentaryGroupMembershipService,
                        )

                        # 抽出器とサービスの初期化
                        extractor = ParliamentaryGroupMemberExtractor()
                        service = ParliamentaryGroupMembershipService()

                        # メンバー情報を抽出
                        extraction_result = extractor.extract_members_sync(
                            selected_group["id"], selected_group["url"]
                        )

                        if extraction_result.error:
                            st.error(f"抽出エラー: {extraction_result.error}")
                        elif not extraction_result.extracted_members:
                            st.warning(
                                "メンバーが抽出されませんでした。URLまたはページ構造を確認してください。"
                            )
                        else:
                            st.success(
                                f"✅ {len(extraction_result.extracted_members)}名の"
                                "メンバーを抽出しました"
                            )

                            # 抽出されたメンバーを表示
                            st.markdown("### 抽出されたメンバー")
                            member_data = []
                            for member in extraction_result.extracted_members:
                                member_data.append(
                                    {
                                        "名前": member.name,
                                        "役職": member.role or "-",
                                        "政党": member.party_name or "-",
                                        "選挙区": member.district or "-",
                                        "その他": member.additional_info or "-",
                                    }
                                )

                            member_df = pd.DataFrame(member_data)
                            st.dataframe(
                                member_df, use_container_width=True, hide_index=True
                            )

                            # 政治家とマッチング
                            with st.spinner("既存の政治家データとマッチング中..."):
                                import asyncio

                                matching_results = asyncio.run(
                                    service.match_politicians(
                                        extraction_result.extracted_members,
                                        conference_id=selected_group["conference_id"],
                                    )
                                )

                            # マッチング結果を表示
                            st.markdown("### マッチング結果")

                            matched_count = sum(
                                1
                                for r in matching_results
                                if r.politician_id is not None
                            )
                            st.info(
                                f"マッチング成功: "
                                f"{matched_count}/{len(matching_results)}名"
                            )

                            # マッチング詳細を表示
                            match_data = []
                            for result in matching_results:
                                match_data.append(
                                    {
                                        "抽出名": result.extracted_member.name,
                                        "役職": result.extracted_member.role or "-",
                                        "マッチした政治家": result.politician_name
                                        or "マッチなし",
                                        "信頼度": f"{result.confidence_score:.2f}"
                                        if result.politician_id
                                        else "-",
                                        "理由": result.matching_reason,
                                    }
                                )

                            match_df = pd.DataFrame(match_data)
                            st.dataframe(
                                match_df, use_container_width=True, hide_index=True
                            )

                            # メンバーシップ作成
                            if not dry_run and matched_count > 0:
                                if st.button("📝 メンバーシップを作成", type="primary"):
                                    with st.spinner("メンバーシップを作成中..."):
                                        creation_result = service.create_memberships(
                                            parliamentary_group_id=selected_group["id"],
                                            matching_results=matching_results,
                                            start_date=start_date,
                                            confidence_threshold=confidence_threshold,
                                            dry_run=False,
                                        )

                                        st.success(
                                            f"✅ {creation_result.created_count}件の"
                                            "メンバーシップを作成しました"
                                        )

                                        if creation_result.errors:
                                            st.warning("一部エラーが発生しました:")
                                            for error in creation_result.errors:
                                                st.write(f"- {error}")
                            else:
                                # ドライランまたはマッチなしの場合の作成予定を表示
                                creation_result = service.create_memberships(
                                    parliamentary_group_id=selected_group["id"],
                                    matching_results=matching_results,
                                    start_date=start_date,
                                    confidence_threshold=confidence_threshold,
                                    dry_run=True,
                                )

                                st.markdown("### 作成予定のメンバーシップ")
                                st.write(
                                    f"- 作成予定: {creation_result.created_count}件"
                                )
                                st.write(
                                    f"- スキップ（既存）: "
                                    f"{creation_result.skipped_count}件"
                                )

                                if creation_result.errors:
                                    st.write("- エラー:")
                                    for error in creation_result.errors[:5]:
                                        st.write(f"  - {error}")
                                    if len(creation_result.errors) > 5:
                                        st.write(
                                            f"  ... 他 "
                                            f"{len(creation_result.errors) - 5}件"
                                        )

                                if not dry_run and creation_result.created_count > 0:
                                    st.info(
                                        "ドライランを解除して再実行すると、実際にメンバーシップが作成されます。"
                                    )

                    except (ScrapingError, ProcessingError) as e:
                        st.error(f"メンバー抽出処理に失敗しました: {str(e)}")
                    except DatabaseError as e:
                        st.error(f"データベースエラーが発生しました: {str(e)}")
                    except Exception as e:
                        st.error(f"予期しないエラーが発生しました: {str(e)}")
                        import traceback

                        st.text(traceback.format_exc())

    # リポジトリのクローズ
    pg_repo.close()
    conf_repo.close()
    if "pgm_repo" in locals():
        pgm_repo.close()


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
            speaker_linked = len(df[df["has_speaker"] == "✅"])
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
                df["party_name"].dropna().unique().tolist()
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
        st.markdown(f"### 政治家一覧 ({len(filtered_df)}名)")

        # カラム名を日本語に変換
        display_df = filtered_df[list(display_columns.keys())].rename(
            columns=display_columns
        )

        # データテーブル表示
        st.dataframe(
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
            csv = display_df.to_csv(index=False, encoding="utf-8-sig")
            st.download_button(
                label="ダウンロード",
                data=csv,
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


if __name__ == "__main__":
    main()
