---
allowed-tools: Read, Glob, Grep, Edit, Write, Bash, TodoWrite, mcp__serena__check_onboarding_performed, mcp__serena__delete_memory, mcp__serena__find_file, mcp__serena__find_referencing_symbols, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__insert_after_symbol, mcp__serena__insert_before_symbol, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__onboarding, mcp__serena__read_memory, mcp__serena__remove_project, mcp__serena__replace_regex, mcp__serena__replace_symbol_body, mcp__serena__restart_language_server, mcp__serena__search_for_pattern, mcp__serena__switch_modes, mcp__serena__think_about_collected_information, mcp__serena__think_about_task_adherence, mcp__serena__think_about_whether_you_are_done, mcp__serena__write_memory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
description: 動作確認手順をサクッとまとめてPRにコメントするコマンド
---
ultrathink

# 動作確認ワークフロー

このコマンドは、PR（Pull Request）の動作確認を効率化するために以下を実施します：
1. PR、関連Issue、変更差分の確認
2. 動作確認方法の判定（Streamlit操作 or CLI実行）
3. Streamlitの場合は操作手順を表示、CLIの場合は実際に動作確認を実行
4. 動作確認内容をPRにコメント

## 1. 現在のブランチとPR情報の取得

現在のブランチを確認：
!git branch --show-current

現在のブランチのPR情報を取得：
!gh pr view $(git branch --show-current) --json number,title,body,url

## 2. 関連Issueの取得

PRの本文からIssue番号を抽出し、Issue内容を確認します。

PRの本文を確認：
!gh pr view $(git branch --show-current) --json body --jq .body

Issue番号が含まれている場合（例: #123, Fixes #456など）、そのIssueの詳細を取得：
（PRの本文から `#数字` や `Fixes #数字` のパターンを探し、Issue番号を特定してください）

各Issue番号について、以下のコマンドでIssue詳細を取得：
!gh issue view [ISSUE_NUMBER]

## 3. 変更差分の確認

変更されたファイルのリストを取得：
!git diff --name-only origin/main...HEAD

変更内容の詳細を確認：
!git diff origin/main...HEAD

## 4. 動作確認方法の判定

変更差分の内容を分析し、以下の観点で動作確認方法を判定してください：

### 判定基準

**Streamlit操作が必要なケース：**
- `src/streamlit/` 配下のファイルが変更されている
- `src/interfaces/web/` 配下のファイルが変更されている
- UIに関連する機能追加・修正
- データの表示方法の変更

**CLI実行で完結するケース：**
- CLIコマンドの追加・修正（`src/cli/` 配下）
- バックエンドロジックのみの変更
- データベーススキーマの変更（マイグレーション）
- テストコードのみの変更
- バッチ処理やスクリプトの修正

### 動作確認の実施

#### ケース1: Streamlit操作が必要な場合

以下の操作手順をユーザーに表示してください：

```
# Streamlit動作確認手順

## 前提条件
- Dockerコンテナが起動していること
- 必要に応じてデータベースがリセットされていること

## 確認手順

1. Streamlitを起動
   ```bash
   just up
   ```

2. ブラウザでアクセス
   - Streamlitのポート番号を確認: `docker ps` または `just ports`
   - ブラウザで http://localhost:[PORT] を開く

3. 以下の操作を実施して動作確認
   [ここに、変更内容に基づいた具体的な操作手順を記載]

   例：
   - 「〇〇管理」タブに移動
   - 「新規登録」ボタンをクリック
   - 必要な情報を入力
   - 「保存」ボタンをクリック
   - データが正しく保存されたことを確認

4. 動作確認のポイント
   [変更内容に応じた確認ポイントを記載]

   例：
   - エラーが表示されないこと
   - データが正しく表示されること
   - バリデーションが正しく動作すること
```

#### ケース2: CLI実行で完結する場合

以下のコマンドを実際に実行して動作確認を行ってください：

```bash
# 動作確認コマンドの実行

# 例: 新しいCLIコマンドが追加された場合
just exec polibase [新しいコマンド] --help

# 例: データ処理系のコマンドの場合
just exec polibase [コマンド名] [オプション]

# 例: テストの実行
just test
```

**実行すべきコマンド：**
[変更内容に基づいて、実際に実行すべきコマンドを特定し、実行してください]

実行結果を確認し、以下の点をチェック：
- エラーが発生しないこと
- 期待される出力が得られること
- データベースに正しくデータが保存されること（必要に応じて確認）

## 5. 動作確認結果のまとめ

以下の形式で動作確認結果をまとめてください：

```markdown
## 動作確認結果

### 確認内容
[実施した動作確認の概要]

### 確認方法
**Streamlit操作** / **CLI実行** （該当する方を記載）

### Streamlit操作手順（Streamlit操作の場合）
1. [手順1]
2. [手順2]
3. [手順3]
...

### CLI実行結果（CLI実行の場合）
```bash
# 実行コマンド
[実行したコマンド]

# 実行結果
[コマンドの出力結果]
```

### 確認ポイント
- [ ] [確認ポイント1]
- [ ] [確認ポイント2]
- [ ] [確認ポイント3]

### 備考
[その他の注意事項や補足情報]
```

## 6. PRへのコメント投稿

まとめた動作確認結果をPRにコメントとして投稿してください：

!gh pr comment $(git branch --show-current) --body "[上記でまとめた動作確認結果のマークダウンテキスト]"

## 注意事項

- Issue番号の抽出は正規表現で柔軟に対応してください（#123, Fixes #456, Closes #789 など）
- 変更内容が複雑な場合は、複数の動作確認手順が必要になる可能性があります
- Streamlit操作手順は、変更内容に応じて具体的かつ実用的なものにしてください
- CLI実行の場合は、実際にコマンドを実行して結果を確認してください
- エラーが発生した場合は、その内容もPRコメントに含めてください
