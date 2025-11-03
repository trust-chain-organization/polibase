# Polibase BI Dashboard POC

Plotly Dashを使用したデータカバレッジダッシュボードのProof of Concept実装。

## 概要

このPOCは、以下を実証します:
- **コードベースのダッシュボード定義**: 全てPythonコードで定義
- **PostgreSQL統合**: SQLAlchemyによるデータベース接続
- **Docker対応**: Docker Composeで簡単にデプロイ
- **Clean Architecture互換**: 独立したインターフェース層として実装

## 機能

- **全体カバレッジ率**: 円グラフでデータ取得状況を可視化
- **組織タイプ別カバレッジ**: 国/都道府県/市町村別の棒グラフ
- **都道府県別カバレッジ**: 上位10都道府県の詳細テーブル
- **リアルタイム更新**: 更新ボタンでデータを再取得

## ディレクトリ構造

```
src/interfaces/bi_dashboard/
├── Dockerfile              # Docker設定
├── docker-compose.yml      # Docker Compose設定
├── requirements.txt        # Python依存関係
├── app.py                  # Dashアプリエントリーポイント
├── layouts/
│   └── main_layout.py     # レイアウト定義
├── callbacks/
│   └── data_callbacks.py  # コールバック定義
└── data/
    └── data_loader.py     # データ取得ロジック
```

## 前提条件

- Docker & Docker Compose
- PostgreSQL (Polibaseデータベース)

## セットアップと実行

### 方法1: 既存のPolibaseデータベースを使用

```bash
# ディレクトリに移動
cd src/interfaces/bi_dashboard

# 環境変数を設定してアプリを起動
export DATABASE_URL=postgresql://polibase:polibase@localhost:5432/polibase
python app.py
```

ブラウザで `http://localhost:8050` にアクセス

### 方法2: Docker Composeで完全起動

```bash
# ディレクトリに移動
cd src/interfaces/bi_dashboard

# Docker Composeで起動
docker-compose up --build

# または、既存のPolibase DBを使う場合（docker-compose.ymlのdb部分をコメントアウト）
docker-compose up bi-dashboard
```

ブラウザで `http://localhost:8050` にアクセス

## 技術スタック

- **Dash 2.14.2**: Plotlyのダッシュボードフレームワーク
- **Plotly 5.18.0**: インタラクティブグラフライブラリ
- **Pandas 2.1.4**: データ処理
- **SQLAlchemy 2.0.23**: ORMとデータベース接続
- **psycopg2-binary 2.9.9**: PostgreSQLドライバ

## Clean Architectureでの位置づけ

```
┌─────────────────────────────────────┐
│     Interfaces Layer (UI)          │
│  ┌───────────────────────────────┐ │
│  │  BI Dashboard (Plotly Dash)   │ │
│  │  - layouts/                    │ │
│  │  - callbacks/                  │ │
│  │  - data/                       │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Application Layer (Use Cases)    │
│  - ProcessMinutesUseCase            │
│  - MatchSpeakersUseCase             │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│       Domain Layer (Entities)       │
│  - GoverningBody                    │
│  - Meeting, Politician              │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│  Infrastructure Layer (Repository)  │
│  - PostgreSQL                       │
└─────────────────────────────────────┘
```

現在のPOCは、直接SQLAlchemyでデータベースにアクセスしていますが、
本番実装では以下のようにClean Architectureに準拠させます:

```python
# 本番実装の例
from application.usecases.get_coverage_stats_usecase import GetCoverageStatsUseCase
from infrastructure.persistence.governing_body_repository import GoverningBodyRepositoryImpl

# Use Caseを使用してデータ取得
usecase = GetCoverageStatsUseCase(repository=GoverningBodyRepositoryImpl())
stats = usecase.execute()
```

## 評価結果

詳細な評価結果は [`tmp/bi_tool_evaluation_20251102.md`](../../../tmp/bi_tool_evaluation_20251102.md) を参照してください。

### Plotly Dashを選定した理由

1. **完全なコード制御**: すべてがPythonコードで定義可能
2. **Clean Architecture適合**: 独立したインターフェース層として配置可能
3. **PostgreSQL統合**: SQLAlchemyによる標準的な連携
4. **柔軟性**: Reactコンポーネントベースで高度なカスタマイズ可能
5. **本番実績**: 多数の企業で実績あり

## 次のステップ

1. **Clean Architecture統合**: Repository経由でのデータ取得に変更
2. **機能拡張**:
   - 日本地図可視化（Folium統合）
   - 時系列データ表示
   - フィルタリング機能
3. **テスト作成**: ユニットテストとインテグレーションテスト
4. **本番デプロイ**: Polibaseプロジェクトへの統合

## ライセンス

このPOCはPolibaseプロジェクトの一部であり、同じライセンスに従います。
