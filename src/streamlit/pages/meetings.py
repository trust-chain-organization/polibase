"""会議管理ページ"""

import asyncio
import threading
from datetime import date
from typing import Any, cast

import pandas as pd

import streamlit as st
from src.application.usecases.execute_minutes_processing_usecase import (
    ExecuteMinutesProcessingDTO,
    ExecuteMinutesProcessingUseCase,
)
from src.common.logging import get_logger
from src.config.async_database import get_async_session
from src.domain.services.meeting_processing_status_service import (
    MeetingProcessingStatusService,
)
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.exceptions import DatabaseError, RecordNotFoundError, SaveError, UpdateError
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl,
)
from src.infrastructure.persistence.governing_body_repository_impl import (
    GoverningBodyRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.minutes_repository_impl import MinutesRepositoryImpl
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import SpeakerRepositoryImpl
from src.seed_generator import SeedGenerator

logger = get_logger(__name__)


def manage_meetings():
    """会議管理（一覧・新規登録・編集）"""
    st.header("会議管理")
    st.markdown("議事録の会議情報を管理します")

    # 編集モードが有効な場合、直接編集画面を表示
    if st.session_state.get("edit_mode", False) and st.session_state.get(
        "edit_meeting_id"
    ):
        # 編集モード時は編集タブのみを表示
        col1, col2 = st.columns([8, 2])
        with col1:
            st.info("編集モード - 編集が完了するかキャンセルすると一覧に戻ります")
        with col2:
            if st.button("一覧に戻る", type="secondary"):
                st.session_state.edit_mode = False
                st.session_state.edit_meeting_id = None
                st.rerun()

        edit_meeting()
    else:
        # 通常モード時はタブを表示（編集タブは削除）
        meeting_tab1, meeting_tab2 = st.tabs(["会議一覧", "新規会議登録"])

        with meeting_tab1:
            show_meetings_list()

        with meeting_tab2:
            add_new_meeting()


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

    # 処理状態サービス用の非同期セッション作成
    from src.config.database import get_db_session
    from src.infrastructure.persistence.async_session_adapter import AsyncSessionAdapter

    sync_session = get_db_session()
    async_session = AsyncSessionAdapter(sync_session)

    # 非同期リポジトリの初期化
    minutes_repo_async = MinutesRepositoryImpl(async_session)
    conversation_repo_async = ConversationRepositoryImpl(async_session)
    speaker_repo_async = SpeakerRepositoryImpl(async_session)

    # 処理状態サービスの初期化
    processing_status_service = MeetingProcessingStatusService(
        minutes_repository=minutes_repo_async,
        conversation_repository=conversation_repo_async,
        speaker_repository=speaker_repo_async,
    )

    # 非同期処理を実行するための関数
    async def get_meeting_status(meeting_id: int):
        return await processing_status_service.get_processing_status(meeting_id)

    meetings: list[dict[str, Any]] = []
    for m in all_meetings:
        if selected_conf_id is None or m.conference_id == selected_conf_id:
            conf = conf_lookup.get(m.conference_id)
            gb = gb_lookup.get(conf.governing_body_id) if conf else None

            # 処理状態を取得
            try:
                import nest_asyncio

                nest_asyncio.apply()
                status = asyncio.run(get_meeting_status(m.id))
            except Exception:
                # エラーが発生した場合はデフォルト値を使用
                status = {
                    "has_minutes": False,
                    "has_conversations": False,
                    "has_speakers": False,
                    "conversation_count": 0,
                    "speaker_count": 0,
                }

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
                    "has_minutes": status["has_minutes"],
                    "has_conversations": status["has_conversations"],
                    "has_speakers": status["has_speakers"],
                    "conversation_count": status["conversation_count"],
                    "speaker_count": status["speaker_count"],
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

        # 処理状態の表示用カラムを追加
        def get_conversation_status(row: pd.Series) -> str:
            if row["has_conversations"]:
                return f"✅ ({row['conversation_count']}件)"
            else:
                return "❌ 未抽出"

        def get_speaker_status(row: pd.Series) -> str:
            if row["has_speakers"]:
                return f"✅ ({row['speaker_count']}件)"
            else:
                return "❌ 未抽出"

        df["発言抽出状態"] = df.apply(get_conversation_status, axis=1)
        df["発言者抽出状態"] = df.apply(get_speaker_status, axis=1)

        # 編集・削除・発言抽出ボタン用のカラム
        for _idx, row in df.iterrows():
            col1, col2, col3, col4 = st.columns([5, 1, 1, 1])

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

                # 処理状態を表示（インラインで表示）
                status_text = []
                if row["has_conversations"]:
                    status_text.append(f"✅ 発言: {row['conversation_count']}件")
                else:
                    status_text.append("❌ 発言: 未抽出")

                if row["has_speakers"]:
                    status_text.append(f"✅ 発言者: {row['speaker_count']}件")
                else:
                    status_text.append("❌ 発言者: 未抽出")

                st.markdown("**処理状態:** " + " | ".join(status_text))

            with col2:
                if st.button("編集", key=f"edit_{row['id']}"):
                    st.session_state.edit_mode = True
                    st.session_state.edit_meeting_id = row["id"]
                    st.rerun()

            with col3:
                # 発言抽出ボタン（Conversationsがない、かつGCSテキストURIがある場合）
                row_dict = cast(dict[str, Any], row)
                meeting_id = int(row["id"])  # type: ignore[arg-type,index]
                has_conversations = row_dict.get("has_conversations", False)
                gcs_text_uri = row_dict.get("gcs_text_uri", None)

                # 処理中の状態を管理
                processing_key = f"processing_{meeting_id}"
                is_processing = st.session_state.get(processing_key, False)

                # エラーメッセージがあれば表示
                error_key = f"error_{meeting_id}"
                if error_key in st.session_state:
                    st.error(f"処理エラー: {st.session_state[error_key]}")
                    del st.session_state[error_key]

                if is_processing:
                    st.button(
                        "処理中...",
                        key=f"extract_{row['id']}",
                        disabled=True,
                        type="secondary",
                    )
                elif not has_conversations and gcs_text_uri:
                    if st.button(
                        "発言抽出",
                        key=f"extract_{row['id']}",
                        type="primary",
                        help="議事録から発言を抽出します",
                    ):
                        # 処理中フラグを設定
                        st.session_state[processing_key] = True
                        # ログ表示用のコンテナを作成
                        st.session_state[f"show_log_{meeting_id}"] = True
                        st.session_state[f"log_{meeting_id}"] = []
                        # バックグラウンドで処理を実行
                        execute_minutes_processing_new(meeting_id)
                        st.rerun()
                elif has_conversations:
                    st.button(
                        "抽出済",
                        key=f"extract_{row['id']}",
                        disabled=True,
                        help="既に発言が抽出されています",
                    )
                else:
                    st.button(
                        "発言抽出",
                        key=f"extract_{row['id']}",
                        disabled=True,
                        help="GCSテキストURIが設定されていません",
                    )

            with col4:
                if st.button("削除", key=f"delete_{row['id']}"):
                    meeting_id = int(row["id"])  # type: ignore[arg-type,index]
                    if meeting_repo.delete(meeting_id):
                        st.success("会議を削除しました")
                        st.rerun()
                    else:
                        st.error(
                            "会議を削除できませんでした（関連する議事録が存在する可能性があります）"
                        )

            # ログ表示エリア
            if st.session_state.get(f"show_log_{meeting_id}", False):
                from src.streamlit.utils.processing_logger import ProcessingLogger

                proc_logger = ProcessingLogger()

                with st.expander(f"処理ログ - 会議ID {meeting_id}", expanded=True):
                    # ファイルからログを読み込む
                    log_entries = proc_logger.get_logs(meeting_id)

                    if log_entries:
                        # ログコンテナを作成して全ログを表示
                        log_container = st.container(height=400)
                        with log_container:
                            for log_entry in log_entries:
                                formatted_msg = log_entry.get("formatted", "")
                                level = log_entry.get("level", "INFO")
                                details = log_entry.get("details", None)

                                # 詳細データがある場合は折りたたみで表示
                                if details:
                                    with st.expander(formatted_msg, expanded=False):
                                        # 詳細データをコードブロックで表示
                                        st.code(details, language="text")
                                else:
                                    # 通常のログメッセージ
                                    if level == "ERROR" or "❌" in formatted_msg:
                                        st.error(formatted_msg)
                                    elif level == "WARNING":
                                        st.warning(formatted_msg)
                                    elif level == "SUCCESS" or "✅" in formatted_msg:
                                        st.success(formatted_msg)
                                    else:
                                        st.info(formatted_msg)
                    else:
                        st.info("処理を開始しています...")

                    # 処理状態を確認
                    is_processing = proc_logger.get_processing_status(meeting_id)
                    if not is_processing:
                        if st.button("ログを閉じる", key=f"close_log_{meeting_id}"):
                            del st.session_state[f"show_log_{meeting_id}"]
                            # 処理中フラグもクリア
                            if f"processing_{meeting_id}" in st.session_state:
                                del st.session_state[f"processing_{meeting_id}"]
                            st.rerun()
                    else:
                        # 処理中は自動リロード
                        st.caption("🔄 処理中... (自動的に更新されます)")
                        import time

                        time.sleep(2)
                        st.rerun()

            st.divider()
    else:
        st.info("会議が登録されていません")

    meeting_repo.close()
    gb_repo.close()
    conf_repo.close()
    sync_session.close()


def add_new_meeting():
    """新規会議登録フォーム"""
    st.subheader("新規会議登録")

    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    gb_repo = RepositoryAdapter(GoverningBodyRepositoryImpl)
    conf_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    # 開催主体選択（フォームの外）
    governing_bodies_entities = gb_repo.get_all()
    all_conferences = conf_repo.get_all()

    # 会議体が紐づいている開催主体のみをフィルタリング
    gb_ids_with_conferences: set[int] = set()
    for conf in all_conferences:
        gb_ids_with_conferences.add(conf.governing_body_id)

    # フィルタリングされた開催主体のリストを作成
    governing_bodies = [
        {"id": gb.id, "name": gb.name, "type": gb.type}
        for gb in governing_bodies_entities
        if gb.id in gb_ids_with_conferences
    ]

    if not governing_bodies:
        st.error(
            "会議体が登録されている開催主体がありません。先に会議体を登録してください。"
        )
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
        # all_conferences は既に取得済みなので再利用
        conferences = [
            {"id": c.id, "name": c.name, "governing_body_id": c.governing_body_id}
            for c in all_conferences
            if c.governing_body_id == selected_gb["id"]
        ]
        # フィルタリング済みなので、会議体が必ず存在するはず
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

    # edit_modeがFalseまたはedit_meeting_idがない場合は早期リターン
    if not st.session_state.get("edit_mode", False) or not st.session_state.get(
        "edit_meeting_id"
    ):
        # manage_meetings関数側で既にメッセージを表示しているので、ここではリターンのみ
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


def execute_minutes_processing_new(meeting_id: int):
    """議事録処理をバックグラウンドで実行する（新版）

    Args:
        meeting_id: 処理対象の会議ID
    """
    from src.streamlit.utils.processing_logger import ProcessingLogger

    # ロガーを初期化
    proc_logger = ProcessingLogger()
    proc_logger.clear_logs(meeting_id)  # 既存のログをクリア
    proc_logger.set_processing_status(meeting_id, True)  # 処理中フラグを設定

    # セッションステートにログ表示フラグを設定
    st.session_state[f"show_log_{meeting_id}"] = True
    st.session_state[f"processing_{meeting_id}"] = True

    def run_async_processing():
        """同期処理を実行するラッパー関数"""
        from src.streamlit.utils.processing_logger import ProcessingLogger
        from src.streamlit.utils.sync_minutes_processor import SyncMinutesProcessor

        proc_logger = ProcessingLogger()

        try:
            # 同期的なプロセッサを使用
            processor = SyncMinutesProcessor(meeting_id)
            result = processor.process()

            # 処理完了フラグを更新
            proc_logger.set_processing_status(meeting_id, False)
            return result

        except Exception as e:
            proc_logger.add_log(
                meeting_id, f"❌ エラーが発生しました: {str(e)}", "error"
            )
            logger.error(f"Failed to process meeting {meeting_id}: {e}", exc_info=True)

            # 処理完了フラグを更新
            proc_logger.set_processing_status(meeting_id, False)
            raise

    # バックグラウンドスレッドで処理を実行
    thread = threading.Thread(target=run_async_processing, daemon=True)
    thread.start()

    # UIフィードバック用のメッセージ
    st.info(f"🔄 会議ID {meeting_id} の発言抽出処理を開始しました...")
    st.caption("処理には数分かかる場合があります。完了後、自動的に画面が更新されます。")


def execute_minutes_processing_old(meeting_id: int):
    """議事録処理をバックグラウンドで実行する

    Args:
        meeting_id: 処理対象の会議ID
    """
    import logging
    from datetime import datetime

    # ログをセッションステートに追加するヘルパー関数
    def add_log(message: str, level: str = "info"):
        """ログメッセージをセッションステートに追加する"""
        log_key = f"log_{meeting_id}"
        if log_key not in st.session_state:
            st.session_state[log_key] = []
        timestamp = datetime.now().strftime("%H:%M:%S")
        st.session_state[log_key].append(f"[{timestamp}] [{level.upper()}] {message}")

    # カスタムログハンドラーを作成
    class SessionStateLogHandler(logging.Handler):
        """ログをセッションステートに保存するハンドラー"""

        def emit(self, record: logging.LogRecord) -> None:
            try:
                msg = self.format(record)
                level = record.levelname.lower()
                if record.name.startswith("src."):  # srcモジュールのログのみキャプチャ
                    add_log(msg, level)
            except Exception:
                self.handleError(record)

    def run_async_processing():
        """非同期処理を実行するラッパー関数"""
        loop = None
        try:
            # ログハンドラーを設定
            log_handler = SessionStateLogHandler()
            log_handler.setFormatter(logging.Formatter("%(message)s"))

            # 関連するロガーにハンドラーを追加
            loggers_to_capture = [
                "src.application.usecases.execute_minutes_processing_usecase",
                "src.minutes_divide_processor",
                "src.infrastructure.external",
                "src.domain.services",
            ]

            for logger_name in loggers_to_capture:
                target_logger = logging.getLogger(logger_name)
                target_logger.addHandler(log_handler)
                target_logger.setLevel(logging.INFO)

            add_log("処理を開始します", "info")
            add_log(f"会議ID {meeting_id} の議事録処理を実行します", "info")

            # nest_asyncioを使用してイベントループの問題を解決
            import nest_asyncio

            nest_asyncio.apply()

            # 新しいイベントループを作成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def process():
                """非同期処理の本体"""
                add_log("データベースに接続しています...", "info")
                # 新しいセッションを作成（別スレッドで実行するため）
                async with get_async_session() as session:
                    # リポジトリの初期化
                    add_log("リポジトリを初期化しています...", "info")
                    meeting_repo = MeetingRepositoryImpl(session)
                    minutes_repo = MinutesRepositoryImpl(session)
                    conversation_repo = ConversationRepositoryImpl(session)
                    speaker_repo = SpeakerRepositoryImpl(session)
                    speaker_service = SpeakerDomainService()

                    # ユースケースの初期化
                    add_log("ユースケースを初期化しています...", "info")
                    use_case = ExecuteMinutesProcessingUseCase(
                        meeting_repository=meeting_repo,
                        minutes_repository=minutes_repo,
                        conversation_repository=conversation_repo,
                        speaker_repository=speaker_repo,
                        speaker_domain_service=speaker_service,
                    )

                    # 処理の実行
                    add_log("議事録処理を実行しています...", "info")
                    request = ExecuteMinutesProcessingDTO(
                        meeting_id=meeting_id, force_reprocess=False
                    )
                    result = await use_case.execute(request)

                    add_log("✅ 処理が完了しました", "success")
                    add_log(f"抽出された発言数: {result.total_conversations}件", "info")
                    add_log(f"抽出された発言者数: {result.unique_speakers}人", "info")
                    add_log(f"処理時間: {result.processing_time_seconds:.2f}秒", "info")

                    logger.info(
                        f"Minutes processing completed for meeting {meeting_id}: "
                        f"{result.total_conversations} conversations extracted"
                    )

                    # 処理完了後、処理中フラグをクリア
                    processing_key = f"processing_{meeting_id}"
                    if processing_key in st.session_state:
                        del st.session_state[processing_key]

                    # ログ表示を維持（完了後も表示を続ける）
                    st.session_state[f"show_log_{meeting_id}"] = True

                    return result

            # 非同期処理を実行
            result = loop.run_until_complete(process())

            # ハンドラーを削除
            for logger_name in loggers_to_capture:
                target_logger = logging.getLogger(logger_name)
                target_logger.removeHandler(log_handler)

            return result

        except Exception as e:
            add_log(f"❌ エラーが発生しました: {str(e)}", "error")
            logger.error(f"Failed to process meeting {meeting_id}: {e}", exc_info=True)

            # エラー時も処理中フラグをクリア
            processing_key = f"processing_{meeting_id}"
            if processing_key in st.session_state:
                del st.session_state[processing_key]

            # エラーメッセージをセッションステートに保存
            error_key = f"error_{meeting_id}"
            st.session_state[error_key] = str(e)

            # ログ表示を維持（エラー時も表示を続ける）
            st.session_state[f"show_log_{meeting_id}"] = True

            raise
        finally:
            if loop:
                loop.close()

    # バックグラウンドスレッドで処理を実行
    thread = threading.Thread(target=run_async_processing, daemon=True)
    thread.start()

    # UIフィードバック用のメッセージ
    st.info(f"🔄 会議ID {meeting_id} の発言抽出処理を開始しました...")
    st.caption("処理には数分かかる場合があります。完了後、自動的に画面が更新されます。")
