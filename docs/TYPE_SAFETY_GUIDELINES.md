# 型安全性ガイドライン

このドキュメントは、Polibaseプロジェクトにおける型安全性の実装方針と実践方法について説明します。

## 概要

Polibaseは、Python 3.11+の型ヒント機能とpyrightを使用して、実行時エラーを削減し、コードの品質を向上させています。

## 型チェック設定

### pyright設定（pyrightconfig.json）

Phase 2では、設定をpyrightconfig.jsonに移行し、レガシーモジュールを除外しています：

```json
{
  "include": ["src"],
  "exclude": [
    "src/web_scraper/**",
    "src/minutes_divide_processor/**",
    "src/party_member_extractor/**",
    "src/update_speaker_links_llm.py",
    "src/process_minutes.py",
    "src/streamlit_app.py"
  ],
  "pythonVersion": "3.13",
  "typeCheckingMode": "standard",
  "reportMissingImports": true,
  "reportMissingTypeStubs": false,
  "reportUnknownParameterType": "error",
  "reportMissingParameterType": "error",
  "reportMissingTypeArgument": "error",
  "reportPrivateUsage": "error",
  "reportUnknownMemberType": "error",
  "reportUnknownVariableType": "error",
  "reportUnknownArgumentType": "error",
  "reportGeneralTypeIssues": "error",
  "reportOptionalMemberAccess": "error",
  "reportOptionalOperand": "error",
  "strictParameterNoneValue": true
}
```

## 実装ガイドライン

### 1. 基本的な型ヒント

すべての関数とメソッドには、引数と戻り値の型ヒントを追加してください：

```python
# 良い例
def calculate_similarity(name1: str, name2: str) -> float:
    """名前の類似度を計算する"""
    return 0.85

# 悪い例
def calculate_similarity(name1, name2):
    return 0.85
```

### 2. Optional型の扱い

Noneを許容する場合は、明示的にOptional型またはUnion型を使用します：

```python
from typing import Optional

# 良い例
def get_politician(id: int) -> Optional[Politician]:
    """政治家を取得。見つからない場合はNoneを返す"""
    return None

# Python 3.10+の場合
def get_politician(id: int) -> Politician | None:
    return None
```

### 3. 型ガードの使用

Optional型を使用する際は、適切な型ガードを実装してください：

```python
# 良い例
politician = await repo.get_by_id(politician_id)
if politician is None:
    raise ValueError(f"Politician {politician_id} not found")
# この時点でpoliticianはPolitician型として扱われる

# または早期リターン
if politician is None:
    return None
# この時点でpoliticianはPolitician型として扱われる
```

### 4. ProtocolとInterface

外部サービスのインターフェースは、Protocolを使用して定義します：

```python
from typing import Protocol, Any

class ILLMService(Protocol):
    """LLMサービスのインターフェース"""

    async def match_speaker_to_politician(
        self, context: dict[str, Any]
    ) -> dict[str, Any] | None:
        """話者を政治家にマッチング"""
        ...
```

### 5. TypedDictの使用

辞書型のデータ構造には、TypedDictを使用して型安全性を確保します：

```python
from typing import TypedDict

class PoliticianData(TypedDict):
    """政治家データの型定義"""
    id: int
    name: str
    party_id: int | None
    position: str | None
```

### 6. Genericを使った型安全なリポジトリ

リポジトリパターンでは、Genericを使用して型安全性を確保します：

```python
from typing import TypeVar, Generic

T = TypeVar("T", bound=BaseEntity)

class BaseRepository(Generic[T]):
    """型安全なリポジトリ基底クラス"""

    async def get_by_id(self, entity_id: int) -> T | None:
        """IDでエンティティを取得"""
        pass
```

### 7. Any型の使用制限

Any型の使用は最小限に抑え、具体的な型を使用してください：

```python
# 避けるべき例
def process_data(data: Any) -> Any:
    return data

# 良い例
def process_data(data: dict[str, str]) -> list[str]:
    return list(data.values())
```

## 型チェックの実行

### 開発時の型チェック

```bash
# Docker環境での実行
docker compose exec polibase uv run --frozen pyright

# ローカル環境での実行
uv run pyright
```

### CI/CDでの型チェック

GitHub Actionsなどで自動的に型チェックを実行し、エラーがある場合はマージを防ぎます。

### 型チェックのテスト

`tests/test_type_safety.py`で型安全性のテストを実行できます：

```bash
docker compose exec polibase uv run pytest tests/test_type_safety.py
```

## 実装例

### TypedRepositoryの使用例

```python
from src.database.typed_repository import TypedRepository
from src.models.speaker_v2 import Speaker

class SpeakerRepository(TypedRepository[Speaker]):
    """型安全なSpeakerリポジトリ"""

    def __init__(self):
        super().__init__(Speaker, "speakers", use_session=True)

    def find_by_name(self, name: str) -> Speaker | None:
        """名前で話者を検索（型安全）"""
        query = "SELECT * FROM speakers WHERE name = :name LIMIT 1"
        return self.fetch_one(query, {"name": name})
```

### Protocolを使った外部依存の定義

```python
from typing import Protocol

class ExtractedMemberRepository(Protocol):
    """外部リポジトリのProtocol定義"""

    async def get_by_conference(
        self, conference_id: int
    ) -> list[ExtractedMemberEntity]:
        """型安全なメソッドシグネチャ"""
        ...
```

## 段階的な移行戦略

### Phase 1: 基本的な型エラーの修正（完了 ✅）
- ✅ Optional型の適切な処理
- ✅ 必須引数の追加
- ✅ 基本的な型ヒントの追加
- ✅ 型チェックテストの作成
- ✅ Protocol定義の追加

### Phase 2: strictモードへの移行準備（進行中 🔄）
- ✅ TypedDictの導入（src/domain/types/に定義）
- ✅ 型安全なリポジトリ基底クラス（TypedRepository）の実装
- ✅ pyrightの設定強化（error報告に変更）
- ✅ レガシーモジュールの除外設定（pyrightconfig.json）
- 🔄 Any型の削減（目標: 5%以下）
- 🔄 既存リポジトリのTypedRepository移行
- 🔄 コアモジュールの型エラー修正

### Phase 3: strictモードの有効化（完了 ✅）
- ✅ pyrightのstrictモード試験（現在はstandardモード維持）
- ✅ 型安全なリポジトリ基底クラスへの移行開始
- ✅ コアモジュールでのAny型使用を0に削減
- 🔄 型カバレッジ向上（継続的改善中）
- 🔄 レガシーモジュールの段階的移行

## トラブルシューティング

### よくあるエラーと対処法

1. **"Type of X is unknown"**
   - 変数や引数に明示的な型ヒントを追加

2. **"Argument of type 'X | None' cannot be assigned to parameter of type 'X'"**
   - 型ガードを使用してNoneチェックを実施

3. **"reportOptionalMemberAccess"**
   - Optional型のメンバーアクセス前にNoneチェックを追加

## 参考資料

- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Pyright Documentation](https://github.com/microsoft/pyright)
- [PEP 484 – Type Hints](https://www.python.org/dev/peps/pep-0484/)
