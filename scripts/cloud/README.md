# GCP Cloud SQL GCS Dump方式の運用ガイド

このディレクトリには、GCSダンプ方式でCloud SQLを運用するためのスクリプトが含まれています。

## 🎯 コンセプト

**使用しない期間は完全に$0にする**

- 使用時: Cloud SQLインスタンスを作成してGCSから復元
- 終了時: GCSにバックアップして、Cloud SQLインスタンスを削除
- 停止中: GCSストレージ代のみ（約$0.02/月）

## 📁 ファイル構成

```
scripts/cloud/
├── README.md                    # このファイル
├── setup-dev-env.sh            # 開発環境起動（GCSから復元）
├── teardown-dev-env.sh         # 開発環境停止（GCSへバックアップ＋削除）
└── list-backups.sh             # バックアップ一覧表示
```

## 🚀 使い方

### 初回セットアップ

1. **環境変数を設定**

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="asia-northeast1"
export CLOUD_SQL_INSTANCE="sagebase-dev-db"
export GCS_BUCKET_NAME="sagebase-backups"
```

または、`.env`ファイルに記載：

```bash
GCP_PROJECT_ID=your-project-id
GCP_REGION=asia-northeast1
CLOUD_SQL_INSTANCE=sagebase-dev-db
GCS_BUCKET_NAME=sagebase-backups
```

2. **GCSバケットを作成**（初回のみ）

```bash
gsutil mb -p $GCP_PROJECT_ID -c STANDARD -l $GCP_REGION gs://$GCS_BUCKET_NAME
```

3. **開発環境を起動**

```bash
./scripts/cloud/setup-dev-env.sh
```

初回実行時は：
- Cloud SQLインスタンスが作成される（5-10分）
- 空のデータベースが作成される
- マイグレーションを実行してスキーマを初期化する必要がある

### 日常的な使い方

#### 作業開始時

```bash
./scripts/cloud/setup-dev-env.sh
```

- GCSに最新バックアップがある場合、自動的に復元されます
- すでにインスタンスが存在する場合は、起動のみ行います
- 所要時間: 新規作成10-15分、起動のみ1-2分

#### 作業終了時

```bash
./scripts/cloud/teardown-dev-env.sh
```

- 現在のデータベースをGCSにバックアップ
- Cloud SQLインスタンスを削除
- 所要時間: 5-10分（データ量による）

#### バックアップ確認

```bash
./scripts/cloud/list-backups.sh
```

## 💰 コスト比較

| 運用方法 | 月額コスト | 年間コスト | 起動時間 |
|---------|-----------|-----------|---------|
| 常時稼働（db-custom-2-8192） | $150 | $1,800 | 即座 |
| 停止運用（activation-policy） | $10-30 | $120-360 | 1-2分 |
| **GCSダンプ方式** | **$0.02** | **$0.24** | **10-15分** |

### コスト内訳（GCSダンプ方式）

- GCS Storage: $0.020/GB/月
- 想定ダンプサイズ: 1GB
- **月額**: 約$0.02
- **年間**: 約$0.24（約¥36/年）

## ⚙️ 設定のカスタマイズ

### インスタンススペック変更

`setup-dev-env.sh`の以下の行を編集：

```bash
# 開発環境用（最小構成）
--tier=db-f1-micro           # $15/月相当（起動時のみ）

# 本番相当（高性能）
--tier=db-custom-2-8192      # $150/月相当（起動時のみ）
```

### バックアップ保持ポリシー

古いバックアップを削除してストレージコストを削減：

```bash
# 30日以上前のバックアップを削除
gsutil -m rm gs://$GCS_BUCKET_NAME/database-snapshots/backup_$(date -d '30 days ago' +%Y%m%d)*.sql
```

または、GCSライフサイクル管理を設定：

```bash
# lifecycle.json
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "Delete"},
        "condition": {
          "age": 30,
          "matchesPrefix": ["database-snapshots/backup_"]
        }
      }
    ]
  }
}

# ライフサイクル設定を適用
gsutil lifecycle set lifecycle.json gs://$GCS_BUCKET_NAME
```

## 🔧 トラブルシューティング

### バックアップが見つからない

```bash
# GCSバケットの確認
gsutil ls gs://$GCS_BUCKET_NAME/database-snapshots/

# バケットが存在しない場合は作成
gsutil mb -p $GCP_PROJECT_ID gs://$GCS_BUCKET_NAME
```

### インスタンス作成が失敗する

```bash
# クォータを確認
gcloud compute project-info describe --project=$GCP_PROJECT_ID

# リージョンを変更してみる
export GCP_REGION="us-central1"
./scripts/cloud/setup-dev-env.sh
```

### 復元が遅い

- データベースサイズが大きい場合、復元に時間がかかります
- 解決策：
  1. 不要なデータを削除してから停止
  2. より高速なインスタンス（db-custom）を使用
  3. リージョンをGCSバケットと同じにする

## 📊 運用例

### パターンA: 週1回作業（推奨）

```bash
# 月曜朝（作業開始）
./scripts/cloud/setup-dev-env.sh    # 10分待機
# 作業...

# 月曜夜（作業終了）
./scripts/cloud/teardown-dev-env.sh # 5分待機

# 月額コスト: $0.02（GCS） + $0.50（1日稼働） = 約$0.52/月
```

### パターンB: 毎日作業

```bash
# 毎朝
./scripts/cloud/setup-dev-env.sh

# 毎晩
./scripts/cloud/teardown-dev-env.sh

# 月額コスト: $0.02（GCS） + $15（30日稼働、db-f1-micro） = 約$15/月
```

この場合、停止運用（activation-policy）の方が楽かもしれません。

### パターンC: 月1回のみ

```bash
# 月1回作業日
./scripts/cloud/setup-dev-env.sh    # 起動
# 作業...
./scripts/cloud/teardown-dev-env.sh # 停止

# 月額コスト: $0.02（GCS） + $0.50（1日稼働） = 約$0.52/月
```

**最もコスト効率が良い！**

## 🎯 まとめ

### メリット
- ✅ 使用しない期間は完全に$0（GCS課金のみ）
- ✅ データは完全に保持される
- ✅ バックアップの履歴管理が簡単
- ✅ 複数のバックアップポイントを保持可能

### デメリット
- ⚠️ 起動に10-15分かかる（初回作成時）
- ⚠️ 毎回バックアップ・復元の待ち時間がある
- ⚠️ 完全自動化には適さない

### こんな人におすすめ
- 週1回以下の利用頻度
- 起動時間は気にしない
- とにかくコストを抑えたい
- データのバックアップ履歴を残したい

### 向いていない人
- 毎日使う
- すぐに起動したい
- 自動化されたCI/CDで使う
