---
description: GitHub Actions経由でClaudeがレビューしたコメントを取得して対応するコマンド
---
ultrathink
# Claude Code Action レビュー対応ワークフロー

現在のブランチ: !git branch --show-current

## 1. PRコメントの取得

### 現在のブランチのPRコメントを全て取得
!gh pr view $(git branch --show-current) --comments --json comments | jq -r '.comments'

### @claudeによる最新コメントを取得
!gh pr view $(git branch --show-current) --comments --json comments | jq -r '.comments | map(select(.author.login == "github-actions[bot]" and (.body | contains("@claude")))) | sort_by(.createdAt) | last | .body'

### コメント作成日時も含めて表示
!gh pr view $(git branch --show-current) --comments --json comments | jq -r '.comments | map(select(.author.login == "github-actions[bot]" and (.body | contains("@claude")))) | sort_by(.createdAt) | last | "作成日時: \(.createdAt)\n\nレビュー内容:\n\(.body)"'

## 2. レビュー内容の分析

上記で取得したClaudeのレビューコメントを分析し、以下の観点で対応計画を立ててください：

1. **指摘事項の整理**
   - セキュリティ関連の指摘
   - パフォーマンス改善の提案
   - コード品質に関する指摘
   - バグや潜在的な問題の指摘

2. **優先順位の決定**
   - 必須対応項目（MUST fix）
   - 推奨対応項目（SHOULD fix）
   - 任意対応項目（NICE to have）

3. **実装計画の作成**
   - 各指摘事項への対応方法
   - 必要な変更箇所の特定
   - タスクのTodoリスト化

## 3. 現在のコード状態の確認

### 変更されたファイルの確認
!git diff --name-only origin/main...HEAD

### PR全体の差分確認
!gh pr diff $(git branch --show-current) --name-only

## 4. レビュー指摘の修正実装

レビューコメントに基づいて修正を実施してください：

1. **コードの修正**
   - 指摘された問題を修正
   - 提案された改善を実装
   - コーディング規約の遵守

2. **修正内容の検証**
   - 修正が指摘事項に対応しているか確認
   - 新たな問題を引き起こしていないか確認

## 5. コード品質チェック

### Ruffによるフォーマットとチェック
!docker compose exec polibase uv run --frozen ruff format .
!docker compose exec polibase uv run --frozen ruff check . --fix

### 型チェック
!docker compose exec polibase uv run --frozen pyright

## 6. テストの実行

### 関連するテストの実行
!docker compose exec polibase uv run pytest -xvs

テストが失敗した場合は、修正してから再実行してください。

## 7. 修正内容の確認とコミット

### 変更内容の確認
!git status
!git diff

### コミット
Claudeのレビュー指摘に対応したことを明記したコミットメッセージを作成してください：
- "Address Claude's review comments: [対応内容の要約]"
- 各指摘事項への対応を箇条書きで記載

## 8. プッシュとフォローアップ

### 変更をプッシュ
!git push

### レビューへの返信コメント
プッシュ後、以下の内容でClaudeのレビューコメントに返信してください：

```
@claude レビューありがとうございます。以下の対応を行いました：

[対応内容の箇条書き]

修正内容はコミット [コミットハッシュ] で確認できます。
```

返信は以下のコマンドで投稿できます：
!gh pr comment $(git branch --show-current) --body "[返信内容]"

## 9. CI結果の確認

修正後のCIが成功することを確認：
!gh pr checks $(git branch --show-current) --watch

## 注意事項

- Claudeの指摘は建設的なフィードバックとして受け止め、コード品質向上に活用してください
- すべての指摘に対応する必要はありませんが、対応しない場合はその理由を明確にしてください
- セキュリティ関連の指摘は最優先で対応してください
- レビューコメントへの返信は、対応内容を明確に記載してください
