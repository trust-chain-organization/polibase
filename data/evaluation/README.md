# Polibase評価データセット作成ガイド

## 概要

このディレクトリには、PolibaseのLLM処理機能を評価するためのデータセットが格納されています。
データセットはGit管理可能なJSON形式で定義され、バージョン管理とレビューが可能です。

## ディレクトリ構造

```
data/evaluation/
├── README.md                    # このファイル
├── schema/
│   └── evaluation_dataset.json  # JSONスキーマ定義
├── datasets/                    # タスク別データセット
│   ├── minutes_division/        # 議事録分割タスク
│   ├── speaker_matching/        # 発言者マッチングタスク
│   ├── party_member_extraction/ # 政党メンバー抽出タスク
│   └── conference_member_matching/ # 議会メンバーマッチングタスク
└── results/                     # 評価結果（gitignored）
    └── .gitkeep
```

## サポートされるタスク

### 1. minutes_division（議事録分割）
PDFや文字列形式の議事録を個別の発言に分割するタスク。

**入力**:
- `text`: 分割対象の議事録テキスト
- `meeting_info`: 会議情報（オプション）

**出力**:
- `conversations`: 発言者名、内容、順序を含む発言の配列

### 2. speaker_matching（発言者マッチング）
議事録の発言者を既存の政治家データベースとマッチングするタスク。

**入力**:
- `speaker_name`: マッチング対象の発言者名
- `context`: 会議コンテキストと候補者リスト

**出力**:
- `matched_politician_id`: マッチした政治家のID
- `confidence`: マッチング信頼度（0-1）
- `match_reason`: マッチング理由の説明

### 3. party_member_extraction（政党メンバー抽出）
政党のウェブサイトから議員情報を抽出するタスク。

**入力**:
- `html_content`: 政党メンバーページのHTML
- `party_name`: 政党名
- `url`: ソースURL

**出力**:
- `politicians`: 名前、政党、役職、選挙区等を含む政治家情報の配列

### 4. conference_member_matching（議会メンバーマッチング）
議会メンバーリストと政治家データベースのバッチ名寄せ処理を評価するタスク。

**入力**:
- `conference_members`: 名寄せ対象の議会メンバーリスト
  - `member_id`: メンバーの一意識別子
  - `name`: メンバー名
  - `party_affiliation`: 所属政党/会派
  - `role`: 議会での役職
  - `conference_id`: 議会ID
- `politician_candidates`: データベースから取得した政治家候補リスト
  - `politician_id`: 政治家のデータベースID
  - `name`: 政治家名
  - `party`: 政党
  - `district`: 選挙区

**出力**:
- `matches`: 各メンバーのマッチング結果配列
  - `member_id`: メンバーID
  - `politician_id`: マッチした政治家のID
  - `match_status`: マッチステータス（matched/needs_review/no_match）
  - `confidence`: マッチング信頼度（0-1）
  - `match_reason`: マッチング理由の説明
  - `alternative_matches`: 曖昧なケースの代替候補
- `statistics`: バッチ処理全体の統計
  - `total_members`: 処理メンバー総数
  - `matched`: 高信頼度マッチ数
  - `needs_review`: レビュー必要数
  - `no_match`: マッチなし数
  - `match_rate`: マッチング成功率
  - `avg_confidence`: 平均信頼度スコア

## データセット作成方法

### 1. スキーマに従う

すべてのデータセットは`schema/evaluation_dataset.json`で定義されたJSONスキーマに従う必要があります。

### 2. 必須フィールド

各データセットには以下のフィールドが必須です：

```json
{
  "version": "1.0.0",           // セマンティックバージョニング
  "task_type": "タスク名",       // 上記4タスクのいずれか
  "metadata": {
    "created_at": "ISO8601日時",
    "created_by": "作成者",
    "description": "説明"
  },
  "test_cases": []              // テストケースの配列
}
```

### 3. テストケースの構造

各テストケースには以下の要素が含まれます：

```json
{
  "id": "一意のID",
  "description": "テストケースの説明",
  "input": {
    // タスク固有の入力データ
  },
  "expected_output": {
    // 期待される出力データ
  },
  "evaluation_criteria": {
    "priority": "low|medium|high",
    "difficulty": "easy|medium|hard",
    "notes": "評価時の注意事項"
  }
}
```

### 4. バージョニング

- データセットのバージョンはセマンティックバージョニング（major.minor.patch）を使用
- 破壊的変更: majorバージョンを上げる
- 機能追加: minorバージョンを上げる
- バグ修正: patchバージョンを上げる

### 5. ファイル命名規則

データセットファイルは**用途・カテゴリベース**の命名を推奨します：
- `basic_cases.json` - 基本的なテストケース
- `edge_cases.json` - エッジケース
- `complex_cases.json` - 複雑なパターン
- `{source}_cases.json` - 特定ソースからのケース
- `golden_set.json` - 正解が確定したゴールデンセット

**避けるべき命名**:
- `sample_v1.json` - ファイル名でのバージョン管理は避ける（データセット内のversionフィールドで管理）

## データセットの検証

作成したデータセットはJSONスキーマに対して検証できます：

```python
import json
import jsonschema

# スキーマの読み込み
with open('schema/evaluation_dataset.json', 'r') as f:
    schema = json.load(f)

# データセットの読み込み
with open('datasets/minutes_division/sample_v1.json', 'r') as f:
    dataset = json.load(f)

# 検証
jsonschema.validate(dataset, schema)
```

## ベストプラクティス

### 1. データの多様性
- 簡単なケースから複雑なケースまで幅広くカバー
- エッジケース（特殊文字、長文、欠損データ等）を含める
- 実際のデータに近い形式を使用

### 2. 期待される出力の明確化
- 曖昧さを排除し、明確な正解を定義
- 複数の正解がある場合は、その旨を明記
- 信頼度スコアの基準を一貫させる

### 3. メタデータの充実
- テストケースの意図を明確に記述
- 難易度と優先度を適切に設定
- 評価時の注意点を記載

### 4. バージョン管理
- 変更履歴をコミットメッセージに記録
- 大きな変更はプルリクエストでレビュー
- データセットの互換性を考慮

## 評価結果の管理

評価結果は`results/`ディレクトリに保存されますが、このディレクトリは.gitignoreされています。
結果を共有する場合は、別途レポートを作成してドキュメント化してください。

## トラブルシューティング

### JSONスキーマ検証エラー
- スキーマ定義を確認し、必須フィールドが含まれているか確認
- データ型が正しいか確認（特に数値と文字列の混同に注意）

### 文字エンコーディング問題
- ファイルはUTF-8で保存
- 日本語文字が正しく表示されるか確認

### バージョン競合
- 同じバージョン番号を再利用しない
- マージ時はバージョン番号を調整

## 貢献方法

新しいデータセットを追加する場合：

1. 適切なタスクディレクトリにファイルを作成
2. JSONスキーマに従ってデータを記述
3. サンプルデータを参考に形式を統一
4. プルリクエストを作成してレビューを受ける

## 関連ドキュメント

- [Polibase README](../../README.md)
- [Clean Architecture Migration](../../docs/CLEAN_ARCHITECTURE_MIGRATION.md)
- [Issue #353](https://github.com/trust-chain-organization/polibase/issues/353) - 評価システム全体の親Issue
