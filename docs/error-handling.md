# エラーハンドリングガイド

## 概要

Polibaseアプリケーションでは、一貫性のあるエラー処理を実現するために、カスタム例外階層を定義しています。このガイドでは、例外の使い方と各レイヤーでのエラーハンドリングのベストプラクティスを説明します。

## 例外階層

### 基底例外
```python
PolibaseError(message: str, details: dict | None = None)
```
- すべてのカスタム例外の基底クラス
- `message`: エラーメッセージ
- `details`: エラーの詳細情報を含む辞書

### 主要な例外カテゴリ

#### 1. 設定関連 (Configuration)
```python
ConfigurationError
├── MissingConfigError  # 必須設定が見つからない
└── InvalidConfigError  # 設定値が無効
```

#### 2. データベース関連 (Database)
```python
DatabaseError
├── ConnectionError       # データベース接続エラー
├── QueryError           # クエリ実行エラー
├── IntegrityError       # 整合性制約違反
├── RecordNotFoundError  # レコードが見つからない
└── DuplicateRecordError # 重複レコード
```

#### 3. 処理関連 (Processing)
```python
ProcessingError
├── PDFProcessingError   # PDF処理エラー
├── TextExtractionError  # テキスト抽出エラー
└── ParsingError        # パースエラー
```

#### 4. LLM関連
```python
LLMError
├── APIKeyError          # APIキーエラー
├── ModelError          # モデルエラー
├── TokenLimitError     # トークン制限超過
└── ResponseParsingError # レスポンスパースエラー
```

#### 5. Web スクレイピング関連
```python
ScrapingError
├── URLError             # URL関連エラー
├── PageLoadError       # ページ読み込みエラー
├── ElementNotFoundError # 要素が見つからない
└── DownloadError       # ダウンロードエラー
```

#### 6. ストレージ関連
```python
StorageError
├── FileNotFoundError    # ファイルが見つからない
├── UploadError         # アップロードエラー
└── PermissionError     # 権限エラー
```

#### 7. バリデーション関連
```python
ValidationError
├── DataValidationError  # データバリデーションエラー
└── SchemaValidationError # スキーマバリデーションエラー
```

#### 8. リポジトリ関連
```python
RepositoryError
├── SaveError           # 保存エラー
├── UpdateError         # 更新エラー
└── DeleteError         # 削除エラー
```

## 各レイヤーでの使用方法

### 1. データベース層（Repository）

```python
from sqlalchemy.exc import IntegrityError as SQLIntegrityError
from sqlalchemy.exc import SQLAlchemyError

from src.exceptions import (
    DatabaseError,
    DuplicateRecordError,
    RecordNotFoundError,
    SaveError,
)

class PoliticianRepository:
    def create_politician(self, politician: PoliticianCreate) -> Politician | None:
        try:
            # データベース操作
            politician_id = self.insert_model("politicians", politician, "id")
            return self.get_by_id(politician_id)
        except SQLIntegrityError as e:
            logger.error(f"Integrity error creating politician: {e}")
            raise DuplicateRecordError("Politician", politician.name) from e
        except SQLAlchemyError as e:
            logger.error(f"Database error creating politician: {e}")
            raise DatabaseError(
                f"Failed to create politician: {politician.name}",
                {"error": str(e), "politician_data": politician.model_dump()},
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error creating politician: {e}")
            raise SaveError(
                f"Unexpected error creating politician: {politician.name}",
                {"error": str(e)},
            ) from e
```

### 2. サービス層

```python
from src.exceptions import DatabaseError, LLMError, QueryError

class SpeakerMatchingService:
    def find_best_match(self, speaker_name: str) -> SpeakerMatch:
        try:
            # LLM処理
            match_result = self._llm_matching(speaker_name)
            return match_result
        except LLMError:
            # LLM固有のエラーは再スロー
            raise
        except Exception as e:
            logger.error(f"Unexpected error during matching: {e}")
            raise LLMError(
                "Unexpected error during LLM matching",
                {"speaker_name": speaker_name, "error": str(e)},
            ) from e
```

### 3. Web層（Streamlit）

```python
from src.exceptions import (
    DatabaseError,
    RecordNotFoundError,
    SaveError,
    UpdateError,
)

try:
    meeting_id = repo.create_meeting(
        conference_id=conference_id,
        meeting_date=meeting_date,
        url=url,
    )
    st.success(f"会議を登録しました (ID: {meeting_id})")
except (SaveError, DatabaseError) as e:
    st.error(f"会議の登録に失敗しました: {str(e)}")
except Exception as e:
    st.error(f"予期しないエラーが発生しました: {str(e)}")
```

### 4. CLI層（Click）

CLIコマンドでは、`@with_error_handling`デコレータを使用して、統一されたエラーハンドリングを実現しています：

```python
@click.command()
@with_error_handling
def my_command():
    # コマンド実装
    pass
```

エラーハンドラーは異なる例外タイプに対して適切な終了コードを返します：

| 例外タイプ | 終了コード | 説明 |
|-----------|------------|------|
| APIKeyError | 2 | API キーが未設定 |
| ConfigurationError | 2 | 設定エラー |
| ConnectionError | 3 | 接続エラー |
| RecordNotFoundError | 4 | レコードが見つからない |
| ValidationError | 5 | バリデーションエラー |
| DatabaseError | 10 | データベースエラー |
| ScrapingError | 11 | スクレイピングエラー |
| ProcessingError | 12 | 処理エラー |
| LLMError | 13 | LLMエラー |
| StorageError | 14 | ストレージエラー |
| その他のPolibaseError | 1 | 一般的なエラー |
| 予期しないエラー | 99 | 未処理の例外 |

## ベストプラクティス

### 1. 詳細情報の提供

```python
# 良い例
raise RecordNotFoundError("Meeting", meeting_id)

# より良い例
raise DatabaseError(
    "Failed to create meeting",
    {
        "conference_id": conference_id,
        "date": meeting_date,
        "error": str(e)
    }
) from e
```

### 2. 例外チェーン

元の例外情報を保持するために、`from e`を使用します：

```python
try:
    # 何かの処理
except SQLAlchemyError as e:
    raise DatabaseError("Operation failed") from e
```

### 3. 適切なログ記録

例外を発生させる前に、エラーログを記録します：

```python
except SQLAlchemyError as e:
    logger.error(f"Database error: {e}")
    raise DatabaseError(...) from e
```

### 4. 特定の例外を優先

一般的な`Exception`よりも、特定の例外タイプを使用します：

```python
# 避けるべき
except Exception as e:
    raise Exception(f"Error: {e}")

# 推奨
except SQLIntegrityError as e:
    raise DuplicateRecordError(...) from e
except SQLAlchemyError as e:
    raise DatabaseError(...) from e
```

### 5. トランザクション管理

データベース操作では、エラー時にロールバックを実行します：

```python
try:
    # データベース操作
    session.commit()
except Exception as e:
    session.rollback()
    logger.error(f"Transaction failed: {e}")
    raise DatabaseError(...) from e
```

## テスト

例外処理のテストは`tests/test_exceptions.py`で実装されています。新しい例外を追加する場合は、対応するテストも追加してください。

```python
def test_custom_exception():
    error = CustomError("Test message", {"key": "value"})
    assert str(error) == "Test message | Details: {'key': 'value'}"
    assert isinstance(error, PolibaseError)
```

## まとめ

適切なエラーハンドリングにより：
- デバッグが容易になります
- ユーザーに分かりやすいエラーメッセージを提供できます
- エラーの原因を特定しやすくなります
- システムの信頼性が向上します

新しいモジュールを追加する際は、このガイドに従って一貫性のあるエラーハンドリングを実装してください。
