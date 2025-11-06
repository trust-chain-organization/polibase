"""Streamlit Google Sign-In認証のテスト。"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_streamlit():
    """Streamlit APIをモック化するフィクスチャ。

    Streamlit実行環境が必要な関数をテストするため、
    st.user, st.login, st.logoutをモック化します。
    """
    with patch("src.interfaces.web.streamlit.auth.google_sign_in.st") as mock_st:
        # デフォルトの振る舞いを設定
        mock_st.user = MagicMock()
        mock_st.login = MagicMock()
        mock_st.logout = MagicMock()
        mock_st.button = MagicMock(return_value=False)
        mock_st.error = MagicMock()
        mock_st.info = MagicMock()
        mock_st.title = MagicMock()
        mock_st.markdown = MagicMock()
        mock_st.image = MagicMock()
        mock_st.caption = MagicMock()
        mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock()])
        yield mock_st


def test_is_user_logged_in_when_authenticated(mock_streamlit):
    """認証済みユーザーの場合、Trueを返すことを確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = True

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    result = google_sign_in.is_user_logged_in()

    # Assert
    assert result is True


def test_is_user_logged_in_when_not_authenticated(mock_streamlit):
    """未認証ユーザーの場合、Falseを返すことを確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = False

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    result = google_sign_in.is_user_logged_in()

    # Assert
    assert result is False


def test_is_user_logged_in_with_none_value(mock_streamlit):
    """is_logged_inがNoneの場合、Falseを返すことを確認。

    Streamlitの初期化前などでis_logged_inがNoneになる可能性があるため、
    その場合は安全にFalseを返すべきです。
    """
    # Arrange
    mock_streamlit.user.is_logged_in = None

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    result = google_sign_in.is_user_logged_in()

    # Assert
    assert result is False
    assert isinstance(result, bool)


def test_is_user_logged_in_returns_bool_type(mock_streamlit):
    """is_logged_inの戻り値がbool型であることを確認。

    Streamlitのis_logged_inは様々な型を返す可能性があるため、
    bool()で明示的に変換していることを確認します。
    """
    # Arrange - 文字列を返す場合
    mock_streamlit.user.is_logged_in = "true"

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    result = google_sign_in.is_user_logged_in()

    # Assert
    assert isinstance(result, bool)
    assert result is True  # 空でない文字列はTrueに変換される


def test_get_user_info_returns_user_data(mock_streamlit):
    """ログイン済みユーザーの情報が正しく取得できることを確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = True
    mock_streamlit.user.to_dict.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/pic.jpg",
    }

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    user_info = google_sign_in.get_user_info()

    # Assert
    assert user_info is not None
    assert user_info["email"] == "test@example.com"
    assert user_info["name"] == "Test User"
    assert user_info["picture"] == "https://example.com/pic.jpg"


def test_get_user_info_returns_none_when_not_logged_in(mock_streamlit):
    """未認証の場合、Noneを返すことを確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = False

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    user_info = google_sign_in.get_user_info()

    # Assert
    assert user_info is None


def test_get_user_info_converts_values_to_strings(mock_streamlit):
    """ユーザー情報の値が文字列に変換されることを確認。

    Streamlitのto_dict()は様々な型を返す可能性があるため、
    明示的にstr()で変換していることを確認します。
    """
    # Arrange
    mock_streamlit.user.is_logged_in = True
    mock_streamlit.user.to_dict.return_value = {
        "email": 123,  # 数値
        "name": None,  # None
        "picture": True,  # bool
    }

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    user_info = google_sign_in.get_user_info()

    # Assert
    assert user_info is not None
    assert isinstance(user_info["email"], str)
    assert isinstance(user_info["name"], str)
    assert isinstance(user_info["picture"], str)
    assert user_info["email"] == "123"
    assert user_info["name"] == "None"
    assert user_info["picture"] == "True"


def test_get_user_info_handles_missing_fields(mock_streamlit):
    """ユーザー情報の一部のフィールドが欠けている場合の処理を確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = True
    mock_streamlit.user.to_dict.return_value = {
        "email": "test@example.com",
        # nameとpictureは含まれていない
    }

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    user_info = google_sign_in.get_user_info()

    # Assert
    assert user_info is not None
    assert user_info["email"] == "test@example.com"
    assert user_info["name"] == ""  # デフォルト値
    assert user_info["picture"] == ""  # デフォルト値


def test_get_user_info_handles_exception(mock_streamlit):
    """to_dict()でエラーが発生した場合、Noneを返すことを確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = True
    mock_streamlit.user.to_dict.side_effect = Exception("Unexpected error")

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    user_info = google_sign_in.get_user_info()

    # Assert
    assert user_info is None


def test_logout_user_calls_st_logout(mock_streamlit):
    """logout_user()がst.logout()を呼び出すことを確認。"""
    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    google_sign_in.logout_user()

    # Assert
    mock_streamlit.logout.assert_called_once()


def test_logout_user_handles_exception(mock_streamlit):
    """ログアウト時のエラーハンドリングを確認。"""
    # Arrange
    mock_streamlit.logout.side_effect = Exception("Logout failed")

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    # エラーが発生してもクラッシュしないことを確認
    google_sign_in.logout_user()

    # Assert
    mock_streamlit.error.assert_called_once()


def test_render_login_page_displays_login_button(mock_streamlit):
    """ログインページにログインボタンが表示されることを確認。"""
    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    google_sign_in.render_login_page()

    # Assert
    mock_streamlit.title.assert_called_once_with("🔐 ログイン")
    mock_streamlit.button.assert_called()


def test_render_login_page_calls_st_login_when_button_clicked(mock_streamlit):
    """ログインボタンがクリックされた時、st.login()が呼ばれることを確認。"""
    # Arrange
    mock_streamlit.button.return_value = True  # ボタンがクリックされた状態

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    google_sign_in.render_login_page()

    # Assert
    mock_streamlit.login.assert_called_once()


def test_render_login_page_handles_login_exception(mock_streamlit):
    """ログイン時のエラーが適切に処理されることを確認。"""
    # Arrange
    mock_streamlit.button.return_value = True
    mock_streamlit.login.side_effect = Exception("Login error")

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    google_sign_in.render_login_page()

    # Assert
    mock_streamlit.error.assert_called()


def test_render_user_info_displays_user_data(mock_streamlit):
    """ユーザー情報が正しく表示されることを確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = True
    mock_streamlit.user.to_dict.return_value = {
        "email": "test@example.com",
        "name": "Test User",
        "picture": "https://example.com/pic.jpg",
    }
    mock_col1, mock_col2 = MagicMock(), MagicMock()
    mock_streamlit.columns.return_value = [mock_col1, mock_col2]

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    google_sign_in.render_user_info()

    # Assert
    mock_streamlit.columns.assert_called_once_with([3, 1])
    # ユーザー情報の表示が行われることを確認
    assert mock_col1.__enter__.called or mock_col2.__enter__.called


def test_render_user_info_handles_no_user_info(mock_streamlit):
    """ユーザー情報が取得できない場合、何も表示しないことを確認。"""
    # Arrange
    mock_streamlit.user.is_logged_in = False

    # Act
    from src.interfaces.web.streamlit.auth import google_sign_in

    google_sign_in.render_user_info()

    # Assert
    # ユーザー情報がない場合は早期リターンするため、columnsは呼ばれない
    mock_streamlit.columns.assert_not_called()
