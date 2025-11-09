# 開発ガイド

## 目次
- [開発環境セットアップ](#開発環境セットアップ)
- [コーディング規約](#コーディング規約)
- [Git運用ルール](#git運用ルール)
- [開発フロー](#開発フロー)
- [デバッグ方法](#デバッグ方法)
- [パフォーマンス最適化](#パフォーマンス最適化)
- [セキュリティガイドライン](#セキュリティガイドライン)

## 開発環境セットアップ

### 必要なツール

| ツール | バージョン | 用途 |
|--------|-----------|------|
| Docker | 20.10+ | コンテナ環境 |
| Docker Compose | 2.0+ | マルチコンテナ管理 |
| Python | 3.11+ | 開発言語 |
| UV | 最新版 | パッケージ管理 |
| Git | 2.30+ | バージョン管理 |
| VS Code | 最新版 | 推奨エディタ |

### 初期セットアップ

#### 1. リポジトリのクローン

```bash
git clone https://github.com/trust-chain-organization/polibase.git
cd polibase
```

#### 2. 環境変数の設定

```bash
# .envファイルの作成
cp .env.example .env

# 必須環境変数の設定
# GOOGLE_API_KEY: Gemini APIキー
# DATABASE_URL: PostgreSQL接続文字列
# GCS_BUCKET_NAME: Google Cloud Storageバケット名（オプション）
```

#### 3. Docker環境の起動

```bash
# Docker Composeで環境構築
docker compose -f docker/docker-compose.yml up -d

# git worktreeを使用している場合
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up -d

# データベースの初期化
./test-setup.sh
```

#### 4. 依存パッケージのインストール

```bash
# ローカル開発用（オプション）
uv sync

# Docker内で実行
docker compose exec sagebase uv sync
```

#### 5. Google Cloud認証（GCS使用時）

```bash
# GCS使用時は認証が必要
gcloud auth application-default login
```

### VS Code設定

#### 推奨拡張機能

`.vscode/extensions.json`:
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "charliermarsh.ruff",
    "ms-vscode.makefile-tools",
    "ms-azuretools.vscode-docker",
    "redhat.vscode-yaml",
    "streetsidesoftware.code-spell-checker"
  ]
}
```

#### ワークスペース設定

`.vscode/settings.json`:
```json
{
  "python.linting.enabled": false,
  "python.formatting.provider": "none",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.autoImportCompletions": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.ruff_cache": true
  }
}
```

## コーディング規約

### Python スタイルガイド

#### 基本ルール

- **PEP 8準拠**: Ruffで自動チェック
- **型ヒント必須**: Python 3.11+の型機能を活用
- **docstring**: Google Style推奨
- **行長制限**: 88文字（Black互換）

#### 命名規則

| 要素 | 規則 | 例 |
|------|------|-----|
| クラス | PascalCase | `ProcessMinutesUseCase` |
| 関数・メソッド | snake_case | `process_minutes()` |
| 定数 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| プライベート | 先頭に`_` | `_internal_method()` |
| ファイル名 | snake_case | `politician_repository.py` |

#### コード例

```python
"""議事録処理モジュール

このモジュールは議事録の処理に関する機能を提供します。
"""

from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime

# 定数定義
MAX_CONVERSATION_LENGTH = 5000
DEFAULT_TIMEOUT = 30


@dataclass
class ProcessingResult:
    """処理結果を表すデータクラス

    Attributes:
        success: 処理の成功/失敗
        conversation_count: 抽出された発言数
        processing_time: 処理時間（秒）
        error_message: エラーメッセージ（エラー時のみ）
    """
    success: bool
    conversation_count: int
    processing_time: float
    error_message: Optional[str] = None


class MinutesProcessor:
    """議事録処理クラス

    議事録PDFから発言を抽出し、構造化データとして保存します。

    Example:
        >>> processor = MinutesProcessor(llm_service)
        >>> result = await processor.process(meeting_id=123)
        >>> print(f"抽出された発言数: {result.conversation_count}")
    """

    def __init__(self, llm_service: ILLMService) -> None:
        """初期化

        Args:
            llm_service: LLMサービスインスタンス
        """
        self._llm_service = llm_service
        self._processing_start: Optional[datetime] = None

    async def process(
        self,
        meeting_id: int,
        force: bool = False
    ) -> ProcessingResult:
        """議事録を処理する

        Args:
            meeting_id: 処理対象の会議ID
            force: 既存データを強制的に上書きするか

        Returns:
            処理結果

        Raises:
            MeetingNotFoundException: 会議が見つからない場合
            ProcessingException: 処理中にエラーが発生した場合
        """
        self._processing_start = datetime.now()

        try:
            # 処理ロジック
            conversations = await self._extract_conversations(meeting_id)

            processing_time = self._calculate_processing_time()

            return ProcessingResult(
                success=True,
                conversation_count=len(conversations),
                processing_time=processing_time
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                conversation_count=0,
                processing_time=self._calculate_processing_time(),
                error_message=str(e)
            )

    def _calculate_processing_time(self) -> float:
        """処理時間を計算する

        Returns:
            処理時間（秒）
        """
        if not self._processing_start:
            return 0.0

        return (datetime.now() - self._processing_start).total_seconds()
```

### Ruff設定

`pyproject.toml`:
```toml
[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # do not perform function calls in argument defaults
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### 型チェック設定

`pyrightconfig.json`:
```json
{
  "include": ["src"],
  "exclude": ["**/__pycache__"],
  "typeCheckingMode": "strict",
  "pythonVersion": "3.11",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "reportUnknownMemberType": false,
  "reportUnknownArgumentType": false,
  "reportUnknownVariableType": false,
  "reportUnknownLambdaType": false,
  "reportGeneralTypeIssues": true,
  "reportOptionalMemberAccess": true,
  "reportOptionalCall": true,
  "reportOptionalIterable": true,
  "reportOptionalContextManager": true,
  "reportOptionalOperand": true,
  "reportTypedDictNotRequiredAccess": true,
  "reportUnnecessaryTypeIgnoreComment": true
}
```

## Git運用ルール

### ブランチ戦略

```
main
├── feature/issue-123-add-new-feature
├── fix/issue-456-fix-bug
├── refactor/issue-789-clean-architecture
└── docs/issue-390-update-documentation
```

| ブランチ | 用途 | 命名規則 |
|---------|------|----------|
| `main` | メインブランチ | - |
| `feature/*` | 新機能開発 | `feature/issue-{番号}-{説明}` |
| `fix/*` | バグ修正 | `fix/issue-{番号}-{説明}` |
| `refactor/*` | リファクタリング | `refactor/issue-{番号}-{説明}` |
| `docs/*` | ドキュメント | `docs/issue-{番号}-{説明}` |

### コミットメッセージ

#### フォーマット

```
<type>: <subject>

<body>

<footer>
```

#### タイプ一覧

| タイプ | 説明 | 例 |
|--------|------|-----|
| `feat` | 新機能 | `feat: LLM履歴記録機能を追加` |
| `fix` | バグ修正 | `fix: 議事録処理のメモリリークを修正` |
| `refactor` | リファクタリング | `refactor: Clean Architectureへ移行` |
| `docs` | ドキュメント | `docs: APIドキュメントを追加` |
| `test` | テスト | `test: ユースケースのテストを追加` |
| `chore` | その他 | `chore: 依存パッケージを更新` |

#### コミット例

```bash
git commit -m "feat: 議事録処理のLLM履歴記録機能を実装

- LLMProcessingHistoryエンティティを追加
- 処理履歴を自動記録するデコレータを実装
- プロンプトバージョン管理機能を追加

Fixes #390"
```

### Pull Request

#### PRテンプレート

`.github/pull_request_template.md`:
```markdown
## 概要
<!-- 変更内容の簡潔な説明 -->

## 関連Issue
Fixes #

## 変更内容
- [ ] 機能A を実装
- [ ] バグB を修正
- [ ] ドキュメントC を更新

## テスト
- [ ] ユニットテストを追加/更新
- [ ] 統合テストを実行
- [ ] 手動テストを実施

## スクリーンショット（UI変更の場合）
<!-- スクリーンショットを添付 -->

## チェックリスト
- [ ] コードはRuffでフォーマット済み
- [ ] 型チェック（pyright）をパス
- [ ] テストがすべて成功
- [ ] ドキュメントを更新（必要な場合）
```

## 開発フロー

### 1. Issue作成

```bash
# GitHub CLIを使用
gh issue create --title "機能: XXXを実装" --body "詳細説明"
```

### 2. ブランチ作成

```bash
# 最新のmainを取得
git checkout main
git pull origin main

# featureブランチを作成
git checkout -b feature/issue-123-implement-xxx
```

### 3. 開発

```bash
# 開発作業
# ...

# フォーマット
docker compose exec sagebase uv run ruff format .

# リント
docker compose exec sagebase uv run ruff check . --fix

# 型チェック
uv run pyright
```

### 4. テスト

```bash
# ユニットテスト実行
docker compose exec sagebase uv run pytest

# カバレッジ測定
docker compose exec sagebase uv run pytest --cov=src --cov-report=html
```

### 5. コミット

```bash
# 変更を確認
git status
git diff

# ステージング
git add .

# コミット
git commit -m "feat: XXX機能を実装"
```

### 6. Push & PR作成

```bash
# リモートにpush
git push -u origin feature/issue-123-implement-xxx

# PR作成
gh pr create --title "Feature: XXX機能の実装" --body "..."
```

## デバッグ方法

### ログ設定

```python
import logging
from src.utils.logger import get_logger

# ロガーの取得
logger = get_logger(__name__)

# ログレベルの設定
logger.setLevel(logging.DEBUG)

# ログ出力
logger.debug("デバッグ情報: %s", variable)
logger.info("処理開始: meeting_id=%d", meeting_id)
logger.warning("警告: データが見つかりません")
logger.error("エラー発生: %s", str(e))
```

### デバッガー使用

#### VS Code デバッグ設定

`.vscode/launch.json`:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: Docker Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

#### デバッグコード挿入

```python
# ブレークポイント設定
import pdb; pdb.set_trace()

# IPython デバッガー（より高機能）
from IPython import embed; embed()

# VS Code デバッガー接続
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

### SQLデバッグ

```python
# SQLAlchemyのクエリログ有効化
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# クエリの確認
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL, echo=True)
```

## パフォーマンス最適化

### プロファイリング

```python
import cProfile
import pstats
from io import StringIO

def profile_function(func):
    """関数のプロファイリングデコレータ"""
    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        profiler.enable()

        result = func(*args, **kwargs)

        profiler.disable()
        stream = StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(10)

        print(stream.getvalue())
        return result

    return wrapper

# 使用例
@profile_function
async def slow_function():
    # 処理
    pass
```

### メモリ最適化

```python
# メモリプロファイリング
from memory_profiler import profile

@profile
def memory_intensive_function():
    # 大量のデータを扱う処理
    pass

# ジェネレータの活用
def process_large_data():
    # Bad: 全データをメモリに載せる
    data = [process(item) for item in large_list]

    # Good: ジェネレータで逐次処理
    for item in large_list:
        yield process(item)
```

### データベース最適化

```python
# N+1問題の回避
from sqlalchemy.orm import selectinload

# Bad: N+1クエリ
meetings = session.query(Meeting).all()
for meeting in meetings:
    print(meeting.conversations)  # 各meetingごとにクエリ発行

# Good: Eager Loading
meetings = session.query(Meeting)\
    .options(selectinload(Meeting.conversations))\
    .all()

# バルクインサート
# Bad: 個別にインサート
for item in items:
    session.add(Item(**item))
    session.commit()

# Good: バルクインサート
session.bulk_insert_mappings(Item, items)
session.commit()
```

### 非同期処理の活用

```python
import asyncio
from typing import List

async def process_items(items: List[int]) -> List[str]:
    """並列処理の例"""
    # Bad: 逐次処理
    results = []
    for item in items:
        result = await process_single_item(item)
        results.append(result)

    # Good: 並列処理
    tasks = [process_single_item(item) for item in items]
    results = await asyncio.gather(*tasks)

    return results
```

## セキュリティガイドライン

### 機密情報の管理

#### 環境変数

```python
import os
from dotenv import load_dotenv

# .envファイルから読み込み
load_dotenv()

# 環境変数の取得（デフォルト値付き）
API_KEY = os.getenv('GOOGLE_API_KEY', '')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://...')

# 必須環境変数のチェック
if not API_KEY:
    raise ValueError("GOOGLE_API_KEY is required")
```

#### シークレット管理

```bash
# .gitignoreに追加
.env
.env.local
*.key
*.pem
credentials.json
```

### SQLインジェクション対策

```python
# Bad: 文字列連結
query = f"SELECT * FROM users WHERE name = '{user_input}'"

# Good: パラメータバインディング
query = "SELECT * FROM users WHERE name = :name"
result = session.execute(query, {"name": user_input})

# SQLAlchemy ORM使用（推奨）
user = session.query(User).filter(User.name == user_input).first()
```

### XSS対策

```python
# Streamlitは自動的にHTMLをエスケープ
st.write(user_input)  # 安全

# HTMLを表示する場合は注意
import html
safe_html = html.escape(user_input)
st.markdown(safe_html, unsafe_allow_html=True)
```

### 認証・認可

```python
from functools import wraps
from typing import Callable

def require_auth(func: Callable) -> Callable:
    """認証が必要なエンドポイントのデコレータ"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 認証チェック
        if not is_authenticated():
            raise UnauthorizedException("認証が必要です")

        return await func(*args, **kwargs)

    return wrapper

# 使用例
@require_auth
async def protected_endpoint():
    # 保護されたリソースへのアクセス
    pass
```

### ログのサニタイズ

```python
import re

def sanitize_log(message: str) -> str:
    """ログメッセージから機密情報を除去"""
    # APIキーのマスク
    message = re.sub(r'api[_-]?key["\']?\s*[:=]\s*["\']?[\w-]+',
                     'api_key=***', message, flags=re.IGNORECASE)

    # パスワードのマスク
    message = re.sub(r'password["\']?\s*[:=]\s*["\']?[^"\s]+',
                     'password=***', message, flags=re.IGNORECASE)

    return message

# 使用例
logger.info(sanitize_log(f"API call with key={api_key}"))
```

## トラブルシューティング

### よくある問題と解決方法

#### Docker関連

```bash
# コンテナが起動しない
docker compose logs sagebase
docker compose down
docker compose up -d --build

# ポート競合
# docker-compose.override.ymlで別ポートを指定
# または既存のプロセスを停止
lsof -i :8501
kill -9 <PID>
```

#### データベース関連

```bash
# 接続エラー
# DATABASE_URLを確認
docker compose exec sagebase python -c "from src.config.database import test_connection; test_connection()"

# マイグレーションエラー
./reset-database.sh
```

#### 依存関係

```bash
# パッケージの競合
uv sync --force-reinstall

# キャッシュクリア
rm -rf .uv_cache
uv sync
```

## 関連ドキュメント

- [アーキテクチャ概要](../architecture/README.md)
- [Clean Architecture詳細](../architecture/clean-architecture.md)
- [テストガイド](./testing.md)
- [デプロイメントガイド](./deployment.md)
- [トラブルシューティング](../troubleshooting/README.md)
