"""CI用の軽量スモークテスト

最小限の動作確認のみを行い、CI時間を短縮する
"""

import os

import pytest


def test_database_connection():
    """データベース接続の確認（CI環境でのみ実行）"""
    if os.getenv("DATABASE_URL"):
        from src.infrastructure.config.database import test_connection

        assert test_connection(), "データベース接続に失敗しました"
    else:
        pytest.skip("DATABASE_URL not set, skipping database test")


def test_cli_import():
    """CLIモジュールのインポート確認"""
    try:
        import src.cli

        assert src.cli is not None
        # CLIモジュールが正常にインポートできることを確認
    except ImportError as e:
        pytest.fail(f"CLIモジュールのインポートに失敗: {e}")


def test_basic_imports():
    """主要モジュールのインポート確認"""
    modules_to_test = [
        "src.domain.entities.meeting",
        "src.domain.entities.politician",
        "src.infrastructure.persistence.base_repository_impl",
        "src.application.usecases.process_minutes_usecase",
    ]

    for module_name in modules_to_test:
        try:
            __import__(module_name)
        except ImportError as e:
            pytest.fail(f"{module_name}のインポートに失敗: {e}")


def test_environment_variables():
    """CI環境での必要な環境変数の確認"""
    if os.getenv("CI"):
        required_vars = ["DATABASE_URL"]
        for var in required_vars:
            assert os.getenv(var), f"環境変数{var}が設定されていません"
    else:
        pytest.skip("Not in CI environment, skipping environment variable test")
