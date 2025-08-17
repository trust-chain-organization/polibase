# Dependency Injection Container Guide

## 概要

Polibaseプロジェクトに`dependency-injector`ライブラリを使用したDIコンテナを導入しました。これによりクリーンアーキテクチャの依存関係管理が改善され、テスト容易性と保守性が向上します。

## 実装内容

### 1. DIコンテナ構造

```
src/infrastructure/di/
├── __init__.py
├── container.py      # メインコンテナ（ApplicationContainer）
└── providers.py      # 各種プロバイダー定義
```

### 2. コンテナ階層

- **ApplicationContainer**: メインコンテナ
  - **DatabaseContainer**: データベース関連（エンジン、セッション）
  - **RepositoryContainer**: リポジトリ実装
  - **ServiceContainer**: 外部サービス実装（LLM、Storage、WebScraper）
  - **UseCaseContainer**: ユースケース実装

### 3. 環境別設定

3つの環境に対応した設定が可能：

- **Development**: 開発環境（デフォルト設定、APIキー不要）
- **Testing**: テスト環境（SQLite、モックサービス）
- **Production**: 本番環境（厳密な設定検証）

## 使用方法

### 基本的な使い方

```python
from src.infrastructure.di.container import init_container

# コンテナの初期化
container = init_container(environment="development")

# リポジトリの取得
speaker_repo = container.repositories.speaker_repository()

# サービスの取得
llm_service = container.services.llm_service()

# ユースケースの取得
process_minutes = container.use_cases.process_minutes_usecase()
```

### CLIコマンドでの使用例

```python
@click.command()
def my_command():
    # コンテナの初期化
    container = init_container()

    # 依存関係の取得
    use_case = container.use_cases.process_minutes_usecase()

    # 実行
    result = await use_case.execute(input_dto)
```

### テストでの使用

```python
def test_my_feature():
    # テスト環境用コンテナ
    container = ApplicationContainer.create_for_environment(Environment.TESTING)

    # モックの注入も可能
    with patch.object(container.services, 'llm_service') as mock_llm:
        mock_llm.return_value = MockLLMService()
        # テスト実行
```

## サンプルコマンド

DIコンテナを使用したサンプルCLIコマンドを実装しました：

```bash
# DIコンテナ情報を表示
polibase show-container-info

# ヘルスチェック
polibase health-check-with-di --check-db --check-llm --check-storage

# 議事録処理（DI使用版）
polibase process-minutes-with-di --meeting-id 123

# 政治家情報スクレイピング（DI使用版）
polibase scrape-politicians-with-di --all-parties
```

## 移行ガイド

### 既存コードの移行

1. **リポジトリの移行**
   ```python
   # Before
   engine = create_engine(DATABASE_URL)
   session = sessionmaker(bind=engine)()
   speaker_repo = SpeakerRepositoryImpl(session)

   # After
   container = get_container()
   speaker_repo = container.repositories.speaker_repository()
   ```

2. **サービスの移行**
   ```python
   # Before
   llm_service = GeminiLLMService(api_key=GOOGLE_API_KEY)

   # After
   container = get_container()
   llm_service = container.services.llm_service()
   ```

3. **ユースケースの移行**
   ```python
   # Before
   use_case = ProcessMinutesUseCase(
       meeting_repo=meeting_repo,
       conversation_repo=conversation_repo,
       speaker_repo=speaker_repo,
       llm_service=llm_service,
       storage_service=storage_service
   )

   # After
   container = get_container()
   use_case = container.use_cases.process_minutes_usecase()
   ```

## 利点

1. **依存関係の明確化**: すべての依存関係が一箇所で管理される
2. **テストの容易化**: モックの注入が簡単
3. **設定の一元管理**: 環境別設定が統一的に管理される
4. **コードの保守性向上**: 依存関係の変更が容易
5. **シングルトンパターンの統一**: DIコンテナがライフサイクルを管理

## 今後の課題

1. **既存コードの完全移行**: すべてのコマンドとサービスをDIコンテナを使用するように移行
2. **パフォーマンス最適化**: 遅延初期化の活用
3. **より詳細なテスト**: 統合テストの充実
4. **ドキュメントの充実**: 各コンテナの詳細な使用方法

## 関連ファイル

- `src/infrastructure/di/container.py`: メインコンテナ
- `src/infrastructure/di/providers.py`: プロバイダー定義
- `src/cli_package/commands/di_example_commands.py`: 使用例
- `tests/infrastructure/di/test_container.py`: テストコード
