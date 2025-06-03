"""Streamlit app for managing meetings"""
import streamlit as st
from datetime import date, datetime
from src.database.meeting_repository import MeetingRepository
import pandas as pd

# ページ設定
st.set_page_config(
    page_title="Polibase - 会議管理",
    page_icon="🏛️",
    layout="wide"
)

# セッション状態の初期化
if 'selected_governing_body' not in st.session_state:
    st.session_state.selected_governing_body = None
if 'selected_conference' not in st.session_state:
    st.session_state.selected_conference = None
if 'edit_mode' not in st.session_state:
    st.session_state.edit_mode = False
if 'edit_meeting_id' not in st.session_state:
    st.session_state.edit_meeting_id = None


def main():
    st.title("🏛️ Polibase - 会議管理システム")
    st.markdown("議事録の会議情報（URL、日付）を管理します")
    
    # タブ作成
    tab1, tab2, tab3 = st.tabs(["会議一覧", "新規会議登録", "会議編集"])
    
    with tab1:
        show_meetings_list()
    
    with tab2:
        add_new_meeting()
    
    with tab3:
        edit_meeting()


def show_meetings_list():
    """会議一覧を表示"""
    st.header("会議一覧")
    
    repo = MeetingRepository()
    
    # フィルター
    col1, col2 = st.columns(2)
    
    with col1:
        governing_bodies = repo.get_governing_bodies()
        gb_options = ["すべて"] + [f"{gb['name']} ({gb['type']})" for gb in governing_bodies]
        gb_selected = st.selectbox("開催主体", gb_options, key="list_gb")
        
        if gb_selected != "すべて":
            # 選択されたオプションから対応するgoverning_bodyを探す
            for i, gb in enumerate(governing_bodies):
                if f"{gb['name']} ({gb['type']})" == gb_selected:
                    selected_gb = gb
                    break
            conferences = repo.get_conferences_by_governing_body(selected_gb['id'])
        else:
            conferences = []
    
    with col2:
        if conferences:
            conf_options = ["すべて"] + [conf['name'] for conf in conferences]
            conf_selected = st.selectbox("会議体", conf_options, key="list_conf")
            
            if conf_selected != "すべて":
                # 選択されたオプションから対応するconferenceを探す
                for conf in conferences:
                    if conf['name'] == conf_selected:
                        selected_conf_id = conf['id']
                        break
            else:
                selected_conf_id = None
        else:
            selected_conf_id = None
            st.info("会議体を選択してください")
    
    # 会議一覧取得
    meetings = repo.get_meetings(conference_id=selected_conf_id)
    
    if meetings:
        # DataFrameに変換
        df = pd.DataFrame(meetings)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date', ascending=False)
        
        # 表示用のカラムを整形
        df['開催日'] = df['date'].dt.strftime('%Y年%m月%d日')
        df['開催主体・会議体'] = df['governing_body_name'] + " - " + df['conference_name']
        
        # 編集・削除ボタン用のカラム
        for idx, row in df.iterrows():
            col1, col2, col3 = st.columns([6, 1, 1])
            
            with col1:
                # URLを表示
                url_display = row['url'] if row['url'] else "URLなし"
                st.markdown(
                    f"**{row['開催日']}** - {row['開催主体・会議体']}",
                    unsafe_allow_html=True
                )
                if row['url']:
                    st.markdown(f"URL: [{url_display}]({row['url']})")
                else:
                    st.markdown(f"URL: {url_display}")
            
            with col2:
                if st.button("編集", key=f"edit_{row['id']}"):
                    st.session_state.edit_mode = True
                    st.session_state.edit_meeting_id = row['id']
                    st.rerun()
            
            with col3:
                if st.button("削除", key=f"delete_{row['id']}"):
                    if repo.delete_meeting(row['id']):
                        st.success("会議を削除しました")
                        st.rerun()
                    else:
                        st.error("会議を削除できませんでした（関連する議事録が存在する可能性があります）")
            
            st.divider()
    else:
        st.info("会議が登録されていません")
    
    repo.close()


def add_new_meeting():
    """新規会議登録フォーム"""
    st.header("新規会議登録")
    
    repo = MeetingRepository()
    
    with st.form("new_meeting_form"):
        # 開催主体選択
        governing_bodies = repo.get_governing_bodies()
        if not governing_bodies:
            st.error("開催主体が登録されていません。先にマスターデータを登録してください。")
            repo.close()
            return
            
        gb_options = [f"{gb['name']} ({gb['type']})" for gb in governing_bodies]
        gb_selected = st.selectbox("開催主体を選択", gb_options)
        
        # 選択されたgoverning_bodyを取得
        selected_gb = None
        for gb in governing_bodies:
            if f"{gb['name']} ({gb['type']})" == gb_selected:
                selected_gb = gb
                break
        
        # 会議体選択
        if selected_gb:
            conferences = repo.get_conferences_by_governing_body(selected_gb['id'])
            if conferences:
                conf_options = [conf['name'] for conf in conferences]
                conf_selected = st.selectbox("会議体を選択", conf_options)
                
                # 選択されたconferenceを取得
                selected_conf = None
                for conf in conferences:
                    if conf['name'] == conf_selected:
                        selected_conf = conf
                        break
            else:
                st.error("選択された開催主体に会議体が登録されていません")
                selected_conf = None
        
        # 日付入力
        meeting_date = st.date_input("開催日", value=date.today())
        
        # URL入力
        url = st.text_input("会議URL（議事録PDFのURLなど）", 
                           placeholder="https://example.com/minutes.pdf")
        
        # 送信ボタン
        submitted = st.form_submit_button("登録")
        
        if submitted and selected_conf:
            if not url:
                st.error("URLを入力してください")
            else:
                try:
                    meeting_id = repo.create_meeting(
                        conference_id=selected_conf['id'],
                        meeting_date=meeting_date,
                        url=url
                    )
                    st.success(f"会議を登録しました (ID: {meeting_id})")
                    
                    # フォームをリセット
                    st.rerun()
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
    
    repo.close()


def edit_meeting():
    """会議編集フォーム"""
    st.header("会議編集")
    
    if not st.session_state.edit_mode or not st.session_state.edit_meeting_id:
        st.info("編集する会議を選択してください（会議一覧タブから編集ボタンをクリック）")
        return
    
    repo = MeetingRepository()
    
    # 編集対象の会議情報を取得
    meeting = repo.get_meeting_by_id(st.session_state.edit_meeting_id)
    if not meeting:
        st.error("会議が見つかりません")
        st.session_state.edit_mode = False
        st.session_state.edit_meeting_id = None
        return
    
    st.info(f"編集中: {meeting['governing_body_name']} - {meeting['conference_name']}")
    
    with st.form("edit_meeting_form"):
        # 日付入力
        current_date = meeting['date'] if meeting['date'] else date.today()
        meeting_date = st.date_input("開催日", value=current_date)
        
        # URL入力
        url = st.text_input("会議URL（議事録PDFのURLなど）", 
                           value=meeting['url'] or "",
                           placeholder="https://example.com/minutes.pdf")
        
        # ボタン
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("更新")
        
        with col2:
            cancelled = st.form_submit_button("キャンセル")
        
        if submitted:
            if not url:
                st.error("URLを入力してください")
            else:
                try:
                    if repo.update_meeting(
                        meeting_id=st.session_state.edit_meeting_id,
                        meeting_date=meeting_date,
                        url=url
                    ):
                        st.success("会議を更新しました")
                        st.session_state.edit_mode = False
                        st.session_state.edit_meeting_id = None
                        st.rerun()
                    else:
                        st.error("会議の更新に失敗しました")
                except Exception as e:
                    st.error(f"エラーが発生しました: {str(e)}")
        
        if cancelled:
            st.session_state.edit_mode = False
            st.session_state.edit_meeting_id = None
            st.rerun()
    
    repo.close()


if __name__ == "__main__":
    main()