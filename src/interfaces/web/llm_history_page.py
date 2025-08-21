"""LLM処理履歴照会ページ"""

import csv
import io
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

import streamlit as st
from src.config.database import get_db_session_context
from src.domain.entities.llm_processing_history import (
    LLMProcessingHistory,
    ProcessingStatus,
    ProcessingType,
)
from src.infrastructure.persistence.llm_processing_history_repository_impl import (
    LLMProcessingHistoryRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter


def render_llm_history_page():
    """LLM処理履歴照会ページをレンダリング"""
    st.header("🤖 LLM処理履歴")
    st.markdown("LLM APIの処理履歴を照会・検索できます")

    # タブ作成
    tab1, tab2 = st.tabs(["履歴一覧", "統計情報"])

    with tab1:
        render_history_list()

    with tab2:
        render_statistics()


def render_history_list():
    """履歴一覧を表示"""
    st.subheader("処理履歴一覧")

    # 検索フィルターセクション
    with st.expander("🔍 検索フィルター", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            # 処理タイプフィルター
            processing_types = ["すべて"] + [pt.value for pt in ProcessingType]
            selected_type = st.selectbox(
                "処理タイプ",
                processing_types,
                key="filter_processing_type",
            )

        with col2:
            # モデルフィルター
            model_names = ["すべて", "gemini-2.0-flash", "gemini-1.5-flash", "その他"]
            selected_model = st.selectbox(
                "モデル",
                model_names,
                key="filter_model",
            )

        with col3:
            # ステータスフィルター
            statuses = ["すべて"] + [s.value for s in ProcessingStatus]
            selected_status = st.selectbox(
                "ステータス",
                statuses,
                key="filter_status",
            )

        # 日付範囲フィルター
        col4, col5 = st.columns(2)
        with col4:
            default_start_date = datetime.now() - timedelta(days=30)
            start_date = st.date_input(
                "開始日",
                value=default_start_date,
                key="filter_start_date",
            )

        with col5:
            end_date = st.date_input(
                "終了日",
                value=datetime.now(),
                key="filter_end_date",
            )

    # ページネーション設定
    items_per_page = st.selectbox(
        "表示件数",
        [10, 25, 50, 100],
        index=1,
        key="items_per_page",
    )

    # フィルター条件を構築
    processing_type = (
        None if selected_type == "すべて" else ProcessingType(selected_type)
    )
    model_name = None if selected_model == "すべて" else selected_model
    status = None if selected_status == "すべて" else ProcessingStatus(selected_status)

    # 検索実行
    if start_date and end_date:
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
    else:
        start_datetime = None
        end_datetime = None

    # 現在のページ番号を取得
    if "current_page" not in st.session_state:
        st.session_state.current_page = 0

    offset = st.session_state.current_page * items_per_page

    # データを取得
    with get_db_session_context():
        repo = RepositoryAdapter(LLMProcessingHistoryRepositoryImpl)

        # 履歴を検索
        histories = repo.search(
            processing_type=processing_type,
            model_name=model_name,
            status=status,
            start_date=start_datetime,
            end_date=end_datetime,
            limit=items_per_page,
            offset=offset,
        )

        # 総件数を取得（ページネーション用）
        total_count = repo.count_by_status(
            status=status if status else ProcessingStatus.COMPLETED,
            processing_type=processing_type,
        )

    # 結果表示
    if histories:
        # CSV エクスポートボタン
        csv_data = generate_csv_data(histories)
        st.download_button(
            label="📥 CSVダウンロード",
            data=csv_data,
            file_name=f"llm_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
        )

        # 履歴を表示
        for history in histories:
            render_history_item(history)

        # ページネーション
        total_pages = (total_count + items_per_page - 1) // items_per_page
        render_pagination(total_pages)

    else:
        st.info("検索条件に一致する履歴が見つかりませんでした")


def render_history_item(history: LLMProcessingHistory) -> None:
    """個別の履歴項目を表示"""
    with st.container():
        # ヘッダー行
        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

        with col1:
            st.markdown(f"**{history.processing_type.value}**")
            st.caption(f"ID: {history.id}")

        with col2:
            st.markdown(f"📊 {history.model_name}")
            if history.model_version:
                st.caption(f"Ver: {history.model_version}")

        with col3:
            # ステータスに応じたバッジ表示
            status_emoji = {
                ProcessingStatus.COMPLETED: "✅",
                ProcessingStatus.FAILED: "❌",
                ProcessingStatus.IN_PROGRESS: "⏳",
                ProcessingStatus.PENDING: "⏸️",
            }
            emoji = status_emoji.get(history.status, "❓")
            st.markdown(f"{emoji} {history.status.value}")

            # 処理時間を表示
            if history.processing_duration_seconds:
                st.caption(f"処理時間: {history.processing_duration_seconds:.2f}秒")

        with col4:
            if st.button("詳細", key=f"detail_{history.id}"):
                st.session_state[
                    f"show_detail_{history.id}"
                ] = not st.session_state.get(f"show_detail_{history.id}", False)

        # 詳細表示
        if st.session_state.get(f"show_detail_{history.id}", False):
            render_history_detail(history)

        st.divider()


def render_history_detail(history: LLMProcessingHistory) -> None:
    """履歴の詳細を表示"""
    with st.expander("詳細情報", expanded=True):
        # 基本情報
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**基本情報**")
            ref_text = (
                f"入力参照: {history.input_reference_type} "
                f"#{history.input_reference_id}"
            )
            st.text(ref_text)
            if history.started_at:
                st.text(f"開始: {history.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
            if history.completed_at:
                st.text(f"完了: {history.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

        with col2:
            st.markdown("**メタデータ**")
            if history.processing_metadata:
                for key, value in history.processing_metadata.items():
                    st.text(f"{key}: {value}")

        # プロンプト情報
        st.markdown("**プロンプト**")
        st.code(history.prompt_template, language="text")

        if history.prompt_variables:
            st.markdown("**プロンプト変数**")
            st.json(history.prompt_variables)

        # 結果またはエラー
        if history.status == ProcessingStatus.COMPLETED and history.result:
            st.markdown("**処理結果**")
            st.json(history.result)
        elif history.status == ProcessingStatus.FAILED and history.error_message:
            st.markdown("**エラー内容**")
            st.error(history.error_message)


def render_pagination(total_pages: int):
    """ページネーションを表示"""
    if total_pages <= 1:
        return

    col1, col2, col3 = st.columns([2, 3, 2])

    with col1:
        if st.button("◀ 前へ", disabled=st.session_state.current_page == 0):
            st.session_state.current_page -= 1
            st.rerun()

    with col2:
        page_text = (
            f"<div style='text-align: center'>"
            f"ページ {st.session_state.current_page + 1} / {total_pages}"
            f"</div>"
        )
        st.markdown(page_text, unsafe_allow_html=True)

    with col3:
        if st.button(
            "次へ ▶", disabled=st.session_state.current_page >= total_pages - 1
        ):
            st.session_state.current_page += 1
            st.rerun()


def render_statistics():
    """統計情報を表示"""
    st.subheader("統計情報")

    # 統計データを取得
    with get_db_session_context():
        repo = RepositoryAdapter(LLMProcessingHistoryRepositoryImpl)

        # 各ステータスの件数を取得
        completed_count = repo.count_by_status(ProcessingStatus.COMPLETED)
        failed_count = repo.count_by_status(ProcessingStatus.FAILED)
        in_progress_count = repo.count_by_status(ProcessingStatus.IN_PROGRESS)
        pending_count = repo.count_by_status(ProcessingStatus.PENDING)

        # 処理タイプ別の統計
        type_stats: list[dict[str, Any]] = []
        for ptype in ProcessingType:
            completed = repo.count_by_status(ProcessingStatus.COMPLETED, ptype)
            failed = repo.count_by_status(ProcessingStatus.FAILED, ptype)
            total = completed + failed
            success_rate = (completed / total * 100) if total > 0 else 0

            type_stats.append(
                {
                    "処理タイプ": ptype.value,
                    "完了": completed,
                    "失敗": failed,
                    "合計": total,
                    "成功率": f"{success_rate:.1f}%",
                }
            )

        # 過去7日間のデータを取得
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        recent_histories = repo.get_by_date_range(start_date, end_date, limit=1000)

        stats: dict[str, Any] = {
            "completed_count": completed_count,
            "failed_count": failed_count,
            "in_progress_count": in_progress_count,
            "pending_count": pending_count,
            "type_stats": type_stats,
            "recent_histories": recent_histories,
        }

    # 各ステータスの件数を表示
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("✅ 完了", stats["completed_count"])

    with col2:
        st.metric("❌ 失敗", stats["failed_count"])

    with col3:
        st.metric("⏳ 処理中", stats["in_progress_count"])

    with col4:
        st.metric("⏸️ 待機中", stats["pending_count"])

    # 処理タイプ別の統計
    st.markdown("### 処理タイプ別統計")

    df = pd.DataFrame(stats["type_stats"])
    st.dataframe(df, use_container_width=True, hide_index=True)  # type: ignore[reportUnknownMemberType]

    # 最近の処理履歴グラフ
    st.markdown("### 最近の処理履歴")

    if stats["recent_histories"]:
        # 日別の処理件数を集計
        daily_counts: dict[str, dict[str, int]] = {}
        for history in stats["recent_histories"]:
            if history.created_at:
                date_str = history.created_at.strftime("%Y-%m-%d")
                if date_str not in daily_counts:
                    daily_counts[date_str] = {"completed": 0, "failed": 0}

                if history.status == ProcessingStatus.COMPLETED:
                    daily_counts[date_str]["completed"] += 1
                elif history.status == ProcessingStatus.FAILED:
                    daily_counts[date_str]["failed"] += 1

        # データフレームに変換
        dates = sorted(daily_counts.keys())
        completed_counts = [daily_counts[date]["completed"] for date in dates]
        failed_counts = [daily_counts[date]["failed"] for date in dates]

        chart_df = pd.DataFrame(
            {
                "日付": dates,
                "完了": completed_counts,
                "失敗": failed_counts,
            }
        )

        st.line_chart(chart_df.set_index("日付"))  # type: ignore[reportUnknownMemberType]


def generate_csv_data(histories: list[LLMProcessingHistory]) -> str:
    """履歴データからCSVを生成"""
    output = io.StringIO()
    writer = csv.writer(output)

    # ヘッダー
    writer.writerow(
        [
            "ID",
            "処理タイプ",
            "モデル",
            "ステータス",
            "入力参照",
            "開始時刻",
            "完了時刻",
            "処理時間(秒)",
            "エラーメッセージ",
        ]
    )

    # データ行
    for history in histories:
        writer.writerow(
            [
                history.id,
                history.processing_type.value,
                history.model_name,
                history.status.value,
                f"{history.input_reference_type}#{history.input_reference_id}",
                history.started_at.strftime("%Y-%m-%d %H:%M:%S")
                if history.started_at
                else "",
                history.completed_at.strftime("%Y-%m-%d %H:%M:%S")
                if history.completed_at
                else "",
                history.processing_duration_seconds
                if history.processing_duration_seconds
                else "",
                history.error_message if history.error_message else "",
            ]
        )

    return output.getvalue()


def manage_llm_history():
    """LLM履歴管理のメインエントリーポイント（同期版）"""
    render_llm_history_page()
