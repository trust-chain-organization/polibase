---
allowed-tools: Read, Glob, Grep, Edit, MultiEdit, Write, Bash, TodoWrite, mcp__serena__check_onboarding_performed, mcp__serena__delete_memory, mcp__serena__find_file, mcp__serena__find_referencing_symbols, mcp__serena__find_symbol, mcp__serena__get_symbols_overview, mcp__serena__insert_after_symbol, mcp__serena__insert_before_symbol, mcp__serena__list_dir, mcp__serena__list_memories, mcp__serena__onboarding, mcp__serena__read_memory, mcp__serena__remove_project, mcp__serena__replace_regex, mcp__serena__replace_symbol_body, mcp__serena__restart_language_server, mcp__serena__search_for_pattern, mcp__serena__switch_modes, mcp__serena__think_about_collected_information, mcp__serena__think_about_task_adherence, mcp__serena__think_about_whether_you_are_done, mcp__serena__write_memory, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
description: GitHub IssueをProduct Backlog Items (PBIs)に分解するコマンド
---
ultrathink
# Product Goal分解ワークフロー

Issue番号: $ARGUMENTS

## 1. Issue内容の詳細確認

### Issueの取得と分析
!gh issue view $ARGUMENTS

### ラベルとマイルストーンの確認
!gh issue view $ARGUMENTS --json labels,milestone,assignees | jq -r '{labels: .labels[].name, milestone: .milestone.title, assignees: .assignees[].login}'

## 2. Product Goalの理解

上記のIssue内容を基に、以下の観点でProduct Goalを分析してください：

1. **ビジネス価値の特定**
   - このGoalが解決しようとしている問題は何か
   - 誰にとっての価値を生み出すのか
   - 成功の定義は何か

2. **スコープの明確化**
   - 含まれる機能要件
   - 含まれない事項（Out of Scope）
   - 前提条件と制約事項

3. **技術的な考慮事項**
   - アーキテクチャへの影響
   - 既存システムとの統合点
   - 技術的リスクと課題

## 3. PBIへの分解

### 分解の原則
- **INVEST原則**に従う（Independent, Negotiable, Valuable, Estimable, Small, Testable）
- 各PBIは独立して価値を提供できる単位にする
- 1-3日で完了できるサイズを目安とする
- 依存関係を明確にする

### PBI作成テンプレート

各PBIには以下の情報を含めてください：

```markdown
## PBI-[番号]: [タイトル]

### 概要
[このPBIで実現する内容の簡潔な説明]

### ユーザーストーリー
As a [ユーザータイプ]
I want [機能/要求]
So that [価値/利益]

### 受入条件
- [ ] [具体的な条件1]
- [ ] [具体的な条件2]
- [ ] [具体的な条件3]

### 技術的実装内容
- [実装すべき主要コンポーネント]
- [変更が必要なファイル/モジュール]
- [必要なテストケース]

### 依存関係
- 前提PBI: [依存するPBI番号]
- ブロック対象: [このPBIがブロックするPBI番号]

### 見積もり
- 開発工数: [時間/日数]
- 複雑度: [Low/Medium/High]
```

## 4. 実装順序の決定

PBIの実装順序を以下の観点で決定してください：

1. **価値の優先順位**
   - ビジネス価値の高いものから
   - リスクの高いものを早期に

2. **技術的依存関係**
   - 基盤となる機能から実装
   - 依存関係のグラフを考慮

3. **フィードバックサイクル**
   - 早期にフィードバックが得られるものを優先
   - 検証可能な単位で進める

## 5. PBI一覧の作成

### マークダウン形式でのPBI一覧

```markdown
# Product Goal: [Issue #$ARGUMENTS のタイトル]

## PBI一覧

| PBI番号 | タイトル | 優先度 | 見積もり | 依存関係 | ステータス |
|---------|----------|--------|----------|----------|------------|
| PBI-001 | [タイトル] | High | 2日 | なし | 未着手 |
| PBI-002 | [タイトル] | Medium | 1日 | PBI-001 | 未着手 |
| ...     | ...      | ...    | ...      | ...      | ...        |

## 実装ロードマップ

### Phase 1: 基盤構築（[期間]）
- PBI-001: [タイトル]
- PBI-002: [タイトル]

### Phase 2: コア機能（[期間]）
- PBI-003: [タイトル]
- PBI-004: [タイトル]

### Phase 3: 拡張機能（[期間]）
- PBI-005: [タイトル]
- PBI-006: [タイトル]
```

## 6. GitHub Issueの作成

### 各PBIのIssue作成

分解したPBIごとに個別のIssueを直接作成してください。以下の手順で進めます：

1. **最初のPBI作成**
   ```bash
   gh issue create \
     --title "[PBI-001] [タイトル]" \
     --body "[PBIの詳細内容]" \
     --label "pbi,enhancement" \
     --assignee "[担当者]"
   ```

2. **作成されたIssue番号を記録**
   各PBIのIssue作成後、返されるIssue番号を記録し、依存関係のあるPBIのbodyに反映する

3. **依存関係の更新**
   後続のPBIを作成する際は、前提PBIのIssue番号を含めて作成：
   ```bash
   gh issue create \
     --title "[PBI-002] [タイトル]" \
     --body "## 概要
   [内容]

   ## 依存関係
   - 前提PBI: #[実際のIssue番号]
   - ブロック対象: [後で更新]

   [その他の内容]" \
     --label "pbi,enhancement" \
     --assignee "[担当者]"
   ```

4. **Issue番号の管理**
   作成したIssue番号を管理するため、以下の形式で記録：
   ```
   PBI-001: #[Issue番号]
   PBI-002: #[Issue番号]
   ...
   ```

### 親Issueとの関連付け

全てのPBIを作成した後、元のIssue（#$ARGUMENTS）にコメントを追加：

```bash
gh issue comment $ARGUMENTS --body "## 分解されたPBI

このProduct Goalを以下のPBIに分解しました：

- [ ] #[PBI-001のIssue番号]: [タイトル]
- [ ] #[PBI-002のIssue番号]: [タイトル]
- [ ] #[PBI-003のIssue番号]: [タイトル]
- [ ] #[PBI-004のIssue番号]: [タイトル]
- [ ] #[PBI-005のIssue番号]: [タイトル]
- [ ] #[PBI-006のIssue番号]: [タイトル]

## 実装計画

### Phase 1: 基盤構築（[期間]）
- #[番号]: [タイトル]
- #[番号]: [タイトル]

### Phase 2: コア機能実装（[期間]）
- #[番号]: [タイトル]
- #[番号]: [タイトル]

### Phase 3: 拡張機能（[期間]）
- #[番号]: [タイトル]
- #[番号]: [タイトル]

詳細な技術設計とロードマップは各PBIを参照してください。"
```

### 依存関係の更新

必要に応じて、作成したPBIの依存関係を更新：

```bash
# ブロック対象のPBI番号が確定した後
gh issue edit [Issue番号] --body "[更新されたbody内容]"
```

## 7. プロジェクト管理の設定

### GitHubプロジェクトボードの活用

1. **カンバンボードの設定**
   - Todo, In Progress, Review, Doneのカラム
   - 各PBIをカードとして配置

2. **自動化の設定**
   - PRとIssueの自動リンク
   - ステータスの自動更新

3. **進捗の可視化**
   - バーンダウンチャート
   - 速度（ベロシティ）の測定

## 8. 最終確認とレビュー

### チェックリスト

- [ ] 全てのPBIがINVEST原則を満たしているか
- [ ] 依存関係が明確に定義されているか
- [ ] 各PBIに明確な受入条件があるか
- [ ] 実装順序が論理的か
- [ ] 全体の見積もりが現実的か

### ステークホルダーとの確認

分解結果を以下の関係者と確認してください：
- プロダクトオーナー
- 技術リード
- 実装担当者

## 注意事項

- PBIは小さすぎず大きすぎない適切なサイズに保つ
- 各PBIは独立してテスト可能であること
- 技術的負債の解消もPBIとして含める
- ドキュメント作成やテスト作成も独立したPBIとして扱う
- 不確実性の高い部分は調査スパイクとして別PBIにする
- **Issue作成は実際にghコマンドで実行し、作成されたIssue番号を記録する**
- **依存関係は実際のIssue番号で管理し、後から更新が必要な場合はgh issue editで更新する**
- **tmpディレクトリにシェルスクリプトを作成するのではなく、直接ghコマンドを実行する**
