"""開催主体管理ページ"""

import pandas as pd

import streamlit as st
from src.database.governing_body_repository import GoverningBodyRepository
from src.seed_generator import SeedGenerator


def manage_governing_bodies():
    """開催主体管理（CRUD）"""
    st.header("開催主体管理")
    st.markdown("開催主体（国、都道府県、市町村）の情報を管理します")

    # サブタブの作成
    gb_tab1, gb_tab2, gb_tab3 = st.tabs(["開催主体一覧", "新規登録", "編集・削除"])

    gb_repo = GoverningBodyRepository()

    with gb_tab1:
        # 開催主体一覧
        st.subheader("開催主体一覧")

        # フィルタリングオプション
        col1, col2 = st.columns(2)

        with col1:
            # 種別でフィルタリング
            type_options = ["すべて"] + gb_repo.get_type_options()
            selected_type = st.selectbox(
                "種別でフィルタ", type_options, key="gb_type_filter"
            )

        with col2:
            # 会議体の有無でフィルタリング
            conference_filter = st.selectbox(
                "会議体でフィルタ",
                ["すべて", "会議体あり", "会議体なし"],
                key="gb_conference_filter",
            )

        # 開催主体取得
        if selected_type == "すべて":
            governing_bodies = gb_repo.get_all_governing_bodies()
        else:
            governing_bodies = gb_repo.get_governing_bodies_by_type(selected_type)

        # 会議体フィルタの適用
        if conference_filter == "会議体あり":
            governing_bodies = [
                gb for gb in governing_bodies if gb.get("conference_count", 0) > 0
            ]
        elif conference_filter == "会議体なし":
            governing_bodies = [
                gb for gb in governing_bodies if gb.get("conference_count", 0) == 0
            ]

        if governing_bodies:
            # SEEDファイル生成セクション（一番上に配置）
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### SEEDファイル生成")
                    st.markdown(
                        "現在登録されている開催主体データからSEEDファイルを生成します"
                    )
                with col2:
                    if st.button(
                        "SEEDファイル生成",
                        key="generate_governing_bodies_seed",
                        type="primary",
                    ):
                        with st.spinner("SEEDファイルを生成中..."):
                            try:
                                generator = SeedGenerator()
                                seed_content = (
                                    generator.generate_governing_bodies_seed()
                                )

                                # ファイルに保存
                                output_path = (
                                    "database/seed_governing_bodies_generated.sql"
                                )
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
                                    "❌ SEEDファイル生成中にエラーが発生しました: "
                                    f"{str(e)}"
                                )

            st.markdown("---")
            # データフレームで表示
            df_data = []
            for gb in governing_bodies:
                df_data.append(  # type: ignore[union-attr]
                    {
                        "ID": gb["id"],
                        "名称": gb["name"],
                        "種別": gb["type"],
                        "会議体数": gb.get("conference_count", 0),
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)  # type: ignore[call-arg]

            # 統計情報
            st.markdown("### 統計情報")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("総数", f"{len(governing_bodies)}件")
            with col2:
                country_count = len(
                    [gb for gb in governing_bodies if gb["type"] == "国"]
                )
                st.metric("国", f"{country_count}件")
            with col3:
                pref_count = len(
                    [gb for gb in governing_bodies if gb["type"] == "都道府県"]
                )
                st.metric("都道府県", f"{pref_count}件")
            with col4:
                city_count = len(
                    [gb for gb in governing_bodies if gb["type"] == "市町村"]
                )
                st.metric("市町村", f"{city_count}件")

            # 会議体の有無の統計
            col1, col2 = st.columns(2)
            with col1:
                with_conf_count = len(
                    [gb for gb in governing_bodies if gb.get("conference_count", 0) > 0]
                )
                st.metric("会議体あり", f"{with_conf_count}件")
            with col2:
                without_conf_count = len(
                    [
                        gb
                        for gb in governing_bodies
                        if gb.get("conference_count", 0) == 0
                    ]
                )
                st.metric("会議体なし", f"{without_conf_count}件")
        else:
            st.info("開催主体が登録されていません")

    with gb_tab2:
        # 新規登録
        st.subheader("新規開催主体登録")

        with st.form("new_governing_body_form"):
            gb_name = st.text_input("開催主体名", key="new_gb_name")
            gb_type = st.selectbox(
                "種別", gb_repo.get_type_options(), key="new_gb_type"
            )

            submitted = st.form_submit_button("登録")

            if submitted:
                if not gb_name:
                    st.error("開催主体名を入力してください")
                else:
                    # 登録処理
                    new_id = gb_repo.create_governing_body(gb_name, gb_type)
                    if new_id:
                        st.success(
                            f"開催主体「{gb_name}」を登録しました（ID: {new_id}）"
                        )
                        st.rerun()
                    else:
                        st.error(
                            "登録に失敗しました。同じ名前と種別の開催主体が既に存在する可能性があります。"
                        )

    with gb_tab3:
        # 編集・削除
        st.subheader("開催主体の編集・削除")

        # 開催主体選択
        governing_bodies = gb_repo.get_all_governing_bodies()
        if governing_bodies:
            gb_options = [
                f"{gb['name']} ({gb['type']}) - ID: {gb['id']}"
                for gb in governing_bodies
            ]
            selected_gb_option = st.selectbox(
                "編集する開催主体を選択", gb_options, key="edit_gb_select"
            )

            # 選択された開催主体のIDを取得
            selected_gb_id = int(selected_gb_option.split("ID: ")[1])
            selected_gb = next(
                gb for gb in governing_bodies if gb["id"] == selected_gb_id
            )

            # 編集フォーム
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### 編集")
                with st.form("edit_governing_body_form"):
                    edit_gb_name = st.text_input(
                        "開催主体名", value=selected_gb["name"], key="edit_gb_name"
                    )
                    edit_gb_type = st.selectbox(
                        "種別",
                        gb_repo.get_type_options(),
                        index=gb_repo.get_type_options().index(selected_gb["type"]),
                        key="edit_gb_type",
                    )

                    update_submitted = st.form_submit_button("更新")

                    if update_submitted:
                        if not edit_gb_name:
                            st.error("開催主体名を入力してください")
                        else:
                            # 更新処理
                            success = gb_repo.update_governing_body(
                                selected_gb_id, edit_gb_name, edit_gb_type
                            )
                            if success:
                                st.success(f"開催主体「{edit_gb_name}」を更新しました")
                                st.rerun()
                            else:
                                st.error(
                                    "更新に失敗しました。同じ名前と種別の開催主体が既に存在する可能性があります。"
                                )

            with col2:
                st.markdown("### 削除")

                # 会議体数を表示
                conference_count = selected_gb.get("conference_count", 0)
                if conference_count > 0:
                    st.warning(
                        f"この開催主体には{conference_count}件の会議体が関連付けられています。削除するには、先に関連する会議体を削除する必要があります。"
                    )
                else:
                    st.info("この開催主体に関連する会議体はありません。")

                    if st.button(
                        "削除",
                        key="delete_gb_button",
                        type="secondary",
                        disabled=conference_count > 0,
                    ):
                        # 削除確認
                        if st.checkbox(
                            f"「{selected_gb['name']}」を本当に削除しますか？",
                            key="confirm_delete_gb",
                        ):
                            if st.button(
                                "削除を実行", key="execute_delete_gb", type="primary"
                            ):
                                success = gb_repo.delete_governing_body(selected_gb_id)
                                if success:
                                    st.success(
                                        f"開催主体「{selected_gb['name']}」を削除しました"
                                    )
                                    st.rerun()
                                else:
                                    st.error("削除に失敗しました")
        else:
            st.info("編集する開催主体がありません")

    # リポジトリのクローズ
    gb_repo.close()
