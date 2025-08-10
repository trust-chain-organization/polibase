# LLM評価テスト

## 概要

LLM評価テストは、Polibaseで使用される各種LLM処理の品質と精度を測定するためのテストスイートです。コスト削減のため、通常のCI/CDパイプラインからは除外され、手動トリガーで実行されます。

## 評価対象タスク

1. **議事録分割 (minutes_division)**
   - 議事録PDFからの発言者と発言内容の抽出精度を評価
   - メトリクス: 発言者一致率、内容類似度、順序精度

2. **発言者マッチング (speaker_matching)**
   - 発言者と政治家データベースのマッチング精度を評価
   - メトリクス: politician_ID一致率、信頼度スコア分布

3. **政党メンバー抽出 (party_member_extraction)**
   - 政党ウェブサイトからのメンバー情報抽出精度を評価
   - メトリクス: 抽出率、名前精度、属性精度

4. **会議メンバーマッチング (conference_member_matching)**
   - 会議メンバーと政治家のマッチング精度を評価
   - メトリクス: 精度(Precision)、再現率(Recall)、F1スコア

## ローカルでの実行

```bash
# 特定タスクの評価
polibase evaluate --task minutes_division

# カスタムデータセットを使用
polibase evaluate --task speaker_matching --dataset path/to/dataset.json

# 全タスクの評価
polibase evaluate --all
```

## GitHub Actionsでの実行

### 手動実行方法

1. GitHubリポジトリの[Actions](https://github.com/trust-chain-organization/polibase/actions)タブを開く
2. 左側のワークフロー一覧から「LLM Evaluation Tests」を選択
3. 右側の「Run workflow」ボタンをクリック
4. 実行パラメータを設定:
   - **Task**: 評価するタスク（空欄で全タスク実行）
   - **Custom dataset path**: カスタムデータセットのパス（オプション）
   - **Use real LLM API**: 実際のLLM APIを使用するか（要シークレット設定）
5. 「Run workflow」ボタンをクリックして実行

### 実行パラメータ

| パラメータ | 説明 | 必須 | デフォルト |
|----------|------|------|-----------|
| task | 評価するタスク名 | いいえ | 全タスク |
| dataset | カスタムデータセットパス | いいえ | デフォルトデータセット |
| use_real_llm | 実LLM APIの使用 | いいえ | false (モック使用) |

### シークレット設定

実際のLLM APIを使用する場合は、以下のシークレットを設定する必要があります：

- `GOOGLE_API_KEY`: Google Gemini APIのAPIキー

設定方法:
1. リポジトリの Settings → Secrets and variables → Actions
2. 「New repository secret」をクリック
3. Name: `GOOGLE_API_KEY`、Value: 実際のAPIキーを入力

## コスト見積もり

各タスクの実行時の概算コスト（Gemini API使用時）:

- 議事録分割: 約50,000トークン (~$0.50)
- 発言者マッチング: 約30,000トークン (~$0.30)
- 政党メンバー抽出: 約40,000トークン (~$0.40)
- 会議メンバーマッチング: 約35,000トークン (~$0.35)
- **全タスク合計**: 約155,000トークン (~$1.55)

*注: 実際のコストはデータセットのサイズと内容により変動します*

## CI/CDパイプラインとの関係

- **通常のCI** (`test.yml`): PRやプッシュ時に自動実行、評価テストは除外
- **評価テスト** (`llm-evaluation.yml`): 手動トリガーのみ、コスト管理のため

この分離により、開発速度を維持しながらAPIコストを管理できます。

## データセット形式

評価データセットはJSON形式で、以下の構造を持ちます:

```json
{
  "version": "1.0.0",
  "task_type": "タスクタイプ",
  "metadata": {
    "created_at": "作成日時",
    "created_by": "作成者",
    "description": "説明"
  },
  "test_cases": [
    {
      "id": "テストケースID",
      "description": "テストケースの説明",
      "input": {
        // タスク固有の入力データ
      },
      "expected_output": {
        // 期待される出力
      }
    }
  ]
}
```

## トラブルシューティング

### 評価が失敗する場合

1. データセットの形式が正しいか確認
2. 必要な環境変数が設定されているか確認
3. データベース接続が正常か確認

### APIキーエラーの場合

1. シークレットが正しく設定されているか確認
2. APIキーの有効性を確認
3. APIクォータを確認

## 今後の改善予定

- [ ] 実際のLLMサービスとの統合実装
- [ ] より詳細なメトリクス収集
- [ ] 結果の可視化ダッシュボード
- [ ] 自動的なベースライン比較
- [ ] コスト最適化のための並列実行
