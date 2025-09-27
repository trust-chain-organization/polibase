"""政党管理ページ"""

import asyncio
import threading

import pandas as pd
from sqlalchemy import text

import streamlit as st
from src.application.usecases.get_party_statistics_usecase import (
    GetPartyStatisticsUseCase,
)
from src.config.async_database import get_async_session
from src.config.database import get_db_engine
from src.infrastructure.persistence.extracted_politician_repository_impl import (
    ExtractedPoliticianRepositoryImpl,
)
from src.infrastructure.persistence.political_party_repository_impl import (
    PoliticalPartyRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.seed_generator import SeedGenerator


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

        # 統計情報を取得（非同期処理を同期的に実行）
        async def get_statistics():
            async with get_async_session() as session:
                party_repo = PoliticalPartyRepositoryImpl(session)
                extracted_repo = ExtractedPoliticianRepositoryImpl(session)
                politician_repo = PoliticianRepositoryImpl(session)

                use_case = GetPartyStatisticsUseCase(
                    party_repo, extracted_repo, politician_repo
                )
                return await use_case.execute()

        party_statistics = asyncio.run(get_statistics())

        # party_idをキーとした辞書に変換
        stats_by_party = {stat["party_id"]: stat for stat in party_statistics}

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
                # 処理中の状態を管理
                scraping_processing_key = f"politician_scraping_{party.id}"
                is_scraping = st.session_state.get(scraping_processing_key, False)

                # 各政党を個別に表示
                # 統計情報を取得
                party_stats = stats_by_party.get(party.id, None)

                # 政党名とURL状態の表示
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

                with col1:
                    st.markdown(f"**{party.name}**")

                with col2:
                    if party.members_list_url:
                        st.success("✅ URL設定済み")
                    else:
                        st.error("❌ URL未設定")

                with col3:
                    if st.button("✏️ 編集", key=f"edit_party_btn_{party.id}"):
                        edit_key = f"edit_party_{party.id}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False
                        st.session_state[edit_key] = not st.session_state[edit_key]
                        st.rerun()

                with col4:
                    # 政治家抽出ボタン
                    if is_scraping:
                        st.button(
                            "処理中...",
                            key=f"scrape_politicians_{party.id}",
                            disabled=True,
                            type="secondary",
                        )
                    elif party.members_list_url:
                        if st.button(
                            "🔍 抽出",
                            key=f"scrape_politicians_{party.id}",
                            type="primary",
                            help="政治家情報を抽出します",
                        ):
                            # 処理中フラグを設定
                            st.session_state[scraping_processing_key] = True
                            # ログ表示用のコンテナを作成
                            st.session_state[f"show_politician_log_{party.id}"] = True
                            # バックグラウンドで処理を実行
                            execute_politician_scraping(party.id, party.name)
                            st.rerun()
                    else:
                        st.button(
                            "🔍 抽出",
                            key=f"scrape_politicians_{party.id}",
                            disabled=True,
                            help="議員一覧URLを設定してください",
                        )

                # 統計情報の表示
                if party_stats:
                    # 統計情報を一行で表示
                    stats_text_parts = []

                    # extracted_politicians総数
                    extracted_total = party_stats["extracted_total"]
                    if extracted_total > 0:
                        stats_text_parts.append(f"📊 抽出済み: {extracted_total}")

                    # 承認済み
                    approved = party_stats["extracted_approved"]
                    if approved > 0:
                        stats_text_parts.append(f"✅ 承認済み: {approved}")

                    # politicians総数
                    politicians_total = party_stats["politicians_total"]
                    stats_text_parts.append(f"👥 政治家: {politicians_total}")

                    # 一行で表示
                    if stats_text_parts:
                        st.caption(" | ".join(stats_text_parts))

                # 編集状態の管理
                edit_key = f"edit_party_{party.id}"
                if edit_key not in st.session_state:
                    st.session_state[edit_key] = False

                # 現在のURLを表示（編集モードでない場合）
                if not st.session_state[edit_key] and party.members_list_url:
                    url = party.members_list_url
                    display_url = url[:50] + "..." if len(url) > 50 else url
                    st.caption(f"🔗 {display_url}")

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

                # ログ表示エリア
                if st.session_state.get(f"show_politician_log_{party.id}", False):
                    import json
                    import time

                    from src.streamlit.utils.processing_logger import ProcessingLogger

                    proc_logger = ProcessingLogger()
                    log_key = party.id

                    # 処理完了をチェック
                    status_file = proc_logger.base_dir / f"completed_{party.id}.json"
                    if status_file.exists():
                        with open(status_file) as f:
                            status = json.load(f)
                            if status.get("completed"):
                                # 処理完了フラグを更新
                                st.session_state[scraping_processing_key] = False
                                # ファイルを削除
                                status_file.unlink()
                                # 自動リロード
                                time.sleep(0.5)
                                st.rerun()

                    # 毎回最新のログを取得
                    logs = proc_logger.get_logs(log_key)

                    # 処理中かログがある場合は表示
                    is_processing = st.session_state.get(scraping_processing_key, False)

                    if logs or is_processing:
                        with st.expander(f"📋 {party.name} - 処理ログ", expanded=True):
                            # 処理中の場合は自動リロード
                            if is_processing:
                                # 0.5秒後に自動リロード（より頻繁に更新）
                                time.sleep(0.5)
                                st.rerun()

                            if is_processing:
                                col_status1, col_status2 = st.columns([1, 9])
                                with col_status1:
                                    st.spinner()
                                with col_status2:
                                    st.info("処理中...")

                            # ログを時系列順に表示
                            for log_entry in logs:
                                level = log_entry.get("level", "info")
                                message = log_entry.get("message", "")
                                details = log_entry.get("details", None)

                                # レベルに応じてアイコンとスタイルを設定
                                if level == "error":
                                    st.error(message)
                                elif level == "warning":
                                    st.warning(message)
                                elif level == "success":
                                    st.success(message)
                                elif level == "details":
                                    with st.expander(message, expanded=False):
                                        if details:
                                            st.text(details)
                                        else:
                                            st.text(message)
                                else:
                                    st.info(message)

                                # 詳細情報がある場合は折りたたみで表示
                                if details and level != "details":
                                    with st.expander("詳細", expanded=False):
                                        st.text(details)

                            # 処理が完了している場合は、リロードボタンを表示
                            if not is_processing:
                                if st.button(
                                    "🔄 ログをクリア",
                                    key=f"clear_log_{party.id}",
                                ):
                                    proc_logger.clear_logs(log_key)
                                    st.session_state[
                                        f"show_politician_log_{party.id}"
                                    ] = False
                                    st.session_state[scraping_processing_key] = False
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
            df_data: list[dict[str, str]] = []
            for party in parties:
                df_data.append(
                    {
                        "政党名": party.name,
                        "議員一覧URL": party.members_list_url or "未設定",
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)  # type: ignore[call-arg]

    finally:
        conn.close()


def execute_politician_scraping(party_id: int, party_name: str):
    """政治家抽出処理をバックグラウンドで実行する

    Args:
        party_id: 処理対象の政党ID
        party_name: 政党名（ログ表示用）
    """
    from src.streamlit.utils.processing_logger import ProcessingLogger

    # ロガーを初期化
    proc_logger = ProcessingLogger()
    log_key = party_id
    proc_logger.clear_logs(log_key)  # 既存のログをクリア
    proc_logger.set_processing_status(log_key, True)  # 処理中フラグを設定

    # セッションステートにログ表示フラグを設定
    st.session_state[f"show_politician_log_{party_id}"] = True
    st.session_state[f"politician_scraping_{party_id}"] = True

    def run_async_processing():
        """非同期処理を実行するラッパー関数"""
        import logging

        from src.streamlit.utils.processing_logger import ProcessingLogger
        from src.streamlit.utils.sync_politician_scraper import SyncPoliticianScraper

        proc_logger = ProcessingLogger()
        log_key = party_id
        logger = logging.getLogger(__name__)

        # 処理開始をログ
        proc_logger.add_log(log_key, "🚀 バックグラウンド処理を開始", "info")

        loop = None
        try:
            # 非同期処理を同期的に実行
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # 同期的なプロセッサを使用
            scraper = SyncPoliticianScraper(party_id, party_name)
            result = loop.run_until_complete(scraper.process())

            # 処理完了をログ
            proc_logger.add_log(
                log_key, "✅ バックグラウンド処理が完了しました", "success"
            )

            # ログが確実に書き込まれるまで少し待つ
            import time

            time.sleep(0.5)

            # 処理完了フラグを更新
            proc_logger.set_processing_status(log_key, False)

            # セッションステートのフラグも更新
            # （別スレッドからは直接できないので、ファイル経由で通知）
            import json

            status_file = proc_logger.base_dir / f"completed_{party_id}.json"
            with open(status_file, "w") as f:
                json.dump({"completed": True}, f)

            return result

        except Exception as e:
            proc_logger.add_log(log_key, f"❌ エラーが発生しました: {str(e)}", "error")
            logger.error(
                f"Failed to scrape politicians for party {party_id}: {e}",
                exc_info=True,
            )

            # 処理完了フラグを更新
            proc_logger.set_processing_status(log_key, False)

            # エラー状態を記録
            import json

            status_file = proc_logger.base_dir / f"completed_{party_id}.json"
            with open(status_file, "w") as f:
                json.dump({"completed": True, "error": str(e)}, f)
        finally:
            if loop:
                # すべてのタスクが完了するまで待つ
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
                loop.close()

            logger.info(f"Background processing thread finished for party {party_id}")

    # バックグラウンドスレッドで処理を実行
    thread = threading.Thread(target=run_async_processing, daemon=True)
    thread.start()

    # UIフィードバック用のメッセージ
    st.info(f"🔍 {party_name}の政治家抽出処理を開始しました...")
    st.caption("処理には数分かかる場合があります。完了後、自動的に画面が更新されます。")
