"""発言者管理ページ"""

import pandas as pd

import streamlit as st
from src.common.logging import get_logger
from src.database.speaker_repository import SpeakerRepository

logger = get_logger(__name__)


def manage_speakers():
    """発言者管理（一覧）"""
    st.header("発言者管理")
    st.markdown("議事録から抽出された発言者レコードの一覧を表示します")

    show_speakers_list()


def show_speakers_list():
    """発言者一覧の表示"""
    # ページネーション設定
    items_per_page = st.selectbox(
        "表示件数", options=[20, 50, 100], index=0, key="speakers_per_page"
    )

    # 現在のページ番号（セッション状態で管理）
    if "speaker_page" not in st.session_state:
        st.session_state.speaker_page = 0

    col1, col2, col3 = st.columns([1, 3, 1])

    # ページネーションボタン
    with col1:
        if st.button("◀ 前へ", disabled=st.session_state.speaker_page == 0):
            st.session_state.speaker_page -= 1
            st.rerun()

    # データ取得と表示
    offset = st.session_state.speaker_page * items_per_page

    try:
        speaker_repo = SpeakerRepository()

        # 発言者データを発言数付きで取得
        speakers_data, total_count = (
            speaker_repo.get_all_speakers_with_conversation_count(
                offset=offset, limit=items_per_page
            )
        )

        # ページ情報表示
        with col2:
            total_pages = (
                (total_count + items_per_page - 1) // items_per_page
                if total_count > 0
                else 1
            )
            page_text = (
                f"ページ {st.session_state.speaker_page + 1} / {total_pages} "
                f"(全 {total_count} 件)"
            )
            st.markdown(
                f"<div style='text-align: center;'>{page_text}</div>",
                unsafe_allow_html=True,
            )

        # 次へボタン
        with col3:
            has_next = (
                st.session_state.speaker_page + 1
            ) * items_per_page < total_count
            if st.button("次へ ▶", disabled=not has_next):
                st.session_state.speaker_page += 1
                st.rerun()

        if speakers_data:
            # データフレーム作成
            df = pd.DataFrame(speakers_data)

            # カラム名を日本語に変換
            df = df.rename(
                columns={
                    "id": "ID",
                    "name": "発言者名",
                    "type": "種別",
                    "political_party_name": "政党名",
                    "position": "役職",
                    "is_politician": "政治家フラグ",
                    "conversation_count": "発言数",
                }
            )

            # 政治家フラグを視覚的に表示
            df["政治家フラグ"] = df["政治家フラグ"].apply(lambda x: "✅" if x else "❌")

            # NULLを"-"に変換
            df = df.fillna("-")

            # 表の表示設定
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn("ID", width="small"),
                    "発言者名": st.column_config.TextColumn("発言者名", width="medium"),
                    "種別": st.column_config.TextColumn("種別", width="small"),
                    "政党名": st.column_config.TextColumn("政党名", width="medium"),
                    "役職": st.column_config.TextColumn("役職", width="medium"),
                    "政治家フラグ": st.column_config.TextColumn(
                        "政治家", width="small"
                    ),
                    "発言数": st.column_config.NumberColumn("発言数", width="small"),
                },
            )

            # 統計情報
            politician_count = sum(
                1 for s in speakers_data if s.get("is_politician", False)
            )
            st.info(f"総発言者数: {total_count} 人 | 政治家数: {politician_count} 人")
        else:
            st.warning("発言者データがありません")

    except Exception as e:
        logger.error(f"発言者データの取得に失敗: {e}", exc_info=True)
        st.error(f"データの取得に失敗しました: {str(e)}")
