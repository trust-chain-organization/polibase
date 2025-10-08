"""Meeting form component for adding new meetings"""

from datetime import date

import pandas as pd

import streamlit as st
from src.domain.entities.conference import Conference
from src.infrastructure.exceptions import DatabaseError, SaveError
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


def add_new_meeting():
    """新規会議登録フォーム"""
    st.subheader("新規会議登録")

    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    governing_body_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    # 開催主体選択（フォームの外）
    governing_bodies = governing_body_repo.get_all()
    if not governing_bodies:
        st.error("開催主体が登録されていません。先にマスターデータを登録してください。")
        meeting_repo.close()
        governing_body_repo.close()
        conference_repo.close()
        return

    gb_options = [f"{gb.name} ({gb.type})" for gb in governing_bodies]
    gb_selected = st.selectbox("開催主体を選択", gb_options, key="new_meeting_gb")

    # 選択されたgoverning_bodyを取得
    selected_gb = None
    for gb in governing_bodies:
        if f"{gb.name} ({gb.type})" == gb_selected:
            selected_gb = gb
            break

    # 会議体選択（選択された開催主体に紐づくもののみ表示）
    conferences: list[Conference] = []
    if selected_gb:
        all_conferences = conference_repo.get_all()
        conferences = [
            conf for conf in all_conferences if conf.governing_body_id == selected_gb.id
        ]
        if not conferences:
            st.error("選択された開催主体に会議体が登録されていません")
            meeting_repo.close()
            governing_body_repo.close()
            conference_repo.close()
            return

    conf_options: list[str] = []
    for conf in conferences:
        conf_display = f"{conf.name}"
        if hasattr(conf, "type") and conf.type:
            conf_display += f" ({conf.type})"
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
            elif selected_conf.id is None:
                st.error("会議体IDが無効です")
            else:
                try:
                    from src.domain.entities.meeting import Meeting

                    new_meeting = Meeting(
                        conference_id=selected_conf.id, date=meeting_date, url=url
                    )
                    created_meeting = meeting_repo.create(new_meeting)
                    st.success(f"会議を登録しました (ID: {created_meeting.id})")

                    # フォームをリセット
                    st.rerun()
                except (SaveError, DatabaseError) as e:
                    st.error(f"会議の登録に失敗しました: {str(e)}")
                except Exception as e:
                    st.error(f"予期しないエラーが発生しました: {str(e)}")

    # 登録済み会議体の確認セクション
    with st.expander("登録済み会議体一覧", expanded=False):
        all_conferences = conference_repo.get_all()
        if all_conferences:
            # 開催主体ごとにグループ化して表示
            # Get governing bodies with their names
            gb_dict = {}
            for conf in all_conferences:
                gb = governing_body_repo.get_by_id(conf.governing_body_id)
                if gb:
                    if gb.name not in gb_dict:
                        gb_dict[gb.name] = []
                    gb_dict[gb.name].append(conf)

            for gb_name, confs in gb_dict.items():
                st.markdown(f"**{gb_name}**")
                # Create DataFrame from conference entities
                display_df: pd.DataFrame = pd.DataFrame(
                    {
                        "会議体名": [c.name for c in confs],
                        "会議体種別": [getattr(c, "type", "") for c in confs],
                    }
                )
                st.dataframe(  # type: ignore
                    display_df, use_container_width=True, hide_index=True
                )
        else:
            st.info("会議体が登録されていません")

    meeting_repo.close()
    governing_body_repo.close()
    conference_repo.close()
