"""View for parliamentary group management."""

from datetime import date
from typing import Any, cast

import streamlit as st
from src.interfaces.web.streamlit.presenters.parliamentary_group_presenter import (
    ParliamentaryGroupPresenter,
)


def render_parliamentary_groups_page():
    """Render the parliamentary groups management page."""
    st.header("議員団管理")
    st.markdown("議員団（会派）の情報を管理します")

    presenter = ParliamentaryGroupPresenter()

    # Create tabs
    tabs = st.tabs(["議員団一覧", "新規登録", "編集・削除", "メンバー抽出"])

    with tabs[0]:
        render_parliamentary_groups_list_tab(presenter)

    with tabs[1]:
        render_new_parliamentary_group_tab(presenter)

    with tabs[2]:
        render_edit_delete_tab(presenter)

    with tabs[3]:
        render_member_extraction_tab(presenter)


def render_parliamentary_groups_list_tab(presenter: ParliamentaryGroupPresenter):
    """Render the parliamentary groups list tab."""
    st.subheader("議員団一覧")

    # Get conferences for filter
    conferences = presenter.get_all_conferences()

    # Conference filter
    def get_conf_display_name(c):
        gb_name = (
            c.governing_body.name
            if hasattr(c, "governing_body") and c.governing_body
            else ""
        )
        return f"{gb_name} - {c.name}"

    conf_options = ["すべて"] + [get_conf_display_name(c) for c in conferences]
    conf_map = {get_conf_display_name(c): c.id for c in conferences}

    selected_conf_filter = st.selectbox(
        "会議体でフィルタ", conf_options, key="conf_filter"
    )

    # Load parliamentary groups
    if selected_conf_filter == "すべて":
        groups = presenter.load_data()
    else:
        conf_id = conf_map[selected_conf_filter]
        groups = presenter.load_parliamentary_groups_with_filters(conf_id, False)

    if groups:
        # Seed file generation section
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown("### SEEDファイル生成")
                st.markdown(
                    "現在登録されている議員団データからSEEDファイルを生成します"
                )
            with col2:
                if st.button(
                    "SEEDファイル生成", key="generate_pg_seed", type="primary"
                ):
                    with st.spinner("SEEDファイルを生成中..."):
                        success, seed_content, file_path_or_error = (
                            presenter.generate_seed_file()
                        )
                        if success:
                            st.success(
                                f"✅ SEEDファイルを生成しました: {file_path_or_error}"
                            )
                            with st.expander("生成されたSEEDファイル", expanded=False):
                                st.code(seed_content, language="sql")
                        else:
                            st.error(
                                f"❌ SEEDファイル生成中にエラーが発生しました: "
                                f"{file_path_or_error}"
                            )

        st.markdown("---")

        # Display data in DataFrame
        df = presenter.to_dataframe(groups, conferences)
        if df is not None:
            st.dataframe(df, use_container_width=True, hide_index=True)

        # Display member counts
        st.markdown("### メンバー数")
        member_df = presenter.get_member_counts(groups)
        if member_df is not None:
            st.dataframe(member_df, use_container_width=True, hide_index=True)
    else:
        st.info("議員団が登録されていません")


def render_new_parliamentary_group_tab(presenter: ParliamentaryGroupPresenter):
    """Render the new parliamentary group registration tab."""
    st.subheader("議員団の新規登録")

    # Get conferences
    conferences = presenter.get_all_conferences()
    if not conferences:
        st.error("会議体が登録されていません。先に会議体を登録してください。")
        return

    def get_conf_display_name(c):
        gb_name = (
            c.governing_body.name
            if hasattr(c, "governing_body") and c.governing_body
            else ""
        )
        return f"{gb_name} - {c.name}"

    conf_options = [get_conf_display_name(c) for c in conferences]
    conf_map = {get_conf_display_name(c): c.id for c in conferences}

    with st.form("new_parliamentary_group_form", clear_on_submit=False):
        selected_conf = st.selectbox("所属会議体", conf_options)

        # Input fields
        group_name = st.text_input("議員団名", placeholder="例: 自民党市議団")
        group_url = st.text_input(
            "議員団URL（任意）",
            placeholder="https://example.com/parliamentary-group",
            help="議員団の公式ページやプロフィールページのURL",
        )
        group_description = st.text_area(
            "説明（任意）", placeholder="議員団の説明や特徴を入力"
        )
        is_active = st.checkbox("活動中", value=True)

        submitted = st.form_submit_button("登録")

    if submitted:
        conf_id = conf_map[selected_conf]
        if not group_name:
            st.error("議員団名を入力してください")
        else:
            success, group, error = presenter.create(
                group_name,
                conf_id,
                group_url if group_url else None,
                group_description if group_description else None,
                is_active,
            )
            if success and group:
                presenter.add_created_group(group, selected_conf)
                st.success(f"議員団「{group.name}」を登録しました（ID: {group.id}）")
            else:
                st.error(f"登録に失敗しました: {error}")

    # Display created groups
    created_groups = presenter.get_created_groups()
    if created_groups:
        st.divider()
        st.subheader("作成済み議員団")

        for i, group in enumerate(created_groups):
            with st.expander(f"✅ {group['name']} (ID: {group['id']})", expanded=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**議員団名**: {group['name']}")
                    st.write(f"**議員団ID**: {group['id']}")
                    st.write(f"**所属会議体**: {group['conference_name']}")
                    if group["url"]:
                        st.write(f"**URL**: {group['url']}")
                    if group["description"]:
                        st.write(f"**説明**: {group['description']}")
                    active_status = "活動中" if group["is_active"] else "非活動"
                    st.write(f"**活動状態**: {active_status}")
                    if group["created_at"]:
                        st.write(f"**作成日時**: {group['created_at']}")
                with col2:
                    if st.button("削除", key=f"remove_created_{i}"):
                        presenter.remove_created_group(i)
                        st.rerun()


def render_edit_delete_tab(presenter: ParliamentaryGroupPresenter):
    """Render the edit/delete tab."""
    st.subheader("議員団の編集・削除")

    # Load all parliamentary groups
    groups = presenter.load_data()
    if not groups:
        st.info("編集する議員団がありません")
        return

    # Get conferences for display
    conferences = presenter.get_all_conferences()

    # Select parliamentary group to edit
    group_options: list[str] = []
    group_map: dict[str, Any] = {}
    for group in groups:
        conf = next((c for c in conferences if c.id == group.conference_id), None)
        conf_name = conf.name if conf else "不明"
        display_name = f"{group.name} ({conf_name})"
        group_options.append(display_name)
        group_map[display_name] = group

    selected_group_display = st.selectbox("編集する議員団を選択", group_options)
    selected_group = group_map[selected_group_display]

    # Edit and delete forms
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 編集")
        with st.form("edit_parliamentary_group_form"):
            new_name = st.text_input("議員団名", value=selected_group.name)
            new_url = st.text_input("議員団URL", value=selected_group.url or "")
            new_description = st.text_area(
                "説明", value=selected_group.description or ""
            )
            new_is_active = st.checkbox("活動中", value=selected_group.is_active)

            submitted = st.form_submit_button("更新")

            if submitted:
                if not new_name:
                    st.error("議員団名を入力してください")
                else:
                    success, error = presenter.update(
                        selected_group.id,
                        new_name,
                        new_url if new_url else None,
                        new_description if new_description else None,
                        new_is_active,
                    )
                    if success:
                        st.success("議員団を更新しました")
                        st.rerun()
                    else:
                        st.error(f"更新に失敗しました: {error}")

    with col2:
        st.markdown("#### メンバー情報")
        # TODO: Display member information when membership repository is available
        st.write("メンバー数: 0名")  # Placeholder

        st.markdown("#### 削除")
        st.warning("⚠️ 議員団を削除すると、所属履歴も削除されます")

        # Can only delete inactive groups
        if selected_group.is_active:
            st.info("活動中の議員団は削除できません。先に非活動にしてください。")
        else:
            if st.button("🗑️ この議員団を削除", type="secondary"):
                success, error = presenter.delete(selected_group.id)
                if success:
                    st.success(f"議員団「{selected_group.name}」を削除しました")
                    st.rerun()
                else:
                    st.error(f"削除に失敗しました: {error}")


def render_member_extraction_tab(presenter: ParliamentaryGroupPresenter):
    """Render the member extraction tab."""
    st.subheader("議員団メンバーの抽出")
    st.markdown("議員団のURLから所属議員を自動的に抽出し、メンバーシップを作成します")

    # Get parliamentary groups with URLs
    groups = presenter.load_data()
    groups_with_url = [g for g in groups if g.url]

    if not groups_with_url:
        st.info(
            "URLが設定されている議員団がありません。先に議員団のURLを設定してください。"
        )
        return

    # Get conferences for display
    conferences = presenter.get_all_conferences()

    # Select parliamentary group
    group_options = []
    group_map = {}
    for group in groups_with_url:
        conf = next((c for c in conferences if c.id == group.conference_id), None)
        if conf:
            gb_name = (
                conf.governing_body.name
                if hasattr(conf, "governing_body") and conf.governing_body
                else ""
            )
            conf_name = f"{gb_name} - {conf.name}"
        else:
            conf_name = "不明"
        display_name = f"{group.name} ({conf_name})"
        group_options.append(display_name)
        group_map[display_name] = group

    selected_group_display = st.selectbox(
        "抽出対象の議員団を選択", group_options, key="extract_group_select"
    )
    selected_group = group_map[selected_group_display]

    # Display current information
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**議員団URL:** {selected_group.url}")
    with col2:
        st.info("**現在のメンバー数:** 0名")  # Placeholder

    # Extraction settings
    st.markdown("### 抽出設定")

    col1, col2 = st.columns(2)
    with col1:
        confidence_threshold = st.slider(
            "マッチング信頼度の閾値",
            min_value=0.5,
            max_value=1.0,
            value=0.7,
            step=0.05,
            help="この値以上の信頼度でマッチングされた政治家のみメンバーシップを作成します",
        )

    with col2:
        start_date = st.date_input(
            "所属開始日",
            value=date.today(),
            help="作成されるメンバーシップの所属開始日",
        )

    dry_run = st.checkbox(
        "ドライラン（実際にはメンバーシップを作成しない）",
        value=True,
        help="チェックすると、抽出結果の確認のみ行い、実際のメンバーシップは作成しません",
    )

    # Execute extraction
    if st.button("🔍 メンバー抽出を実行", type="primary"):
        with st.spinner("メンバー情報を抽出中..."):
            success, result, error = presenter.extract_members(
                selected_group.id,
                cast(str, selected_group.url),
                confidence_threshold,
                start_date,
                dry_run,
            )

            if success and result:
                if result.extracted_members:
                    st.success(
                        f"✅ {len(result.extracted_members)}名のメンバーを抽出しました"
                    )

                    # Display extracted members
                    st.markdown("### 抽出されたメンバー")
                    # This would display the actual extraction results
                    st.info("メンバー抽出機能は現在実装中です")
                else:
                    st.warning("メンバーが抽出されませんでした")
            else:
                st.error(f"抽出エラー: {error}")


def main():
    """Main function for testing."""
    render_parliamentary_groups_page()


if __name__ == "__main__":
    main()
