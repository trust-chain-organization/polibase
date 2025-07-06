# Clean Architecture 移行ガイド

## 概要

このドキュメントは、Polibaseプロジェクトを現在の機能ベースのアーキテクチャからClean Architectureへ移行するためのガイドラインです。

## 新しいアーキテクチャ構造

```
src/
├── domain/              # ドメイン層（ビジネスロジック）
│   ├── entities/        # エンティティ（ビジネスオブジェクト）
│   ├── repositories/    # リポジトリインターフェース
│   └── services/        # ドメインサービス
├── application/         # アプリケーション層（ユースケース）
│   ├── usecases/        # ユースケース実装
│   ├── dtos/            # データ転送オブジェクト
│   └── handlers/        # コマンドハンドラー
├── infrastructure/      # インフラストラクチャ層（外部との連携）
│   ├── persistence/     # データベース実装
│   ├── external/        # 外部サービス（LLM、GCS等）
│   └── web/             # Web関連
└── interfaces/          # インターフェース層（エントリーポイント）
    ├── cli/             # CLIコマンド
    └── web/             # Web UI（Streamlit）
```

## 層の責務

### 1. ドメイン層 (Domain Layer)
- **責務**: ビジネスロジックとビジネスルールの実装
- **依存**: 他の層に依存しない
- **含まれるもの**:
  - エンティティ（Politician、Speaker、Meeting等）
  - リポジトリインターフェース
  - ドメインサービス（SpeakerDomainService等）

### 2. アプリケーション層 (Application Layer)
- **責務**: ユースケースの実装とビジネスフローの調整
- **依存**: ドメイン層のみ
- **含まれるもの**:
  - ユースケース（ProcessMinutesUseCase等）
  - DTO（データ転送オブジェクト）
  - アプリケーションサービス

### 3. インフラストラクチャ層 (Infrastructure Layer)
- **責務**: 外部システムとの連携実装
- **依存**: ドメイン層、アプリケーション層
- **含まれるもの**:
  - リポジトリ実装（SQLAlchemy使用）
  - 外部サービスアダプター（Gemini API、GCS等）
  - データベース設定

### 4. インターフェース層 (Interfaces Layer)
- **責務**: ユーザーインターフェースとエントリーポイント
- **依存**: すべての層
- **含まれるもの**:
  - CLIコマンド実装
  - Streamlit UI
  - APIエンドポイント（将来的に）

## 移行手順

### Phase 1: 基本構造の作成（完了）
1. ✅ ディレクトリ構造の作成
2. ✅ ドメインエンティティの定義
3. ✅ リポジトリインターフェースの定義
4. ✅ ドメインサービスの実装
5. ✅ 基本的なユースケースの実装

### Phase 2: 既存コードの移行（進行中）
1. 既存のリポジトリをインフラストラクチャ層へ移行
2. 外部サービス（LLM、GCS）のアダプター作成
3. CLIコマンドをインターフェース層へ移行
4. Streamlit UIをインターフェース層へ移行

### Phase 3: 依存関係の整理
1. 各層の依存関係を確認・修正
2. DIコンテナの導入検討
3. 設定管理の統一

### Phase 4: テストとドキュメント
1. 各層のユニットテスト作成
2. 統合テストの更新
3. アーキテクチャドキュメントの作成

## 移行時の注意点

### 1. 段階的な移行
- 一度にすべてを移行せず、機能単位で段階的に移行
- 既存の機能を維持しながら新しい構造へ移行
- テストを書きながら移行を進める

### 2. 依存関係の方向
- 内側の層（ドメイン）は外側の層に依存しない
- 依存性は常に内向き（外側→内側）
- インターフェースを使用して依存関係を逆転

### 3. 命名規則
- エンティティ: 単数形（例: Speaker, Politician）
- リポジトリ: エンティティ名 + Repository（例: SpeakerRepository）
- ユースケース: 動詞 + 名詞 + UseCase（例: ProcessMinutesUseCase）
- DTO: 用途 + DTO（例: CreateSpeakerDTO）

## 実装例

### エンティティの例
```python
# src/domain/entities/speaker.py
from src.domain.entities.base import BaseEntity

class Speaker(BaseEntity):
    def __init__(self, name: str, ...):
        super().__init__()
        self.name = name
        # ...
```

### リポジトリインターフェースの例
```python
# src/domain/repositories/speaker_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from src.domain.entities.speaker import Speaker

class SpeakerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: int) -> Optional[Speaker]:
        pass
```

### ユースケースの例
```python
# src/application/usecases/match_speakers_usecase.py
class MatchSpeakersUseCase:
    def __init__(self, speaker_repo: SpeakerRepository, ...):
        self.speaker_repo = speaker_repo

    async def execute(self, ...):
        # ビジネスロジックの実装
```

### リポジトリ実装の例
```python
# src/infrastructure/persistence/speaker_repository_impl.py
from src.domain.repositories.speaker_repository import SpeakerRepository

class SpeakerRepositoryImpl(SpeakerRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int) -> Optional[Speaker]:
        # SQLAlchemyを使用した実装
```

## 移行チェックリスト

### ドメイン層
- [ ] すべてのエンティティを定義
- [ ] リポジトリインターフェースを定義
- [ ] ドメインサービスを実装
- [ ] ビジネスルールをドメイン層に集約

### アプリケーション層
- [ ] 主要なユースケースを実装
- [ ] DTOを定義
- [ ] ユースケース間の調整ロジックを実装

### インフラストラクチャ層
- [ ] リポジトリ実装を移行
- [ ] 外部サービスアダプターを作成
- [ ] データベース設定を移行

### インターフェース層
- [ ] CLIコマンドを移行
- [ ] Streamlit UIを移行
- [ ] エントリーポイントを整理

## トラブルシューティング

### 循環参照エラー
- 依存関係の方向を確認
- インターフェースを使用して依存関係を逆転

### インポートエラー
- 相対インポートではなく絶対インポートを使用
- `src.domain.entities.speaker` のような形式で記述

### 既存コードとの互換性
- 移行期間中は両方の構造を維持
- ファサードパターンを使用して既存コードから新しい構造を呼び出す

## 今後の拡張

1. **DIコンテナの導入**
   - 依存性注入の自動化
   - テストの容易化

2. **イベント駆動アーキテクチャ**
   - ドメインイベントの導入
   - 非同期処理の改善

3. **CQRSパターン**
   - 読み取りと書き込みの分離
   - パフォーマンスの最適化

## 参考資料

- [Clean Architecture by Robert C. Martin](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain-Driven Design by Eric Evans](https://domainlanguage.com/ddd/)
- [Implementing Domain-Driven Design by Vaughn Vernon](https://www.amazon.com/Implementing-Domain-Driven-Design-Vaughn-Vernon/dp/0321834577)
