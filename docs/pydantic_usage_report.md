# Pydantic使用状況調査レポート

## 概要
本ドキュメントは、polibaseプロジェクトにおけるPydanticの現在の使用状況を調査した結果をまとめたものです。

## 調査結果

### 1. Pydanticの導入状況
- **Pydantic バージョン**: 2.11.4（langchainの依存関係として暗黙的に導入）
- **pyproject.tomlへの記載**: なし（問題点）

### 2. Pydanticを使用しているモジュール

以下の13ファイルでPydanticが使用されています：

#### データモデル定義ファイル
1. `src/minutes_divide_processor/models.py` - 議事録分割処理のモデル
2. `src/party_member_extractor/models.py` - 政党議員抽出のモデル
3. `src/conference_member_extractor/models.py` - 会議体メンバー抽出のモデル
4. `src/parliamentary_group_member_extractor/models.py` - 議員団メンバー抽出のモデル
5. `src/politician_extract_processor.disabled/models.py` - 政治家抽出処理のモデル（無効化中）

#### サービス・処理ファイル
6. `src/parliamentary_group_member_extractor/extractor.py`
7. `src/conference_member_extractor/extractor.py`
8. `src/database/speaker_matching_service.py`
9. `src/database/politician_matching_service.py`
10. `src/services/chain_factory.py`
11. `src/services/llm_service.py`
12. `src/database/speaker_matching_service_refactored.py`

#### テストファイル
13. `tests/test_llm_services.py`

### 3. Pydanticを使用していない主要モジュール

#### データベース層
- 全てのリポジトリクラス（`*_repository.py`）
- 生のSQL文とdictを使用してデータを扱っている
- 型安全性が確保されていない

#### Web UI層
- `src/streamlit_app.py`
- `src/monitoring_app.py`

#### CLI層
- `src/cli.py`および関連コマンドファイル

### 4. 現在の課題

1. **暗黙的な依存関係**
   - Pydanticがpyproject.tomlに明示的に記載されていない
   - langchainの依存関係に頼っている状態

2. **一貫性の欠如**
   - 一部のモジュールではPydanticを使用
   - データベース層では未使用
   - 型安全性が部分的にしか確保されていない

3. **データ検証の不足**
   - リポジトリ層でのデータ検証が手動
   - 実行時エラーのリスク

## 改善提案

### フェーズ1: 基盤整備
1. pyproject.tomlにPydanticを明示的に追加
2. データベース層用の基本Pydanticモデルを作成

### フェーズ2: 段階的移行
1. 主要なエンティティ（politicians、meetings、speakers等）のPydanticモデルを作成
2. BaseRepositoryにPydanticモデルサポートを追加
3. 各リポジトリを段階的に移行

### フェーズ3: 完全移行
1. 全てのデータ層でPydanticを使用
2. APIレスポンス/リクエストの型安全性確保
3. CLI引数のバリデーション強化

## 期待される効果

1. **型安全性の向上**
   - コンパイル時の型チェック強化
   - 実行時のデータ検証

2. **開発効率の向上**
   - IDEの補完機能の改善
   - バグの早期発見

3. **保守性の向上**
   - データ構造の明確化
   - ドキュメント自動生成の可能性
