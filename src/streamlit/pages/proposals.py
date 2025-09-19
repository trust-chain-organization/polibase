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
from src.infrastructure.external.llm_service import GeminiLLMService
from src.infrastructure.external.proposal_scraper_service import ProposalScraperService
from src.infrastructure.external.web_scraper_service import PlaywrightScraperService
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.extracted_proposal_judge_repository_impl import (
    ExtractedProposalJudgeRepositoryImpl,
)
from src.infrastructure.persistence.meeting_repository_impl import MeetingRepositoryImpl
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

            st.divider()

        # 編集モード
        if "edit_proposal_id" in st.session_state:
            edit_proposal(st.session_state.edit_proposal_id)

    else:
        st.info("議案が登録されていません")

    proposal_repo.close()
    meeting_repo.close()


def edit_proposal(proposal_id: int):
    """議案編集フォーム."""
    st.subheader("議案編集")

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
                abstain_count = len(
                    [j for j in judges if j.extracted_judgment == "棄権"]
                )
                absent_count = len(
                    [j for j in judges if j.extracted_judgment == "欠席"]
                )

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("賛成", approve_count)
                with col2:
                    st.metric("反対", oppose_count)
                with col3:
                    st.metric("棄権", abstain_count)
                with col4:
                    st.metric("欠席", absent_count)

                st.divider()

                # 各抽出結果の表示
                for judge in judges:
                    col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])

                    with col1:
                        # 政治家名または議員団名を表示
                        name = (
                            judge.extracted_politician_name
                            or judge.extracted_parliamentary_group_name
                            or "不明"
                        )
                        st.markdown(f"**{name}**")
                        judgment = judge.extracted_judgment or "不明"

                        # 賛否に応じて色付きバッジで表示
                        judgment_color = {
                            "賛成": "🟢",
                            "反対": "🔴",
                            "棄権": "🟡",
                            "欠席": "⚫",
                        }.get(judgment, "⚪")

                        status_text = judge.matching_status
                        st.caption(f"{judgment_color} {judgment} | 状態: {status_text}")
                        if judge.matching_confidence:
                            st.caption(f"信頼度: {judge.matching_confidence:.2%}")
                        if judge.extracted_party_name:
                            st.caption(f"政党: {judge.extracted_party_name}")

                    with col2:
                        if st.button("編集", key=f"edit_extracted_{judge.id}"):
                            st.session_state.edit_extracted_id = judge.id
                            st.rerun()

                    with col3:
                        # マッチング実行ボタン
                        if judge.matching_status == "pending":
                            if st.button(
                                "マッチング", key=f"match_extracted_{judge.id}"
                            ):
                                with st.spinner("マッチング中..."):
                                    # TODO: マッチング処理の実装
                                    st.info("マッチング機能は開発中です")
                        else:
                            st.button(
                                "マッチング済",
                                key=f"match_extracted_{judge.id}",
                                disabled=True,
                            )

                    with col4:
                        # ProposalJudgeへの変換ボタン
                        if (
                            judge.matching_status == "matched"
                            and judge.matched_politician_id
                        ):
                            if st.button("確定", key=f"confirm_extracted_{judge.id}"):
                                try:
                                    # ProposalJudgeに変換
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
                                        st.success("賛否情報を確定しました")
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
                            )

                    with col5:
                        if st.button("削除", key=f"delete_extracted_{judge.id}"):
                            if extracted_repo.delete(judge.id):
                                st.success("抽出結果を削除しました")
                                st.rerun()
                            else:
                                st.error("削除に失敗しました")

                    st.divider()

        # 編集モード
        if "edit_extracted_id" in st.session_state:
            edit_extracted_judge(st.session_state.edit_extracted_id)

    else:
        st.info("抽出結果がありません")

    extracted_repo.close()
    proposal_repo.close()
    politician_repo.close()


def edit_extracted_judge(extracted_id: int):
    """抽出結果編集フォーム."""
    st.subheader("抽出結果編集")

    extracted_repo = RepositoryAdapter(ExtractedProposalJudgeRepositoryImpl)
    extracted = extracted_repo.get_by_id(extracted_id)

    if extracted:
        with st.form(key=f"edit_extracted_form_{extracted_id}"):
            politician_name = st.text_input(
                "政治家名", value=extracted.extracted_politician_name or ""
            )
            party_name = st.text_input(
                "政党名", value=extracted.extracted_party_name or ""
            )
            parliamentary_group = st.text_input(
                "議員団名", value=extracted.extracted_parliamentary_group_name or ""
            )
            judgment = st.selectbox(
                "賛否",
                options=["賛成", "反対", "棄権", "欠席"],
                index=["賛成", "反対", "棄権", "欠席"].index(
                    extracted.extracted_judgment
                )
                if extracted.extracted_judgment in ["賛成", "反対", "棄権", "欠席"]
                else 0,
            )

            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("更新"):
                    extracted.extracted_politician_name = (
                        politician_name if politician_name else None
                    )
                    extracted.extracted_party_name = party_name if party_name else None
                    extracted.extracted_parliamentary_group_name = (
                        parliamentary_group if parliamentary_group else None
                    )
                    extracted.extracted_judgment = judgment

                    if extracted_repo.update(extracted):
                        st.success("抽出結果を更新しました")
                        del st.session_state.edit_extracted_id
                        st.rerun()
                    else:
                        st.error("更新に失敗しました")

            with col2:
                if st.form_submit_button("キャンセル"):
                    del st.session_state.edit_extracted_id
                    st.rerun()

    extracted_repo.close()


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
                options=["賛成", "反対", "棄権", "欠席"],
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

    # IDから名前を引けるようにマップ作成
    proposal_map = {p.id: p for p in proposals}
    politician_map = {p.id: p for p in politicians}

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
        st.info("確定賛否情報がありません")

    judge_repo.close()
    proposal_repo.close()
    politician_repo.close()


def edit_proposal_judge(judge_id: int):
    """確定賛否情報編集フォーム."""
    st.subheader("賛否情報編集")

    judge_repo = RepositoryAdapter(ProposalJudgeRepositoryImpl)
    judge = judge_repo.get_by_id(judge_id)

    if judge:
        with st.form(key=f"edit_judge_form_{judge_id}"):
            judgment = st.selectbox(
                "賛否",
                options=["賛成", "反対", "棄権", "欠席"],
                index=["賛成", "反対", "棄権", "欠席"].index(judge.approve)
                if judge.approve in ["賛成", "反対", "棄権", "欠席"]
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
