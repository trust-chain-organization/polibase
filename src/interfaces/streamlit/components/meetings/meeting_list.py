"""Meeting list display component"""

from typing import Any, cast

import pandas as pd

import streamlit as st
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import (
    MeetingRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


def show_meetings_list():
    """会議一覧を表示"""
    st.subheader("会議一覧")

    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    # フィルター
    col1, col2 = st.columns(2)

    with col1:
        governing_bodies = governing_body_repo.get_all()
        gb_options = ["すべて"] + [f"{gb.name} ({gb.type})" for gb in governing_bodies]
        gb_selected = st.selectbox("開催主体", gb_options, key="list_gb")

        if gb_selected != "すべて":
            # 選択されたオプションから対応するgoverning_bodyを探す
            selected_gb = None
            for _i, gb in enumerate(governing_bodies):
                if f"{gb.name} ({gb.type})" == gb_selected:
                    selected_gb = gb
                    break
            if selected_gb:
                all_conferences = conference_repo.get_all()
                conferences = [
                    conf
                    for conf in all_conferences
                    if conf.governing_body_id == selected_gb.id
                ]
            else:
                conferences = []
        else:
            conferences = []

    with col2:
        if conferences:
            conf_options = ["すべて"] + [conf.name for conf in conferences]
            conf_selected = st.selectbox("会議体", conf_options, key="list_conf")

            if conf_selected != "すべて":
                # 選択されたオプションから対応するconferenceを探す
                selected_conf_id = None
                for conf in conferences:
                    if conf.name == conf_selected:
                        selected_conf_id = conf.id
                        break
            else:
                selected_conf_id = None
        else:
            selected_conf_id = None
            if gb_selected != "すべて":
                st.info("会議体を選択してください")

    # 会議一覧取得
    all_meetings, _ = meeting_repo.get_meetings_with_filters(
        conference_id=selected_conf_id, limit=1000
    )
    meetings = all_meetings

    if meetings:
        # DataFrameに変換
        df = pd.DataFrame(meetings)
        df["date"] = pd.to_datetime(df["date"])  # type: ignore
        df = df.sort_values("date", ascending=False)

        # 表示用のカラムを整形
        df["開催日"] = df["date"].dt.strftime("%Y年%m月%d日")  # type: ignore
        df["開催主体・会議体"] = (
            df["governing_body_name"] + " - " + df["conference_name"]
        )

        # 編集・削除ボタン用のカラム
        for _idx, row in df.iterrows():
            col1, col2, col3 = st.columns([6, 1, 1])

            with col1:
                # URLを表示
                url_value = cast(Any, row["url"])
                # 型を明示的に処理
                if pd.isna(url_value):  # type: ignore
                    url_str: str | None = None
                else:
                    url_str = str(url_value)
                has_url = bool(url_str and url_str != "None" and url_str != "")
                url_display = url_str if has_url else "URLなし"
                date_str = cast(str, row["開催日"])
                org_str = cast(str, row["開催主体・会議体"])
                st.markdown(
                    f"**{date_str}** - {org_str}",
                    unsafe_allow_html=True,
                )
                if has_url:
                    st.markdown(f"URL: [{url_display}]({url_str})")
                else:
                    st.markdown(f"URL: {url_display}")

            with col2:
                if st.button("編集", key=f"edit_{cast(int, row['id'])}"):
                    st.session_state.edit_mode = True
                    st.session_state.edit_meeting_id = cast(int, row["id"])
                    st.rerun()

            with col3:
                if st.button("削除", key=f"delete_{cast(int, row['id'])}"):
                    meeting_id = cast(int, row["id"])
                    if meeting_repo.delete(meeting_id):
                        st.success("会議を削除しました")
                        st.rerun()
                    else:
                        st.error(
                            "会議を削除できませんでした（関連する議事録が存在する可能性があります）"
                        )

            st.divider()
    else:
        st.info("会議が登録されていません")

    meeting_repo.close()
    governing_body_repo.close()
    conference_repo.close()
