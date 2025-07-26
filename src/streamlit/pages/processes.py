"""処理実行ページ"""

import subprocess
from typing import Any, cast

from sqlalchemy import text

import streamlit as st
from src.config.database import get_db_engine
from src.database.meeting_repository import MeetingRepository
from src.exceptions import ProcessingError


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


def run_command_with_progress(command: str | list[str], process_name: str) -> None:
    """コマンドをバックグラウンドで実行し、進捗を管理"""
    # セッション状態の初期化を確認
    if "process_status" not in st.session_state:
        st.session_state.process_status = {}
    if "process_output" not in st.session_state:
        st.session_state.process_output = {}

    process_status = cast(dict[str, str], st.session_state.process_status)  # type: ignore[attr-defined]
    process_output = cast(dict[str, list[str]], st.session_state.process_output)  # type: ignore[attr-defined]

    process_status[process_name] = "running"
    process_output[process_name] = []

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
        output_lines: list[str] = []

        # 出力をリアルタイムで収集
        with status_placeholder.container():
            st.info("🔄 処理実行中...")

        for line in iter(process.stdout.readline, ""):  # type: ignore[union-attr]
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
        process_output[process_name] = output_lines

        if process.returncode == 0:
            process_status[process_name] = "completed"
            with status_placeholder.container():
                st.success("✅ 処理が完了しました")
        else:
            process_status[process_name] = "failed"
            with status_placeholder.container():
                st.error("❌ 処理が失敗しました")

        # 最終的な出力を表示（全ログを表示）
        with output_placeholder.container():
            with st.expander("実行ログ", expanded=False):
                st.code("\n".join(output_lines), language="text")

    except subprocess.TimeoutExpired:
        process_status[process_name] = "timeout"
        process_output[process_name] = ["処理がタイムアウトしました"]
        with status_placeholder.container():
            st.error("❌ 処理がタイムアウトしました")
        with output_placeholder.container():
            st.code("処理がタイムアウトしました", language="text")
    except ProcessingError as e:
        process_status[process_name] = "error"
        process_output[process_name] = [f"処理エラー: {str(e)}"]
        with status_placeholder.container():
            st.error("❌ 処理エラーが発生しました")
        with output_placeholder.container():
            st.code(f"処理エラー: {str(e)}", language="text")
    except Exception as e:
        process_status[process_name] = "error"
        process_output[process_name] = [f"予期しないエラー: {str(e)}"]
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
                    linked_row = linked_result.fetchone()
                    linked_count = getattr(linked_row, "count", 0) if linked_row else 0

                    if speakers_records or (linked_count and linked_count > 0):
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
                # Playwrightの依存関係とブラウザをインストール（個別に実行）
                with st.spinner("Playwrightの依存関係をインストール中..."):
                    install_deps_result = subprocess.run(
                        ["uv", "run", "playwright", "install-deps"],
                        capture_output=True,
                        text=True,
                    )
                    if install_deps_result.returncode != 0:
                        st.error(
                            "依存関係のインストールに失敗しました: "
                            f"{install_deps_result.stderr}"
                        )
                        return

                with st.spinner("Chromiumブラウザをインストール中..."):
                    install_browser_result = subprocess.run(
                        ["uv", "run", "playwright", "install", "chromium"],
                        capture_output=True,
                        text=True,
                    )
                    if install_browser_result.returncode != 0:
                        st.error(
                            "Chromiumのインストールに失敗しました: "
                            f"{install_browser_result.stderr}"
                        )
                        return

                # スクレイピングコマンドを構築（リスト形式）
                scrape_command = ["uv", "run", "polibase", "scrape-politicians"]

                if selected_party == "すべての政党":
                    scrape_command.append("--all-parties")
                else:
                    # "党名 (ID: 123)" の形式からIDを抽出
                    party_id = int(selected_party.split("ID: ")[1].rstrip(")"))
                    scrape_command.extend(["--party-id", str(party_id)])

                if dry_run:
                    scrape_command.append("--dry-run")

                with st.spinner("政治家情報取得処理を実行中..."):
                    run_command_with_progress(scrape_command, "extract_politicians")

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


def execute_conference_member_processes():
    """会議体メンバー管理処理の実行"""
    st.subheader("会議体メンバー管理")
    st.markdown("会議体の議員メンバー情報を抽出・マッチング・管理します")

    # 会議体選択
    from datetime import date

    from src.database.conference_repository import ConferenceRepository

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
    conference_options: list[str] = []
    conf_map: dict[str, Any] = {}
    for conf in conferences:
        conf = cast(Any, conf)  # SQLAlchemy Row
        status_str: str = f"（抽出: {conf.extracted_count}人"
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
                    "uv run polibase extract-conference-members "
                    f"--conference-id {conference_id}"
                )
                + (" --force" if batch_force else ""),
                (
                    "uv run polibase match-conference-members "
                    f"--conference-id {conference_id}"
                ),
                (
                    "uv run polibase create-affiliations "
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
                status_groups: dict[str, list[Any]] = {
                    "matched": [],
                    "needs_review": [],
                    "pending": [],
                    "no_match": [],
                }

                for member in members:
                    member = cast(Any, member)  # SQLAlchemy Row
                    status_groups[member.matching_status].append(member)

                # マッチ済み
                if status_groups["matched"]:
                    st.markdown("#### ✅ マッチ済み")
                    for member in status_groups["matched"]:
                        member = cast(Any, member)  # SQLAlchemy Row
                        confidence_text = (
                            f"（信頼度: {member.matching_confidence:.0%}）"
                            if member.matching_confidence
                            else ""
                        )
                        role: str = member.extracted_role or "委員"
                        st.success(
                            f"{member.extracted_name} ({role}) → "
                            f"{member.politician_name} {confidence_text}"
                        )

                # 要確認
                if status_groups["needs_review"]:
                    st.markdown("#### ⚠️ 要確認")
                    for member in status_groups["needs_review"]:
                        member = cast(Any, member)  # SQLAlchemy Row
                        confidence_text = (
                            f"（信頼度: {member.matching_confidence:.0%}）"
                            if member.matching_confidence
                            else ""
                        )
                        role: str = member.extracted_role or "委員"
                        st.warning(
                            f"{member.extracted_name} ({role}) → "
                            f"{member.politician_name} {confidence_text}"
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
                        role: str = member.extracted_role or "委員"
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
                        role: str = member.extracted_role or "委員"
                        st.error(f"{member.extracted_name} ({role}) {party_text}")
            else:
                st.info("抽出されたメンバーはありません")

    conf_repo.close()


def execute_scraping_processes():
    """スクレイピング処理の実行"""
    st.subheader("スクレイピング処理")

    # 議事録スクレイピング
    st.markdown("### 議事録スクレイピング")

    # スクレイピング方法の選択
    scrape_method = st.radio(
        "スクレイピング方法",
        ["会議を選択", "URLを直接入力"],
        horizontal=True,
        help="会議オブジェクトから選択するか、URLを直接入力するかを選択",
    )

    col1, col2 = st.columns(2)

    with col1:
        meeting_id = None
        scrape_url = None

        if scrape_method == "会議を選択":
            # データベースから会議リストを取得
            engine = get_db_engine()
            with engine.connect() as conn:
                meetings_result = conn.execute(
                    text("""
                        SELECT
                            m.id,
                            m.date,
                            m.name,
                            m.url,
                            c.name as conference_name,
                            gb.name as governing_body_name
                        FROM meetings m
                        JOIN conferences c ON m.conference_id = c.id
                        JOIN governing_bodies gb ON c.governing_body_id = gb.id
                        WHERE m.url IS NOT NULL
                        ORDER BY m.date DESC, gb.name, c.name
                        LIMIT 100
                    """)
                )
                meetings = meetings_result.fetchall()

            if not meetings:
                st.warning("URLが設定されている会議がありません。")
            else:
                # 会議選択のためのフォーマット
                meeting_options = ["選択してください"] + [
                    (
                        f"{meeting.date} - {meeting.governing_body_name} "
                        f"{meeting.conference_name} {meeting.name or ''} "
                        f"(ID: {meeting.id})"
                    )
                    for meeting in meetings
                ]

                selected_meeting = st.selectbox(
                    "会議を選択",
                    meeting_options,
                    help="スクレイピングする会議を選択してください",
                )

                if selected_meeting != "選択してください":
                    # 選択された会議のIDを取得
                    meeting_id = int(selected_meeting.split("(ID: ")[1].rstrip(")"))
                    # 選択された会議の情報を表示
                    selected_meeting_info = next(
                        m for m in meetings if m.id == meeting_id
                    )
                    st.info(f"**URL:** {selected_meeting_info.url}")

        else:  # URLを直接入力
            scrape_url = st.text_input(
                "議事録URL",
                placeholder="https://example.com/minutes.html",
                help="スクレイピングする議事録のURL",
            )

        upload_to_gcs = st.checkbox("GCSにアップロード", value=False)

    with col2:
        if st.button(
            "議事録をスクレイピング",
            key="scrape_minutes",
            disabled=(scrape_method == "会議を選択" and not meeting_id)
            or (scrape_method == "URLを直接入力" and not scrape_url),
        ):
            if scrape_method == "会議を選択":
                command = f"uv run polibase scrape-minutes --meeting-id {meeting_id}"
            else:
                command = f"uv run polibase scrape-minutes '{scrape_url}'"

            if upload_to_gcs:
                command += " --upload-to-gcs"

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

    from datetime import datetime

    import pandas as pd

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
        st.dataframe(status_df, use_container_width=True)  # type: ignore[call-arg]

        if st.button("ステータスをクリア"):
            st.session_state.process_status = {}
            st.session_state.process_output = {}
            st.rerun()
    else:
        st.info("実行中の処理はありません")

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
