# Polibase API ドキュメント

## 目次
- [概要](#概要)
- [現在のインターフェース](#現在のインターフェース)
- [計画中のREST API](#計画中のrest-api)
- [認証・認可](#認証認可)
- [エラーハンドリング](#エラーハンドリング)
- [レート制限](#レート制限)
- [WebSocket API](#websocket-api)

## 概要

Polibaseは現在、CLI（コマンドラインインターフェース）とStreamlit Web UIを通じて機能を提供しています。将来的にはRESTful APIを実装し、外部システムとの統合を可能にする予定です。

## 現在のインターフェース

### CLI API

Polibaseの主要機能はCLIコマンドとして提供されています。

#### コマンド一覧

```bash
polibase --help
```

#### 議事録処理

```bash
# 議事録の処理
polibase process-minutes [OPTIONS]

Options:
  --meeting-id INTEGER  処理する会議のID
  --force              既存データを上書き
  --use-llm            LLMを使用して処理（デフォルト: true）
  --help               ヘルプを表示
```

**処理フロー**:
1. 会議データの取得
2. PDFまたはテキストの読み込み
3. LLMによる発言抽出
4. データベースへの保存

#### 政治家情報スクレイピング

```bash
# 全政党の政治家情報を取得
polibase scrape-politicians --all-parties

# 特定政党の政治家情報を取得
polibase scrape-politicians --party-id 5

# ドライラン（実行せずに確認）
polibase scrape-politicians --all-parties --dry-run
```

**レスポンス例**:
```json
{
  "success": true,
  "scraped_count": 150,
  "new_politicians": 10,
  "updated_politicians": 140,
  "errors": []
}
```

#### スピーカーマッチング

```bash
# LLMを使用したスピーカーと政治家のマッチング
polibase update-speakers --use-llm

Options:
  --limit INTEGER      処理するスピーカー数の上限
  --confidence FLOAT   マッチング信頼度の閾値（0.0-1.0）
```

#### 会議メンバー管理

```bash
# Step 1: メンバー抽出
polibase extract-conference-members --conference-id 185

# Step 2: メンバーマッチング
polibase match-conference-members --conference-id 185

# Step 3: 所属情報作成
polibase create-affiliations --conference-id 185
```

#### データベース管理

```bash
# バックアップ
polibase database backup
polibase database backup --no-gcs  # ローカルのみ

# リストア
polibase database restore backup.sql
polibase database restore gs://bucket/backup.sql

# バックアップ一覧
polibase database list
```

### Streamlit Web UI エンドポイント

StreamlitアプリケーションはHTTPエンドポイントとして以下のページを提供：

```
http://localhost:8501/
├── 会議管理        # 会議の一覧と詳細
├── 政党管理        # 政党情報とメンバーリストURL
├── 会議体管理      # 会議体の管理
├── 政治家管理      # 政治家の検索と編集
└── モニタリング    # データカバレッジの可視化
```

## 計画中のREST API

### API仕様（OpenAPI 3.0）

```yaml
openapi: 3.0.0
info:
  title: Polibase API
  version: 1.0.0
  description: 日本の政治活動追跡システムAPI
servers:
  - url: https://api.polibase.jp/v1
    description: Production server
  - url: http://localhost:8000/v1
    description: Development server

paths:
  /meetings:
    get:
      summary: 会議一覧の取得
      parameters:
        - name: conference_id
          in: query
          schema:
            type: integer
        - name: date_from
          in: query
          schema:
            type: string
            format: date
        - name: date_to
          in: query
          schema:
            type: string
            format: date
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: per_page
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  meetings:
                    type: array
                    items:
                      $ref: '#/components/schemas/Meeting'
                  total:
                    type: integer
                  page:
                    type: integer
                  per_page:
                    type: integer

  /meetings/{id}:
    get:
      summary: 会議詳細の取得
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/MeetingDetail'
        '404':
          description: 会議が見つかりません

  /meetings/{id}/process:
    post:
      summary: 議事録の処理開始
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                force:
                  type: boolean
                  default: false
                use_llm:
                  type: boolean
                  default: true
      responses:
        '202':
          description: 処理開始
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string
                  message:
                    type: string

  /politicians:
    get:
      summary: 政治家一覧の取得
      parameters:
        - name: name
          in: query
          schema:
            type: string
        - name: party_id
          in: query
          schema:
            type: integer
        - name: prefecture
          in: query
          schema:
            type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  politicians:
                    type: array
                    items:
                      $ref: '#/components/schemas/Politician'

  /politicians/{id}:
    get:
      summary: 政治家詳細の取得
      parameters:
        - name: id
          in: path
          required: true
          schema:
            type: integer
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/PoliticianDetail'

  /conversations:
    get:
      summary: 発言の検索
      parameters:
        - name: speaker_id
          in: query
          schema:
            type: integer
        - name: politician_id
          in: query
          schema:
            type: integer
        - name: keyword
          in: query
          schema:
            type: string
        - name: date_from
          in: query
          schema:
            type: string
            format: date
        - name: date_to
          in: query
          schema:
            type: string
            format: date
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  conversations:
                    type: array
                    items:
                      $ref: '#/components/schemas/Conversation'

  /scraping/politicians:
    post:
      summary: 政治家情報のスクレイピング開始
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                party_id:
                  type: integer
                all_parties:
                  type: boolean
      responses:
        '202':
          description: スクレイピング開始
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string

  /jobs/{job_id}:
    get:
      summary: ジョブステータスの取得
      parameters:
        - name: job_id
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  job_id:
                    type: string
                  status:
                    type: string
                    enum: [pending, processing, completed, failed]
                  progress:
                    type: integer
                  result:
                    type: object
                  error:
                    type: string

components:
  schemas:
    Meeting:
      type: object
      properties:
        id:
          type: integer
        conference_id:
          type: integer
        conference_name:
          type: string
        date:
          type: string
          format: date
        name:
          type: string
        url:
          type: string
        created_at:
          type: string
          format: date-time

    MeetingDetail:
      allOf:
        - $ref: '#/components/schemas/Meeting'
        - type: object
          properties:
            minutes:
              type: array
              items:
                $ref: '#/components/schemas/Minutes'
            conversation_count:
              type: integer

    Minutes:
      type: object
      properties:
        id:
          type: integer
        url:
          type: string
        processed_at:
          type: string
          format: date-time

    Politician:
      type: object
      properties:
        id:
          type: integer
        name:
          type: string
        political_party:
          type: string
        prefecture:
          type: string
        electoral_district:
          type: string
        position:
          type: string
        profile_url:
          type: string

    PoliticianDetail:
      allOf:
        - $ref: '#/components/schemas/Politician'
        - type: object
          properties:
            party_membership_history:
              type: array
              items:
                type: object
            conference_affiliations:
              type: array
              items:
                type: object
            recent_conversations:
              type: array
              items:
                $ref: '#/components/schemas/Conversation'

    Conversation:
      type: object
      properties:
        id:
          type: integer
        speaker_name:
          type: string
        comment:
          type: string
        sequence_number:
          type: integer
        meeting_id:
          type: integer
        meeting_date:
          type: string
          format: date
        created_at:
          type: string
          format: date-time
```

### エンドポイント設計方針

#### RESTful設計原則
- **リソース指向**: URLはリソースを表現
- **HTTPメソッド**: 適切なメソッドの使用（GET, POST, PUT, DELETE）
- **ステートレス**: セッション情報を保持しない
- **HATEOAS**: レスポンスに関連リソースへのリンクを含む

#### ページネーション
```json
{
  "data": [...],
  "pagination": {
    "total": 1000,
    "page": 1,
    "per_page": 20,
    "total_pages": 50,
    "links": {
      "first": "/api/v1/meetings?page=1",
      "last": "/api/v1/meetings?page=50",
      "next": "/api/v1/meetings?page=2",
      "prev": null
    }
  }
}
```

#### フィルタリング
```
GET /api/v1/politicians?party_id=5&prefecture=東京都
GET /api/v1/conversations?date_from=2024-01-01&date_to=2024-12-31
```

#### ソート
```
GET /api/v1/meetings?sort=date:desc
GET /api/v1/politicians?sort=name:asc,created_at:desc
```

## 認証・認可

### 認証方式（計画）

#### APIキー認証
```http
GET /api/v1/meetings
Authorization: Bearer YOUR_API_KEY
```

#### OAuth 2.0
```http
POST /oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=client_credentials&
client_id=YOUR_CLIENT_ID&
client_secret=YOUR_CLIENT_SECRET
```

### 認可レベル

| レベル | 説明 | 可能な操作 |
|-------|------|-----------|
| Public | 公開データ | 読み取りのみ |
| User | 一般ユーザー | 読み取り、一部書き込み |
| Admin | 管理者 | すべての操作 |

## エラーハンドリング

### エラーレスポンス形式

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "指定された会議が見つかりません",
    "details": {
      "meeting_id": 123
    },
    "timestamp": "2024-08-25T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### HTTPステータスコード

| コード | 意味 | 使用例 |
|-------|------|--------|
| 200 | OK | 正常な取得・更新 |
| 201 | Created | リソースの作成成功 |
| 202 | Accepted | 非同期処理の開始 |
| 400 | Bad Request | 不正なリクエスト |
| 401 | Unauthorized | 認証エラー |
| 403 | Forbidden | 権限不足 |
| 404 | Not Found | リソースが存在しない |
| 409 | Conflict | リソースの競合 |
| 429 | Too Many Requests | レート制限超過 |
| 500 | Internal Server Error | サーバーエラー |
| 503 | Service Unavailable | メンテナンス中 |

### エラーコード一覧

| コード | 説明 |
|-------|------|
| `INVALID_PARAMETER` | パラメータが不正 |
| `RESOURCE_NOT_FOUND` | リソースが見つからない |
| `DUPLICATE_RESOURCE` | リソースが既に存在 |
| `PROCESSING_ERROR` | 処理中にエラー発生 |
| `LLM_ERROR` | LLM処理エラー |
| `DATABASE_ERROR` | データベースエラー |
| `RATE_LIMIT_EXCEEDED` | レート制限超過 |
| `AUTHENTICATION_FAILED` | 認証失敗 |
| `PERMISSION_DENIED` | 権限不足 |

## レート制限

### 制限ポリシー

| プラン | リクエスト/分 | リクエスト/日 | 同時接続数 |
|--------|-------------|--------------|-----------|
| Free | 60 | 1,000 | 2 |
| Basic | 600 | 10,000 | 10 |
| Pro | 3,000 | 100,000 | 50 |
| Enterprise | カスタム | カスタム | カスタム |

### レート制限ヘッダー

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1628856000
X-RateLimit-Reset-After: 30
```

### レート制限超過時のレスポンス

```http
HTTP/1.1 429 Too Many Requests
Retry-After: 30
Content-Type: application/json

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "レート制限を超過しました。30秒後に再試行してください。",
    "retry_after": 30
  }
}
```

## WebSocket API

### リアルタイム更新（計画）

```javascript
// WebSocket接続
const ws = new WebSocket('wss://api.polibase.jp/v1/ws');

// 認証
ws.send(JSON.stringify({
  type: 'auth',
  token: 'YOUR_API_TOKEN'
}));

// サブスクリプション
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'meetings',
  filters: {
    conference_id: 185
  }
}));

// メッセージ受信
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update received:', data);
};
```

### イベントタイプ

| イベント | 説明 | ペイロード |
|---------|------|-----------|
| `meeting.created` | 新規会議作成 | Meeting object |
| `meeting.processed` | 議事録処理完了 | Processing result |
| `politician.updated` | 政治家情報更新 | Politician object |
| `conversation.added` | 発言追加 | Conversation object |

## SDK・クライアントライブラリ（計画）

### Python SDK

```python
from polibase import PolibaseClient

client = PolibaseClient(api_key='YOUR_API_KEY')

# 会議一覧の取得
meetings = client.meetings.list(
    conference_id=185,
    date_from='2024-01-01'
)

# 議事録処理の開始
job = client.meetings.process(
    meeting_id=123,
    force=True
)

# ジョブステータスの確認
status = client.jobs.get(job.id)
```

### JavaScript/TypeScript SDK

```typescript
import { PolibaseClient } from '@polibase/client';

const client = new PolibaseClient({
  apiKey: 'YOUR_API_KEY'
});

// 政治家検索
const politicians = await client.politicians.search({
  name: '山田',
  partyId: 5
});

// WebSocket接続
const ws = client.websocket();
ws.subscribe('meetings', (event) => {
  console.log('Meeting update:', event);
});
```

## API利用規約

### 利用制限
- 商用利用は要相談
- スクレイピング結果の再配布禁止
- 過度なリクエストの禁止

### データ利用ポリシー
- 個人情報の適切な取り扱い
- 公職者の公開情報のみを扱う
- データの正確性は保証しない

### SLA（Service Level Agreement）
- 稼働率: 99.9%（月間）
- レスポンスタイム: 平均200ms以下
- サポート: ビジネスアワー対応

## 関連ドキュメント

- [アーキテクチャ概要](../architecture/README.md)
- [Clean Architecture詳細](../architecture/clean-architecture.md)
- [データベース設計](../architecture/database-design.md)
- [開発ガイド](../guides/development.md)
- [CLIリファレンス](../user-guide/README.md)
