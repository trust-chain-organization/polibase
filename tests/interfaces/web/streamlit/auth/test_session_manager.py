"""AuthSessionManagerのユニットテスト。"""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from src.interfaces.web.streamlit.auth.session_manager import AuthSessionManager


@pytest.fixture
def mock_streamlit():
    """Streamlitのモックを作成します。"""
    with patch("src.interfaces.web.streamlit.utils.session_manager.st") as mock_st:
        mock_st.session_state = {}
        yield mock_st


@pytest.fixture
def session_manager(mock_streamlit):
    """AuthSessionManagerのインスタンスを作成します。"""
    return AuthSessionManager()


def test_session_manager_initialization(session_manager):
    """AuthSessionManagerの初期化をテストします。"""
    assert session_manager.namespace == "auth"
    assert not session_manager.is_authenticated()


def test_set_and_get_token(session_manager):
    """トークンの設定と取得をテストします。"""
    token = {
        "access_token": "test_token",
        "expires_in": 3600,
    }

    session_manager.set_token(token)
    retrieved_token = session_manager.get_token()

    assert retrieved_token == token


def test_set_and_get_user_info(session_manager):
    """ユーザー情報の設定と取得をテストします。"""
    user_info = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg",
    }

    session_manager.set_user_info(user_info)
    retrieved_user_info = session_manager.get_user_info()

    assert retrieved_user_info == user_info


def test_get_user_email(session_manager):
    """ユーザーのメールアドレス取得をテストします。"""
    user_info = {
        "email": "test@example.com",
        "name": "Test User",
    }

    session_manager.set_user_info(user_info)
    email = session_manager.get_user_email()

    assert email == "test@example.com"


def test_get_user_email_when_no_user_info(session_manager):
    """ユーザー情報がない場合のメールアドレス取得をテストします。"""
    email = session_manager.get_user_email()
    assert email is None


def test_get_user_name(session_manager):
    """ユーザー名の取得をテストします。"""
    user_info = {
        "email": "test@example.com",
        "name": "Test User",
    }

    session_manager.set_user_info(user_info)
    name = session_manager.get_user_name()

    assert name == "Test User"


def test_get_user_name_fallback_to_email(session_manager):
    """名前がない場合のフォールバックをテストします。"""
    user_info = {
        "email": "test@example.com",
    }

    session_manager.set_user_info(user_info)
    name = session_manager.get_user_name()

    assert name == "test@example.com"


def test_is_authenticated_with_valid_token(session_manager, mock_streamlit):
    """有効なトークンでの認証状態をテストします。"""
    token = {
        "access_token": "test_token",
    }
    session_manager.set_token(token)

    # authenticated_atを設定
    session_manager.set("authenticated_at", datetime.now().isoformat())

    assert session_manager.is_authenticated()


def test_is_authenticated_without_token(session_manager):
    """トークンがない場合の認証状態をテストします。"""
    assert not session_manager.is_authenticated()


def test_clear_auth(session_manager, mock_streamlit):
    """認証情報のクリアをテストします。"""
    token = {"access_token": "test_token"}
    user_info = {"email": "test@example.com"}

    session_manager.set_token(token)
    session_manager.set_user_info(user_info)

    assert session_manager.is_authenticated()

    session_manager.clear_auth()

    assert not session_manager.is_authenticated()
    assert session_manager.get_token() is None
    assert session_manager.get_user_info() is None


def test_token_expiry_check_with_expires_in(session_manager, mock_streamlit):
    """expires_inを使用したトークン有効期限チェックをテストします。"""
    # 期限切れのトークン
    expired_token = {
        "access_token": "test_token",
        "expires_in": 3600,
    }

    # 2時間前に認証されたことにする
    past_time = datetime.now() - timedelta(hours=2)
    mock_streamlit.session_state["auth_authenticated_at"] = past_time.isoformat()
    mock_streamlit.session_state["auth_token"] = expired_token

    assert not session_manager.is_authenticated()


def test_get_authenticated_at(session_manager):
    """認証時刻の取得をテストします。"""
    now = datetime.now()
    session_manager.set("authenticated_at", now.isoformat())

    authenticated_at = session_manager.get_authenticated_at()

    assert authenticated_at is not None
    # 誤差を考慮して1秒以内であることを確認
    assert abs((authenticated_at - now).total_seconds()) < 1


def test_get_authenticated_at_when_not_set(session_manager):
    """認証時刻が設定されていない場合のテストです。"""
    authenticated_at = session_manager.get_authenticated_at()
    assert authenticated_at is None
