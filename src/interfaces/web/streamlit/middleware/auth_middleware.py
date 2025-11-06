"""認証ミドルウェア。

このモジュールは、Streamlitページへのアクセスを制御する認証ミドルウェアを提供します。
未認証のユーザーがアクセスした場合、ログインページを表示します。
"""

import os
from collections.abc import Callable
from typing import Any

import streamlit as st

from src.interfaces.web.streamlit.auth.google_auth import GoogleAuthenticator
from src.interfaces.web.streamlit.auth.session_manager import AuthSessionManager


def require_auth[F: Callable[..., Any]](func: F) -> F:
    """認証を必須とするデコレータ。

    このデコレータは、関数実行前にユーザーの認証状態をチェックします。
    未認証の場合はログインページを表示し、認証済みの場合は元の関数を実行します。

    Args:
        func: デコレートする関数

    Returns:
        デコレートされた関数

    Example:
        @require_auth
        def my_protected_page():
            st.write("この内容は認証されたユーザーのみ閲覧可能")
    """

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        session_manager = AuthSessionManager()

        # 認証状態をチェック
        if session_manager.is_authenticated():
            # 認証済み - 元の関数を実行
            return func(*args, **kwargs)

        # 未認証 - ログインページを表示
        render_login_page(session_manager)
        return None

    return wrapper  # type: ignore


def render_login_page(session_manager: AuthSessionManager) -> None:
    """ログインページをレンダリングします。

    Args:
        session_manager: 認証セッションマネージャー
    """
    st.title("🔐 ログイン")

    # 認証が無効化されている場合の処理
    auth_disabled = os.getenv("GOOGLE_OAUTH_DISABLED", "false").lower() == "true"

    if auth_disabled:
        st.warning("⚠️ 認証機能は現在無効化されています（開発モード）")
        st.info("本番環境では必ず認証を有効化してください。")
        if st.button("認証なしで続行"):
            # 開発用の仮ユーザー情報を設定
            session_manager.set_user_info(
                {
                    "email": "dev@example.com",
                    "name": "Development User",
                    "picture": "",
                }
            )
            session_manager.set_token({"access_token": "dev_token"})
            st.rerun()
        return

    st.markdown("""
    ## Polibaseへようこそ

    このアプリケーションにアクセスするには、Googleアカウントでログインしてください。

    ### アクセス権限について

    - 許可されたGoogleアカウントのみアクセス可能です
    - アクセス権限が必要な場合は、管理者にお問い合わせください
    """)

    try:
        # GoogleAuthenticatorの初期化
        authenticator = GoogleAuthenticator()

        # OAuth認証ボタンを表示
        result = authenticator.authorize_button(
            button_text="🔑 Googleでログイン",
            key="google_oauth_login",
        )

        if result and "token" in result:
            token = result["token"]

            # アクセストークンを使用してユーザー情報を取得
            user_info = authenticator.get_user_info(token["access_token"])

            if user_info:
                user_email = user_info.get("email", "")

                # ホワイトリストチェック
                if authenticator.is_email_allowed(user_email):
                    # 認証成功 - セッションに保存
                    session_manager.set_token(token)
                    session_manager.set_user_info(user_info)

                    st.success(f"✅ ログインに成功しました: {user_email}")
                    st.rerun()
                else:
                    # アクセス拒否
                    st.error(
                        f"❌ アクセスが拒否されました。\n\n"
                        f"アカウント: {user_email}\n\n"
                        f"このアカウントは許可されていません。"
                        f"アクセス権限が必要な場合は、管理者にお問い合わせください。"
                    )
                    # トークンを無効化
                    authenticator.logout(token)
            else:
                st.error("ユーザー情報の取得に失敗しました。再度お試しください。")

    except ValueError as e:
        st.error(f"❌ 認証設定エラー: {e}")
        st.info(
            "Google OAuth認証の設定が正しく行われていません。\n"
            "環境変数を確認してください：\n"
            "- GOOGLE_OAUTH_CLIENT_ID\n"
            "- GOOGLE_OAUTH_CLIENT_SECRET\n"
            "- GOOGLE_OAUTH_REDIRECT_URI\n"
            "- GOOGLE_OAUTH_ALLOWED_EMAILS（オプション）"
        )
    except Exception as e:
        st.error(f"❌ 予期しないエラーが発生しました: {e}")
        st.info("問題が解決しない場合は、管理者にお問い合わせください。")
