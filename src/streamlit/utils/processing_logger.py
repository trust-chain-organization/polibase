"""議事録処理のログ管理ユーティリティ"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path


class ProcessingLogger:
    """処理ログをファイルに保存・読み込むクラス"""

    def __init__(self, base_dir: str | None = None):
        """初期化

        Args:
            base_dir: ログファイルを保存するディレクトリ
                （Noneの場合は環境変数またはtempfileを使用）
        """
        if base_dir is None:
            # 環境変数から取得、なければtempfileで安全なディレクトリを作成
            base_dir = os.environ.get(
                "POLIBASE_LOG_DIR", os.path.join(tempfile.gettempdir(), "polibase_logs")
            )
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_log_file(self, meeting_id: int) -> Path:
        """会議IDに対応するログファイルパスを取得

        Args:
            meeting_id: 会議ID

        Returns:
            ログファイルのパス
        """
        return self.base_dir / f"meeting_{meeting_id}.json"

    def add_log(
        self,
        meeting_id: int,
        message: str,
        level: str = "info",
        details: str | None = None,
    ) -> None:
        """ログメッセージを追加

        Args:
            meeting_id: 会議ID
            message: ログメッセージ
            level: ログレベル (info, warning, error, success, detail)
            details: 詳細データ（長いテキストなど、折りたたみ表示する場合）
        """
        log_file = self.get_log_file(meeting_id)

        # 既存のログを読み込む
        logs = self.get_logs(meeting_id)

        # 新しいログエントリを追加
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "level": level.upper(),
            "message": message,
            "formatted": f"[{timestamp}] [{level.upper()}] {message}",
        }

        # 詳細データがある場合は追加
        if details:
            log_entry["details"] = details

        logs.append(log_entry)

        # ファイルに保存
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)

    def get_logs(self, meeting_id: int) -> list[dict[str, str]]:
        """ログを取得

        Args:
            meeting_id: 会議ID

        Returns:
            ログエントリのリスト
        """
        log_file = self.get_log_file(meeting_id)

        if log_file.exists():
            try:
                with open(log_file, encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():  # Check if file has content
                        return json.loads(content)
                    else:
                        return []  # Return empty list for empty file
            except (OSError, json.JSONDecodeError):
                # If file is corrupted or can't be read, return empty list
                return []
        return []

    def clear_logs(self, meeting_id: int) -> None:
        """ログをクリア

        Args:
            meeting_id: 会議ID
        """
        log_file = self.get_log_file(meeting_id)
        if log_file.exists():
            log_file.unlink()

    def set_processing_status(self, meeting_id: int, is_processing: bool) -> None:
        """処理状態を設定

        Args:
            meeting_id: 会議ID
            is_processing: 処理中かどうか
        """
        status_file = self.base_dir / f"status_{meeting_id}.json"
        with open(status_file, "w") as f:
            json.dump({"is_processing": is_processing}, f)

    def get_processing_status(self, meeting_id: int) -> bool:
        """処理状態を取得

        Args:
            meeting_id: 会議ID

        Returns:
            処理中かどうか
        """
        status_file = self.base_dir / f"status_{meeting_id}.json"
        if status_file.exists():
            with open(status_file) as f:
                data = json.load(f)
                return data.get("is_processing", False)
        return False
