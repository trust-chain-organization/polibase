"""Political party management component"""

from typing import Any

import pandas as pd
from sqlalchemy import text

import streamlit as st
from src.config.database import get_db_engine
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
                                # 最後に改行がない場合は追加
                                if not seed_content.endswith("\n"):
                                    f.write("\n")

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
                # 各政党を個別に表示
                col1, col2, col3, col4 = st.columns([3, 2, 3, 1])

                with col1:
                    st.markdown(f"**{party.name}**")

                with col2:
                    if party.members_list_url:
                        st.success("✅ URL設定済み")
                    else:
                        st.error("❌ URL未設定")

                with col3:
                    # 編集状態の管理
                    edit_key = f"edit_party_{party.id}"
                    if edit_key not in st.session_state:
                        st.session_state[edit_key] = False

                    # 現在のURLを表示（編集モードでない場合）
                    if not st.session_state[edit_key] and party.members_list_url:
                        url = party.members_list_url
                        display_url = url[:30] + "..." if len(url) > 30 else url
                        st.caption(f"🔗 {display_url}")

                with col4:
                    if st.button("✏️ 編集", key=f"edit_party_btn_{party.id}"):
                        st.session_state[edit_key] = not st.session_state[edit_key]
                        st.rerun()

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
            df_data: list[dict[str, Any]] = []
            for party in parties:
                df_data.append(
                    {
                        "政党名": party.name,
                        "議員一覧URL": party.members_list_url or "未設定",
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)  # type: ignore[no-untyped-call]

    finally:
        conn.close()
