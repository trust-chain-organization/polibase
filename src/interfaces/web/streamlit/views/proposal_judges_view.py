"""View for proposal judges (voting information) management."""

import streamlit as st
from src.interfaces.web.streamlit.presenters.proposal_presenter import (
    ProposalPresenter,
)


def render_proposal_judges_page():
    """Render the proposal judges management page."""
    st.header("議案賛否情報管理")
    st.markdown("議案に対する議員の賛否情報を管理します")

    presenter = ProposalPresenter()

    # Create tabs
    tabs = st.tabs(["賛否情報一覧", "議員別投票履歴", "議会別集計", "手動編集"])

    with tabs[0]:
        render_judges_list_tab(presenter)

    with tabs[1]:
        render_politician_voting_history_tab(presenter)

    with tabs[2]:
        render_conference_summary_tab(presenter)

    with tabs[3]:
        render_manual_edit_tab(presenter)


def render_judges_list_tab(presenter: ProposalPresenter):
    """Render the judges list tab."""
    st.subheader("賛否情報一覧")

    # Load all proposals
    proposals = presenter.load_all_proposals()

    if not proposals:
        st.info("議案が登録されていません。先に議案を登録してください。")
        return

    # Filter by proposal
    col1, col2 = st.columns(2)

    with col1:
        proposal_options = ["すべて"] + [
            f"{p.proposal_number or f'ID:{p.id}'} - {p.content[:30]}..."
            for p in proposals
        ]
        selected_proposal_str = st.selectbox("議案でフィルタ", proposal_options)

    with col2:
        status_options = ["すべて", "matched", "needs_review", "no_match", "pending"]
        status_labels = {
            "すべて": "すべて",
            "matched": "✅ マッチ済",
            "needs_review": "⚠️ 要確認",
            "no_match": "❌ 未マッチ",
            "pending": "⏳ 処理待ち",
        }
        selected_status = st.selectbox(
            "マッチング状態でフィルタ",
            status_options,
            format_func=lambda x: status_labels[x],
        )

    # Get judges based on filter
    if selected_proposal_str != "すべて":
        # Find selected proposal
        selected_idx = proposal_options.index(selected_proposal_str) - 1
        selected_proposal = proposals[selected_idx]
        judges = presenter.get_extracted_judges_for_proposal(selected_proposal.id)  # type: ignore[arg-type]
    else:
        # Get all judges
        judges = []
        for proposal in proposals:
            proposal_judges = presenter.get_extracted_judges_for_proposal(proposal.id)  # type: ignore[arg-type]
            judges.extend(proposal_judges)

    # Filter by status
    if selected_status != "すべて":
        judges = [j for j in judges if j.matching_status == selected_status]

    if judges:
        st.markdown(f"**{len(judges)}件の賛否情報**")

        # Group by proposal for better display
        proposals_map = {p.id: p for p in proposals}

        # Display judges
        for judge in judges[:50]:  # Show first 50
            proposal = proposals_map.get(judge.proposal_id)
            if not proposal:
                continue

            name = (
                judge.extracted_politician_name
                or judge.extracted_parliamentary_group_name
                or "不明"
            )
            with st.expander(
                f"{proposal.proposal_number or f'ID:{proposal.id}'} - {name}",
                expanded=False,
            ):
                col1, col2, col3 = st.columns([2, 1, 1])

                with col1:
                    st.markdown("**抽出情報**")
                    st.markdown(f"議員名: {judge.extracted_politician_name or '-'}")
                    st.markdown(f"政党: {judge.extracted_party_name or '-'}")
                    st.markdown(
                        f"議員団: {judge.extracted_parliamentary_group_name or '-'}"
                    )

                with col2:
                    st.markdown("**賛否**")
                    judgment_emoji = {
                        "賛成": "👍",
                        "反対": "👎",
                        "棄権": "🤷",
                        "欠席": "🚫",
                    }
                    judgment = judge.extracted_judgment or "-"
                    emoji = judgment_emoji.get(judgment, "")
                    st.markdown(f"{emoji} **{judgment}**")

                with col3:
                    st.markdown("**マッチング状態**")
                    status_info = {
                        "matched": ("✅", "マッチ済", "success"),
                        "needs_review": ("⚠️", "要確認", "warning"),
                        "no_match": ("❌", "未マッチ", "error"),
                        "pending": ("⏳", "処理待ち", "info"),
                    }
                    emoji, label, color = status_info.get(
                        judge.matching_status, ("❓", "不明", "secondary")
                    )
                    st.markdown(f"{emoji} {label}")

                    if judge.matching_confidence:
                        st.progress(
                            judge.matching_confidence,
                            text=f"信頼度: {judge.matching_confidence:.0%}",
                        )

                if judge.matched_politician_id:
                    st.markdown(f"**マッチした議員ID:** {judge.matched_politician_id}")

                if judge.source_url:
                    st.markdown(f"**ソース:** [{judge.source_url}]({judge.source_url})")

        # Statistics
        st.divider()
        st.markdown("### 統計情報")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            matched_count = len([j for j in judges if j.matching_status == "matched"])
            st.metric("マッチ済", f"{matched_count}件")

        with col2:
            needs_review = len(
                [j for j in judges if j.matching_status == "needs_review"]
            )
            st.metric("要確認", f"{needs_review}件")

        with col3:
            no_match = len([j for j in judges if j.matching_status == "no_match"])
            st.metric("未マッチ", f"{no_match}件")

        with col4:
            pending = len([j for j in judges if j.matching_status == "pending"])
            st.metric("処理待ち", f"{pending}件")

    else:
        st.info("賛否情報がありません")


def render_politician_voting_history_tab(presenter: ProposalPresenter):
    """Render the politician voting history tab."""
    st.subheader("議員別投票履歴")

    # Get all politicians
    politicians = presenter.politician_repo.get_all()

    if not politicians:
        st.info("議員が登録されていません")
        return

    # Select politician
    politician_options = [f"{p.name} (ID:{p.id})" for p in politicians]
    selected_politician_str = st.selectbox("議員を選択", politician_options)

    # Get selected politician
    selected_id = int(selected_politician_str.split("ID:")[1].replace(")", ""))
    selected_politician = next(p for p in politicians if p.id == selected_id)

    # Get all judges for this politician
    all_judges = []
    proposals = presenter.load_all_proposals()
    for proposal in proposals:
        judges = presenter.get_extracted_judges_for_proposal(proposal.id)  # type: ignore[arg-type]
        politician_judges = [
            j for j in judges if j.matched_politician_id == selected_politician.id
        ]
        all_judges.extend(politician_judges)

    if all_judges:
        st.markdown(f"**{selected_politician.name}の投票履歴 ({len(all_judges)}件)**")

        # Voting summary
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            approve = len([j for j in all_judges if j.extracted_judgment == "賛成"])
            st.metric("賛成", f"{approve}件")
        with col2:
            reject = len([j for j in all_judges if j.extracted_judgment == "反対"])
            st.metric("反対", f"{reject}件")
        with col3:
            abstain = len([j for j in all_judges if j.extracted_judgment == "棄権"])
            st.metric("棄権", f"{abstain}件")
        with col4:
            absent = len([j for j in all_judges if j.extracted_judgment == "欠席"])
            st.metric("欠席", f"{absent}件")

        st.divider()

        # Show voting history
        proposals_map = {p.id: p for p in proposals}
        for judge in all_judges:
            proposal = proposals_map.get(judge.proposal_id)
            if proposal:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(
                        f"**{proposal.proposal_number or f'ID:{proposal.id}'}**"
                    )
                    st.caption(f"{proposal.content[:50]}...")
                with col2:
                    judgment_emoji = {
                        "賛成": "👍",
                        "反対": "👎",
                        "棄権": "🤷",
                        "欠席": "🚫",
                    }
                    judgment = judge.extracted_judgment or "-"
                    emoji = judgment_emoji.get(judgment, "")
                    st.markdown(f"{emoji} {judgment}")
                with col3:
                    if proposal.submission_date:
                        st.caption(proposal.submission_date)
    else:
        st.info(f"{selected_politician.name}の投票履歴はありません")


def render_conference_summary_tab(presenter: ProposalPresenter):
    """Render the conference summary tab."""
    st.subheader("議会別集計")

    # Get all meetings
    meetings = presenter.get_all_meetings()

    if not meetings:
        st.info("会議が登録されていません")
        return

    # Select meeting
    meeting_options = [f"{m.meeting_name} ({m.meeting_date})" for m in meetings]
    selected_meeting_str = st.selectbox("会議を選択", meeting_options)

    # Get selected meeting
    selected_idx = meeting_options.index(selected_meeting_str)
    selected_meeting = meetings[selected_idx]

    # Get proposals for this meeting
    proposals = presenter.load_proposals_by_meeting(selected_meeting.id)

    if not proposals:
        st.info(f"{selected_meeting.meeting_name}に議案がありません")
        return

    st.markdown(f"**{selected_meeting.meeting_name}の議案 ({len(proposals)}件)**")

    # Show each proposal with voting summary
    for proposal in proposals:
        judges = presenter.get_extracted_judges_for_proposal(proposal.id)  # type: ignore[arg-type]

        with st.expander(
            f"{proposal.proposal_number or f'ID:{proposal.id}'} - "
            f"{proposal.content[:50]}...",
            expanded=False,
        ):
            if judges:
                # Voting summary
                col1, col2, col3, col4, col5 = st.columns(5)
                with col1:
                    st.markdown(f"**状態:** {proposal.status or '-'}")
                with col2:
                    approve = len([j for j in judges if j.extracted_judgment == "賛成"])
                    st.metric("賛成", approve)
                with col3:
                    reject = len([j for j in judges if j.extracted_judgment == "反対"])
                    st.metric("反対", reject)
                with col4:
                    abstain = len([j for j in judges if j.extracted_judgment == "棄権"])
                    st.metric("棄権", abstain)
                with col5:
                    absent = len([j for j in judges if j.extracted_judgment == "欠席"])
                    st.metric("欠席", absent)

                # Party breakdown
                st.markdown("**政党別投票**")
                party_votes = {}
                for judge in judges:
                    if judge.extracted_party_name:
                        if judge.extracted_party_name not in party_votes:
                            party_votes[judge.extracted_party_name] = {
                                "賛成": 0,
                                "反対": 0,
                                "棄権": 0,
                                "欠席": 0,
                            }
                        if judge.extracted_judgment:
                            party_votes[judge.extracted_party_name][
                                judge.extracted_judgment
                            ] += 1

                for party, votes in party_votes.items():
                    col1, col2, col3, col4, col5 = st.columns(5)
                    with col1:
                        st.markdown(f"**{party}**")
                    with col2:
                        st.caption(f"賛成: {votes['賛成']}")
                    with col3:
                        st.caption(f"反対: {votes['反対']}")
                    with col4:
                        st.caption(f"棄権: {votes['棄権']}")
                    with col5:
                        st.caption(f"欠席: {votes['欠席']}")
            else:
                st.info("賛否情報がありません")


def render_manual_edit_tab(presenter: ProposalPresenter):
    """Render the manual edit tab for judges."""
    st.subheader("賛否情報の手動編集")
    st.markdown(
        "マッチング状態が「要確認」または「未マッチ」の賛否情報を手動で編集します"
    )

    # Get judges that need review
    all_judges = []
    proposals = presenter.load_all_proposals()
    for proposal in proposals:
        judges = presenter.get_extracted_judges_for_proposal(proposal.id)  # type: ignore[arg-type]
        review_judges = [
            j
            for j in judges
            if j.matching_status in ["needs_review", "no_match", "pending"]
        ]
        all_judges.extend(review_judges)

    if not all_judges:
        st.success("すべての賛否情報が処理済みです")
        return

    st.info(f"{len(all_judges)}件の賛否情報が確認を必要としています")

    # Select judge to edit
    proposals_map = {p.id: p for p in proposals}
    judge_options = []
    for judge in all_judges:
        proposal = proposals_map.get(judge.proposal_id)
        if proposal:
            name = (
                judge.extracted_politician_name
                or judge.extracted_parliamentary_group_name
                or "不明"
            )
            judge_options.append(
                f"{proposal.proposal_number or f'ID:{proposal.id}'} - "
                f"{name} ({judge.matching_status})"
            )

    if not judge_options:
        st.info("編集する賛否情報がありません")
        return

    selected_judge_str = st.selectbox("編集する賛否情報を選択", judge_options)
    selected_idx = judge_options.index(selected_judge_str)
    selected_judge = all_judges[selected_idx]

    # Show current information
    st.markdown("### 現在の情報")
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**抽出された情報**")
        st.markdown(f"議員名: {selected_judge.extracted_politician_name or '-'}")
        st.markdown(f"政党: {selected_judge.extracted_party_name or '-'}")
        st.markdown(
            f"議員団: {selected_judge.extracted_parliamentary_group_name or '-'}"
        )
        st.markdown(f"賛否: {selected_judge.extracted_judgment or '-'}")

    with col2:
        st.markdown("**マッチング情報**")
        st.markdown(f"状態: {selected_judge.matching_status}")
        if selected_judge.matching_confidence:
            st.markdown(f"信頼度: {selected_judge.matching_confidence:.0%}")
        if selected_judge.matched_politician_id:
            st.markdown(f"議員ID: {selected_judge.matched_politician_id}")

    # Edit form
    st.markdown("### 編集")
    with st.form("edit_judge_form"):
        # Get all politicians for matching
        politicians = presenter.politician_repo.get_all()
        politician_options = ["未マッチ"] + [
            f"{p.name} (ID:{p.id})" for p in politicians
        ]

        # Find current selection
        current_idx = 0
        if selected_judge.matched_politician_id:
            for i, p in enumerate(politicians, 1):
                if p.id == selected_judge.matched_politician_id:
                    current_idx = i
                    break

        # Selected politician for future implementation
        st.selectbox(
            "議員を選択",
            politician_options,
            index=current_idx,
            help="この賛否情報をマッチさせる議員を選択してください",
        )

        # Confidence score
        confidence = st.slider(
            "信頼度",
            min_value=0.0,
            max_value=1.0,
            value=selected_judge.matching_confidence or 0.5,
            step=0.05,
            help="0.7以上で「マッチ済」、0.5-0.7で「要確認」、0.5未満で「未マッチ」になります",
        )

        # Status
        if confidence >= 0.7:
            # new_status = "matched"  # For future implementation
            status_label = "✅ マッチ済"
        elif confidence >= 0.5:
            # new_status = "needs_review"  # For future implementation
            status_label = "⚠️ 要確認"
        else:
            # new_status = "no_match"  # For future implementation
            status_label = "❌ 未マッチ"

        st.info(f"新しい状態: {status_label}")

        submitted = st.form_submit_button("更新", type="primary")

        if submitted:
            # TODO: Implement update logic for ExtractedProposalJudge
            # This would require adding an update method to the repository
            st.warning("手動編集機能は現在実装中です")
            # After implementation:
            # - Update the matched_politician_id
            # - Update the matching_confidence
            # - Update the matching_status
            # - Set matched_at to current time
