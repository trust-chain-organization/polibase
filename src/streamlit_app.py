"""Streamlit app for managing meetings"""

from datetime import date

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


def main():
    st.title("🏛️ Polibase - 会議管理システム")
    st.markdown("議事録の会議情報（URL、日付）を管理します")

    # タブ作成
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["会議一覧", "新規会議登録", "会議編集", "政党管理", "会議体管理"]
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


if __name__ == "__main__":
    main()
