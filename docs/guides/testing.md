# テストガイド

## 目次
- [テスト戦略](#テスト戦略)
- [テストの書き方](#テストの書き方)
- [モックの使い方](#モックの使い方)
- [カバレッジ目標](#カバレッジ目標)
- [CI/CDでのテスト](#cicdでのテスト)

## テスト戦略

### テストピラミッド

```
        E2Eテスト
       /    5%    \
      /            \
     統合テスト
    /    20%      \
   /              \
  ユニットテスト
 /     75%        \
```

### テストの種類

| 種類 | 目的 | ツール | 実行時間 |
|------|------|--------|----------|
| ユニットテスト | 個別機能の検証 | pytest | 高速（<1秒） |
| 統合テスト | 複数コンポーネントの連携 | pytest + Docker | 中速（1-10秒） |
| E2Eテスト | エンドツーエンドのシナリオ | Playwright | 低速（>10秒） |

## テストの書き方

### ユニットテスト

```python
# tests/domain/services/test_politician_domain_service.py
import pytest
from src.domain.services.politician_domain_service import PoliticianDomainService
from src.domain.entities.politician import Politician

class TestPoliticianDomainService:
    """政治家ドメインサービスのテスト"""

    @pytest.fixture
    def service(self):
        """テスト用サービスインスタンス"""
        return PoliticianDomainService()

    def test_normalize_name_removes_honorifics(self, service):
        """敬称が除去されることを確認"""
        # Arrange
        name_with_honorific = "山田太郎議員"

        # Act
        normalized = service.normalize_name(name_with_honorific)

        # Assert
        assert normalized == "山田太郎"

    def test_calculate_similarity_same_name(self, service):
        """同名の政治家の類似度が高いことを確認"""
        # Arrange
        politician1 = Politician(name="山田太郎", political_party_id=1)
        politician2 = Politician(name="山田太郎", political_party_id=1)

        # Act
        similarity = service.calculate_similarity(politician1, politician2)

        # Assert
        assert similarity >= 0.8
```

### 統合テスト

```python
# tests/application/usecases/test_process_minutes_usecase.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.application.usecases.process_minutes_usecase import ProcessMinutesUseCase
from src.application.dtos.process_minutes_dto import ProcessMinutesInputDto

@pytest.mark.asyncio
class TestProcessMinutesUseCase:
    """議事録処理ユースケースの統合テスト"""

    @pytest.fixture
    async def use_case(self):
        """モックを使用したユースケース"""
        meeting_repo = AsyncMock()
        minutes_repo = AsyncMock()
        minutes_service = MagicMock()
        llm_service = AsyncMock()

        return ProcessMinutesUseCase(
            meeting_repo=meeting_repo,
            minutes_repo=minutes_repo,
            minutes_service=minutes_service,
            llm_service=llm_service
        )

    async def test_process_new_meeting(self, use_case):
        """新規会議の処理が成功することを確認"""
        # Arrange
        input_dto = ProcessMinutesInputDto(meeting_id=123)
        use_case.meeting_repo.find_by_id.return_value = MagicMock(
            id=123,
            gcs_text_uri="gs://bucket/text.txt"
        )
        use_case.minutes_repo.find_by_meeting_id.return_value = None
        use_case.llm_service.extract_conversations.return_value = [
            {"speaker": "山田", "comment": "発言内容"}
        ]

        # Act
        result = await use_case.execute(input_dto)

        # Assert
        assert result.success is True
        assert result.conversation_count == 1
        use_case.meeting_repo.find_by_id.assert_called_once_with(123)
```

### データベーステスト

```python
# tests/infrastructure/persistence/test_politician_repository.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.politician_repository import PoliticianRepositoryImpl
from src.domain.entities.politician import Politician

@pytest.mark.asyncio
class TestPoliticianRepository:
    """政治家リポジトリのデータベーステスト"""

    @pytest.fixture
    async def repository(self, db_session: AsyncSession):
        """テスト用リポジトリ"""
        return PoliticianRepositoryImpl(db_session)

    async def test_save_and_find_by_id(self, repository):
        """保存と取得が正しく動作することを確認"""
        # Arrange
        politician = Politician(name="テスト太郎", political_party_id=1)

        # Act
        saved = await repository.save(politician)
        found = await repository.find_by_id(saved.id)

        # Assert
        assert found is not None
        assert found.name == "テスト太郎"
        assert found.political_party_id == 1
```

## モックの使い方

### 外部サービスのモック

```python
# tests/mocks/llm_service_mock.py
from typing import List, Dict, Any
from src.infrastructure.interfaces.llm_service import ILLMService

class MockLLMService(ILLMService):
    """テスト用のLLMサービスモック"""

    def __init__(self, responses: Dict[str, Any] = None):
        self.responses = responses or {}
        self.call_count = 0

    async def extract_conversations(self, text: str) -> List[Dict[str, Any]]:
        """固定レスポンスを返す"""
        self.call_count += 1
        return self.responses.get("extract_conversations", [
            {"speaker": "モック発言者", "comment": "モック発言内容"}
        ])

    async def match_speaker(self, speaker_name: str, candidates: List[str]) -> str:
        """最初の候補を返す"""
        return candidates[0] if candidates else speaker_name
```

### pytest-mockの使用

```python
import pytest
from unittest.mock import patch, MagicMock

@pytest.mark.asyncio
async def test_with_mock(mocker):
    """pytest-mockを使用したテスト"""
    # モックの作成
    mock_service = mocker.patch('src.services.some_service.SomeService')
    mock_service.return_value.process.return_value = "processed"

    # テスト実行
    result = await function_under_test()

    # アサーション
    assert result == "expected"
    mock_service.return_value.process.assert_called_once()
```

### 環境変数のモック

```python
import os
import pytest

@pytest.fixture
def mock_env(monkeypatch):
    """環境変数のモック"""
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    yield
    # クリーンアップは自動
```

## カバレッジ目標

### 目標カバレッジ率

| 層 | 目標 | 現状 | 優先度 |
|----|------|------|--------|
| Domain層 | 90% | - | 高 |
| Application層 | 85% | - | 高 |
| Infrastructure層 | 70% | - | 中 |
| Interfaces層 | 60% | - | 低 |
| 全体 | 80% | - | - |

### カバレッジ測定

```bash
# カバレッジ測定
docker compose exec polibase uv run pytest --cov=src --cov-report=term-missing

# HTMLレポート生成
docker compose exec polibase uv run pytest --cov=src --cov-report=html

# 特定モジュールのカバレッジ
docker compose exec polibase uv run pytest --cov=src.domain tests/domain/
```

### カバレッジ設定

`pyproject.toml`:
```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*.py",
    "*/__init__.py",
    "*/migrations/*"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:"
]
precision = 2
show_missing = true
skip_covered = false
```

## CI/CDでのテスト

### GitHub Actions設定

`.github/workflows/test.yml`:
```yaml
name: Test

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install UV
        run: pip install uv

      - name: Install dependencies
        run: uv sync

      - name: Run linting
        run: |
          uv run ruff check .
          uv run ruff format . --check

      - name: Run type checking
        run: uv run pyright

      - name: Run tests
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost/test_db
          GOOGLE_API_KEY: test-key
        run: |
          uv run pytest --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

### テスト自動実行

```bash
# pre-commitフック
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: pytest
        entry: docker compose exec -T polibase uv run pytest
        language: system
        pass_filenames: false
        always_run: true
```

## テストのベストプラクティス

### テストの原則

1. **FIRST原則**
   - **F**ast: 高速に実行
   - **I**ndependent: 独立して実行可能
   - **R**epeatable: 再現可能
   - **S**elf-validating: 自己検証可能
   - **T**imely: タイムリーに作成

2. **AAA パターン**
   - **A**rrange: 準備
   - **A**ct: 実行
   - **A**ssert: 検証

### テストの命名

```python
def test_<対象>_<条件>_<期待結果>():
    """
    例:
    - test_normalize_name_with_honorific_returns_clean_name
    - test_process_minutes_when_already_processed_returns_cached
    - test_save_politician_with_invalid_data_raises_exception
    """
    pass
```

### フィクスチャの活用

```python
# conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture(scope="session")
async def db_engine():
    """テスト用データベースエンジン"""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture
async def db_session(db_engine):
    """テスト用データベースセッション"""
    async with AsyncSession(db_engine) as session:
        yield session
        await session.rollback()
```

## トラブルシューティング

### よくあるテストエラー

#### 非同期テストのエラー
```python
# 問題: RuntimeError: This event loop is already running
# 解決: pytest-asyncioを使用
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result == expected
```

#### モックが効かない
```python
# 問題: モックが適用されない
# 解決: 正しいパスを指定
@patch('src.module.ClassName')  # インポート元ではなく使用場所
def test_with_mock(mock_class):
    pass
```

#### データベーステストの分離
```python
# 問題: テスト間でデータが共有される
# 解決: トランザクションロールバック
@pytest.fixture
async def isolated_db_session(db_session):
    async with db_session.begin():
        yield db_session
        await db_session.rollback()
```

## 関連ドキュメント

- [開発ガイド](./development.md)
- [デプロイメントガイド](./deployment.md)
- [CI/CDガイド](../CI_CD_ENHANCEMENTS.md)
- [トラブルシューティング](../troubleshooting/README.md)
