# リポジトリ移行ガイド

このドキュメントは、レガシーリポジトリ（`src/database/`）から新しいClean Architecture実装（`src/infrastructure/persistence/`）への移行方法を説明します。

## 概要

### 現在の状況
- **レガシー実装**: `src/database/` - 同期的な実装、`BaseRepository`を継承
- **新実装**: `src/infrastructure/persistence/` - 非同期実装、Clean Architecture準拠

### 移行戦略
1. 新しい非同期リポジトリ実装を作成
2. `RepositoryAdapter`を使用して既存コードから利用可能にする
3. 段階的に参照を新実装に切り替える
4. 最終的にレガシーコードを削除

## ステップバイステップガイド

### Step 1: 新リポジトリ実装の作成

`src/infrastructure/persistence/`に新しいリポジトリ実装を作成します。

```python
# src/infrastructure/persistence/example_repository_impl.py
from typing import Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

class ExampleRepositoryImpl:
    """新しい非同期リポジトリ実装"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, entity_id: int) -> Optional[dict[str, Any]]:
        """IDでエンティティを取得"""
        query = text("SELECT * FROM examples WHERE id = :id")
        result = await self.session.execute(query, {"id": entity_id})
        row = result.fetchone()
        return dict(row._mapping) if row else None

    async def create(self, data: dict[str, Any]) -> int:
        """新しいエンティティを作成"""
        # 実装...
        pass
```

### Step 2: アダプターを使用した統合

既存のレガシーコードから新実装を使用するには、`RepositoryAdapter`を使用します。

```python
# src/database/example_repository.py (レガシー)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.example_repository_impl import ExampleRepositoryImpl

class ExampleRepository(BaseRepository):
    """レガシーリポジトリ（移行期間中のファサード）"""

    def __init__(self, session: Session | None = None):
        super().__init__(use_session=True, session=session)
        # アダプター経由で新実装を使用
        self._impl = RepositoryAdapter(ExampleRepositoryImpl, session)

    def get_by_id(self, entity_id: int) -> dict[str, Any] | None:
        """既存のインターフェースを維持しつつ新実装を使用"""
        return self._impl.get_by_id(entity_id)
```

### Step 3: テストの作成

新実装のテストを作成します。

```python
# tests/infrastructure/persistence/test_example_repository_impl.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.persistence.example_repository_impl import ExampleRepositoryImpl

@pytest.mark.asyncio
async def test_get_by_id(async_session: AsyncSession):
    """get_by_idのテスト"""
    repo = ExampleRepositoryImpl(async_session)

    # テストデータを準備
    # ...

    result = await repo.get_by_id(1)
    assert result is not None
    assert result["id"] == 1
```

アダプターのテスト：

```python
# tests/integration/test_example_adapter.py
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.example_repository_impl import ExampleRepositoryImpl

def test_adapter_sync_call():
    """アダプター経由での同期呼び出しテスト"""
    adapter = RepositoryAdapter(ExampleRepositoryImpl)

    # 同期コンテキストから非同期メソッドを呼び出せることを確認
    try:
        result = adapter.get_by_id(1)
    except Exception as e:
        # DB接続エラーは許容（アダプター自体のエラーでないことを確認）
        assert "database" in str(e).lower()
```

### Step 4: 段階的な移行

1. **初期段階**: レガシーリポジトリ内でアダプター経由で新実装を使用
2. **中間段階**: 呼び出し元を新実装に直接切り替え（非同期化）
3. **最終段階**: レガシーコードを削除

## RepositoryAdapterの仕組み

`RepositoryAdapter`は同期コードから非同期リポジトリを使用するためのブリッジです。

### 主な機能
- 非同期メソッドを同期的に呼び出し可能にする
- イベントループの管理を自動化
- エラーハンドリングの統一

### 使用例

```python
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.monitoring_repository_impl import MonitoringRepositoryImpl

# アダプターの作成
adapter = RepositoryAdapter(MonitoringRepositoryImpl)

# 同期コンテキストから非同期メソッドを呼び出し
metrics = adapter.get_overall_metrics()  # 内部でasyncioを処理

# コンテキストマネージャーとしても使用可能
with RepositoryAdapter(MonitoringRepositoryImpl) as adapter:
    data = adapter.get_recent_activities(limit=10)
```

## 注意事項

### パフォーマンス
- アダプター経由の呼び出しは、同期・非同期の変換によるオーバーヘッドがある
- 最終的には呼び出し元も非同期化することを推奨

### エラーハンドリング
- データベース接続エラーは適切に伝播される
- 非同期関連のエラーはアダプター内で処理される

### トランザクション管理
- 新実装では非同期セッションを使用
- トランザクション境界に注意が必要

## チェックリスト

リポジトリを移行する際のチェックリスト：

- [ ] 新リポジトリ実装の作成（`src/infrastructure/persistence/`）
- [ ] すべての既存メソッドをカバー
- [ ] エンティティ・モデル間の変換実装
- [ ] アダプターを使用したレガシーコードの更新
- [ ] ユニットテストの作成
- [ ] 統合テストの作成
- [ ] パフォーマンステスト
- [ ] ドキュメントの更新
- [ ] 段階的な移行計画の策定

## トラブルシューティング

### よくある問題

#### 1. "Event loop is already running"エラー
**原因**: Jupyterなどの環境で既にイベントループが動作している
**解決**: `RepositoryAdapter`が自動的に処理するが、必要に応じて別スレッドで実行

#### 2. 非同期セッションの作成エラー
**原因**: データベースURLが非同期ドライバに対応していない
**解決**: `postgresql://` を `postgresql+asyncpg://` に変更

#### 3. パフォーマンスの劣化
**原因**: 同期・非同期の変換オーバーヘッド
**解決**: 呼び出し元も非同期化を検討

## 参考資料

- [Clean Architecture移行ガイド](./CLEAN_ARCHITECTURE_MIGRATION.md)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
