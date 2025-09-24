"""議案管理UI（Streamlit）."""

import asyncio
import logging
from typing import cast

import pandas as pd

import streamlit as st
from src.application.dtos.proposal_dto import ScrapeProposalInputDTO
from src.application.dtos.proposal_judge_dto import ExtractProposalJudgesInputDTO
from src.application.usecases.extract_proposal_judges_usecase import (
    ExtractProposalJudgesUseCase,
)
from src.application.usecases.scrape_proposal_usecase import ScrapeProposalUseCase
from src.domain.entities.proposal import Proposal
from src.domain.entities.proposal_judge import ProposalJudge
from src.domain.entities.proposal_parliamentary_group_judge import (
    ProposalParliamentaryGroupJudge,
)
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.proposal_scraper_service import ProposalScraperService
from src.infrastructure.external.web_scraper_service import PlaywrightScraperService
from src.infrastructure.persistence import (
    proposal_parliamentary_group_judge_repository_impl as ppgjr,
)
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.politician_affiliation_repository_impl import (
    PoliticianAffiliationRepositoryImpl,
)
from src.infrastructure.persistence.politician_repository_impl import (
    PoliticianRepositoryImpl,
)
from src.infrastructure.persistence.proposal_judge_repository_impl import (
    ProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.proposal_repository_impl import (
    ProposalRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter

logger = logging.getLogger(__name__)


def manage_proposals():
    """議案管理メインページ."""
    st.title("議案管理")

    # タブ作成
    tab1, tab2, tab3 = st.tabs(
        [
            "議案管理 (Proposals)",
            "LLM抽出結果 (ExtractedProposalJudges)",
            "確定賛否情報 (ProposalJudges)",
        ]
    )

    with tab1:
        manage_proposals_tab()

    with tab2:
        manage_extracted_judges_tab()

    with tab3:
        manage_proposal_judges_tab()


def manage_proposals_tab():
    """議案管理タブ."""
    st.subheader("議案一覧")

    # リポジトリ初期化
    proposal_repo = RepositoryAdapter(ProposalRepositoryImpl)
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    conference_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    # フィルター
    meetings = meeting_repo.get_all()
    meeting_options = ["すべて"] + [f"{m.date} - ID:{m.id}" for m in meetings if m.date]
    selected_meeting = st.selectbox(
        "会議でフィルタリング", meeting_options, key="filter_meeting"
    )

    # 新規議案登録フォーム
    with st.expander("新規議案登録", expanded=False):
        st.info(
            "会議体を選択し、議案URLを登録してください。議案情報は後でLLMで自動抽出されます。"
        )

        # 会議体選択（フォームの外）
        conferences = conference_repo.get_all()
        conference_id = st.selectbox(
            "会議体",
            options=[c.id for c in conferences],
            format_func=lambda x: next(
                (f"{c.name}" for c in conferences if c.id == x),
                "不明",
            ),
            key="new_proposal_conference",
            help="この議案を審議する会議体を選択してください",
        )

        # 選択された会議体に関連する会議を取得
        selected_conference_meetings = [
            m for m in meetings if m.conference_id == conference_id
        ]

        with st.form(key="new_proposal_form"):
            # 会議選択（フィルタリングされた会議）
            if selected_conference_meetings:
                meeting_id = st.selectbox(
                    "会議（オプション）",
                    options=[None] + [m.id for m in selected_conference_meetings],
                    format_func=lambda x: "未選択"
                    if x is None
                    else next(
                        (
                            f"{m.date} - {m.name if m.name else 'ID:' + str(m.id)}"
                            for m in selected_conference_meetings
                            if m.id == x
                        ),
                        "不明",
                    ),
                    key="new_proposal_meeting",
                    help="特定の会議に紐付ける場合は選択してください",
                )
            else:
                meeting_id = None
                st.info("選択した会議体には会議が登録されていません")

            detail_url = st.text_input(
                "詳細URL",
                key="new_proposal_detail_url",
                help="議案の詳細情報が記載されているページのURL",
            )
            status_url = st.text_input(
                "状態URL",
                key="new_proposal_status_url",
                help="議案の審議状態や賛否結果が記載されているページのURL（オプション）",
            )

            if st.form_submit_button("登録"):
                if detail_url and conference_id:
                    try:
                        # 暫定的な内容を設定（後でLLMで抽出される）
                        new_proposal = Proposal(
                            content=f"新規議案（URL: {detail_url[:50]}...）",
                            detail_url=detail_url,
                            status_url=status_url if status_url else None,
                            meeting_id=meeting_id,
                            submission_date=None,  # LLMで後から抽出される
                        )
                        created = proposal_repo.create(new_proposal)
                        if created:
                            st.success(
                                "議案URLを登録しました。「情報抽出」ボタンで情報を抽出してください。"
                            )
                            st.rerun()
                        else:
                            st.error("議案の登録に失敗しました")
                    except Exception as e:
                        st.error(f"エラーが発生しました: {str(e)}")
                else:
                    st.error("会議体と詳細URLは必須です")

    # 議案一覧取得
    proposals = proposal_repo.get_all()

    # フィルタリング
    if selected_meeting != "すべて":
        meeting_id = int(selected_meeting.split("ID:")[1])
        proposals = [p for p in proposals if p.meeting_id == meeting_id]

    if proposals:
        # DataFrameに変換
        df_data = []
        for p in proposals:
            df_data.append(
                {
                    "id": p.id,
                    "proposal_number": p.proposal_number or "番号なし",
                    "content": p.content[:50] + "..."
                    if len(p.content) > 50
                    else p.content,
                    "submitter": p.submitter or "不明",
                    "status": p.status or "未処理",
                    "meeting_id": p.meeting_id,
                    "detail_url": p.detail_url,
                    "status_url": p.status_url,
                }
            )
        df = pd.DataFrame(df_data)

        # 各レコードの表示と操作ボタン
        for _idx, row in df.iterrows():
            col1, col2, col3, col4, col5 = st.columns([3.5, 1, 1, 1, 1])

            with col1:
                st.markdown(f"**{row['proposal_number']}**: {row['content']}")
                # 会議体と会議情報を表示
                if row["meeting_id"]:
                    meeting = next(
                        (m for m in meetings if m.id == row["meeting_id"]), None
                    )
                    if meeting:
                        conference = next(
                            (c for c in conferences if c.id == meeting.conference_id),
                            None,
                        )
                        if conference:
                            st.caption(
                                f"会議体: {conference.name} | 会議: {meeting.date}"
                            )
                st.caption(f"提出者: {row['submitter']} | 状態: {row['status']}")
                if row["detail_url"]:
                    st.caption(f"詳細URL: {row['detail_url']}")
                if row["status_url"]:
                    st.caption(f"状態URL: {row['status_url']}")

            with col2:
                if st.button("編集", key=f"edit_proposal_{row['id']}"):
                    st.session_state.edit_proposal_id = row["id"]
                    st.rerun()

            with col3:
                # スクレイピング実行ボタン
                detail_url = cast(str, row["detail_url"])
                status_url = cast(str | None, row["status_url"])
                if detail_url:
                    if st.button("情報抽出", key=f"scrape_proposal_{row['id']}"):
                        with st.spinner("URLから情報を抽出中..."):
                            try:
                                # スクレイピング実行
                                scraper_service = ProposalScraperService()
                                # 型の問題を回避するために直接インスタンスを作成
                                from src.config.database import get_db_session
                                from src.infrastructure.persistence import (
                                    async_session_adapter as asa,
                                )

                                sync_session = get_db_session()
                                async_session = asa.AsyncSessionAdapter(sync_session)
                                proposal_repo_async = ProposalRepositoryImpl(
                                    async_session
                                )

                                use_case = ScrapeProposalUseCase(
                                    proposal_repository=proposal_repo_async,
                                    proposal_scraper_service=scraper_service,
                                )
                                # 入力DTOを作成
                                input_dto = ScrapeProposalInputDTO(
                                    url=detail_url, meeting_id=None
                                )
                                # 非同期処理を同期的に実行
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                result = loop.run_until_complete(
                                    use_case.execute(input_dto)
                                )
                                if result:
                                    st.success("スクレイピングが完了しました")
                                    st.rerun()
                                else:
                                    st.error("スクレイピングに失敗しました")
                            except Exception as e:
                                st.error(f"エラー: {str(e)}")
                elif status_url:
                    st.button(
                        "スクレイピング済",
                        key=f"scrape_proposal_{row['id']}",
                        disabled=True,
                    )
                else:
                    st.button(
                        "URLなし", key=f"scrape_proposal_{row['id']}", disabled=True
                    )

            with col4:
                # 賛否抽出ボタン
                status_url = cast(str | None, row["status_url"])
                if status_url:
                    if st.button("賛否抽出", key=f"extract_judges_{row['id']}"):
                        with st.spinner("賛否情報を抽出中..."):
                            sync_session = None
                            try:
                                # ExtractProposalJudgesUseCaseの初期化
                                from src.config.database import get_db_session
                                from src.infrastructure.persistence import (
                                    async_session_adapter as asa,
                                )
                                from src.infrastructure.persistence import (
                                    extracted_proposal_judge_repository_impl as epjr,
                                )
                                from src.infrastructure.persistence import (
                                    politician_repository_impl as pr,
                                )
                                from src.infrastructure.persistence import (
                                    proposal_judge_repository_impl as pjr,
                                )

                                sync_session = get_db_session()
                                async_session = asa.AsyncSessionAdapter(sync_session)

                                # リポジトリの初期化
                                proposal_repo_async = ProposalRepositoryImpl(
                                    async_session
                                )
                                politician_repo = pr.PoliticianRepositoryImpl(
                                    async_session
                                )
                                extracted_repo = (
                                    epjr.ExtractedProposalJudgeRepositoryImpl(
                                        async_session
                                    )
                                )
                                judge_repo_async = pjr.ProposalJudgeRepositoryImpl(
                                    async_session
                                )

                                # サービスの初期化
                                llm_service = GeminiLLMService()
                                scraper_service = PlaywrightScraperService(
                                    llm_service=llm_service
                                )

                                # ユースケースの作成
                                use_case = ExtractProposalJudgesUseCase(
                                    proposal_repository=proposal_repo_async,
                                    politician_repository=politician_repo,
                                    extracted_proposal_judge_repository=extracted_repo,
                                    proposal_judge_repository=judge_repo_async,
                                    web_scraper_service=scraper_service,
                                    llm_service=llm_service,
                                )

                                # 既存データのチェック（簡易的なチェック）
                                # 注: 既存データの確認は非同期処理内で行う

                                # 入力DTOを作成
                                input_dto = ExtractProposalJudgesInputDTO(
                                    url=status_url,
                                    proposal_id=int(row["id"]),
                                    force=False,  # 既存データの確認はUseCaseで行う
                                )

                                # 非同期処理を同期的に実行
                                # Streamlitでは asyncio.run() を使用する
                                result = asyncio.run(use_case.extract_judges(input_dto))

                                if result and result.extracted_count > 0:
                                    st.success(
                                        f"賛否情報を{result.extracted_count}件抽出しました"
                                    )
                                    st.rerun()
                                else:
                                    st.warning("賛否情報が見つかりませんでした")
                            except TimeoutError:
                                st.error(
                                    "処理がタイムアウトしました。しばらく待ってから再度お試しください。"
                                )
                            except Exception as e:
                                error_msg = str(e)
                                if "GOOGLE_API_KEY" in error_msg:
                                    st.error(
                                        "Google Gemini APIキーが設定されていません。"
                                        "環境変数GOOGLE_API_KEYを設定してください。"
                                    )
                                elif "API" in error_msg.upper():
                                    st.error(
                                        "LLM APIでエラーが発生しました。"
                                        "しばらく待ってから再度お試しください。"
                                    )
                                else:
                                    st.error(f"エラーが発生しました: {error_msg}")
                            finally:
                                # セッションを確実にクローズ
                                if sync_session:
                                    sync_session.close()
                else:
                    st.button(
                        "賛否抽出",
                        key=f"extract_judges_{row['id']}",
                        disabled=True,
                        help="status_urlが設定されていません",
                    )

            with col5:
                if st.button("削除", key=f"delete_proposal_{row['id']}"):
                    if proposal_repo.delete(row["id"]):
                        st.success("議案を削除しました")
                        st.rerun()
                    else:
                        st.error("議案の削除に失敗しました")

            # 編集モードの場合、このレコードの直下に編集フォームを表示
            if (
                "edit_proposal_id" in st.session_state
                and st.session_state.edit_proposal_id == row["id"]
            ):
                with st.container():
                    st.divider()
                    edit_proposal(int(row["id"]))
                    st.divider()
            else:
                st.divider()

    else:
        st.info("議案が登録されていません")

    proposal_repo.close()
    meeting_repo.close()


def edit_proposal(proposal_id: int):
    """議案編集フォーム."""
    st.markdown("#### 議案編集")

    proposal_repo = RepositoryAdapter(ProposalRepositoryImpl)
    proposal = proposal_repo.get_by_id(proposal_id)

    if proposal:
        with st.form(key=f"edit_proposal_form_{proposal_id}"):
            content = st.text_area("議案内容", value=proposal.content)
            proposal_number = st.text_input(
                "議案番号", value=proposal.proposal_number or ""
            )
            submitter = st.text_input("提出者", value=proposal.submitter or "")
            status = st.text_input("状態", value=proposal.status or "")
            detail_url = st.text_input(
                "詳細URL",
                value=proposal.detail_url or "",
                help="議案の詳細情報が記載されているページのURL",
            )
            status_url = st.text_input(
                "状態URL",
                value=proposal.status_url or "",
                help="議案の審議状態や賛否結果が記載されているページのURL",
            )
            summary = st.text_area("概要", value=proposal.summary or "")

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("更新"):
                    proposal.content = content
                    proposal.proposal_number = (
                        proposal_number if proposal_number else None
                    )
                    proposal.submitter = submitter if submitter else None
                    proposal.status = status if status else None
                    proposal.detail_url = detail_url if detail_url else None
                    proposal.status_url = status_url if status_url else None
                    proposal.summary = summary if summary else None

                    if proposal_repo.update(proposal):
                        st.success("議案を更新しました")
                        del st.session_state.edit_proposal_id
                        st.rerun()
                    else:
                        st.error("更新に失敗しました")

            with col2:
                if st.form_submit_button("キャンセル"):
                    del st.session_state.edit_proposal_id
                    st.rerun()

    proposal_repo.close()


def manage_extracted_judges_tab():
    """LLM抽出結果管理タブ."""
    st.subheader("LLM抽出結果一覧")

    # リポジトリ初期化
    extracted_repo = RepositoryAdapter(ExtractedProposalJudgeRepositoryImpl)
    proposal_repo = RepositoryAdapter(ProposalRepositoryImpl)
    politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
    parliamentary_group_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl)

    # フィルター
    col1, col2 = st.columns(2)
    with col1:
        proposals = proposal_repo.get_all()
        proposal_options = ["すべて"] + [
            f"{p.proposal_number or f'ID:{p.id}'}: {p.content[:30]}..."
            for p in proposals
        ]
        selected_proposal = st.selectbox(
            "議案でフィルタリング", proposal_options, key="filter_extracted_proposal"
        )

    with col2:
        status_options = ["すべて", "pending", "matched", "needs_review", "no_match"]
        selected_status = st.selectbox(
            "状態でフィルタリング", status_options, key="filter_extracted_status"
        )

    # 抽出結果一覧取得
    extracted_judges = extracted_repo.get_all()

    # フィルタリング
    if selected_proposal != "すべて":
        proposal_id = proposals[proposal_options.index(selected_proposal) - 1].id
        extracted_judges = [e for e in extracted_judges if e.proposal_id == proposal_id]

    if selected_status != "すべて":
        extracted_judges = [
            e for e in extracted_judges if e.matching_status == selected_status
        ]

    # 編集モードのフラグだけチェック（実際の編集フォームは各レコードの下に表示）

    # 確定処理（編集フォームから呼ばれた場合）
    if "confirm_extracted_id" in st.session_state:
        confirm_id = st.session_state.confirm_extracted_id
        extracted = extracted_repo.get_by_id(confirm_id)

        if extracted and extracted.matching_status == "matched":
            try:
                # 会派の賛否として確定する場合
                if extracted.matched_parliamentary_group_id:
                    group_judge_repo = RepositoryAdapter(
                        ppgjr.ProposalParliamentaryGroupJudgeRepositoryImpl
                    )
                    new_judge = ProposalParliamentaryGroupJudge(
                        proposal_id=extracted.proposal_id,
                        parliamentary_group_id=extracted.matched_parliamentary_group_id,
                        judgment=extracted.extracted_judgment,
                    )
                    if group_judge_repo.create(new_judge):
                        # 変換済みのExtractedJudgeを削除
                        extracted_repo.delete(confirm_id)
                        st.success("✅ 会派の賛否情報を確定しました")
                    else:
                        st.error("確定に失敗しました")
                    group_judge_repo.close()

                # 政治家個人の賛否として確定する場合
                elif extracted.matched_politician_id:
                    proposal_judge_repo = RepositoryAdapter(ProposalJudgeRepositoryImpl)
                    new_judge = ProposalJudge(
                        proposal_id=extracted.proposal_id,
                        politician_id=extracted.matched_politician_id,
                        approve=extracted.extracted_judgment,
                    )
                    if proposal_judge_repo.create(new_judge):
                        # 変換済みのExtractedJudgeを削除
                        extracted_repo.delete(confirm_id)
                        st.success("✅ 政治家の賛否情報を確定しました")
                    else:
                        st.error("確定に失敗しました")
                    proposal_judge_repo.close()

            except Exception as e:
                st.error(f"確定処理でエラーが発生しました: {str(e)}")

        # 確定処理後、セッションステートをクリア
        del st.session_state.confirm_extracted_id
        st.rerun()

    if extracted_judges:
        # 議案情報を取得してマッピング
        proposal_dict = {}
        for proposal in proposals:
            proposal_dict[proposal.id] = proposal

        # 議案ごとにグループ化
        judges_by_proposal = {}
        for judge in extracted_judges:
            if judge.proposal_id not in judges_by_proposal:
                judges_by_proposal[judge.proposal_id] = []
            judges_by_proposal[judge.proposal_id].append(judge)

        # 議案ごとに表示
        for proposal_id, judges in judges_by_proposal.items():
            proposal = proposal_dict.get(proposal_id)

            # 議案情報のヘッダー
            proposal_title = (
                f"{proposal.proposal_number or f'ID:{proposal_id}'}"
                if proposal
                else f"ID:{proposal_id}"
            )
            proposal_content = proposal.content[:60] if proposal else "不明"

            with st.expander(
                f"📋 議案: {proposal_title} - {proposal_content}... "
                f"(抽出件数: {len(judges)}件)",
                expanded=True,
            ):
                if proposal and proposal.status_url:
                    st.caption(f"🔗 [賛否情報ソース]({proposal.status_url})")

                # 賛否の集計を表示
                approve_count = len(
                    [j for j in judges if j.extracted_judgment == "賛成"]
                )
                oppose_count = len(
                    [j for j in judges if j.extracted_judgment == "反対"]
                )

                col1, col2 = st.columns(2)
                with col1:
                    st.metric("賛成", approve_count)
                with col2:
                    st.metric("反対", oppose_count)

                st.divider()

                # 各抽出結果の表示
                for judge in judges:
                    col1, col2, col3, col4 = st.columns([4, 1.5, 1.5, 1])

                    with col1:
                        # 政治家名または議員団名を表示
                        name = (
                            judge.extracted_politician_name
                            or judge.extracted_parliamentary_group_name
                            or "不明"
                        )

                        # マッチング済みの場合、紐付け先を表示
                        if judge.matched_politician_id:
                            politician = politician_repo.get_by_id(
                                judge.matched_politician_id
                            )
                            if politician:
                                name = f"{name} → {politician.name}"
                        elif judge.matched_parliamentary_group_id:
                            group = parliamentary_group_repo.get_by_id(
                                judge.matched_parliamentary_group_id
                            )
                            if group:
                                name = f"{name} → {group.name}"

                        judgment = judge.extracted_judgment or "不明"

                        # 賛否に応じて色付きバッジで表示
                        judgment_color = {
                            "賛成": "🟢",
                            "反対": "🔴",
                        }.get(judgment, "⚪")

                        status_text = {
                            "pending": "未紐付",
                            "matched": "紐付済",
                            "no_match": "なし",
                            "needs_review": "要確認",
                        }.get(judge.matching_status, judge.matching_status)

                        # 追加情報をツールチップに
                        tooltip = []
                        if judge.matching_confidence:
                            tooltip.append(f"信頼度: {judge.matching_confidence:.0%}")
                        if judge.extracted_party_name:
                            tooltip.append(f"政党: {judge.extracted_party_name}")
                        tooltip_text = " | ".join(tooltip) if tooltip else None

                        # 1行にまとめて表示
                        display_text = (
                            f"{judgment_color} **{name}** - {judgment} ({status_text})"
                        )
                        if tooltip_text:
                            st.markdown(display_text, help=tooltip_text)
                        else:
                            st.markdown(display_text)

                    with col2:
                        # 編集中の場合はキャンセルボタン、そうでない場合は編集ボタン
                        is_editing = (
                            "edit_extracted_id" in st.session_state
                            and st.session_state.edit_extracted_id == judge.id
                        )
                        button_label = "編集" if not is_editing else "取消"

                        if st.button(
                            button_label,
                            key=f"edit_extracted_{judge.id}",
                            use_container_width=False,
                        ):
                            if is_editing:
                                # 編集をキャンセル
                                del st.session_state.edit_extracted_id
                            else:
                                # 編集モードに入る
                                st.session_state.edit_extracted_id = judge.id
                            st.rerun()

                    with col3:
                        # 会派または政治家の賛否を確定するボタン
                        can_confirm = judge.matching_status == "matched" and (
                            judge.matched_parliamentary_group_id
                            or judge.matched_politician_id
                        )

                        if can_confirm:
                            if st.button(
                                "確定",
                                key=f"confirm_extracted_{judge.id}",
                                use_container_width=False,
                            ):
                                try:
                                    # 会派の賛否として確定する場合
                                    if judge.matched_parliamentary_group_id:
                                        group_judge_repo = RepositoryAdapter(
                                            ppgjr.ProposalParliamentaryGroupJudgeRepositoryImpl
                                        )
                                        new_judge = ProposalParliamentaryGroupJudge(
                                            proposal_id=judge.proposal_id,
                                            parliamentary_group_id=judge.matched_parliamentary_group_id,
                                            judgment=judge.extracted_judgment,
                                        )
                                        if group_judge_repo.create(new_judge):
                                            # 変換済みのExtractedJudgeを削除
                                            extracted_repo.delete(judge.id)
                                            st.success("会派の賛否情報を確定しました")
                                            st.rerun()
                                        else:
                                            st.error("確定に失敗しました")
                                        group_judge_repo.close()

                                    # 政治家個人の賛否として確定する場合
                                    elif judge.matched_politician_id:
                                        proposal_judge_repo = RepositoryAdapter(
                                            ProposalJudgeRepositoryImpl
                                        )
                                        new_judge = ProposalJudge(
                                            proposal_id=judge.proposal_id,
                                            politician_id=judge.matched_politician_id,
                                            approve=judge.extracted_judgment,
                                        )
                                        if proposal_judge_repo.create(new_judge):
                                            # 変換済みのExtractedJudgeを削除
                                            extracted_repo.delete(judge.id)
                                            st.success("政治家の賛否情報を確定しました")
                                            st.rerun()
                                        else:
                                            st.error("確定に失敗しました")
                                        proposal_judge_repo.close()

                                except Exception as e:
                                    st.error(f"エラー: {str(e)}")
                        else:
                            st.button(
                                "確定",
                                key=f"confirm_extracted_{judge.id}",
                                disabled=True,
                                help="紐付けが必要です",
                                use_container_width=False,
                            )

                    with col4:
                        if st.button(
                            "削除",
                            key=f"delete_extracted_{judge.id}",
                            use_container_width=False,
                        ):
                            if extracted_repo.delete(judge.id):
                                st.success("抽出結果を削除しました")
                                st.rerun()
                            else:
                                st.error("削除に失敗しました")

                    # 編集モードの場合、このレコードの直下に編集フォームを表示
                    if (
                        "edit_extracted_id" in st.session_state
                        and st.session_state.edit_extracted_id == judge.id
                    ):
                        st.divider()
                        with st.container():
                            edit_extracted_judge(judge.id)
                        st.divider()
                    else:
                        # 編集モードでない場合のみdividerを表示（コンパクトに）
                        st.markdown("---")

    else:
        st.info("抽出結果がありません")

    extracted_repo.close()
    proposal_repo.close()
    politician_repo.close()
    parliamentary_group_repo.close()


def edit_extracted_judge(extracted_id: int):
    """抽出結果編集・紐付けフォーム."""
    st.subheader("抽出結果の編集と紐付け")

    extracted_repo = RepositoryAdapter(ExtractedProposalJudgeRepositoryImpl)
    politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)
    parliamentary_group_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl)
    proposal_repo = RepositoryAdapter(ProposalRepositoryImpl)
    meeting_repo = RepositoryAdapter(MeetingRepositoryImpl)
    politician_affiliation_repo = RepositoryAdapter(PoliticianAffiliationRepositoryImpl)

    extracted = extracted_repo.get_by_id(extracted_id)

    if not extracted:
        st.error("抽出結果が見つかりません")
        if st.button("戻る"):
            del st.session_state.edit_extracted_id
            st.rerun()
        extracted_repo.close()
        politician_repo.close()
        parliamentary_group_repo.close()
        proposal_repo.close()
        meeting_repo.close()
        politician_affiliation_repo.close()
        return

    # 議案から会議、そしてConferenceを特定
    proposal = proposal_repo.get_by_id(extracted.proposal_id)
    conference_id = None
    if proposal and proposal.meeting_id:
        meeting = meeting_repo.get_by_id(proposal.meeting_id)
        if meeting:
            conference_id = meeting.conference_id

    # extracted が存在する場合の処理
    # 現在の抽出内容を表示
    st.info(f"""
    **抽出された内容:**
    - 名前: {
        (
            extracted.extracted_politician_name
            or extracted.extracted_parliamentary_group_name
            or "不明"
        )
    }
    - 政党: {extracted.extracted_party_name or "不明"}
    - 賛否: {extracted.extracted_judgment or "不明"}
    """)

    # 議員と議員団のデータを事前に取得（フォーム外で取得）
    if conference_id:
        # Conferenceに所属する政治家を取得
        affiliations = politician_affiliation_repo.get_by_conference(conference_id)
        politician_ids = [a.politician_id for a in affiliations if a.politician_id]

        all_politicians = politician_repo.get_all()
        politicians = [p for p in all_politicians if p.id in politician_ids]

        # Conferenceに所属する議員団を取得
        all_groups = parliamentary_group_repo.get_all()
        groups = [g for g in all_groups if g.conference_id == conference_id]

        if politicians or groups:
            st.success(
                f"開催主体の議員: {len(politicians)}名、議員団: {len(groups)}団体"
            )
        else:
            st.warning("この議案の開催主体に紐づく政治家・議員団が見つかりません")
            # フォールバックとして全データを表示
            politicians = all_politicians
            groups = all_groups
    else:
        st.warning(
            "議案の開催主体を特定できませんでした。すべての政治家・議員団を表示します"
        )
        politicians = politician_repo.get_all()
        groups = parliamentary_group_repo.get_all()

    with st.form(key=f"edit_extracted_form_{extracted_id}"):
        st.markdown("### 紐付け設定")
        st.markdown("議員または議員団のいずれか一つを選択してください")

        # 議員と議員団の選択肢を両方表示
        col1, col2 = st.columns(2)

        # 議員選択
        with col1:
            st.markdown("#### 👤 議員に紐付ける場合")

            # 名前でフィルタリング（抽出名に近いものを上位に）
            if extracted.extracted_politician_name:
                # 部分一致する議員を優先表示
                filtered_politicians = [
                    p
                    for p in politicians
                    if extracted.extracted_politician_name in p.name
                    or p.name in extracted.extracted_politician_name
                ]
                other_politicians = [
                    p for p in politicians if p not in filtered_politicians
                ]
                politicians = filtered_politicians + other_politicians
                # 候補数を表示（フォーム内ではst.successは使えない）
                politician_help_text = (
                    f"議員を選択する場合、議員団は選択できません"
                    f"（候補: {len(filtered_politicians)}件の部分一致）"
                    if filtered_politicians
                    else "議員を選択する場合、議員団は選択できません"
                )
            else:
                politician_help_text = "議員を選択する場合、議員団は選択できません"

            selected_politician_id = st.selectbox(
                "議員を選択",
                options=[None] + [p.id for p in politicians],
                format_func=lambda x: "-- 選択してください --"
                if x is None
                else next((f"{p.name}" for p in politicians if p.id == x), ""),
                index=0
                if not extracted.matched_politician_id
                else next(
                    (
                        i + 1
                        for i, p in enumerate(politicians)
                        if p.id == extracted.matched_politician_id
                    ),
                    0,
                ),
                help=politician_help_text,
            )

        # 議員団選択
        with col2:
            st.markdown("#### 🏛️ 議員団に紐付ける場合")

            # 名前でフィルタリング
            if extracted.extracted_parliamentary_group_name:
                filtered_groups = [
                    g
                    for g in groups
                    if extracted.extracted_parliamentary_group_name in g.name
                    or g.name in extracted.extracted_parliamentary_group_name
                ]
                other_groups = [g for g in groups if g not in filtered_groups]
                groups = filtered_groups + other_groups
                # 候補数を表示（フォーム内ではst.successは使えない）
                group_help_text = (
                    f"議員団を選択する場合、議員は選択できません"
                    f"（候補: {len(filtered_groups)}件の部分一致）"
                    if filtered_groups
                    else "議員団を選択する場合、議員は選択できません"
                )
            else:
                group_help_text = "議員団を選択する場合、議員は選択できません"

            selected_group_id = st.selectbox(
                "議員団を選択",
                options=[None] + [g.id for g in groups],
                format_func=lambda x: "-- 選択してください --"
                if x is None
                else next((f"{g.name}" for g in groups if g.id == x), ""),
                index=0
                if not extracted.matched_parliamentary_group_id
                else next(
                    (
                        i + 1
                        for i, g in enumerate(groups)
                        if g.id == extracted.matched_parliamentary_group_id
                    ),
                    0,
                ),
                help=group_help_text,
            )

            # 賛否判定
            st.markdown("### 賛否判定")
            judgment = st.selectbox(
                "賛否",
                options=["賛成", "反対"],
                index=["賛成", "反対"].index(extracted.extracted_judgment)
                if extracted.extracted_judgment in ["賛成", "反対"]
                else 0,
            )

            # 人手による紐付けは信頼度100%固定
            confidence = 1.0

            st.markdown("---")

            col1, col2, col3 = st.columns(3)
            with col1:
                submit_save = st.form_submit_button("💾 保存", type="primary")

            with col2:
                submit_cancel = st.form_submit_button("❌ キャンセル")

            with col3:
                # 紐付けされている場合のみ確定ボタンを有効化
                can_confirm = selected_politician_id or selected_group_id
                if can_confirm:
                    submit_confirm = st.form_submit_button(
                        "✅ 保存して確定", type="secondary"
                    )
                else:
                    submit_confirm = st.form_submit_button(
                        "✅ 保存して確定",
                        disabled=True,
                        help="議員または議員団を選択してください",
                    )

        # フォーム送信後の処理（フォームの外で処理）
        if "submit_save" in locals() and submit_save:
            # 更新処理
            extracted.extracted_judgment = judgment

            # 両方選択されている場合のバリデーション
            if selected_politician_id and selected_group_id:
                st.error(
                    "議員と議員団の両方を選択することはできません。どちらか一つを選択してください。"
                )
            elif selected_politician_id:
                # 議員に紐付け
                extracted.matched_politician_id = selected_politician_id
                extracted.matched_parliamentary_group_id = None
                extracted.matching_confidence = 1.0
                extracted.matching_status = "matched"

                if extracted_repo.update(extracted):
                    politician = next(
                        (p for p in politicians if p.id == selected_politician_id), None
                    )
                    if politician:
                        st.success(f"✅ 議員「{politician.name}」に紐付けました")
                    else:
                        st.success("✅ 議員に紐付けました")
                    del st.session_state.edit_extracted_id
                    st.rerun()
                else:
                    st.error("更新に失敗しました")

            elif selected_group_id:
                # 議員団に紐付け
                extracted.matched_parliamentary_group_id = selected_group_id
                extracted.matched_politician_id = None
                extracted.matching_confidence = 1.0
                extracted.matching_status = "matched"

                if extracted_repo.update(extracted):
                    group = next((g for g in groups if g.id == selected_group_id), None)
                    if group:
                        st.success(f"✅ 議員団「{group.name}」に紐付けました")
                    else:
                        st.success("✅ 議員団に紐付けました")
                    del st.session_state.edit_extracted_id
                    st.rerun()
                else:
                    st.error("更新に失敗しました")

            else:
                # 紐付けなし（賛否のみ更新）
                extracted.matched_politician_id = None
                extracted.matched_parliamentary_group_id = None
                extracted.matching_confidence = None
                extracted.matching_status = "pending"

                if extracted_repo.update(extracted):
                    st.success("✅ 賛否情報を更新しました（紐付けなし）")
                    del st.session_state.edit_extracted_id
                    st.rerun()
                else:
                    st.error("更新に失敗しました")

        elif "submit_cancel" in locals() and submit_cancel:
            del st.session_state.edit_extracted_id
            st.rerun()

        elif "submit_confirm" in locals() and submit_confirm:
            # 両方選択されている場合のバリデーション
            if selected_politician_id and selected_group_id:
                st.error("議員と議員団の両方を選択することはできません")
            else:
                # 紐付けを保存してから確定処理
                extracted.extracted_judgment = judgment

                if selected_politician_id:
                    extracted.matched_politician_id = selected_politician_id
                    extracted.matched_parliamentary_group_id = None
                    extracted.matching_confidence = 1.0
                    extracted.matching_status = "matched"
                elif selected_group_id:
                    extracted.matched_parliamentary_group_id = selected_group_id
                    extracted.matched_politician_id = None
                    extracted.matching_confidence = 1.0
                    extracted.matching_status = "matched"

                if extracted_repo.update(extracted):
                    # 確定処理を実行
                    st.session_state.confirm_extracted_id = extracted_id
                    del st.session_state.edit_extracted_id
                    st.rerun()

    extracted_repo.close()
    politician_repo.close()
    parliamentary_group_repo.close()
    proposal_repo.close()
    meeting_repo.close()
    politician_affiliation_repo.close()


def manage_proposal_judges_tab():
    """確定賛否情報管理タブ."""
    st.subheader("確定賛否情報一覧")

    # リポジトリ初期化
    judge_repo = RepositoryAdapter(ProposalJudgeRepositoryImpl)
    proposal_repo = RepositoryAdapter(ProposalRepositoryImpl)
    politician_repo = RepositoryAdapter(PoliticianRepositoryImpl)

    # 新規賛否情報登録フォーム
    with st.expander("新規賛否情報登録", expanded=False):
        with st.form(key="new_judge_form"):
            col1, col2 = st.columns(2)

            proposals = proposal_repo.get_all()
            politicians = politician_repo.get_all()

            with col1:
                proposal_id = st.selectbox(
                    "議案",
                    options=[p.id for p in proposals],
                    format_func=lambda x: next(
                        (
                            f"{p.proposal_number or f'ID:{p.id}'}: {p.content[:30]}..."
                            for p in proposals
                            if p.id == x
                        ),
                        "",
                    ),
                    key="new_judge_proposal",
                )

            with col2:
                politician_id = st.selectbox(
                    "政治家",
                    options=[p.id for p in politicians],
                    format_func=lambda x: next(
                        (f"{p.name}" for p in politicians if p.id == x),
                        "",
                    ),
                    key="new_judge_politician",
                )

            judgment = st.selectbox(
                "賛否",
                options=["賛成", "反対"],
                key="new_judge_judgment",
            )

            if st.form_submit_button("登録"):
                if proposal_id and politician_id:
                    try:
                        new_judge = ProposalJudge(
                            proposal_id=proposal_id,
                            politician_id=politician_id,
                            approve=judgment,
                        )
                        if judge_repo.create(new_judge):
                            st.success("賛否情報を登録しました")
                            st.rerun()
                        else:
                            st.error("登録に失敗しました")
                    except Exception as e:
                        st.error(f"エラー: {str(e)}")
                else:
                    st.error("議案と政治家を選択してください")

    # 確定賛否情報一覧取得
    judges = judge_repo.get_all()
    proposals = proposal_repo.get_all()
    politicians = politician_repo.get_all()

    # 議員団の賛否情報も取得
    group_judge_repo = RepositoryAdapter(
        ppgjr.ProposalParliamentaryGroupJudgeRepositoryImpl
    )
    parliamentary_group_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl)
    group_judges = group_judge_repo.get_all()
    parliamentary_groups = parliamentary_group_repo.get_all()

    # IDから名前を引けるようにマップ作成
    proposal_map = {p.id: p for p in proposals}
    politician_map = {p.id: p for p in politicians}
    group_map = {g.id: g for g in parliamentary_groups}

    if judges:
        # 各レコードの表示と操作ボタン
        for judge in judges:
            col1, col2, col3 = st.columns([5, 1, 1])

            proposal = proposal_map.get(judge.proposal_id)
            politician = politician_map.get(judge.politician_id)

            with col1:
                politician_name = (
                    politician.name if politician else f"ID:{judge.politician_id}"
                )
                if proposal:
                    prop_num = proposal.proposal_number or f"ID:{proposal.id}"
                    proposal_text = f"{prop_num}: {proposal.content[:30]}..."
                else:
                    proposal_text = f"議案ID:{judge.proposal_id}"
                st.markdown(f"**{politician_name}** - {judge.approve or '不明'}")
                st.caption(f"議案: {proposal_text}")
                if politician and politician.party:
                    st.caption(f"政党: {politician.party}")

            with col2:
                if st.button("編集", key=f"edit_judge_{judge.id}"):
                    st.session_state.edit_judge_id = judge.id
                    st.rerun()

            with col3:
                if st.button("削除", key=f"delete_judge_{judge.id}"):
                    if judge_repo.delete(judge.id):
                        st.success("賛否情報を削除しました")
                        st.rerun()
                    else:
                        st.error("削除に失敗しました")

            st.divider()

        # 編集モード
        if "edit_judge_id" in st.session_state:
            edit_proposal_judge(st.session_state.edit_judge_id)

    else:
        st.info("政治家の確定賛否情報がありません")

    # 議員団の賛否情報を表示
    if group_judges:
        st.subheader("議員団の賛否情報")
        for group_judge in group_judges:
            col1, col2, col3 = st.columns([5, 1, 1])

            proposal = proposal_map.get(group_judge.proposal_id)
            group = group_map.get(group_judge.parliamentary_group_id)

            with col1:
                group_name = (
                    group.name if group else f"ID:{group_judge.parliamentary_group_id}"
                )
                if proposal:
                    prop_num = proposal.proposal_number or f"ID:{proposal.id}"
                    proposal_text = f"{prop_num}: {proposal.content[:30]}..."
                else:
                    proposal_text = f"議案ID:{group_judge.proposal_id}"
                st.markdown(f"**{group_name}** - {group_judge.judgment or '不明'}")
                st.caption(f"議案: {proposal_text}")
                if group_judge.member_count:
                    st.caption(f"賛同人数: {group_judge.member_count}名")
                if group_judge.note:
                    st.caption(f"備考: {group_judge.note}")

            with col2:
                if st.button("編集", key=f"edit_group_judge_{group_judge.id}"):
                    st.info("議員団賛否の編集機能は開発中です")

            with col3:
                if st.button("削除", key=f"delete_group_judge_{group_judge.id}"):
                    if group_judge_repo.delete(group_judge.id):
                        st.success("議員団賛否情報を削除しました")
                        st.rerun()
                    else:
                        st.error("削除に失敗しました")

            st.divider()
    elif not judges:  # 両方ない場合
        st.info("確定賛否情報がありません")

    judge_repo.close()
    proposal_repo.close()
    politician_repo.close()
    group_judge_repo.close()
    parliamentary_group_repo.close()


def edit_proposal_judge(judge_id: int):
    """確定賛否情報編集フォーム."""
    st.subheader("賛否情報編集")

    judge_repo = RepositoryAdapter(ProposalJudgeRepositoryImpl)
    judge = judge_repo.get_by_id(judge_id)

    if judge:
        with st.form(key=f"edit_judge_form_{judge_id}"):
            judgment = st.selectbox(
                "賛否",
                options=["賛成", "反対"],
                index=["賛成", "反対"].index(judge.approve)
                if judge.approve in ["賛成", "反対"]
                else 0,
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("更新"):
                    judge.approve = judgment

                    if judge_repo.update(judge):
                        st.success("賛否情報を更新しました")
                        del st.session_state.edit_judge_id
                        st.rerun()
                    else:
                        st.error("更新に失敗しました")

            with col2:
                if st.form_submit_button("キャンセル"):
                    del st.session_state.edit_judge_id
                    st.rerun()

    judge_repo.close()
