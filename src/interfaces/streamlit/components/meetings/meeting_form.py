"""Meeting form component for adding new meetings"""

from datetime import date

import pandas as pd
import streamlit as st

from src.database.meeting_repository import MeetingRepository
from src.exceptions import DatabaseError, SaveError


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
                display_df = pd.DataFrame(gb_conf_df[["name", "type"]])
                display_df.columns = ["会議体名", "会議体種別"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("会議体が登録されていません")

    repo.close()
