# Streamlit アプリケーション

## 概要

Polibase Streamlitアプリケーションは、政治活動追跡システムのWebインターフェースを提供します。
Streamlit 1.37.0+ の `st.navigation` を使用したURL ベースルーティングをサポートしています。

## アプリケーション構造

### エントリーポイント
- `app.py` - 新しいURL ベースルーティングを使用したメインエントリーポイント

### ページ構造
```
src/streamlit/
├── app.py                   # メインエントリーポイント（st.navigation使用）
├── pages/                   # 各機能のページモジュール
│   ├── conferences.py       # 会議体管理
│   ├── governing_bodies.py  # 開催主体管理
│   ├── meetings.py          # 会議管理
│   ├── parliamentary_groups.py # 議員団管理
│   ├── political_parties.py # 政党管理
│   ├── politicians.py       # 政治家管理
│   └── processes.py         # 処理実行
└── utils/                   # 共通ユーティリティ
    └── common.py            # 共通関数
```

## URL ルーティング

新しいアプリケーションでは、以下のURLパスでアクセス可能です：

| ページ | URL パス | 説明 |
|--------|----------|------|
| ホーム | `/` | アプリケーションのホームページ |
| 会議管理 | `/meetings` | 議事録の会議情報（URL、日付）を管理 |
| 政党管理 | `/parties` | 政党情報と政党員リストURLの管理 |
| 会議体管理 | `/conferences` | 議会や委員会などの会議体情報を管理 |
| 開催主体管理 | `/governing-bodies` | 国・都道府県・市町村などの管理 |
| 議員団管理 | `/parliamentary-groups` | 議員団（会派）情報の管理 |
| 処理実行 | `/processes` | 議事録処理やスクレイピングの実行 |
| 政治家管理 | `/politicians` | 政治家情報の検索・編集・管理 |
| LLM履歴 | `/llm-history` | LLM処理履歴の確認と検索 |

## 起動方法

```bash
# 統一CLIを使用（推奨）
docker compose -f docker/docker-compose.yml exec polibase uv run polibase streamlit

# 直接実行
docker compose -f docker/docker-compose.yml exec polibase uv run streamlit run src/streamlit/app.py

# ローカル環境で実行
uv run streamlit run src/streamlit/app.py
```

## 開発ガイド

### 新しいページの追加
1. `pages/` ディレクトリに新しいページモジュールを作成
2. ページ関数を実装（例：`def manage_new_feature()`）
3. `app.py` に新しいページを追加：
   ```python
   st.Page(manage_new_feature, title="新機能", url_path="new-feature", icon="🆕")
   ```

### セッション状態の管理
- `utils/common.py` の `init_session_state()` でセッション状態を初期化
- ページ間でデータを共有する場合は `st.session_state` を使用

### 共通レイアウト
- 各ページは独立したモジュールとして実装
- 共通のヘッダーやフッターは `app.py` のホームページで定義

## 技術的な注意点

- Streamlit 1.37.0 以上が必要（`st.navigation` APIのため）
- ログとSentryの初期化は `app.py` の最初で実行
- noqa: E402 コメントは初期化後のインポートに必要（Ruffの警告を抑制）
