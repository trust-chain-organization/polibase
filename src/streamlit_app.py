"""Streamlit app for managing meetings"""

import subprocess
from datetime import date, datetime

import pandas as pd
import streamlit as st
from sqlalchemy import text

from src.config.database import get_db_engine
from src.database.conference_repository import ConferenceRepository
from src.database.meeting_repository import MeetingRepository

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
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["会議一覧", "新規会議登録", "会議編集", "政党管理", "会議体管理", "処理実行"]
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

    # 会議体選択の方法を選ぶ
    selection_method = st.radio(
        "会議体の選択方法",
        ["開催主体から選択", "すべての会議体から選択"],
        horizontal=True,
    )

    with st.form("new_meeting_form"):
        selected_conf = None

        if selection_method == "開催主体から選択":
            # 従来の方法：開催主体 → 会議体
            governing_bodies = repo.get_governing_bodies()
            if not governing_bodies:
                st.error(
                    "開催主体が登録されていません。"
                    "先にマスターデータを登録してください。"
                )
                repo.close()
                return

            gb_options = [f"{gb['name']} ({gb['type']})" for gb in governing_bodies]
            gb_selected = st.selectbox("開催主体を選択", gb_options)

            # 選択されたgoverning_bodyを取得
            selected_gb = None
            for gb in governing_bodies:
                if f"{gb['name']} ({gb['type']})" == gb_selected:
                    selected_gb = gb
                    break

            # 会議体選択
            if selected_gb:
                conferences = repo.get_conferences_by_governing_body(selected_gb["id"])
                if conferences:
                    conf_options = []
                    for conf in conferences:
                        conf_display = f"{conf['name']}"
                        if conf.get("type"):
                            conf_display += f" ({conf['type']})"
                        conf_options.append(conf_display)

                    conf_selected = st.selectbox("会議体を選択", conf_options)

                    # 選択されたconferenceを取得
                    for i, conf in enumerate(conferences):
                        if conf_options[i] == conf_selected:
                            selected_conf = conf
                            break
                else:
                    st.error("選択された開催主体に会議体が登録されていません")

        else:
            # 新しい方法：すべての会議体から直接選択
            all_conferences = repo.get_all_conferences()
            if not all_conferences:
                st.error(
                    "会議体が登録されていません。"
                    "先にマスターデータを登録してください。"
                )
                repo.close()
                return

            # 会議体を開催主体でグループ化して表示
            conf_options = []
            conf_map = {}

            for conf in all_conferences:
                display_name = f"{conf['governing_body_name']} - {conf['name']}"
                if conf.get("type"):
                    display_name += f" ({conf['type']})"
                conf_options.append(display_name)
                conf_map[display_name] = conf

            conf_selected = st.selectbox(
                "会議体を選択（開催主体 - 会議体名）",
                conf_options,
                help="形式: 開催主体名 - 会議体名 (種別)",
            )

            selected_conf = conf_map[conf_selected]

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
            conf_df = pd.DataFrame(all_conferences)
            conf_df = conf_df[
                ["governing_body_name", "governing_body_type", "name", "type"]
            ]
            conf_df.columns = ["開催主体", "開催主体種別", "会議体名", "会議体種別"]
            st.dataframe(conf_df, use_container_width=True)
        else:
            st.info("会議体が登録されていません")

    repo.close()


def edit_meeting():
    """会議編集フォーム"""
    st.header("会議編集")

    if not st.session_state.edit_mode or not st.session_state.edit_meeting_id:
        st.info(
            "編集する会議を選択してください" "（会議一覧タブから編集ボタンをクリック）"
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
    conf_tab1, conf_tab2, conf_tab3 = st.tabs(["会議体一覧", "新規登録", "編集・削除"])

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
                    "開催主体が登録されていません。" "先に開催主体を登録してください。"
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
                    "⚠️ 会議体を削除すると、"
                    "関連するデータも削除される可能性があります"
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
        ["議事録処理", "政治家情報抽出", "スクレイピング", "その他"],
    )

    if process_category == "議事録処理":
        execute_minutes_processes()
    elif process_category == "政治家情報抽出":
        execute_politician_processes()
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
        # プロセスを開始
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
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
        st.markdown("### 政治家抽出処理")
        st.markdown("議事録から政治家を抽出します")

        if st.button("政治家抽出を実行", key="extract_politicians"):
            command = "uv run polibase extract-politicians"

            with st.spinner("政治家抽出処理を実行中..."):
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
        st.markdown("### スピーカー紐付け処理")
        st.markdown("LLMを使用して発言者と政治家を紐付けます")

        use_llm = st.checkbox("LLMを使用する", value=True)

        if st.button("スピーカー紐付けを実行", key="update_speakers"):
            command = "uv run polibase update-speakers"
            if use_llm:
                command += " --use-llm"

            with st.spinner("スピーカー紐付け処理を実行中..."):
                run_command_with_progress(command, "update_speakers")

        # 進捗表示
        if "update_speakers" in st.session_state.process_status:
            status = st.session_state.process_status["update_speakers"]
            if status == "running":
                st.info("🔄 処理実行中...")
            elif status == "completed":
                st.success("✅ 処理が完了しました")
            elif status == "failed":
                st.error("❌ 処理が失敗しました")
            elif status == "error":
                st.error("❌ エラーが発生しました")

            # 出力表示
            if "update_speakers" in st.session_state.process_output:
                with st.expander("実行ログ", expanded=False):
                    output = "\n".join(
                        st.session_state.process_output["update_speakers"]
                    )
                    st.code(output, language="text")


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


if __name__ == "__main__":
    main()
