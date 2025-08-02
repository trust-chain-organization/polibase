---
allowed-tools: Read, Glob, Grep, Edit, MultiEdit, Write, Bash, TodoWrite, mcp__serena__check_onboarding_performed, mcp__serena__delete_memory, mcp__serena__find_file, mcp__serena__find_referencing_symbols, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__insert_after_symbol, mcp__serena__insert_before_symbol, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__onboarding, mcp__serena__read_memory, mcp__serena__remove_project, mcp__serena__replace_regex, mcp__serena__replace_symbol_body, mcp__serena__restart_language_server, mcp__serena__search_for_pattern, mcp__serena__switch_modes, mcp__serena__think_about_collected_information, mcp__serena__think_about_task_adherence, mcp__serena__think_about_whether_you_are_done, mcp__serena__write_memory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
description: PBIラベルのついたIssueをコードベースを調査して詳細化するコマンド
---
ultrathink
# PBI改善ワークフロー

Issue番号: $ARGUMENTS

## 1. Issue内容とラベルの確認

### Issueの取得
!gh issue view $ARGUMENTS

### ラベルの検証
!gh issue view $ARGUMENTS --json labels | jq -r '.labels[].name' | grep -q "PBI" || echo "警告: このIssueにはPBIラベルがありません"

## 2. 現在のPBI内容の分析

上記のIssue内容を基に、以下の観点で現在のPBIの不足点を特定してください：

1. **ユーザーストーリーの明確さ**
   - Who（誰が）、What（何を）、Why（なぜ）が明確か
   - ビジネス価値が明確か

2. **受入条件の具体性**
   - 測定可能な条件になっているか
   - テスト可能な内容か

3. **技術的詳細の充実度**
   - 実装範囲が明確か
   - 技術的な考慮事項が記載されているか

## 3. コードベースの調査

PBIに関連するコードベースを調査して、以下の情報を収集してください：
なお、コードベースの調査には serena MCP を使用します。

### 関連ファイルの特定
1. **既存の実装を調査**
   - 類似機能の実装パターン
   - 使用されているフレームワーク/ライブラリ
   - アーキテクチャパターン

2. **影響範囲の分析**
   - 変更が必要なモジュール
   - 依存関係の確認
   - テストの影響範囲

### 調査コマンド例
```bash
# 関連ファイルの検索
!rg -l "関連キーワード" --type py

# ディレクトリ構造の確認
!ls -la src/

# 既存のテストケースの確認
!find . -name "*test*.py" -type f | grep -E "関連モジュール"
```

## 4. PBIの詳細化（対話形式）

コードベースの調査結果を基に、ユーザーと対話しながらPBIを詳細化してください：

### 4.1 ユーザーストーリーの改善

**現在のストーリー:** [Issueから抽出]

**質問例:**
- このPBIの主要な利用者は誰ですか？（管理者、一般ユーザー、開発者など）
- この機能によって解決される具体的な問題は何ですか？
- 期待される成果や価値は何ですか？

**改善案の提示:**
```markdown
As a [利用者タイプ]
I want [具体的な機能/要求]
So that [明確な価値/利益]
```

### 4.2 受入条件の具体化

**現在の受入条件:** [Issueから抽出]

**質問例:**
- この機能が「完成した」と判断する具体的な基準は何ですか？
- どのような振る舞いをテストで確認すべきですか？
- パフォーマンスやセキュリティの要件はありますか？

**改善案の提示:**
```markdown
### 機能要件
- [ ] [具体的な機能要件1]
- [ ] [具体的な機能要件2]

### 非機能要件
- [ ] [パフォーマンス要件]
- [ ] [セキュリティ要件]

### テスト要件
- [ ] [単体テストの範囲]
- [ ] [統合テストの範囲]
```

### 4.3 技術的実装詳細の追加

**コードベース調査結果の共有:**
- 関連する既存実装のパターン
- 推奨されるアプローチ
- 考慮すべき技術的制約

**質問例:**
- 提案した実装アプローチで問題ないですか？
- 追加で考慮すべき技術的要件はありますか？
- 既存のコードとの統合で注意すべき点はありますか？

**改善案の提示:**
```markdown
### 技術的実装内容
#### アーキテクチャ
- [採用するパターン/アプローチ]
- [既存システムとの統合方法]

#### 実装範囲
- 新規作成ファイル:
  - `path/to/new/file.py`: [説明]
- 修正ファイル:
  - `path/to/existing/file.py`: [変更内容]

#### 依存関係
- 使用ライブラリ: [ライブラリ名とバージョン]
- 前提条件: [必要な環境や設定]
```

### 4.4 工数見積もりとリスク

**質問例:**
- この実装にどの程度の時間を見込んでいますか？
- 技術的な不確実性やリスクはありますか？
- 依存する他のタスクやPBIはありますか？

**改善案の提示:**
```markdown
### 見積もり
- 開発工数: [X日]
- レビュー/テスト: [Y日]
- 合計: [Z日]

### リスクと対策
- リスク1: [内容]
  - 対策: [対策内容]
- リスク2: [内容]
  - 対策: [対策内容]

### 依存関係
- ブロッカー: [依存するIssue/PBI]
- ブロック対象: [このPBIに依存するIssue/PBI]
```

## 5. PBI更新内容の確認

### 最終的なPBI内容

改善されたPBI内容を整理して、ユーザーに確認を求めてください：

```markdown
# [PBIタイトル]

## ユーザーストーリー
[改善されたユーザーストーリー]

## 背景
[問題の背景と解決したい課題]

## 受入条件
### 機能要件
[具体的な機能要件リスト]

### 非機能要件
[パフォーマンス、セキュリティなど]

### テスト要件
[必要なテストの範囲]

## 技術的実装内容
### アーキテクチャ
[技術的なアプローチ]

### 実装範囲
[作成/修正するファイルリスト]

### 依存関係
[使用ライブラリ、前提条件]

## 見積もりとリスク
### 工数見積もり
[開発、テスト、レビューの見積もり]

### リスクと対策
[識別されたリスクと対策]

### 依存関係
[他のIssue/PBIとの関係]

## 参考情報
[調査で得られた有用な情報、関連ドキュメントへのリンクなど]
```

## 6. Issueの更新

ユーザーの承認が得られたら、GitHubのIssueを更新します：

```bash
# Issue本文の更新
!gh issue edit $ARGUMENTS --body "[更新されたPBI内容]"

# 必要に応じてラベルの追加
!gh issue edit $ARGUMENTS --add-label "ready-for-development"

# コメントの追加（変更履歴として）
!gh issue comment $ARGUMENTS --body "PBIを詳細化しました。主な変更点：
- ユーザーストーリーを明確化
- 受入条件を具体化
- 技術的実装内容を追加
- 工数見積もりとリスク分析を追加"
```

## 7. 完了確認

### チェックリスト
- [ ] PBIラベルが付いているIssueであることを確認
- [ ] コードベースの調査を実施
- [ ] ユーザーとの対話でPBIを詳細化
- [ ] 全ての必要項目が記載されている
- [ ] ユーザーの承認を得た
- [ ] Issueを更新した

### 次のステップの案内

PBIの詳細化が完了しました。次のステップ：
1. 開発チームでのレビュー
2. 必要に応じて追加の詳細化
3. スプリントプランニングでの取り込み

## 注意事項

- PBIラベルがないIssueは対象外とする
- ユーザーとの対話を重視し、一方的な更新は避ける
- コードベースの調査結果を根拠として示す
- 技術的な詳細は実装者が理解できるレベルまで具体化する
- 既存のコーディング規約やアーキテクチャパターンに準拠する
