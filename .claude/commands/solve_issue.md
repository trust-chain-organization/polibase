---
allowed-tools: Read, Glob, Grep, Edit, MultiEdit, Write, Bash, TodoWrite, mcp__serena__check_onboarding_performed, mcp__serena__delete_memory, mcp__serena__find_file, mcp__serena__find_referencing_symbols, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__insert_after_symbol, mcp__serena__insert_before_symbol, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__onboarding, mcp__serena__read_memory, mcp__serena__remove_project, mcp__serena__replace_regex, mcp__serena__replace_symbol_body, mcp__serena__restart_language_server, mcp__serena__search_for_pattern, mcp__serena__switch_modes, mcp__serena__think_about_collected_information, mcp__serena__think_about_task_adherence, mcp__serena__think_about_whether_you_are_done, mcp__serena__write_memory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
description: GitHub Issueを自動的に解決するコマンド
---
ultrathink
# Issue解決ワークフロー

Issue番号: $ARGUMENTS

## 1. Issue内容の確認

!gh issue view $ARGUMENTS

## 2. ブランチの作成

現在のブランチ状態を確認し、必要に応じて新しいブランチを作成します。

!git status

## 3. 修正案の作成

上記のIssue内容を基に、以下の観点で修正案を作成してください：

1. **問題の理解**
   - Issueで報告されている問題を正確に理解する
   - 受け入れ基準を確認する

2. **技術的な解決策**
   - 実装方法を検討する
     - serena MCPを使用してコードベースを調査します。
   - 必要なファイルの変更を特定する
   - ユニットテストが必要な箇所を特定する

3. **実装計画**
   - タスクを細分化してTodoリストを作成する
   - 各タスクの優先順位を設定する

## 4. 実装

修正案が承認されたら、以下の手順で実装を進めてください：

1. **コードの実装**
   - 特定したファイルを修正する
     - serena MCPを使用して関連するコードを調査し、必要な変更を行います。
       - DRY原則に従い、重複コードを避けます
     - context7 MCPを使用してライブラリのドキュメントを確認し、適切なAPIとパッケージを使用します
   - 必要に応じて新しいファイルを作成する
   - コーディング規約に従う（Ruff、型チェック）

2. **ユニットテストの作成**
   - 新しい機能や修正した機能に対するテストを作成する
   - 既存のテストが壊れていないことを確認する

## 5. 動作確認

実装が完了したら、以下の動作確認を実行してください：

1. **機能の動作確認**
   - 実装した機能が期待通りに動作することを確認する
   - エッジケースも考慮する

2. **コード品質チェック**
   uv run --frozen ruff format .
   uv run --frozen ruff check . --fix
   uv run --frozen pyright

## 6. テストの実行

全てのテストが成功することを確認してください：

uv run pytest -xvs

テストが失敗した場合は、修正を行い再度テストを実行してください。

## 7. コミットとプルリクエスト

1. **変更内容の確認**
   !git status
   !git diff

2. **コミット**
   変更をコミットし、Issue番号を含むコミットメッセージを作成してください。

3. **プルリクエストの作成**
   !git push -u origin HEAD

   その後、以下の内容でプルリクエストを作成してください：
   - タイトル: Issue #$ARGUMENTS の解決
   - 本文: 実装内容の詳細説明
   - Issueへのリンク: Fixes #$ARGUMENTS

## 注意事項

- 各ステップで問題が発生した場合は、その都度修正を行ってください
- テストが全て成功するまでプルリクエストは作成しないでください
  - Github Actionsの予算が少なくJob時間制限があるため不要なCIを実行させないためです。
- コーディング規約（Ruff、型チェック）を遵守してください
