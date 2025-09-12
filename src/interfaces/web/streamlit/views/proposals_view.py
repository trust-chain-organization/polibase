"""View for proposal management."""

import streamlit as st
from src.interfaces.web.streamlit.presenters.proposal_presenter import (
    ProposalPresenter,
)


def render_proposals_page():
    """Render the proposals management page."""
    st.header("議案管理")
    st.markdown("議案情報と賛否データを管理します")

    presenter = ProposalPresenter()

    # Create tabs
    tabs = st.tabs(
        ["議案一覧", "新規登録", "URLからスクレイピング", "編集・削除", "賛否抽出"]
    )

    with tabs[0]:
        render_proposals_list_tab(presenter)

    with tabs[1]:
        render_new_proposal_tab(presenter)

    with tabs[2]:
        render_scrape_proposal_tab(presenter)

    with tabs[3]:
        render_edit_delete_tab(presenter)

    with tabs[4]:
        render_extract_judges_tab(presenter)


def render_proposals_list_tab(presenter: ProposalPresenter):
    """Render the proposals list tab."""
    st.subheader("議案一覧")

    # Get meetings for filter
    meetings = presenter.get_all_meetings()

    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        # Filter by meeting
        meeting_options = ["すべて"] + [
            f"{m.meeting_name} ({m.meeting_date})" for m in meetings
        ]
        meeting_map = {f"{m.meeting_name} ({m.meeting_date})": m.id for m in meetings}
        selected_meeting = st.selectbox("会議でフィルタ", meeting_options)

    with col2:
        # Filter by status
        status_options = ["すべて", "審議中", "可決", "否決", "継続審議", "取り下げ"]
        selected_status = st.selectbox("状態でフィルタ", status_options)

    with col3:
        # Search by proposal number
        search_number = st.text_input("議案番号で検索", placeholder="例: 議案第1号")

    # Load proposals based on filters
    if selected_meeting != "すべて":
        meeting_id = meeting_map.get(selected_meeting)
        proposals = (
            presenter.load_proposals_by_meeting(meeting_id) if meeting_id else []
        )
    elif selected_status != "すべて":
        proposals = presenter.load_proposals_by_status(selected_status)
    else:
        proposals = presenter.load_all_proposals()

    # Filter by proposal number if provided
    if search_number and proposals:
        proposals = [
            p
            for p in proposals
            if p.proposal_number and search_number.lower() in p.proposal_number.lower()
        ]

    if proposals:
        # Display data in DataFrame
        df = presenter.to_dataframe(proposals)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Statistics
            st.markdown("### 統計情報")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総議案数", f"{len(proposals)}件")
            with col2:
                approved = len([p for p in proposals if p.status == "可決"])
                st.metric("可決", f"{approved}件")
            with col3:
                rejected = len([p for p in proposals if p.status == "否決"])
                st.metric("否決", f"{rejected}件")
            with col4:
                with_url = len([p for p in proposals if p.url])
                st.metric("URL登録済", f"{with_url}件")

            # Expandable detail view
            st.markdown("### 詳細表示")
            for proposal in proposals[:10]:  # Show first 10
                with st.expander(
                    f"{proposal.proposal_number or f'ID:{proposal.id}'} - "
                    f"{proposal.content[:50]}..."
                ):
                    st.markdown(f"**議案番号:** {proposal.proposal_number or '-'}")
                    st.markdown(f"**状態:** {proposal.status or '-'}")
                    st.markdown(f"**提出者:** {proposal.submitter or '-'}")
                    st.markdown(f"**提出日:** {proposal.submission_date or '-'}")
                    if proposal.url:
                        st.markdown(f"**URL:** [{proposal.url}]({proposal.url})")
                    st.markdown("**内容:**")
                    st.text_area(
                        "議案内容",
                        value=proposal.content,
                        height=200,
                        disabled=True,
                        key=f"content_{proposal.id}",
                    )
                    if proposal.summary:
                        st.markdown("**要約:**")
                        st.text_area(
                            "要約",
                            value=proposal.summary,
                            height=100,
                            disabled=True,
                            key=f"summary_{proposal.id}",
                        )
    else:
        st.info("登録された議案がありません")


def render_new_proposal_tab(presenter: ProposalPresenter):
    """Render the new proposal registration tab."""
    st.subheader("新規議案登録")

    meetings = presenter.get_all_meetings()

    with st.form("new_proposal_form"):
        st.markdown("### 基本情報")
        proposal_number = st.text_input("議案番号", placeholder="議案第1号")
        content = st.text_area(
            "議案内容 *", placeholder="議案の内容を入力してください", height=200
        )

        col1, col2 = st.columns(2)
        with col1:
            status_options = ["審議中", "可決", "否決", "継続審議", "取り下げ"]
            status = st.selectbox("状態", status_options)

        with col2:
            meeting_options = ["なし"] + [
                f"{m.meeting_name} ({m.meeting_date})" for m in meetings
            ]
            meeting_map = {
                f"{m.meeting_name} ({m.meeting_date})": m.id for m in meetings
            }
            selected_meeting = st.selectbox("関連会議", meeting_options)

        st.markdown("### 詳細情報")
        col1, col2 = st.columns(2)
        with col1:
            submitter = st.text_input("提出者", placeholder="例: 市長")
            submission_date = st.date_input("提出日", value=None)

        with col2:
            url = st.text_input("議案URL", placeholder="https://example.com/proposal")

        summary = st.text_area("要約（任意）", placeholder="議案の要約", height=100)

        submitted = st.form_submit_button("登録", type="primary")

        if submitted:
            if not content:
                st.error("議案内容を入力してください")
            else:
                meeting_id = (
                    meeting_map.get(selected_meeting)
                    if selected_meeting != "なし"
                    else None
                )
                submission_date_str = (
                    submission_date.isoformat() if submission_date else None
                )

                success, proposal_id, error = presenter.create_proposal(
                    content=content,
                    proposal_number=proposal_number if proposal_number else None,
                    status=status,
                    url=url if url else None,
                    submission_date=submission_date_str,
                    submitter=submitter if submitter else None,
                    meeting_id=meeting_id,
                    summary=summary if summary else None,
                )

                if success:
                    st.success(f"議案を登録しました（ID: {proposal_id}）")
                    st.rerun()
                else:
                    st.error(f"登録に失敗しました: {error}")


def render_scrape_proposal_tab(presenter: ProposalPresenter):
    """Render the scrape proposal tab."""
    st.subheader("URLから議案をスクレイピング")
    st.markdown("議案詳細ページのURLから自動的に議案情報を取得します")

    meetings = presenter.get_all_meetings()

    with st.form("scrape_proposal_form"):
        url = st.text_input(
            "議案URL *",
            placeholder="https://example.com/council/proposal/123",
            help="議案詳細ページのURLを入力してください",
        )

        meeting_options = ["なし"] + [
            f"{m.meeting_name} ({m.meeting_date})" for m in meetings
        ]
        meeting_map = {f"{m.meeting_name} ({m.meeting_date})": m.id for m in meetings}
        selected_meeting = st.selectbox(
            "関連会議（任意）",
            meeting_options,
            help="スクレイピングした議案を関連付ける会議を選択してください",
        )

        submitted = st.form_submit_button("スクレイピング実行", type="primary")

        if submitted:
            if not url:
                st.error("URLを入力してください")
            elif not url.startswith(("http://", "https://")):
                st.error("有効なURLを入力してください")
            else:
                meeting_id = (
                    meeting_map.get(selected_meeting)
                    if selected_meeting != "なし"
                    else None
                )

                with st.spinner("議案情報をスクレイピング中..."):
                    success, proposal_id, error = presenter.scrape_proposal_from_url(
                        url, meeting_id
                    )

                    if success:
                        st.success(
                            f"議案のスクレイピングが完了しました（ID: {proposal_id}）"
                        )
                        st.info("議案一覧タブで内容を確認してください")
                    else:
                        st.error(f"スクレイピングに失敗しました: {error}")


def render_edit_delete_tab(presenter: ProposalPresenter):
    """Render the edit/delete tab."""
    st.subheader("議案の編集・削除")

    # Load all proposals
    proposals = presenter.load_all_proposals()
    if not proposals:
        st.info("編集する議案がありません")
        return

    meetings = presenter.get_all_meetings()

    # Select proposal to edit
    proposal_options = [
        f"{p.proposal_number or f'ID:{p.id}'} - {p.content[:50]}..." for p in proposals
    ]
    selected_proposal_str = st.selectbox("編集する議案を選択", proposal_options)

    # Get selected proposal
    selected_idx = proposal_options.index(selected_proposal_str)
    selected_proposal = proposals[selected_idx]

    # Edit and delete forms
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("#### 編集")
        with st.form("edit_proposal_form"):
            new_proposal_number = st.text_input(
                "議案番号", value=selected_proposal.proposal_number or ""
            )
            new_content = st.text_area(
                "議案内容 *", value=selected_proposal.content, height=200
            )

            col1_inner, col2_inner = st.columns(2)
            with col1_inner:
                status_options = ["審議中", "可決", "否決", "継続審議", "取り下げ"]
                current_status_idx = (
                    status_options.index(selected_proposal.status)
                    if selected_proposal.status in status_options
                    else 0
                )
                new_status = st.selectbox(
                    "状態", status_options, index=current_status_idx
                )

            with col2_inner:
                meeting_options = ["なし"] + [
                    f"{m.meeting_name} ({m.meeting_date})" for m in meetings
                ]
                meeting_map = {
                    f"{m.meeting_name} ({m.meeting_date})": m.id for m in meetings
                }
                current_meeting_idx = 0
                if selected_proposal.meeting_id:
                    for i, m in enumerate(meetings, 1):
                        if m.id == selected_proposal.meeting_id:
                            current_meeting_idx = i
                            break
                new_meeting = st.selectbox(
                    "関連会議", meeting_options, index=current_meeting_idx
                )

            col1_inner2, col2_inner2 = st.columns(2)
            with col1_inner2:
                new_submitter = st.text_input(
                    "提出者", value=selected_proposal.submitter or ""
                )
                new_submission_date = st.date_input(
                    "提出日",
                    value=(
                        selected_proposal.submission_date
                        if selected_proposal.submission_date
                        else None
                    ),
                )

            with col2_inner2:
                new_url = st.text_input("議案URL", value=selected_proposal.url or "")

            new_summary = st.text_area(
                "要約", value=selected_proposal.summary or "", height=100
            )

            submitted = st.form_submit_button("更新")

            if submitted:
                if not new_content:
                    st.error("議案内容を入力してください")
                else:
                    meeting_id = (
                        meeting_map.get(new_meeting) if new_meeting != "なし" else None
                    )
                    submission_date_str = (
                        new_submission_date.isoformat() if new_submission_date else None
                    )

                    success, error = presenter.update_proposal(
                        proposal_id=selected_proposal.id,  # type: ignore[arg-type]
                        content=new_content,
                        proposal_number=new_proposal_number or None,
                        status=new_status,
                        url=new_url or None,
                        submission_date=submission_date_str,
                        submitter=new_submitter or None,
                        meeting_id=meeting_id,
                        summary=new_summary or None,
                    )

                    if success:
                        st.success("議案を更新しました")
                        st.rerun()
                    else:
                        st.error(f"更新に失敗しました: {error}")

    with col2:
        st.markdown("#### 削除")
        st.warning("削除した議案は復元できません")
        if st.button("削除", type="secondary", key="delete_proposal"):
            success, error = presenter.delete_proposal(selected_proposal.id)  # type: ignore[arg-type]
            if success:
                st.success("議案を削除しました")
                st.rerun()
            else:
                st.error(f"削除に失敗しました: {error}")


def render_extract_judges_tab(presenter: ProposalPresenter):
    """Render the extract judges tab."""
    st.subheader("議案賛否抽出")
    st.markdown("議案URLから議員の賛否情報を自動抽出します")

    # Load proposals with URLs
    all_proposals = presenter.load_all_proposals()
    proposals_with_url = [p for p in all_proposals if p.url]

    if not proposals_with_url:
        st.info("URLが登録されている議案がありません。先に議案を登録してください。")
        return

    # Select proposal
    proposal_options = [
        f"{p.proposal_number or f'ID:{p.id}'} - {p.content[:50]}..."
        for p in proposals_with_url
    ]
    selected_proposal_str = st.selectbox(
        "賛否を抽出する議案を選択",
        proposal_options,
        help="URLが登録されている議案のみ表示されます",
    )

    # Get selected proposal
    selected_idx = proposal_options.index(selected_proposal_str)
    selected_proposal = proposals_with_url[selected_idx]

    # Show proposal details
    with st.expander("議案詳細", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**議案番号:** {selected_proposal.proposal_number or '-'}")
            st.markdown(f"**状態:** {selected_proposal.status or '-'}")
            st.markdown(f"**提出者:** {selected_proposal.submitter or '-'}")
        with col2:
            st.markdown(f"**提出日:** {selected_proposal.submission_date or '-'}")
            st.markdown(f"**URL:** [{selected_proposal.url}]({selected_proposal.url})")

        st.markdown("**内容:**")
        st.text_area(
            "議案内容",
            value=selected_proposal.content,
            height=100,
            disabled=True,
            key="extract_content",
        )

    # Check existing extracted judges
    existing_judges = presenter.get_extracted_judges_for_proposal(
        selected_proposal.id  # type: ignore[arg-type]
    )

    if existing_judges:
        st.info(f"この議案には既に{len(existing_judges)}件の賛否情報が抽出されています")

        # Show existing data
        with st.expander("抽出済みの賛否情報", expanded=False):
            for judge in existing_judges[:10]:  # Show first 10
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    name = (
                        judge.extracted_politician_name
                        or judge.extracted_parliamentary_group_name
                        or "不明"
                    )
                    st.markdown(f"**{name}**")
                    if judge.extracted_party_name:
                        st.caption(f"政党: {judge.extracted_party_name}")
                with col2:
                    st.markdown(f"賛否: **{judge.extracted_judgment or '-'}**")
                with col3:
                    status_emoji = {
                        "matched": "✅",
                        "needs_review": "⚠️",
                        "no_match": "❌",
                        "pending": "⏳",
                    }
                    st.markdown(
                        f"状態: {status_emoji.get(judge.matching_status, '❓')} "
                        f"{judge.matching_status}"
                    )

    # Extract button
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col1:
        if existing_judges:
            st.warning("再度抽出を実行すると、新しいデータが追加されます")
    with col2:
        if st.button(
            "賛否抽出を実行",
            type="primary",
            disabled=not selected_proposal.url,
            key="extract_judges",
        ):
            with st.spinner("議案の賛否情報を抽出中..."):
                success, count, error = presenter.extract_judges_from_proposal(
                    selected_proposal.id  # type: ignore[arg-type]
                )

                if success:
                    st.success(f"✅ {count}件の賛否情報を抽出しました")
                    st.info("抽出した情報は「賛否情報管理」ページで確認・編集できます")
                    st.rerun()
                else:
                    st.error(f"❌ 抽出に失敗しました: {error}")
