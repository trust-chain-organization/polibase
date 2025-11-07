"""Streamlit標準のGoogle Sign-In実装。

このモジュールは、Streamlit 1.42.0以降で利用可能な標準認証APIを使用して、
Google Sign-Inを実装します。
"""

import streamlit as st


def render_login_page() -> None:
    """ログインページをレンダリングします。

    Streamlit標準の `st.login()` を使用してGoogle OAuth認証フローを開始します。
    """
    st.title("🔐 ログイン")

    st.markdown(
        """
    ## Polibaseへようこそ

    このアプリケーションにアクセスするには、Googleアカウントでログインしてください。

    ### セットアップ方法

    1. Google Cloud Consoleで OAuth 2.0 クライアントIDを作成
    2. `.streamlit/secrets.toml` に認証情報を設定
    3. このページの「Googleでログイン」ボタンをクリック

    詳細な設定方法は `.streamlit/secrets.toml.example` を参照してください。
    """
    )

    # ログインボタンを表示
    if st.button("🔑 Googleでログイン", use_container_width=True):
        try:
            st.login()
        except Exception as e:
            st.error(f"ログインエラー: {e}")
            st.info(
                "認証設定を確認してください:\n"
                "- `.streamlit/secrets.toml` が存在するか\n"
                "- Google OAuth認証情報が正しく設定されているか"
            )


def is_user_logged_in() -> bool:
    """ユーザーがログインしているか確認します。

    Returns:
        ログインしている場合True、それ以外はFalse
    """
    try:
        return bool(st.user.is_logged_in)
    except Exception:
        # st.userが利用できない場合（認証が設定されていない場合など）
        return False


def get_user_info() -> dict[str, str] | None:
    """ログイン済みユーザーの情報を取得します。

    Returns:
        ユーザー情報の辞書、ログインしていない場合はNone
    """
    if not is_user_logged_in():
        return None

    try:
        user_dict = st.user.to_dict()
        return {
            "email": str(user_dict.get("email", "")),
            "name": str(user_dict.get("name", "")),
            "picture": str(user_dict.get("picture", "")),
        }
    except Exception:
        return None


def logout_user() -> None:
    """ユーザーをログアウトします。"""
    try:
        st.logout()
    except Exception as e:
        st.error(f"ログアウトエラー: {e}")


def render_user_info() -> None:
    """ログイン済みユーザーの情報を表示します。"""
    user_info = get_user_info()
    if not user_info:
        return

    col1, col2 = st.columns([3, 1])

    with col1:
        # ユーザー情報を表示
        if user_info.get("picture"):
            st.image(user_info["picture"], width=50)
        st.markdown(f"**{user_info.get('name', 'ユーザー')}**")
        st.caption(user_info.get("email", ""))

    with col2:
        # ログアウトボタン
        if st.button("ログアウト", key="logout_button"):
            logout_user()
            st.rerun()
