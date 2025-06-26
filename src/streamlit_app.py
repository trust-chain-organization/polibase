"""Streamlit app for managing meetings"""

import subprocess
from datetime import date, datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.config.database import get_db_engine
from src.database.conference_repository import ConferenceRepository
from src.database.governing_body_repository import GoverningBodyRepository
from src.database.meeting_repository import MeetingRepository
from src.database.parliamentary_group_repository import (
    ParliamentaryGroupMembershipRepository,
    ParliamentaryGroupRepository,
)

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


def main():
    st.title("🏛️ Polibase - 会議管理システム")
    st.markdown("議事録の会議情報（URL、日付）を管理します")

    # タブ作成
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(
        [
            "会議一覧",
            "新規会議登録",
            "会議編集",
            "政党管理",
            "会議体管理",
            "開催主体管理",
            "議員団管理",
            "処理実行",
        ]
    )

    with tab1:
        show_meetings_list()

    with tab2:
        add_new_meeting()

    with tab3:
        edit_meeting()

    with tab4:
        manage_political_parties()

    with tab5:
        manage_conferences()

    with tab6:
        manage_governing_bodies()

    with tab7:
        manage_parliamentary_groups()

    with tab8:
        execute_processes()


def show_meetings_list():
    """会議一覧を表示"""
    st.header("会議一覧")

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
    st.header("新規会議登録")

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
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")

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
    st.header("会議編集")

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
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")

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

        # 政党ごとにURL編集フォームを表示
        for party in parties:
            with st.expander(f"{party.name}"):
                with st.form(f"party_form_{party.id}"):
                    current_url = party.members_list_url or ""
                    new_url = st.text_input(
                        "議員一覧ページURL",
                        value=current_url,
                        placeholder="https://example.com/members",
                        help="この政党の議員一覧が掲載されているWebページのURL",
                    )

                    submitted = st.form_submit_button("更新")

                    if submitted:
                        update_query = text("""
                            UPDATE political_parties
                            SET members_list_url = :url
                            WHERE id = :party_id
                        """)
                        conn.execute(
                            update_query,
                            {"url": new_url if new_url else None, "party_id": party.id},
                        )
                        conn.commit()
                        st.success(f"{party.name}のURLを更新しました")
                        st.rerun()

                # 現在のURL表示
                if party.members_list_url:
                    st.markdown(
                        f"現在のURL: [{party.members_list_url}]"
                        f"({party.members_list_url})"
                    )
                else:
                    st.markdown("現在のURL: 未設定")

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

    # サブタブを作成
    conf_tab1, conf_tab2, conf_tab3, conf_tab4 = st.tabs(
        ["会議体一覧", "新規登録", "編集・削除", "議員紹介URL管理"]
    )

    with conf_tab1:
        # 会議体一覧
        st.subheader("登録済み会議体一覧")

        conferences = conf_repo.get_all_conferences()
        if conferences:
            # DataFrameに変換
            df = pd.DataFrame(conferences)
            df = df[
                ["id", "governing_body_name", "governing_body_type", "name", "type"]
            ]
            df.columns = ["ID", "開催主体", "開催主体種別", "会議体名", "会議体種別"]

            # 開催主体でグループ化して表示
            for gb_name in df["開催主体"].unique():
                with st.expander(f"📂 {gb_name}"):
                    gb_df = df[df["開催主体"] == gb_name]
                    st.dataframe(
                        gb_df[["ID", "会議体名", "会議体種別"]],
                        use_container_width=True,
                        hide_index=True,
                    )
        else:
            st.info("会議体が登録されていません")

    with conf_tab2:
        # 新規登録
        st.subheader("新規会議体登録")

        with st.form("new_conference_form"):
            # 開催主体選択
            governing_bodies = conf_repo.get_governing_bodies()
            if not governing_bodies:
                st.error(
                    "開催主体が登録されていません。先に開催主体を登録してください。"
                )
            else:
                gb_options = [f"{gb['name']} ({gb['type']})" for gb in governing_bodies]
                gb_selected = st.selectbox("開催主体", gb_options)

                # 選択された開催主体のIDを取得
                selected_gb_id = None
                for gb in governing_bodies:
                    if f"{gb['name']} ({gb['type']})" == gb_selected:
                        selected_gb_id = gb["id"]
                        break

                # 会議体情報入力
                conf_name = st.text_input(
                    "会議体名", placeholder="例: 本会議、予算委員会"
                )
                conf_type = st.text_input(
                    "会議体種別（任意）",
                    placeholder="例: 本会議、常任委員会、特別委員会",
                )

                submitted = st.form_submit_button("登録")

                if submitted:
                    if not conf_name:
                        st.error("会議体名を入力してください")
                    elif selected_gb_id:
                        conf_id = conf_repo.create_conference(
                            name=conf_name,
                            governing_body_id=selected_gb_id,
                            type=conf_type if conf_type else None,
                        )
                        if conf_id:
                            st.success(f"会議体を登録しました (ID: {conf_id})")
                            st.rerun()
                        else:
                            st.error(
                                "会議体の登録に失敗しました"
                                "（同じ名前の会議体が既に存在する可能性があります）"
                            )

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
                conf_options.append(display_name)
                conf_map[display_name] = conf

            selected_conf_display = st.selectbox("編集する会議体を選択", conf_options)

            selected_conf = conf_map[selected_conf_display]

            # 編集フォーム
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 編集")
                with st.form("edit_conference_form"):
                    new_name = st.text_input("会議体名", value=selected_conf["name"])
                    new_type = st.text_input(
                        "会議体種別", value=selected_conf.get("type", "")
                    )

                    submitted = st.form_submit_button("更新")

                    if submitted:
                        if not new_name:
                            st.error("会議体名を入力してください")
                        else:
                            if conf_repo.update_conference(
                                conference_id=selected_conf["id"],
                                name=new_name,
                                type=new_type if new_type else None,
                            ):
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

    with conf_tab4:
        # 議員紹介URL管理
        st.subheader("議員紹介URL管理")
        st.markdown("各会議体の議員が紹介されているページURLを管理します")

        conferences = conf_repo.get_all_conferences()
        if not conferences:
            st.info("会議体が登録されていません")
        else:
            # 開催主体と会議体種別で階層的にグループ化
            hierarchy = {}
            for conf in conferences:
                gb_name = conf["governing_body_name"]
                conf_type = conf.get("type", "その他")

                if gb_name not in hierarchy:
                    hierarchy[gb_name] = {}
                if conf_type not in hierarchy[gb_name]:
                    hierarchy[gb_name][conf_type] = []
                hierarchy[gb_name][conf_type].append(conf)

            # 開催主体ごとに表示（タブで分ける）
            gb_names = sorted(hierarchy.keys())
            if len(gb_names) > 1:
                gb_tabs = st.tabs(gb_names)

                for gb_name, gb_tab in zip(gb_names, gb_tabs, strict=False):
                    with gb_tab:
                        _display_conferences_by_type(hierarchy[gb_name], conf_repo)
            else:
                # 開催主体が1つの場合はタブを使わない
                gb_name = gb_names[0]
                st.markdown(f"### 📂 {gb_name}")
                _display_conferences_by_type(hierarchy[gb_name], conf_repo)

            # 一括確認セクション
            with st.expander("登録済みURL一覧", expanded=False):
                df_data = []
                for conf in conferences:
                    df_data.append(
                        {
                            "開催主体": conf["governing_body_name"],
                            "種別": conf.get("type", "その他"),
                            "会議体名": conf["name"],
                            "議員紹介URL": conf.get("members_introduction_url")
                            or "未設定",
                        }
                    )

                df = pd.DataFrame(df_data)
                # URLが設定されているものを上に表示
                df["URLステータス"] = df["議員紹介URL"].apply(
                    lambda x: "✅ 設定済み" if x != "未設定" else "❌ 未設定"
                )
                df = df.sort_values(
                    by=["URLステータス", "開催主体", "種別", "会議体名"],
                    ascending=[False, True, True, True],
                )
                st.dataframe(
                    df.drop(columns=["URLステータス"]),
                    use_container_width=True,
                    hide_index=True,
                )

    conf_repo.close()


def _display_conferences_by_type(type_groups: dict, conf_repo):
    """
    会議体種別ごとに会議体を表示する補助関数

    Args:
        type_groups: 会議体種別でグループ化された会議体のdict
        conf_repo: ConferenceRepositoryインスタンス
    """
    # 種別の表示順序を定義（優先度順）
    type_order = ["本会議", "常任委員会", "特別委員会", "その他"]

    # 存在する種別を優先度順にソート
    sorted_types = []
    for t in type_order:
        if t in type_groups:
            sorted_types.append(t)
    # type_orderに含まれない種別を追加
    for t in sorted(type_groups.keys()):
        if t not in sorted_types:
            sorted_types.append(t)

    for conf_type in sorted_types:
        conf_list = type_groups[conf_type]

        # 種別ごとにセクションを作成
        with st.container():
            # 種別ヘッダーと会議体数を表示
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"#### 📋 {conf_type}")
            with col2:
                # URL設定状況を表示
                url_set_count = sum(
                    1 for c in conf_list if c.get("members_introduction_url")
                )
                st.metric(
                    "URL設定済み",
                    f"{url_set_count}/{len(conf_list)}",
                    label_visibility="collapsed",
                )

            # 会議体ごとにコンパクトな入力フォームを表示
            for conf in sorted(conf_list, key=lambda x: x["name"]):
                with st.container():
                    # 会議体名とURL入力を同じ行に配置
                    col1, col2, col3 = st.columns([2, 3, 1])

                    with col1:
                        # 会議体名とURL設定状況
                        url_status = (
                            "✅" if conf.get("members_introduction_url") else "❌"
                        )
                        st.markdown(
                            f"**{url_status} {conf['name']}**", help=f"ID: {conf['id']}"
                        )

                    with col2:
                        # URL入力フォーム（インラインで表示）
                        current_url = conf.get("members_introduction_url", "") or ""
                        new_url = st.text_input(
                            "URL",
                            value=current_url,
                            placeholder="https://example.com/members",
                            key=f"members_url_input_{conf['id']}",
                            label_visibility="collapsed",
                        )

                    with col3:
                        # 更新ボタン
                        if st.button(
                            "更新",
                            key=f"update_btn_{conf['id']}",
                            type="primary" if new_url != current_url else "secondary",
                            disabled=(new_url == current_url),
                        ):
                            if conf_repo.update_conference_members_url(
                                conference_id=conf["id"],
                                members_introduction_url=new_url if new_url else None,
                            ):
                                st.success(f"{conf['name']}のURLを更新しました")
                                st.rerun()
                            else:
                                st.error("URLの更新に失敗しました")

            st.divider()


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

        env = os.environ.copy()
        env["STREAMLIT_RUNNING"] = "true"

        # プロセスを開始
        process = subprocess.Popen(
            command,
            shell=True,
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

    except Exception as e:
        st.session_state.process_status[process_name] = "error"
        st.session_state.process_output[process_name] = [f"エラー: {str(e)}"]
        with status_placeholder.container():
            st.error("❌ エラーが発生しました")
        with output_placeholder.container():
            st.code(f"エラー: {str(e)}", language="text")


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
        st.info("会議体管理タブの「議員紹介URL管理」から設定してください。")
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

        # 種別でフィルタリング
        type_options = ["すべて"] + gb_repo.get_type_options()
        selected_type = st.selectbox(
            "種別でフィルタ", type_options, key="gb_type_filter"
        )

        # 開催主体取得
        if selected_type == "すべて":
            governing_bodies = gb_repo.get_all_governing_bodies()
        else:
            governing_bodies = gb_repo.get_governing_bodies_by_type(selected_type)

        if governing_bodies:
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
            col1, col2, col3 = st.columns(3)
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

            city_count = len([gb for gb in governing_bodies if gb["type"] == "市町村"])
            st.metric("市町村", f"{city_count}件")
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

        with st.form("new_parliamentary_group_form"):
            # 会議体選択
            conferences = conf_repo.get_all_conferences()
            if not conferences:
                st.error("会議体が登録されていません。先に会議体を登録してください。")
                st.stop()

            conf_options = [
                f"{c['governing_body_name']} - {c['name']}" for c in conferences
            ]
            conf_map = {
                f"{c['governing_body_name']} - {c['name']}": c["id"]
                for c in conferences
            }

            selected_conf = st.selectbox("所属会議体", conf_options)
            conf_id = conf_map[selected_conf]

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
                if not group_name:
                    st.error("議員団名を入力してください")
                else:
                    result = pg_repo.create_parliamentary_group(
                        name=group_name,
                        conference_id=conf_id,
                        url=group_url if group_url else None,
                        description=group_description if group_description else None,
                        is_active=is_active,
                    )
                    if result:
                        st.success(f"議員団を登録しました (ID: {result['id']})")
                        st.rerun()
                    else:
                        st.error(
                            "議員団の登録に失敗しました"
                            "（同じ名前の議員団が既に存在する可能性があります）"
                        )

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

                    except Exception as e:
                        st.error(f"処理中にエラーが発生しました: {str(e)}")
                        import traceback

                        st.text(traceback.format_exc())


if __name__ == "__main__":
    main()
