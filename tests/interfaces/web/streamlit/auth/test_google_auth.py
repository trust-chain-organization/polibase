"""GoogleAuthenticatorのユニットテスト。"""

from unittest.mock import MagicMock, patch

import pytest

from src.interfaces.web.streamlit.auth.google_auth import GoogleAuthenticator


@pytest.fixture
def mock_env():
    """環境変数のモックを作成します。"""
    env_vars = {
        "GOOGLE_OAUTH_CLIENT_ID": "test-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_OAUTH_REDIRECT_URI": "http://localhost:8501/",
        "GOOGLE_OAUTH_ALLOWED_EMAILS": "user1@example.com,user2@example.com",
    }

    with patch.dict("os.environ", env_vars, clear=False):
        yield env_vars


@pytest.fixture
def authenticator(mock_env):
    """GoogleAuthenticatorのインスタンスを作成します。"""
    with patch(
        "src.interfaces.web.streamlit.auth.google_auth.OAuth2Component"
    ) as mock_oauth2:
        mock_oauth2.return_value = MagicMock()
        return GoogleAuthenticator()


def test_authenticator_initialization(authenticator):
    """GoogleAuthenticatorの初期化をテストします。"""
    assert authenticator.client_id == "test-client-id"
    assert authenticator.client_secret == "test-client-secret"
    assert authenticator.redirect_uri == "http://localhost:8501/"
    assert "user1@example.com" in authenticator.allowed_emails
    assert "user2@example.com" in authenticator.allowed_emails


def test_initialization_without_credentials():
    """認証情報がない場合の初期化をテストします。"""
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="Google OAuth credentials not configured"):
            GoogleAuthenticator()


def test_is_email_allowed_with_whitelist(authenticator):
    """ホワイトリストを使用したメールアドレスチェックをテストします。"""
    assert authenticator.is_email_allowed("user1@example.com")
    assert authenticator.is_email_allowed(
        "USER1@EXAMPLE.COM"
    )  # 大文字小文字を区別しない
    assert not authenticator.is_email_allowed("notallowed@example.com")


def test_is_email_allowed_without_whitelist():
    """ホワイトリストがない場合のメールアドレスチェックをテストします。"""
    env_vars = {
        "GOOGLE_OAUTH_CLIENT_ID": "test-client-id",
        "GOOGLE_OAUTH_CLIENT_SECRET": "test-client-secret",
        "GOOGLE_OAUTH_REDIRECT_URI": "http://localhost:8501/",
        "GOOGLE_OAUTH_ALLOWED_EMAILS": "",  # 空の場合
    }

    with patch.dict("os.environ", env_vars, clear=False):
        with patch(
            "src.interfaces.web.streamlit.auth.google_auth.OAuth2Component"
        ) as mock_oauth2:
            mock_oauth2.return_value = MagicMock()
            auth = GoogleAuthenticator()

            # ホワイトリストがない場合は全てのメールを許可
            assert auth.is_email_allowed("anyone@example.com")
            assert auth.is_email_allowed("test@test.com")


def test_get_user_info_success(authenticator):
    """ユーザー情報の取得成功をテストします。"""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/picture.jpg",
    }
    mock_response.raise_for_status = MagicMock()

    with patch(
        "src.interfaces.web.streamlit.auth.google_auth.requests.get"
    ) as mock_get:
        mock_get.return_value = mock_response

        user_info = authenticator.get_user_info("test_access_token")

        assert user_info is not None
        assert user_info["email"] == "test@example.com"
        assert user_info["name"] == "Test User"


def test_get_user_info_failure(authenticator):
    """ユーザー情報の取得失敗をテストします。"""
    import requests

    with patch(
        "src.interfaces.web.streamlit.auth.google_auth.requests.get"
    ) as mock_get:
        mock_get.side_effect = requests.RequestException("Network error")

        with patch("src.interfaces.web.streamlit.auth.google_auth.st") as mock_st:
            user_info = authenticator.get_user_info("test_access_token")

            assert user_info is None
            mock_st.error.assert_called_once()


def test_authorize_button(authenticator):
    """認証ボタンの表示をテストします。"""
    mock_result = {"token": {"access_token": "test_token"}}

    authenticator.oauth2.authorize_button = MagicMock(return_value=mock_result)

    result = authenticator.authorize_button()

    assert result == mock_result
    authenticator.oauth2.authorize_button.assert_called_once()


def test_logout_success(authenticator):
    """ログアウト成功をテストします。"""
    token = {"access_token": "test_token"}

    authenticator.oauth2.revoke_token = MagicMock()

    success = authenticator.logout(token)

    assert success
    authenticator.oauth2.revoke_token.assert_called_once_with(token)


def test_logout_failure(authenticator):
    """ログアウト失敗をテストします。"""
    token = {"access_token": "test_token"}

    authenticator.oauth2.revoke_token = MagicMock(
        side_effect=Exception("Revoke failed")
    )

    with patch("src.interfaces.web.streamlit.auth.google_auth.st") as mock_st:
        success = authenticator.logout(token)

        assert not success
        mock_st.error.assert_called_once()
