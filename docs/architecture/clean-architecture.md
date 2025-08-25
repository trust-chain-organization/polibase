# Clean Architecture実装詳細

## 目次
- [概要](#概要)
- [設計原則](#設計原則)
- [ディレクトリ構造](#ディレクトリ構造)
- [層の詳細](#層の詳細)
- [実装パターン](#実装パターン)
- [命名規則](#命名規則)
- [ベストプラクティス](#ベストプラクティス)
- [移行戦略](#移行戦略)

## 概要

PolibaseはClean Architectureを採用し、保守性、テスト容易性、拡張性の高いシステムを実現しています。本ドキュメントでは、Clean Architectureの実装詳細と開発ガイドラインを提供します。

### Clean Architectureとは

Clean Architectureは、Robert C. Martin（Uncle Bob）によって提唱されたソフトウェアアーキテクチャで、以下の特徴を持ちます：

- **関心の分離**: 各層が明確な責務を持つ
- **依存性の逆転**: ビジネスロジックが外部フレームワークに依存しない
- **テスト容易性**: 各層を独立してテスト可能
- **フレームワーク非依存**: 特定のフレームワークに縛られない

## 設計原則

### 依存性ルール

```
[Interfaces] → [Application] → [Domain] ← [Infrastructure]
         ↓                        ↑              ↓
         └────────────────────────┴──────────────┘
```

**重要な原則**:
1. **内向きの依存**: 依存は常に内側（Domain）に向かう
2. **Domain層の独立性**: Domain層は他の層に依存しない
3. **インターフェース分離**: 具象実装ではなくインターフェースに依存

### SOLIDプリンシプル

#### S: 単一責任の原則（Single Responsibility Principle）
```python
# Good: 単一の責任を持つクラス
class PoliticianDomainService:
    """政治家に関するドメインロジックのみを扱う"""
    def validate_politician(self, politician: Politician) -> bool:
        pass

    def normalize_name(self, name: str) -> str:
        pass

# Bad: 複数の責任を持つクラス
class PoliticianService:
    def validate_politician(self): pass
    def save_to_database(self): pass  # データアクセスの責任
    def send_notification(self): pass  # 通知の責任
```

#### O: 開放閉鎖の原則（Open/Closed Principle）
```python
# Good: 拡張に対して開き、修正に対して閉じている
from abc import ABC, abstractmethod

class BaseValidator(ABC):
    @abstractmethod
    def validate(self, entity) -> bool:
        pass

class PoliticianValidator(BaseValidator):
    def validate(self, entity) -> bool:
        # 政治家固有の検証ロジック
        pass
```

#### L: リスコフの置換原則（Liskov Substitution Principle）
```python
# Good: 派生クラスは基底クラスと置換可能
class BaseRepository(Generic[T]):
    async def find_by_id(self, id: int) -> Optional[T]:
        pass

class PoliticianRepository(BaseRepository[Politician]):
    async def find_by_id(self, id: int) -> Optional[Politician]:
        # 基底クラスと同じ契約を守る
        pass
```

#### I: インターフェース分離の原則（Interface Segregation Principle）
```python
# Good: 小さく特化したインターフェース
class IReadRepository(Protocol):
    async def find_by_id(self, id: int): pass
    async def find_all(self): pass

class IWriteRepository(Protocol):
    async def save(self, entity): pass
    async def delete(self, entity): pass

# クライアントは必要なインターフェースのみに依存
```

#### D: 依存性逆転の原則（Dependency Inversion Principle）
```python
# Good: 抽象に依存
class ProcessMinutesUseCase:
    def __init__(self, meeting_repo: IMeetingRepository):
        self.meeting_repo = meeting_repo  # インターフェースに依存
```

## ディレクトリ構造

```
src/
├── domain/                  # ドメイン層
│   ├── entities/           # エンティティ
│   │   ├── __init__.py
│   │   ├── base.py         # BaseEntity
│   │   ├── politician.py   # Politicianエンティティ
│   │   ├── speaker.py      # Speakerエンティティ
│   │   ├── meeting.py      # Meetingエンティティ
│   │   └── ...
│   ├── repositories/       # リポジトリインターフェース
│   │   ├── __init__.py
│   │   ├── base.py         # BaseRepository[T]
│   │   ├── politician_repository.py
│   │   └── ...
│   └── services/           # ドメインサービス
│       ├── __init__.py
│       ├── speaker_domain_service.py
│       ├── politician_domain_service.py
│       └── ...
│
├── application/            # アプリケーション層
│   ├── usecases/          # ユースケース
│   │   ├── __init__.py
│   │   ├── process_minutes_usecase.py
│   │   ├── match_speakers_usecase.py
│   │   └── ...
│   └── dtos/              # データ転送オブジェクト
│       ├── __init__.py
│       ├── process_minutes_dto.py
│       └── ...
│
├── infrastructure/        # インフラストラクチャ層
│   ├── persistence/       # データベース実装
│   │   ├── __init__.py
│   │   ├── base_repository.py
│   │   ├── politician_repository.py
│   │   └── ...
│   ├── external/          # 外部サービス
│   │   ├── __init__.py
│   │   ├── llm_service.py       # LLMサービスインターフェース
│   │   ├── gemini_llm_service.py # Gemini実装
│   │   ├── storage_service.py    # ストレージインターフェース
│   │   ├── gcs_storage_service.py # GCS実装
│   │   └── ...
│   └── interfaces/        # サービスインターフェース定義
│       ├── __init__.py
│       ├── llm_service.py
│       └── storage_service.py
│
└── interfaces/            # インターフェース層
    ├── cli/              # CLIコマンド
    │   ├── __init__.py
    │   ├── commands/
    │   │   ├── process_minutes.py
    │   │   └── ...
    │   └── main.py
    └── web/              # Web UI
        ├── __init__.py
        ├── streamlit_app.py
        └── pages/
            ├── meetings.py
            └── ...
```

## 層の詳細

### Domain層

#### エンティティ（Entities）

エンティティはビジネスオブジェクトとビジネスルールを表現します。

```python
# src/domain/entities/base.py
from datetime import datetime
from typing import Optional

class BaseEntity:
    """全エンティティの基底クラス"""

    def __init__(self, id: Optional[int] = None):
        self.id = id
        self.created_at: Optional[datetime] = None
        self.updated_at: Optional[datetime] = None

    def __eq__(self, other):
        if not isinstance(other, BaseEntity):
            return False
        return self.id == other.id if self.id else self is other

    def __hash__(self):
        return hash(self.id) if self.id else id(self)
```

```python
# src/domain/entities/politician.py
from typing import Optional
from .base import BaseEntity

class Politician(BaseEntity):
    """政治家エンティティ"""

    def __init__(
        self,
        id: Optional[int] = None,
        name: str = "",
        political_party_id: Optional[int] = None,
        prefecture: Optional[str] = None,
        electoral_district: Optional[str] = None,
        position: Optional[str] = None,
        profile_url: Optional[str] = None,
        party_position: Optional[str] = None
    ):
        super().__init__(id)
        self.name = name
        self.political_party_id = political_party_id
        self.prefecture = prefecture
        self.electoral_district = electoral_district
        self.position = position
        self.profile_url = profile_url
        self.party_position = party_position

    def is_party_leader(self) -> bool:
        """党首かどうかを判定"""
        return self.party_position in ["党首", "代表", "委員長"]

    def validate(self) -> bool:
        """エンティティの妥当性を検証"""
        if not self.name:
            raise ValueError("政治家の名前は必須です")
        if len(self.name) > 100:
            raise ValueError("名前は100文字以内である必要があります")
        return True
```

#### リポジトリインターフェース

リポジトリインターフェースはデータアクセスの抽象化を提供します。

```python
# src/domain/repositories/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """基底リポジトリインターフェース"""

    @abstractmethod
    async def find_by_id(self, id: int) -> Optional[T]:
        """IDによるエンティティの取得"""
        pass

    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        """全エンティティの取得"""
        pass

    @abstractmethod
    async def save(self, entity: T) -> T:
        """エンティティの保存"""
        pass

    @abstractmethod
    async def delete(self, entity: T) -> bool:
        """エンティティの削除"""
        pass

    @abstractmethod
    async def count(self) -> int:
        """エンティティ数のカウント"""
        pass
```

```python
# src/domain/repositories/politician_repository.py
from abc import abstractmethod
from typing import List, Optional
from .base import BaseRepository
from ..entities.politician import Politician

class IPoliticianRepository(BaseRepository[Politician]):
    """政治家リポジトリインターフェース"""

    @abstractmethod
    async def find_by_name(self, name: str) -> Optional[Politician]:
        """名前による政治家の検索"""
        pass

    @abstractmethod
    async def find_by_party(self, party_id: int) -> List[Politician]:
        """政党による政治家の検索"""
        pass

    @abstractmethod
    async def find_by_name_and_party(
        self,
        name: str,
        party_id: int
    ) -> Optional[Politician]:
        """名前と政党による政治家の検索"""
        pass
```

#### ドメインサービス

ドメインサービスは、特定のエンティティに属さないビジネスロジックを実装します。

```python
# src/domain/services/politician_domain_service.py
from typing import List, Tuple, Optional
from ..entities.politician import Politician

class PoliticianDomainService:
    """政治家に関するドメインサービス"""

    def normalize_name(self, name: str) -> str:
        """名前の正規化

        Args:
            name: 正規化する名前

        Returns:
            正規化された名前
        """
        # 敬称の除去
        honorifics = ["議員", "先生", "氏", "さん", "君", "様"]
        normalized = name
        for honorific in honorifics:
            normalized = normalized.replace(honorific, "")

        # 空白の正規化
        normalized = normalized.strip()
        normalized = " ".join(normalized.split())

        return normalized

    def calculate_similarity(
        self,
        politician1: Politician,
        politician2: Politician
    ) -> float:
        """2人の政治家の類似度を計算

        Args:
            politician1: 比較する政治家1
            politician2: 比較する政治家2

        Returns:
            類似度スコア（0.0〜1.0）
        """
        score = 0.0

        # 名前の類似度
        if politician1.name == politician2.name:
            score += 0.5
        elif self.normalize_name(politician1.name) == \
             self.normalize_name(politician2.name):
            score += 0.3

        # 政党の一致
        if politician1.political_party_id == politician2.political_party_id:
            score += 0.3

        # 選挙区の一致
        if politician1.electoral_district and \
           politician1.electoral_district == politician2.electoral_district:
            score += 0.2

        return min(score, 1.0)

    def find_duplicates(
        self,
        politicians: List[Politician]
    ) -> List[Tuple[Politician, Politician]]:
        """重複する政治家を検出

        Args:
            politicians: 政治家のリスト

        Returns:
            重複ペアのリスト
        """
        duplicates = []

        for i, pol1 in enumerate(politicians):
            for pol2 in politicians[i + 1:]:
                similarity = self.calculate_similarity(pol1, pol2)
                if similarity >= 0.8:  # 80%以上の類似度を重複とみなす
                    duplicates.append((pol1, pol2))

        return duplicates
```

### Application層

#### ユースケース

ユースケースはアプリケーション固有のビジネスルールを実装します。

```python
# src/application/usecases/process_minutes_usecase.py
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

from ..dtos.process_minutes_dto import (
    ProcessMinutesInputDto,
    ProcessMinutesOutputDto
)
from ...domain.repositories.meeting_repository import IMeetingRepository
from ...domain.repositories.minutes_repository import IMinutesRepository
from ...domain.services.minutes_domain_service import MinutesDomainService
from ...infrastructure.interfaces.llm_service import ILLMService
from ...infrastructure.interfaces.storage_service import IStorageService

@dataclass
class ProcessMinutesResult:
    """議事録処理結果"""
    success: bool
    meeting_id: int
    conversation_count: int
    processing_time: float
    error_message: Optional[str] = None

class ProcessMinutesUseCase:
    """議事録処理ユースケース

    議事録PDFまたはテキストを処理し、発言を抽出して
    データベースに保存します。

    Attributes:
        meeting_repo: 会議リポジトリ
        minutes_repo: 議事録リポジトリ
        minutes_service: 議事録ドメインサービス
        llm_service: LLMサービス
        storage_service: ストレージサービス
    """

    def __init__(
        self,
        meeting_repo: IMeetingRepository,
        minutes_repo: IMinutesRepository,
        minutes_service: MinutesDomainService,
        llm_service: ILLMService,
        storage_service: Optional[IStorageService] = None
    ):
        self.meeting_repo = meeting_repo
        self.minutes_repo = minutes_repo
        self.minutes_service = minutes_service
        self.llm_service = llm_service
        self.storage_service = storage_service

    async def execute(
        self,
        input_dto: ProcessMinutesInputDto
    ) -> ProcessMinutesOutputDto:
        """議事録を処理する

        Args:
            input_dto: 処理入力DTO

        Returns:
            ProcessMinutesOutputDto: 処理結果

        Raises:
            MeetingNotFoundException: 会議が見つからない
            ProcessingException: 処理中にエラー発生
        """
        start_time = datetime.now()

        try:
            # 1. 会議の取得
            meeting = await self.meeting_repo.find_by_id(input_dto.meeting_id)
            if not meeting:
                raise MeetingNotFoundException(
                    f"会議ID {input_dto.meeting_id} が見つかりません"
                )

            # 2. 既存の処理確認
            if not input_dto.force:
                existing = await self.minutes_repo.find_by_meeting_id(
                    input_dto.meeting_id
                )
                if existing:
                    return ProcessMinutesOutputDto(
                        success=True,
                        meeting_id=input_dto.meeting_id,
                        message="既に処理済みです",
                        conversation_count=0
                    )

            # 3. PDFまたはテキストの取得
            content = ""
            if meeting.gcs_text_uri and self.storage_service:
                # GCSからテキストを取得
                content = await self.storage_service.download(
                    meeting.gcs_text_uri
                )
            elif meeting.gcs_pdf_uri and self.storage_service:
                # GCSからPDFを取得して処理
                pdf_content = await self.storage_service.download(
                    meeting.gcs_pdf_uri
                )
                content = self.minutes_service.extract_text_from_pdf(
                    pdf_content
                )
            else:
                raise ValueError("処理可能なコンテンツが見つかりません")

            # 4. LLMによる発言抽出
            conversations = await self.llm_service.extract_conversations(
                content
            )

            # 5. データベースへの保存
            for conv in conversations:
                await self.minutes_repo.save_conversation(
                    meeting_id=input_dto.meeting_id,
                    conversation=conv
                )

            # 6. 処理時間の計算
            processing_time = (datetime.now() - start_time).total_seconds()

            return ProcessMinutesOutputDto(
                success=True,
                meeting_id=input_dto.meeting_id,
                conversation_count=len(conversations),
                processing_time=processing_time,
                message=f"{len(conversations)}件の発言を抽出しました"
            )

        except Exception as e:
            return ProcessMinutesOutputDto(
                success=False,
                meeting_id=input_dto.meeting_id,
                conversation_count=0,
                processing_time=(datetime.now() - start_time).total_seconds(),
                error_message=str(e)
            )

class MeetingNotFoundException(Exception):
    """会議が見つからない例外"""
    pass

class ProcessingException(Exception):
    """処理中の例外"""
    pass
```

#### DTO（Data Transfer Objects）

DTOは層間のデータ転送に使用されます。

```python
# src/application/dtos/process_minutes_dto.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class ProcessMinutesInputDto:
    """議事録処理入力DTO"""
    meeting_id: int
    force: bool = False
    use_llm: bool = True

@dataclass
class ProcessMinutesOutputDto:
    """議事録処理出力DTO"""
    success: bool
    meeting_id: int
    conversation_count: int
    processing_time: float
    message: str = ""
    error_message: Optional[str] = None
```

### Infrastructure層

#### リポジトリ実装

```python
# src/infrastructure/persistence/base_repository.py
from typing import TypeVar, Generic, Optional, List, Type
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from ...domain.entities.base import BaseEntity

T = TypeVar('T', bound=BaseEntity)

class BaseRepositoryImpl(Generic[T]):
    """基底リポジトリ実装"""

    def __init__(
        self,
        session: AsyncSession,
        model_class: Type[T]
    ):
        self.session = session
        self.model_class = model_class

    async def find_by_id(self, id: int) -> Optional[T]:
        """IDによるエンティティの取得"""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()

    async def find_all(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[T]:
        """全エンティティの取得"""
        result = await self.session.execute(
            select(self.model_class)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def save(self, entity: T) -> T:
        """エンティティの保存"""
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: T) -> bool:
        """エンティティの削除"""
        await self.session.delete(entity)
        await self.session.commit()
        return True

    async def count(self) -> int:
        """エンティティ数のカウント"""
        result = await self.session.execute(
            select(func.count()).select_from(self.model_class)
        )
        return result.scalar() or 0
```

#### 外部サービス

```python
# src/infrastructure/interfaces/llm_service.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any

class ILLMService(ABC):
    """LLMサービスインターフェース"""

    @abstractmethod
    async def extract_conversations(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """テキストから発言を抽出"""
        pass

    @abstractmethod
    async def match_speaker(
        self,
        speaker_name: str,
        candidates: List[str]
    ) -> str:
        """発言者名を候補者リストとマッチング"""
        pass
```

```python
# src/infrastructure/external/gemini_llm_service.py
import google.generativeai as genai
from typing import List, Dict, Any

from ..interfaces.llm_service import ILLMService

class GeminiLLMService(ILLMService):
    """Gemini LLMサービス実装"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    async def extract_conversations(
        self,
        text: str
    ) -> List[Dict[str, Any]]:
        """テキストから発言を抽出"""
        prompt = f"""
        以下の議事録テキストから発言を抽出してください。
        JSONフォーマットで出力してください。

        テキスト:
        {text}
        """

        response = await self.model.generate_content_async(prompt)
        # レスポンスの解析と返却
        return self._parse_response(response.text)

    async def match_speaker(
        self,
        speaker_name: str,
        candidates: List[str]
    ) -> str:
        """発言者名を候補者リストとマッチング"""
        prompt = f"""
        発言者名「{speaker_name}」に最も一致する候補を選んでください。

        候補:
        {', '.join(candidates)}
        """

        response = await self.model.generate_content_async(prompt)
        return response.text.strip()

    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """レスポンスを解析してリストに変換"""
        # JSON解析ロジック
        pass
```

### Interfaces層

#### CLIコマンド

```python
# src/interfaces/cli/commands/process_minutes.py
import click
from typing import Optional

from ....application.usecases.process_minutes_usecase import (
    ProcessMinutesUseCase
)
from ....application.dtos.process_minutes_dto import (
    ProcessMinutesInputDto
)
from ....infrastructure.persistence.database import get_session
from ....infrastructure.persistence.meeting_repository import (
    MeetingRepositoryImpl
)
from ....infrastructure.persistence.minutes_repository import (
    MinutesRepositoryImpl
)
from ....domain.services.minutes_domain_service import (
    MinutesDomainService
)
from ....infrastructure.external.gemini_llm_service import (
    GeminiLLMService
)

@click.command()
@click.option('--meeting-id', type=int, required=True, help='会議ID')
@click.option('--force', is_flag=True, help='既存データを上書き')
async def process_minutes(meeting_id: int, force: bool):
    """議事録を処理する"""

    async with get_session() as session:
        # 依存性の注入
        meeting_repo = MeetingRepositoryImpl(session)
        minutes_repo = MinutesRepositoryImpl(session)
        minutes_service = MinutesDomainService()
        llm_service = GeminiLLMService(api_key=get_api_key())

        # ユースケースの実行
        use_case = ProcessMinutesUseCase(
            meeting_repo=meeting_repo,
            minutes_repo=minutes_repo,
            minutes_service=minutes_service,
            llm_service=llm_service
        )

        input_dto = ProcessMinutesInputDto(
            meeting_id=meeting_id,
            force=force
        )

        result = await use_case.execute(input_dto)

        if result.success:
            click.echo(f"✅ {result.message}")
        else:
            click.echo(f"❌ エラー: {result.error_message}")
```

## 実装パターン

### リポジトリパターン

データアクセスを抽象化し、ドメイン層をデータベース実装から分離します。

```python
# Domain層でインターフェースを定義
class IRepository(ABC):
    @abstractmethod
    async def find_by_id(self, id: int):
        pass

# Infrastructure層で実装
class RepositoryImpl(IRepository):
    async def find_by_id(self, id: int):
        # SQLAlchemyを使用した実装
        pass
```

### 依存性注入（DI）

コンストラクタインジェクションを使用して依存性を注入します。

```python
class UseCase:
    def __init__(
        self,
        repository: IRepository,  # インターフェースに依存
        service: IService         # インターフェースに依存
    ):
        self.repository = repository
        self.service = service
```

### Factory パターン

複雑なオブジェクトの生成を隠蔽します。

```python
class UseCaseFactory:
    @staticmethod
    def create_process_minutes_usecase(
        session: AsyncSession
    ) -> ProcessMinutesUseCase:
        meeting_repo = MeetingRepositoryImpl(session)
        minutes_repo = MinutesRepositoryImpl(session)
        minutes_service = MinutesDomainService()
        llm_service = GeminiLLMService(api_key=get_api_key())

        return ProcessMinutesUseCase(
            meeting_repo=meeting_repo,
            minutes_repo=minutes_repo,
            minutes_service=minutes_service,
            llm_service=llm_service
        )
```

## 命名規則

### クラス名
- **エンティティ**: 単数形の名詞（`Politician`, `Speaker`）
- **リポジトリインターフェース**: `I` + エンティティ名 + `Repository`
- **リポジトリ実装**: エンティティ名 + `RepositoryImpl`
- **ユースケース**: 動詞 + 名詞 + `UseCase`
- **ドメインサービス**: エンティティ名 + `DomainService`
- **DTO**: 用途 + `InputDto` / `OutputDto`

### メソッド名
- **リポジトリ**: `find_by_*`, `save`, `delete`, `count`
- **ユースケース**: `execute`
- **ドメインサービス**: 動詞 + 名詞（`normalize_name`, `calculate_similarity`）

### ファイル名
- **snake_case**: すべてのファイル名
- **エンティティ**: エンティティ名の小文字（`politician.py`）
- **リポジトリ**: エンティティ名 + `_repository.py`
- **ユースケース**: ユースケース名の小文字（`process_minutes_usecase.py`）

## ベストプラクティス

### 1. エンティティの設計
- ビジネスロジックをエンティティに配置
- データベース関連のロジックは含めない
- 不変性を保つ（可能な限り）

### 2. リポジトリの実装
- 単一責任の原則を守る
- 複雑なクエリはカスタムメソッドとして実装
- トランザクション管理はユースケース層で行う

### 3. ユースケースの実装
- 1つのユースケース = 1つのユーザーストーリー
- エラーハンドリングを適切に行う
- ログ記録を実装

### 4. DTOの使用
- 層間のデータ転送にはDTOを使用
- エンティティを直接公開しない
- バリデーションはDTO作成時に実施

### 5. テストの作成
- 各層を独立してテスト
- モックを活用してユニットテスト
- 統合テストでは実際のデータベースを使用

### 6. 非同期処理
- すべてのリポジトリメソッドはasync/await
- 並列処理可能な処理は並列化
- タイムアウトを適切に設定

## 移行戦略

### Phase 1: 新機能の実装（現在）
- 新しい機能はClean Architectureで実装
- 既存コードとの共存

### Phase 2: コア機能の移行
- 議事録処理システムの移行
- 政治家管理システムの移行
- スピーカーマッチングの移行

### Phase 3: インフラ層の統一
- データベースアクセスの統一
- 外部サービスの抽象化
- エラーハンドリングの統一

### Phase 4: レガシーコードの削除
- 旧実装の削除
- ディレクトリ構造の最適化
- ドキュメントの最終更新

### 移行時の注意点

1. **段階的な移行**: 一度にすべてを移行しない
2. **テストの維持**: 移行中もテストカバレッジを維持
3. **後方互換性**: 移行中は既存機能を壊さない
4. **ドキュメント化**: 移行状況を常に文書化
5. **レビュー**: すべての移行はコードレビューを通す

## トラブルシューティング

### 循環依存の解決
```python
# Bad: 循環依存
# domain/entities/a.py
from .b import B

# domain/entities/b.py
from .a import A

# Good: インターフェースを使用
# domain/entities/a.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .b import B
```

### 非同期処理のデッドロック
```python
# Bad: デッドロックの可能性
async def process():
    async with get_session() as session1:
        async with get_session() as session2:
            # 処理

# Good: 単一セッションを使用
async def process():
    async with get_session() as session:
        # すべての処理で同じセッションを使用
```

### パフォーマンス問題
```python
# Bad: N+1問題
for meeting in meetings:
    speaker = await speaker_repo.find_by_meeting_id(meeting.id)

# Good: 一括取得
meeting_ids = [m.id for m in meetings]
speakers = await speaker_repo.find_by_meeting_ids(meeting_ids)
```

## 関連ドキュメント

- [アーキテクチャ概要](./README.md)
- [データベース設計](./database-design.md)
- [Clean Architecture移行ガイド](../CLEAN_ARCHITECTURE_MIGRATION.md)
- [開発ガイド](../guides/development.md)
- [テストガイド](../guides/testing.md)
