---
allowed-tools: Read, Glob, Grep, Edit, MultiEdit, Write, Bash, TodoWrite, mcp__serena__check_onboarding_performed, mcp__serena__delete_memory, mcp__serena__find_file, mcp__serena__find_referencing_symbols, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__insert_after_symbol, mcp__serena__insert_before_symbol, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__onboarding, mcp__serena__read_memory, mcp__serena__remove_project, mcp__serena__replace_regex, mcp__serena__replace_symbol_body, mcp__serena__restart_language_server, mcp__serena__search_for_pattern, mcp__serena__switch_modes, mcp__serena__think_about_collected_information, mcp__serena__think_about_task_adherence, mcp__serena__think_about_whether_you_are_done, mcp__serena__write_memory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
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

3. **serena MCP, context7 MCPを使用したコードベースの調査**
   - 必要に応じて関連するコードを調査し、修正が必要な箇所を特定する
   - 例: `mcp__serena__find_file`, `mcp__serena__get_symbols_overview` などを使用
   - 例: `mcp__context7__resolve-library-id`, `mcp__context7__get-library-docs` でライブラリのドキュメントを確認

## 5. コード品質チェック

### Ruffによるフォーマットとチェック
uv run --frozen ruff format .
uv run --frozen ruff check . --fix

### 型チェック
uv run --frozen pyright

## 6. テストの実行

### 全テストの実行
uv run pytest

失敗したテストがある場合は、個別に実行して詳細を確認：
uv run pytest -xvs [失敗したテストファイル]

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
