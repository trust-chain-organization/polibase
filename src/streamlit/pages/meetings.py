"""会議管理ページ"""

from datetime import date
from typing import Any, cast

import pandas as pd

import streamlit as st
from src.exceptions import DatabaseError, RecordNotFoundError, SaveError, UpdateError
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.seed_generator import SeedGenerator


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

    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    gb_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    conf_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    # フィルター
    col1, col2 = st.columns(2)

    with col1:
        governing_bodies_entities = gb_repo.get_all()
        governing_bodies = [
            {"id": gb.id, "name": gb.name, "type": gb.type}
            for gb in governing_bodies_entities
        ]
        gb_options = ["すべて"] + [
            f"{gb['name']} ({gb['type']})" for gb in governing_bodies
        ]
        gb_selected = st.selectbox("開催主体", gb_options, key="list_gb")

        if gb_selected != "すべて":
            # 選択されたオプションから対応するgoverning_bodyを探す
            selected_gb = None
            for _i, gb in enumerate(governing_bodies):
                if f"{gb['name']} ({gb['type']})" == gb_selected:
                    selected_gb = gb
                    break
            # Get all conferences and filter by governing body
            all_conferences = conf_repo.get_all()
            conferences = [
                {"id": c.id, "name": c.name, "governing_body_id": c.governing_body_id}
                for c in all_conferences
                if c.governing_body_id == (selected_gb["id"] if selected_gb else 0)
            ]
        else:
            conferences = []

    with col2:
        selected_conf_id: int | None = None
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
    all_meetings = meeting_repo.get_all()
    all_conferences = conf_repo.get_all()
    all_governing_bodies = gb_repo.get_all()

    # Create lookups for conference and governing body names
    conf_lookup = {c.id: c for c in all_conferences}
    gb_lookup = {gb.id: gb for gb in all_governing_bodies}

    meetings: list[dict[str, Any]] = []
    for m in all_meetings:
        if selected_conf_id is None or m.conference_id == selected_conf_id:
            conf = conf_lookup.get(m.conference_id)
            gb = gb_lookup.get(conf.governing_body_id) if conf else None
            meetings.append(
                {
                    "id": m.id,
                    "conference_id": m.conference_id,
                    "date": m.date,
                    "url": m.url,
                    "gcs_pdf_uri": m.gcs_pdf_uri,
                    "gcs_text_uri": m.gcs_text_uri,
                    "conference_name": conf.name if conf else "不明",
                    "governing_body_name": gb.name if gb else "不明",
                }
            )

    if meetings:
        # SEEDファイル生成セクション（一番上に配置）
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### SEEDファイル生成")
                st.markdown("現在登録されている会議データからSEEDファイルを生成します")
            with col2:
                if st.button(
                    "SEEDファイル生成",
                    key="generate_meetings_seed",
                    type="primary",
                ):
                    with st.spinner("SEEDファイルを生成中..."):
                        try:
                            generator = SeedGenerator()
                            seed_content = generator.generate_meetings_seed()

                            # ファイルに保存
                            output_path = "database/seed_meetings_generated.sql"
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
        # DataFrameに変換
        df = pd.DataFrame(meetings)
        df["date"] = pd.to_datetime(df["date"])  # type: ignore[arg-type]
        df = df.sort_values("date", ascending=False)

        # 表示用のカラムを整形
        df["開催日"] = df["date"].dt.strftime("%Y年%m月%d日")  # type: ignore[union-attr]
        df["開催主体・会議体"] = (
            df["governing_body_name"] + " - " + df["conference_name"]
        )

        # 編集・削除ボタン用のカラム
        for _idx, row in df.iterrows():
            col1, col2, col3 = st.columns([6, 1, 1])

            with col1:
                # URLを表示
                url_val: Any = row["url"]  # type: ignore[index]
                is_not_na = bool(pd.notna(url_val))  # type: ignore[arg-type]
                url_display: str = (
                    str(url_val)  # type: ignore[arg-type]
                    if is_not_na and url_val
                    else "URLなし"
                )
                st.markdown(
                    f"**{row['開催日']}** - {row['開催主体・会議体']}",
                    unsafe_allow_html=True,
                )
                if pd.notna(row["url"]) and row["url"]:  # type: ignore[arg-type,index]
                    st.markdown(f"URL: [{url_display}]({row['url']})")
                else:
                    st.markdown(f"URL: {url_display}")

                # GCS URIを表示
                row_dict = cast(dict[str, Any], row)
                gcs_pdf_uri: str | None = cast(
                    str | None, row_dict.get("gcs_pdf_uri", None)
                )
                gcs_text_uri: str | None = cast(
                    str | None, row_dict.get("gcs_text_uri", None)
                )

                if gcs_pdf_uri is not None and gcs_pdf_uri:
                    st.markdown(f"📄 PDF URI: `{gcs_pdf_uri}`")
                if gcs_text_uri is not None and gcs_text_uri:
                    st.markdown(f"📝 Text URI: `{gcs_text_uri}`")

                if not (
                    (gcs_pdf_uri is not None and gcs_pdf_uri)
                    or (gcs_text_uri is not None and gcs_text_uri)
                ):
                    st.markdown(
                        "🔸 *GCS未アップロード*",
                        help="議事録スクレイピングを実行するとGCSにアップロードされます",
                    )

            with col2:
                if st.button("編集", key=f"edit_{row['id']}"):
                    st.session_state.edit_mode = True
                    st.session_state.edit_meeting_id = row["id"]
                    st.rerun()

            with col3:
                if st.button("削除", key=f"delete_{row['id']}"):
                    meeting_id = int(row["id"])  # type: ignore[arg-type,index]
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
    gb_repo.close()
    conf_repo.close()


def add_new_meeting():
    """新規会議登録フォーム"""
    st.subheader("新規会議登録")

    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    gb_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    conf_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    # 開催主体選択（フォームの外）
    governing_bodies_entities = gb_repo.get_all()
    governing_bodies = [
        {"id": gb.id, "name": gb.name, "type": gb.type}
        for gb in governing_bodies_entities
    ]
    if not governing_bodies:
        st.error("開催主体が登録されていません。先にマスターデータを登録してください。")
        meeting_repo.close()
        gb_repo.close()
        conf_repo.close()
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
        all_conferences = conf_repo.get_all()
        conferences = [
            {"id": c.id, "name": c.name, "governing_body_id": c.governing_body_id}
            for c in all_conferences
            if c.governing_body_id == selected_gb["id"]
        ]
        if not conferences:
            st.error("選択された開催主体に会議体が登録されていません")
            meeting_repo.close()
            gb_repo.close()
            conf_repo.close()
            return

    conf_options: list[str] = []
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
                    from src.domain.entities.meeting import Meeting

                    new_meeting = Meeting(
                        conference_id=selected_conf["id"],
                        date=meeting_date,
                        url=url if url else None,
                    )
                    created_meeting = meeting_repo.create(new_meeting)
                    meeting_id = created_meeting.id if created_meeting else None
                    st.success(f"会議を登録しました (ID: {meeting_id})")

                    # フォームをリセット
                    st.rerun()
                except (SaveError, DatabaseError) as e:
                    st.error(f"会議の登録に失敗しました: {str(e)}")
                except Exception as e:
                    st.error(f"予期しないエラーが発生しました: {str(e)}")

    # 登録済み会議体の確認セクション
    with st.expander("登録済み会議体一覧", expanded=False):
        all_conferences = conf_repo.get_all()
        if all_conferences:
            # 開催主体ごとにグループ化して表示
            # GoverningBodyエンティティのIDから名前を引くためのマップを作成
            gb_map = {gb.id: gb for gb in governing_bodies_entities}

            # 開催主体ごとに会議体をグループ化
            conf_by_gb: dict[str, list[dict[str, str | None]]] = {}
            for conf in all_conferences:
                gb_id = conf.governing_body_id
                if gb_id in gb_map:
                    gb = gb_map[gb_id]
                    gb_name = f"{gb.name} ({gb.type})" if gb.type else gb.name
                    if gb_name not in conf_by_gb:
                        conf_by_gb[gb_name] = []
                    conf_by_gb[gb_name].append({"name": conf.name, "type": conf.type})

            # グループ化された会議体を表示
            for gb_name, conferences in conf_by_gb.items():
                st.markdown(f"**{gb_name}**")
                display_df = pd.DataFrame(conferences)
                display_df.columns = ["会議体名", "会議体種別"]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        else:
            st.info("会議体が登録されていません")

    meeting_repo.close()
    gb_repo.close()
    conf_repo.close()


def edit_meeting():
    """会議編集フォーム"""
    st.subheader("会議編集")

    if not st.session_state.edit_mode or not st.session_state.edit_meeting_id:
        st.info(
            "編集する会議を選択してください（会議一覧タブから編集ボタンをクリック）"
        )
        return

    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    gb_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    conf_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    # 編集対象の会議情報を取得
    meeting_entity = meeting_repo.get_by_id(st.session_state.edit_meeting_id)
    if not meeting_entity:
        st.error("会議が見つかりません")
        st.session_state.edit_mode = False
        return

    # Convert to dictionary
    meeting = {
        "id": meeting_entity.id,
        "conference_id": meeting_entity.conference_id,
        "date": meeting_entity.date,
        "url": meeting_entity.url,
        "gcs_pdf_uri": meeting_entity.gcs_pdf_uri,
        "gcs_text_uri": meeting_entity.gcs_text_uri,
    }
    if not meeting:
        st.error("会議が見つかりません")
        st.session_state.edit_mode = False
        st.session_state.edit_meeting_id = None
        return

    # Get conference info for display
    conference = conf_repo.get_by_id(meeting["conference_id"])
    if conference:
        gb = (
            gb_repo.get_by_id(conference.governing_body_id)
            if conference.governing_body_id
            else None
        )
        edit_info = f"編集中: {gb.name if gb else '不明'} - {conference.name}"
    else:
        edit_info = "編集中"

    # Cast meeting to dict for proper type handling
    meeting_dict = cast(dict[str, Any], meeting)
    st.info(edit_info)

    with st.form("edit_meeting_form"):
        # 日付入力
        current_date = meeting_dict["date"] if meeting_dict["date"] else date.today()
        meeting_date = st.date_input("開催日", value=current_date)

        # URL入力
        url = st.text_input(
            "会議URL（議事録PDFのURLなど）",
            value=meeting_dict["url"] or "",
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
                    from src.domain.entities.meeting import Meeting

                    updated_meeting = Meeting(
                        id=st.session_state.edit_meeting_id,
                        conference_id=meeting["conference_id"],
                        date=meeting_date,
                        url=url,
                        gcs_pdf_uri=meeting.get("gcs_pdf_uri"),
                        gcs_text_uri=meeting.get("gcs_text_uri"),
                    )
                    if meeting_repo.update(updated_meeting):
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

    meeting_repo.close()
    gb_repo.close()
    conf_repo.close()
