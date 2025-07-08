---
description: CI失敗を分析して修正するコマンド
---
ultrathink

# CI失敗解決ワークフロー

現在のブランチ: !git branch --show-current

## 1. CI状態の確認

### 現在のPRのCI状態を確認
!gh pr checks $(git branch --show-current) --json name,status,conclusion | jq -r '.[] | {name: .name, status: .status, conclusion: .conclusion}'

### 失敗しているチェックのみを表示
!gh pr checks $(git branch --show-current) --json name,status,conclusion | jq -r '.[] | select(.conclusion == "failure") | .name'

## 2. 失敗の詳細分析

失敗したチェックの詳細情報を取得：
!gh pr checks $(git branch --show-current) --json name,status,conclusion,detailsUrl | jq -r '.[] | select(.conclusion == "failure") | "Check: \(.name)\nStatus: \(.status)\nConclusion: \(.conclusion)\nDetails: \(.detailsUrl)\n"'

### ワークフローログの取得
最新の失敗したワークフローのログを確認：
!gh run list --branch=$(git branch --show-current) --limit=3 --json databaseId,workflowName,conclusion,createdAt | jq -r '.[] | select(.conclusion == "failure") | "Run ID: \(.databaseId)\nWorkflow: \(.workflowName)\nCreated: \(.createdAt)\n"'

## 3. 修正案の作成

上記のCI失敗情報を基に、以下の観点で修正案を作成してください：

1. **失敗原因の特定**
   - エラーメッセージの分析
   - 失敗したテストケースの確認
   - Lintエラーや型エラーの特定

2. **修正方針の決定**
   - 必要な変更箇所の特定
   - 修正方法の検討
   - 影響範囲の確認

3. **実装計画**
   - タスクの細分化とTodoリストの作成
   - 各修正の優先順位設定

## 4. 修正の実装

修正案に基づいて実装を進めてください：

1. **コードの修正**
   - 特定したエラーを修正する
   - コーディング規約に従う

2. **ローカルでの検証**
   - 関連するテストを実行する
   - Lintチェックを実行する
   - 型チェックを実行する

## 5. コード品質チェック

### Ruffによるフォーマットとチェック
!docker compose exec polibase uv run --frozen ruff format .
!docker compose exec polibase uv run --frozen ruff check . --fix

### 型チェック
!docker compose exec polibase uv run --frozen pyright

## 6. テストの実行

### 全テストの実行
!docker compose exec polibase uv run pytest

失敗したテストがある場合は、個別に実行して詳細を確認：
!docker compose exec polibase uv run pytest -xvs [失敗したテストファイル]

## 7. 変更の確認とプッシュ

### 変更内容の確認
!git status
!git diff

### コミットとプッシュ
変更をコミットし、CI失敗を修正したことを明記したコミットメッセージを作成してください。
その後、変更をプッシュしてCIを再実行させてください。

!git push

## 8. CI結果の再確認

プッシュ後、CIが成功することを確認：
!gh pr checks $(git branch --show-current) --watch

## 注意事項

- 各ステップで問題が発生した場合は、その都度対処してください
- ローカルでテストが通ることを確認してからプッシュしてください
- CI特有の環境差異（環境変数、依存関係など）に注意してください
- 必要に応じてCIの設定ファイル（.github/workflows/など）も確認・修正してください
