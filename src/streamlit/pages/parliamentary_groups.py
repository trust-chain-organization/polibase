"""議員団管理ページ"""

from datetime import date
from typing import Any, cast

import pandas as pd

import streamlit as st
from src.exceptions import DatabaseError, ProcessingError, ScrapingError
from src.infrastructure.persistence.conference_repository_impl import (
    ConferenceRepositoryImpl,
)
from src.infrastructure.persistence.parliamentary_group_repository_impl import (
    ParliamentaryGroupMembershipRepositoryImpl,
    ParliamentaryGroupRepositoryImpl,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.seed_generator import SeedGenerator


def manage_parliamentary_groups():
    """議員団管理（CRUD）"""
    st.header("議員団管理")
    st.markdown("議員団（会派）の情報を管理します")

    # サブタブの作成
    group_tab1, group_tab2, group_tab3, group_tab4 = st.tabs(
        ["議員団一覧", "新規登録", "編集・削除", "メンバー抽出"]
    )

    pg_repo = RepositoryAdapter(ParliamentaryGroupRepositoryImpl)
    conf_repo = RepositoryAdapter(ConferenceRepositoryImpl)

    with group_tab1:
        # 議員団一覧
        st.subheader("議員団一覧")

        # 会議体でフィルタリング
        conferences = conf_repo.get_all_conferences()
        conf_options = ["すべて"] + [
            f"{c['governing_body_name']} - {c['name']}" for c in conferences
        ]
        conf_map = {
            f"{c['governing_body_name']} - {c['name']}": c["id"] for c in conferences
        }

        selected_conf_filter = st.selectbox(
            "会議体でフィルタ", conf_options, key="conf_filter"
        )

        # 議員団取得
        if selected_conf_filter == "すべて":
            groups = pg_repo.search_parliamentary_groups()
        else:
            conf_id = conf_map[selected_conf_filter]
            groups = pg_repo.get_parliamentary_groups_by_conference(
                conf_id, active_only=False
            )

        if groups:
            # SEEDファイル生成セクション（一番上に配置）
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown("### SEEDファイル生成")
                    st.markdown(
                        "現在登録されている議員団データからSEEDファイルを生成します"
                    )
                with col2:
                    if st.button(
                        "SEEDファイル生成",
                        key="generate_parliamentary_groups_seed",
                        type="primary",
                    ):
                        with st.spinner("SEEDファイルを生成中..."):
                            try:
                                generator = SeedGenerator()
                                seed_content = (
                                    generator.generate_parliamentary_groups_seed()
                                )

                                # ファイルに保存
                                output_path = (
                                    "database/seed_parliamentary_groups_generated.sql"
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
            for group in groups:
                # 会議体名を取得
                conf = next(
                    (c for c in conferences if c["id"] == group["conference_id"]), None
                )
                conf_name = (
                    f"{conf['governing_body_name']} - {conf['name']}"
                    if conf
                    else "不明"
                )

                df_data.append(  # type: ignore[union-attr]
                    {
                        "ID": group["id"],
                        "議員団名": group["name"],
                        "会議体": conf_name,
                        "URL": group.get("url", "") or "未設定",
                        "説明": group.get("description", "") or "",
                        "状態": "活動中" if group.get("is_active", True) else "非活動",
                        "作成日": group["created_at"],
                    }
                )

            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, hide_index=True)  # type: ignore[call-arg]

            # メンバー数の表示
            st.markdown("### メンバー数")
            pgm_repo = RepositoryAdapter(ParliamentaryGroupMembershipRepositoryImpl)
            member_counts = []
            for group in groups:
                current_members = pgm_repo.get_current_members(group["id"])
                member_counts.append(  # type: ignore[union-attr]
                    {
                        "議員団名": group["name"],
                        "現在のメンバー数": len(current_members),
                    }
                )

            member_df = pd.DataFrame(member_counts)
            st.dataframe(member_df, use_container_width=True, hide_index=True)  # type: ignore[call-arg]
        else:
            st.info("議員団が登録されていません")

    with group_tab2:
        # 新規登録
        st.subheader("議員団の新規登録")

        # フォームの外で会議体を取得
        conferences = conf_repo.get_all_conferences()
        if not conferences:
            st.error("会議体が登録されていません。先に会議体を登録してください。")
            st.stop()

        conf_options = [
            f"{c['governing_body_name']} - {c['name']}" for c in conferences
        ]
        conf_map = {
            f"{c['governing_body_name']} - {c['name']}": c["id"] for c in conferences
        }

        with st.form("new_parliamentary_group_form", clear_on_submit=False):
            selected_conf = st.selectbox("所属会議体", conf_options)

            # 議員団情報入力
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
                try:
                    result = pg_repo.create_parliamentary_group(
                        name=group_name,
                        conference_id=conf_id,
                        url=group_url if group_url else None,
                        description=group_description if group_description else None,
                        is_active=is_active,
                    )
                    if result:
                        # 作成結果をセッション状態に保存
                        created_group: dict[str, Any] = {
                            "id": result["id"],
                            "name": result["name"],
                            "conference_id": result["conference_id"],
                            "conference_name": selected_conf,
                            "url": result.get("url", ""),
                            "description": result.get("description", ""),
                            "is_active": result.get("is_active", True),
                            "created_at": result.get("created_at", ""),
                        }
                        st.session_state.created_parliamentary_groups.append(
                            created_group
                        )
                    else:
                        st.error(
                            "議員団の登録に失敗しました（同じ名前の議員団が既に存在する可能性があります）"
                        )
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
                    import traceback

                    st.text(traceback.format_exc())

        # 作成済み議員団の表示
        if st.session_state.created_parliamentary_groups:
            st.divider()
            st.subheader("作成済み議員団")

            for i, group in enumerate(st.session_state.created_parliamentary_groups):
                with st.expander(
                    f"✅ {group['name']} (ID: {group['id']})", expanded=True
                ):
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
                            st.session_state.created_parliamentary_groups.pop(i)
                            st.rerun()

    with group_tab3:
        # 編集・削除
        st.subheader("議員団の編集・削除")

        groups = pg_repo.search_parliamentary_groups()
        if not groups:
            st.info("編集する議員団がありません")
        else:
            # 議員団選択
            conferences = conf_repo.get_all_conferences()
            group_options: list[str] = []
            group_map: dict[str, Any] = {}
            for group in groups:
                conf = next(
                    (c for c in conferences if c["id"] == group["conference_id"]), None
                )
                conf_name = conf["name"] if conf else "不明"
                display_name = f"{group['name']} ({conf_name})"
                group_options.append(display_name)
                group_map[display_name] = group

            selected_group_display = st.selectbox("編集する議員団を選択", group_options)
            selected_group: dict[str, Any] = group_map[selected_group_display]

            # 編集フォーム
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 編集")
                with st.form("edit_parliamentary_group_form"):
                    new_name = st.text_input(
                        "議員団名", value=cast(str, selected_group["name"])
                    )
                    new_url = st.text_input(
                        "議員団URL",
                        value=cast(str, selected_group.get("url", "") or ""),
                    )
                    new_description = st.text_area(
                        "説明",
                        value=cast(str, selected_group.get("description", "") or ""),
                    )
                    new_is_active = st.checkbox(
                        "活動中",
                        value=cast(bool, selected_group.get("is_active", True)),
                    )

                    submitted = st.form_submit_button("更新")

                    if submitted:
                        if not new_name:
                            st.error("議員団名を入力してください")
                        else:
                            if pg_repo.update_parliamentary_group(
                                group_id=cast(int, selected_group["id"]),
                                name=new_name,
                                url=new_url if new_url else None,
                                description=new_description
                                if new_description
                                else None,
                                is_active=new_is_active,
                            ):
                                st.success("議員団を更新しました")
                                st.rerun()
                            else:
                                st.error("議員団の更新に失敗しました")

            with col2:
                st.markdown("#### メンバー情報")
                pgm_repo = RepositoryAdapter(ParliamentaryGroupMembershipRepositoryImpl)
                current_members = pgm_repo.get_current_members(
                    cast(int, selected_group["id"])
                )

                if current_members:
                    st.write(f"現在のメンバー数: {len(current_members)}名")
                    member_names = [m["politician_name"] for m in current_members]
                    st.write("メンバー: " + ", ".join(member_names[:5]))
                    if len(member_names) > 5:
                        st.write(f"... 他 {len(member_names) - 5}名")
                else:
                    st.write("メンバーなし")

                st.markdown("#### 削除")
                st.warning("⚠️ 議員団を削除すると、所属履歴も削除されます")

                # 削除は活動中でない議員団のみ可能
                if selected_group.get("is_active", True):
                    st.info(
                        "活動中の議員団は削除できません。先に非活動にしてください。"
                    )
                elif current_members:
                    st.info("メンバーがいる議員団は削除できません。")
                else:
                    if st.button("🗑️ この議員団を削除", type="secondary"):
                        # Note: 削除機能は未実装のため、将来的に実装予定
                        st.error("削除機能は現在実装されていません")

    with group_tab4:
        # メンバー抽出
        st.subheader("議員団メンバーの抽出")
        st.markdown(
            "議員団のURLから所属議員を自動的に抽出し、メンバーシップを作成します"
        )

        # URLが設定されている議員団を取得
        groups_with_url = [
            g for g in pg_repo.search_parliamentary_groups() if g.get("url")
        ]

        if not groups_with_url:
            st.info(
                "URLが設定されている議員団がありません。先に議員団のURLを設定してください。"
            )
        else:
            # 議員団選択
            conferences = conf_repo.get_all_conferences()
            group_options = []
            group_map = {}
            for group in groups_with_url:
                conf = next(
                    (c for c in conferences if c["id"] == group["conference_id"]), None
                )
                conf_name = (
                    f"{conf['governing_body_name']} - {conf['name']}"
                    if conf
                    else "不明"
                )
                display_name = f"{group['name']} ({conf_name})"
                group_options.append(display_name)
                group_map[display_name] = group

            selected_group_display = st.selectbox(
                "抽出対象の議員団を選択", group_options, key="extract_group_select"
            )
            selected_group = group_map[selected_group_display]

            # 現在のメンバー数を表示
            pgm_repo = RepositoryAdapter(ParliamentaryGroupMembershipRepositoryImpl)
            current_members = pgm_repo.get_current_members(
                cast(int, selected_group["id"])
            )

            col1, col2 = st.columns(2)
            with col1:
                st.info(f"**議員団URL:** {selected_group['url']}")
            with col2:
                st.info(f"**現在のメンバー数:** {len(current_members)}名")

            # 抽出設定
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

            # 実行ボタン
            if st.button("🔍 メンバー抽出を実行", type="primary"):
                with st.spinner("メンバー情報を抽出中..."):
                    try:
                        from src.parliamentary_group_member_extractor import (
                            ParliamentaryGroupMemberExtractor,
                            ParliamentaryGroupMembershipService,
                        )

                        # 抽出器とサービスの初期化
                        extractor = ParliamentaryGroupMemberExtractor()
                        service = ParliamentaryGroupMembershipService()

                        # メンバー情報を抽出
                        extraction_result = extractor.extract_members_sync(
                            cast(int, selected_group["id"]),
                            cast(str, selected_group["url"]),
                        )

                        if extraction_result.error:
                            st.error(f"抽出エラー: {extraction_result.error}")
                        elif not extraction_result.extracted_members:
                            st.warning(
                                "メンバーが抽出されませんでした。URLまたはページ構造を確認してください。"
                            )
                        else:
                            st.success(
                                f"✅ {len(extraction_result.extracted_members)}名の"
                                "メンバーを抽出しました"
                            )

                            # 抽出されたメンバーを表示
                            st.markdown("### 抽出されたメンバー")
                            member_data: list[dict[str, Any]] = []
                            for member in extraction_result.extracted_members:
                                member_data.append(
                                    {
                                        "名前": member.name,
                                        "役職": member.role or "-",
                                        "政党": member.party_name or "-",
                                        "選挙区": member.district or "-",
                                        "その他": member.additional_info or "-",
                                    }
                                )

                            member_df = pd.DataFrame(member_data)
                            st.dataframe(  # type: ignore[call-arg]
                                member_df, use_container_width=True, hide_index=True
                            )

                            # 政治家とマッチング
                            with st.spinner("既存の政治家データとマッチング中..."):
                                import asyncio

                                matching_results = asyncio.run(
                                    service.match_politicians(
                                        extraction_result.extracted_members,
                                        conference_id=selected_group["conference_id"],
                                    )
                                )

                            # マッチング結果を表示
                            st.markdown("### マッチング結果")

                            matched_count = sum(
                                1
                                for r in matching_results
                                if r.politician_id is not None
                            )
                            st.info(
                                f"マッチング成功: {matched_count}/"
                                f"{len(matching_results)}名"
                            )

                            # マッチング詳細を表示
                            match_data: list[dict[str, Any]] = []
                            for result in matching_results:
                                match_data.append(
                                    {
                                        "抽出名": result.extracted_member.name,
                                        "役職": result.extracted_member.role or "-",
                                        "マッチした政治家": result.politician_name
                                        or "マッチなし",
                                        "信頼度": f"{result.confidence_score:.2f}"
                                        if result.politician_id
                                        else "-",
                                        "理由": result.matching_reason,
                                    }
                                )

                            match_df = pd.DataFrame(match_data)
                            st.dataframe(  # type: ignore[call-arg]
                                match_df, use_container_width=True, hide_index=True
                            )

                            # メンバーシップ作成
                            if not dry_run and matched_count > 0:
                                if st.button("📝 メンバーシップを作成", type="primary"):
                                    with st.spinner("メンバーシップを作成中..."):
                                        creation_result = service.create_memberships(
                                            parliamentary_group_id=selected_group["id"],
                                            matching_results=matching_results,
                                            start_date=start_date,
                                            confidence_threshold=confidence_threshold,
                                            dry_run=False,
                                        )

                                        st.success(
                                            f"✅ {creation_result.created_count}件の"
                                            "メンバーシップを作成しました"
                                        )

                                        if creation_result.errors:
                                            st.warning("一部エラーが発生しました:")
                                            for error in creation_result.errors:
                                                st.write(f"- {error}")
                            else:
                                # ドライランまたはマッチなしの場合の作成予定を表示
                                creation_result = service.create_memberships(
                                    parliamentary_group_id=selected_group["id"],
                                    matching_results=matching_results,
                                    start_date=start_date,
                                    confidence_threshold=confidence_threshold,
                                    dry_run=True,
                                )

                                st.markdown("### 作成予定のメンバーシップ")
                                st.write(
                                    f"- 作成予定: {creation_result.created_count}件"
                                )
                                st.write(
                                    f"- スキップ（既存）: "
                                    f"{creation_result.skipped_count}件"
                                )

                                if creation_result.errors:
                                    st.write("- エラー:")
                                    for error in creation_result.errors[:5]:
                                        st.write(f"  - {error}")
                                    if len(creation_result.errors) > 5:
                                        remaining = len(creation_result.errors) - 5
                                        st.write(f"  ... 他 {remaining}件")

                                if not dry_run and creation_result.created_count > 0:
                                    st.info(
                                        "ドライランを解除して再実行すると、実際にメンバーシップが作成されます。"
                                    )

                    except (ScrapingError, ProcessingError) as e:
                        st.error(f"メンバー抽出処理に失敗しました: {str(e)}")
                    except DatabaseError as e:
                        st.error(f"データベースエラーが発生しました: {str(e)}")
                    except Exception as e:
                        st.error(f"予期しないエラーが発生しました: {str(e)}")
                        import traceback

                        st.text(traceback.format_exc())

    # リポジトリのクローズ
    pg_repo.close()
    conf_repo.close()
    if "pgm_repo" in locals():
        pgm_repo.close()  # type: ignore[possibly-undefined]
