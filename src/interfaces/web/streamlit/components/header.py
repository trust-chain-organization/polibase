"""ヘッダーコンポーネント。

このモジュールは、Streamlitアプリケーションのヘッダーを提供します。
ユーザーのログイン状態を表示し、ログアウト機能を提供します。
"""

import os

import streamlit as st

from src.interfaces.web.streamlit.auth.google_auth import GoogleAuthenticator
from src.interfaces.web.streamlit.auth.session_manager import AuthSessionManager


def render_header() -> None:
    """アプリケーションのヘッダーをレンダリングします。

    ユーザーのログイン状態を表示し、ログアウトボタンを提供します。
    認証が無効化されている場合は、開発モードであることを表示します。
    """
    session_manager = AuthSessionManager()
    auth_disabled = os.getenv("GOOGLE_OAUTH_DISABLED", "false").lower() == "true"

    # サイドバーにユーザー情報を表示
    with st.sidebar:
        st.divider()

        if auth_disabled:
            st.caption("🔓 開発モード（認証無効）")
        elif session_manager.is_authenticated():
            _render_authenticated_user_info(session_manager)
        else:
            st.caption("未認証")


def _render_authenticated_user_info(session_manager: AuthSessionManager) -> None:
    """認証済みユーザーの情報を表示します。

    Args:
        session_manager: 認証セッションマネージャー
    """
    user_info = session_manager.get_user_info()

    if not user_info:
        return

    # ユーザー情報を表示
    user_name = user_info.get("name", "")
    user_email = user_info.get("email", "")
    user_picture = user_info.get("picture", "")

    # プロフィール画像とユーザー名を表示
    col1, col2 = st.columns([1, 3])

    with col1:
        if user_picture:
            st.image(user_picture, width=50)
        else:
            st.write("👤")

    with col2:
        if user_name:
            st.caption(f"**{user_name}**")
        st.caption(user_email)

    # ログアウトボタン
    if st.button("🚪 ログアウト", use_container_width=True, key="logout_button"):
        _handle_logout(session_manager)


def _handle_logout(session_manager: AuthSessionManager) -> None:
    """ログアウト処理を実行します。

    Args:
        session_manager: 認証セッションマネージャー
    """
    try:
        # トークンを取得
        token = session_manager.get_token()

        # セッションをクリア
        session_manager.clear_auth()

        # Google OAuthトークンを無効化（オプション）
        if token:
            try:
                authenticator = GoogleAuthenticator()
                authenticator.logout(token)
            except Exception:
                # トークン無効化に失敗しても続行
                pass

        # ページをリロード
        st.rerun()

    except Exception as e:
        st.error(f"ログアウトに失敗しました: {e}")
