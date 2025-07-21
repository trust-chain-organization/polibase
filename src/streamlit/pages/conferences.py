"""会議体管理ページ"""

from typing import Any, cast

import streamlit as st
from src.database.conference_repository import ConferenceRepository
from src.seed_generator import SeedGenerator


def manage_conferences():
    """会議体管理（登録・編集・削除）"""
    st.header("会議体管理")
    st.markdown("会議体（議会・委員会など）を管理します")

    conf_repo = ConferenceRepository()

    # 会議体管理用のメッセージを表示
    if (
        "conf_success_message" in st.session_state
        and st.session_state.conf_success_message
    ):
        col1, col2 = st.columns([10, 1])
        with col1:
            st.success(st.session_state.conf_success_message)
        with col2:
            if st.button("✖", key="clear_conf_success", help="メッセージを閉じる"):
                st.session_state.conf_success_message = None
                st.session_state.conf_message_details = None
                st.rerun()

        # 詳細情報があれば表示
        if (
            "conf_message_details" in st.session_state
            and st.session_state.conf_message_details
        ):
            with st.expander("詳細を表示", expanded=True):
                st.markdown(st.session_state.conf_message_details)

    if "conf_error_message" in st.session_state and st.session_state.conf_error_message:
        col1, col2 = st.columns([10, 1])
        with col1:
            st.error(st.session_state.conf_error_message)
        with col2:
            if st.button("✖", key="clear_conf_error", help="メッセージを閉じる"):
                st.session_state.conf_error_message = None
                st.rerun()

    # サブタブを作成
    conf_tab1, conf_tab2, conf_tab3 = st.tabs(["会議体一覧", "新規登録", "編集・削除"])

    with conf_tab1:
        # 会議体一覧
        st.subheader("登録済み会議体一覧")

        conferences = conf_repo.get_all_conferences()
        if conferences:
            # SEEDファイル生成セクション（一番上に配置）
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### SEEDファイル生成")
                    st.markdown(
                        "現在登録されている会議体データからSEEDファイルを生成します"
                    )
                with col2:
                    if st.button(
                        "SEEDファイル生成",
                        key="generate_conferences_seed",
                        type="primary",
                    ):
                        with st.spinner("SEEDファイルを生成中..."):
                            try:
                                generator = SeedGenerator()
                                seed_content = generator.generate_conferences_seed()

                                # ファイルに保存
                                output_path = "database/seed_conferences_generated.sql"
                                with open(output_path, "w") as f:
                                    f.write(seed_content)

                                st.success(
                                    f"✅ SEEDファイルを生成しました: {output_path}"
                                )

                                # 生成内容をプレビュー表示
                                with st.expander(
                                    "生成されたSEEDファイル", expanded=False
                                ):
                                    st.code(seed_content, language="sql")
                            except Exception as e:
                                st.error(
                                    f"❌ SEEDファイル生成中にエラーが発生しました: {str(e)}"
                                )

            st.markdown("---")
            # フィルター設定
            col_filter1, col_filter2, col_filter3 = st.columns([2, 2, 6])
            with col_filter1:
                url_filter = st.selectbox(
                    "議員紹介URL",
                    ["すべて", "設定済み", "未設定"],
                    key="conf_url_filter",
                )

            # フィルタリング適用
            filtered_conferences = conferences
            if url_filter == "設定済み":
                filtered_conferences = [
                    conf for conf in conferences if conf.get("members_introduction_url")
                ]
            elif url_filter == "未設定":
                filtered_conferences = [
                    conf
                    for conf in conferences
                    if not conf.get("members_introduction_url")
                ]

            # 統計情報を表示
            total_count = len(conferences)
            with_url_count = len(
                [c for c in conferences if c.get("members_introduction_url")]
            )
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

            # フィルター後の会議体が存在するかチェック
            if filtered_conferences:
                # 開催主体でグループ化
                grouped_conferences: dict[str, list[dict[str, Any]]] = {}
                for conf in filtered_conferences:
                    gb_name = conf["governing_body_name"] or "未設定"
                    if gb_name not in grouped_conferences:
                        grouped_conferences[gb_name] = []
                    grouped_conferences[gb_name].append(conf)

                # 開催主体ごとに表示（未設定を最後に）
                sorted_gb_names = sorted(
                    grouped_conferences.keys(),
                    key=lambda x: (x == "未設定", x),  # 未設定を最後に
                )
                for gb_name in sorted_gb_names:
                    gb_conferences = grouped_conferences[gb_name]
                    with st.expander(f"📂 {gb_name}", expanded=True):
                        for idx, conf in enumerate(gb_conferences):
                            # 各会議体を個別に表示
                            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                            with col1:
                                st.markdown(f"**{conf['name']}**")
                                if conf.get("type"):
                                    st.caption(f"種別: {conf['type']}")

                            with col2:
                                if conf.get("members_introduction_url"):
                                    st.success("✅ URL設定済み")
                                else:
                                    st.error("❌ URL未設定")

                            with col3:
                                # 編集状態の管理
                                edit_key = f"edit_conf_{conf['id']}"
                                if edit_key not in st.session_state:
                                    st.session_state[edit_key] = False

                                # 現在のURLを表示（編集モードでない場合）
                                if not st.session_state[edit_key] and conf.get(
                                    "members_introduction_url"
                                ):
                                    url = conf["members_introduction_url"]
                                    display_url = (
                                        url[:30] + "..." if len(url) > 30 else url
                                    )
                                    st.caption(f"🔗 {display_url}")

                            with col4:
                                if st.button("✏️ 編集", key=f"edit_btn_{conf['id']}"):
                                    st.session_state[edit_key] = not st.session_state[
                                        edit_key
                                    ]
                                    st.rerun()

                            # 編集モード
                            if st.session_state[edit_key]:
                                with st.container():
                                    st.markdown("---")

                                    # 開催主体の選択
                                    governing_bodies = conf_repo.get_governing_bodies()
                                    gb_options = ["なし"] + [
                                        f"{gb['name']} ({gb['type']})"
                                        for gb in governing_bodies
                                    ]

                                    # 現在の開催主体を選択状態にする
                                    current_gb_index = 0
                                    if conf.get("governing_body_id"):
                                        for i, gb in enumerate(governing_bodies):
                                            if gb["id"] == conf["governing_body_id"]:
                                                current_gb_index = (
                                                    i + 1
                                                )  # "なし"の分を加算
                                                break

                                    selected_gb = st.selectbox(
                                        "開催主体",
                                        gb_options,
                                        index=current_gb_index,
                                        key=f"gb_select_{conf['id']}",
                                    )

                                    # URLの入力
                                    new_url = st.text_input(
                                        "議員紹介URL",
                                        value=conf.get("members_introduction_url", ""),
                                        key=f"url_input_{conf['id']}",
                                        placeholder="https://example.com/members",
                                    )

                                    col_save, col_cancel = st.columns([1, 1])

                                with col_save:
                                    if st.button(
                                        "💾 保存", key=f"save_btn_{conf['id']}"
                                    ):
                                        # 選択された開催主体のIDを取得
                                        selected_gb_id = None
                                        if selected_gb != "なし":
                                            for gb in governing_bodies:
                                                if (
                                                    f"{gb['name']} ({gb['type']})"
                                                    == selected_gb
                                                ):
                                                    selected_gb_id = gb["id"]
                                                    break

                                        # URLと開催主体を更新
                                        conf_repo.update_conference(
                                            conference_id=conf["id"],
                                            governing_body_id=selected_gb_id,
                                            members_introduction_url=(
                                                new_url if new_url else None
                                            ),
                                        )
                                        st.session_state[edit_key] = False
                                        st.session_state.conf_success_message = (
                                            f"✅ {conf['name']}を更新しました"
                                        )
                                        st.rerun()

                                with col_cancel:
                                    if st.button(
                                        "❌ キャンセル",
                                        key=f"cancel_btn_{conf['id']}",
                                    ):
                                        st.session_state[edit_key] = False
                                        st.rerun()

                            # 区切り線（最後の項目以外）
                            if idx < len(gb_conferences) - 1:
                                st.markdown("---")
            else:
                # フィルター結果が空の場合
                if url_filter == "設定済み":
                    st.info("議員紹介URLが設定済みの会議体はありません")
                elif url_filter == "未設定":
                    st.info("議員紹介URLが未設定の会議体はありません")
        else:
            st.info("会議体が登録されていません")

    with conf_tab2:
        # 新規登録
        st.subheader("新規会議体登録")

        with st.form("new_conference_form"):
            # 開催主体選択
            governing_bodies = conf_repo.get_governing_bodies()
            gb_options = ["なし"] + [
                f"{gb['name']} ({gb['type']})" for gb in governing_bodies
            ]
            gb_selected = st.selectbox("開催主体（任意）", gb_options)

            # 選択された開催主体のIDを取得
            selected_gb_id = None
            if gb_selected != "なし":
                for gb in governing_bodies:
                    if f"{gb['name']} ({gb['type']})" == gb_selected:
                        selected_gb_id = gb["id"]
                        break

            # 会議体情報入力
            conf_name = st.text_input("会議体名", placeholder="例: 本会議、予算委員会")
            conf_type = st.text_input(
                "会議体種別（任意）",
                placeholder="例: 本会議、常任委員会、特別委員会",
            )
            members_url = st.text_input(
                "議員紹介URL（任意）",
                placeholder="https://example.com/members",
                help="会議体の議員一覧が掲載されているページのURL",
            )

            submitted = st.form_submit_button("登録")

            if submitted:
                if not conf_name:
                    st.session_state.conf_error_message = "会議体名を入力してください"
                    st.rerun()
                else:
                    conf_id = conf_repo.create_conference(
                        name=conf_name,
                        governing_body_id=selected_gb_id
                        if selected_gb_id is not None
                        else 0,
                        type=conf_type if conf_type else None,
                    )
                    if conf_id:
                        # 議員紹介URLが入力されていれば更新
                        if members_url:
                            conf_repo.update_conference_members_url(
                                conference_id=conf_id,
                                members_introduction_url=members_url,
                            )

                        # 成功メッセージと詳細をセッション状態に保存
                        st.session_state.conf_success_message = (
                            "✅ 会議体を登録しました"
                        )
                        st.session_state.conf_message_details = f"""
                        **会議体ID:** {conf_id}

                        **開催主体:** {gb_selected}

                        **会議体名:** {conf_name}

                        **会議体種別:** {conf_type if conf_type else "未設定"}

                        **議員紹介URL:** {"✅ 設定済み" if members_url else "❌ 未設定"}
                        {f"\\n- {members_url}" if members_url else ""}
                        """

                        st.rerun()
                    else:
                        st.session_state.conf_error_message = (
                            "会議体の登録に失敗しました"
                            "（同じ名前の会議体が既に存在する可能性があります）"
                        )
                        st.rerun()

    with conf_tab3:
        # 編集・削除
        st.subheader("会議体の編集・削除")

        conferences = conf_repo.get_all_conferences()
        if not conferences:
            st.info("編集する会議体がありません")
        else:
            # 会議体選択
            conf_options = []
            conf_map = {}
            for conf in conferences:
                display_name = f"{conf['governing_body_name']} - {conf['name']}"
                if conf.get("type"):
                    display_name += f" ({conf['type']})"
                # URL設定状態を追加
                url_status = "✅" if conf.get("members_introduction_url") else "❌"
                display_name = f"{url_status} {display_name}"
                conf_options.append(display_name)
                conf_map[display_name] = conf

            selected_conf_display = st.selectbox("編集する会議体を選択", conf_options)

            selected_conf = cast(dict[str, Any], conf_map[selected_conf_display])

            # 現在の議員紹介URLの状態を表示
            if selected_conf.get("members_introduction_url"):
                st.info(f"🔗 現在のURL: {selected_conf['members_introduction_url']}")
            else:
                st.warning("❌ 議員紹介URLが未設定です")

            # 編集フォーム
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 編集")
                with st.form("edit_conference_form"):
                    new_name = st.text_input(
                        "会議体名", value=cast(str, selected_conf["name"])
                    )
                    new_type = st.text_input(
                        "会議体種別",
                        value=cast(str, selected_conf.get("type", "")),
                    )
                    new_members_url = st.text_input(
                        "議員紹介URL",
                        value=cast(
                            str, selected_conf.get("members_introduction_url", "") or ""
                        ),
                        placeholder="https://example.com/members",
                        help="会議体の議員一覧が掲載されているページのURL",
                    )

                    submitted = st.form_submit_button("更新")

                    if submitted:
                        if not new_name:
                            st.error("会議体名を入力してください")
                        else:
                            # 基本情報を更新
                            if conf_repo.update_conference(
                                conference_id=selected_conf["id"],
                                name=new_name,
                                type=new_type if new_type else None,
                            ):
                                # 議員紹介URLを更新
                                conf_repo.update_conference_members_url(
                                    conference_id=selected_conf["id"],
                                    members_introduction_url=new_members_url
                                    if new_members_url
                                    else None,
                                )
                                st.success("会議体を更新しました")
                                st.rerun()
                            else:
                                st.error("会議体の更新に失敗しました")

            with col2:
                st.markdown("#### 削除")
                st.warning(
                    "⚠️ 会議体を削除すると、関連するデータも削除される可能性があります"
                )

                if st.button("🗑️ この会議体を削除", type="secondary"):
                    if conf_repo.delete_conference(cast(int, selected_conf["id"])):
                        st.success("会議体を削除しました")
                        st.rerun()
                    else:
                        st.error(
                            "会議体を削除できませんでした（関連する会議が存在する可能性があります）"
                        )

    conf_repo.close()
