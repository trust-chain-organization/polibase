# BAML vs Pydantic 技術調査レポート

**Issue**: #729
**調査日**: 2025-11-08
**ステータス**: 完了
**結論**: 短期的にはPydantic継続を推奨、中期的にPoCで効果検証

---

## エグゼクティブサマリー

PolibaseのLLM周りの型チェックについて、PydanticとBAMLの技術比較を実施しました。

**主な発見**:
- BAMLはトークン使用量を80%削減できる可能性
- しかし、LangChainとの統合が不可能（BAMLはLangChainの代替）
- 移行にはLangChain全体の置き換えが必要（影響範囲：19ファイル以上）

**推奨アクション**:
1. **短期（現在）**: Pydanticを継続使用
2. **中期（次四半期）**: 小規模PoCでBAMLの効果を実測
3. **長期（半年後）**: PoCの結果次第で全面移行を判断

---

## 1. 背景と目的

### 1.1 背景

Issue #729で指摘されたように、「pydanticだとLLMのアウトプット周りの型とか綺麗にかけていない気がする」という懸念があります。

参考資料: https://docs.boundaryml.com/guide/comparisons/baml-vs-pydantic

### 1.2 調査目的

以下の点を明確化し、技術的判断の材料を提供すること：

- BAMLとPydanticの技術的な違い
- 移行のメリット・デメリット
- 移行コストと工数見積もり
- トークンコストへの影響
- 推奨アクション

---

## 2. 技術比較

### 2.1 Pydantic

#### 概要
Pythonの汎用データ検証ライブラリ。LLM以外の用途でも広く使用される。

#### 主な特徴
- ✅ 成熟したエコシステム
- ✅ LangChainとの深い統合
- ✅ 豊富なドキュメントとコミュニティ
- ✅ 汎用的なデータ検証が可能
- ⚠️ LLM特化の機能は限定的
- ⚠️ トークン使用量が多い

#### Polibaseでの使用状況
- **使用ファイル数**: 19ファイル
- **主な用途**:
  1. LLMアウトプットの型定義（議員抽出、話者マッチング、議事録処理）
  2. DTO（データ転送オブジェクト）
  3. データベースモデル（`PydanticBaseModel`）
- **統合方法**: LangChainの`with_structured_output(pydantic_schema)`

#### コード例
```python
from pydantic import BaseModel, Field

class ExtractedMember(BaseModel):
    """抽出された議員団メンバー情報"""
    name: str = Field(description="議員名")
    role: str | None = Field(default=None, description="役職")
    party_name: str | None = Field(default=None, description="所属政党名")

# LangChainとの統合
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")
structured_llm = llm.with_structured_output(ExtractedMember)
```

### 2.2 BAML (BoundaryML)

#### 概要
LLM構造化抽出のための専用ソリューション。LLMとの対話に最適化された型システムとツールチェーンを提供。

#### 主な特徴
- ✅ **トークン効率**: Pydanticより80%削減
- ✅ **ボイラープレート削減**: パース、リトライ、エラーハンドリングが自動生成
- ✅ **開発体験**: VSCode統合、即座にテスト可能
- ✅ **マルチモデル対応**: 20以上のLLMプロバイダー
- ✅ **組み込みレジリエンス**: リトライ、フォールバック、エラーハンドリング
- ⚠️ 新しいツールのため学習曲線がある
- ⚠️ Pydanticほど成熟していない（生態系が限定的）
- ❌ **LangChainとの統合が不可能**（代替となる）

#### 型定義の例（.bamlファイル）
```baml
class ExtractedMember {
    name string
    role string?
    party_name string?
}

function ExtractMember(html: string) -> ExtractedMember {
    client GPT4
    prompt #"
        Extract member information from the HTML:
        {{ html }}
    "#
}
```

#### 生成されるPythonコード
```python
from baml_client import b

# 自動生成されたクライアント
result = await b.ExtractMember(html_content)
# result.name, result.role, result.party_name
```

### 2.3 技術比較表

| 項目 | Pydantic | BAML |
|------|----------|------|
| **トークン効率** | 標準 | 80%削減 |
| **学習曲線** | 低い（Pythonの標準的なクラス定義） | 中程度（独自DSL） |
| **LangChain統合** | ✅ ネイティブサポート | ❌ 不可能 |
| **ボイラープレート** | 多い（手動でパース、リトライ） | 少ない（自動生成） |
| **開発ツール** | 標準的なPython IDE | VSCode拡張で即座にテスト |
| **エラーハンドリング** | 手動実装 | 自動生成 |
| **マルチモデル** | LangChain経由で可能 | ネイティブサポート |
| **エコシステム** | 成熟（v2.x） | 新しい |
| **用途** | 汎用データ検証 | LLM特化 |
| **型安全性** | Python型ヒント | BAML型システム |

---

## 3. Polibaseでの影響分析

### 3.1 現在のアーキテクチャ

```
LLMフレームワーク: LangChain + LangGraph
                      ↓
         GeminiLLMService (ILLMService実装)
                      ↓
    with_structured_output(pydantic_schema)
                      ↓
         Pydanticモデルで型安全な抽出
```

**依存関係**:
- `langchain>=0.3.20,<0.4`
- `langchain-google-genai>=2.0.11,<3`
- `langgraph>=0.3.5,<0.4`
- `pydantic>=2.0.0,<3`

### 3.2 BAML移行時のアーキテクチャ

```
LLMフレームワーク: BAML
                      ↓
         BAMLクライアント（自動生成）
                      ↓
         .baml型定義
                      ↓
         型安全な抽出
```

**重要な制約**: LangChainとの統合が不可能

### 3.3 影響範囲

#### 置き換え必要なコンポーネント

1. **LLMサービス層** (完全書き換え)
   - `src/infrastructure/external/llm_service.py` (GeminiLLMService)
   - `src/domain/services/interfaces/llm_service.py` (ILLMService)

2. **Pydanticモデル** (19ファイル)
   - `src/parliamentary_group_member_extractor/models.py`
   - `src/conference_member_extractor/models.py`
   - `src/party_member_extractor/models.py`
   - `src/minutes_divide_processor/models.py`
   - `src/domain/services/politician_matching_service.py`
   - `src/domain/services/speaker_matching_service.py`
   - 他13ファイル

3. **LangChain依存コード**
   - `src/services/chain_factory.py`
   - `src/services/llm_service.py`
   - プロンプトテンプレート管理

4. **LangGraphワークフロー**
   - `src/infrastructure/external/langgraph_nodes/`
   - 複雑なステートマシン

#### 保持できるコンポーネント

- Clean Architectureのレイヤー構造
- リポジトリパターン
- ドメインエンティティ
- ユースケース（インターフェース変更のみ）

---

## 4. トークンコスト影響分析

### 4.1 トークン削減の仕組み

BAMLが80%トークン削減を実現する理由：

1. **スキーマ形式の最適化**
   - PydanticのJSONスキーマは冗長
   - BAMLはLLM向けに最適化された形式

2. **プロンプト統合**
   - 型定義とプロンプトを統合
   - 重複した説明を排除

#### Pydanticの場合（例）

```json
{
  "type": "object",
  "properties": {
    "name": {
      "type": "string",
      "description": "議員名"
    },
    "role": {
      "type": ["string", "null"],
      "description": "役職（議長、副議長、委員長、委員など）"
    },
    "party_name": {
      "type": ["string", "null"],
      "description": "所属政党名"
    }
  },
  "required": ["name"]
}
```

トークン数: **約150トークン**

#### BAMLの場合（例）

```baml
class ExtractedMember {
  name string
  role string?
  party_name string?
}
```

トークン数: **約30トークン** (80%削減)

### 4.2 コスト影響試算

#### 前提条件
- 月間LLM呼び出し回数: **10,000回**（推定）
- 平均入力トークン: **1,500トークン/回**
- 平均出力トークン: **500トークン/回**
- Gemini 2.0 Flash料金（2025年現在）:
  - 入力: $0.075 / 1M tokens
  - 出力: $0.30 / 1M tokens

#### 現在のコスト（Pydantic）

```
スキーマトークン: 150トークン/回
月間スキーマトークン: 150 × 10,000 = 1,500,000トークン
スキーマコスト: 1.5M × $0.075 / 1M = $0.1125/月

総入力トークン: (1,500 + 150) × 10,000 = 16,500,000トークン
総出力トークン: 500 × 10,000 = 5,000,000トークン

月間コスト:
  入力: 16.5M × $0.075 / 1M = $1.2375
  出力: 5.0M × $0.30 / 1M = $1.5000
  合計: $2.7375/月
```

#### BAML移行後のコスト

```
スキーマトークン: 30トークン/回 (80%削減)
月間スキーマトークン: 30 × 10,000 = 300,000トークン
スキーマコスト: 0.3M × $0.075 / 1M = $0.0225/月

総入力トークン: (1,500 + 30) × 10,000 = 15,300,000トークン
総出力トークン: 500 × 10,000 = 5,000,000トークン

月間コスト:
  入力: 15.3M × $0.075 / 1M = $1.1475
  出力: 5.0M × $0.30 / 1M = $1.5000
  合計: $2.6475/月
```

#### コスト削減効果

- **月間削減額**: $0.09/月
- **年間削減額**: $1.08/年
- **削減率**: 3.3%

**注意**: この試算はスキーマトークンのみの削減を考慮。実際にはプロンプト最適化でさらなる削減の可能性あり。

### 4.3 実際のコスト削減可能性

上記試算は**控えめな見積もり**です。以下の要因で、実際の削減効果はより大きい可能性があります：

1. **プロンプト統合効果**
   - BAMLは型定義とプロンプトを統合
   - 重複した説明を排除
   - 推定: さらに10-20%の削減

2. **複雑なネストされた型**
   - Polibaseでは複雑な型が多い（`SectionInfoList`, `SpeakerAndSpeechContentList`など）
   - Pydanticの冗長なJSONスキーマ vs BAMLの簡潔な定義
   - 推定: 複雑な型では50-60%の削減

3. **リトライ最適化**
   - BAMLの自動リトライは賢い
   - 失敗したフィールドのみ再試行
   - 推定: リトライコストを30-40%削減

**楽観的試算**: 月間$0.3-0.5の削減（年間$3.6-6.0）

---

## 5. 移行工数見積もり

### 5.1 タスク分解

| フェーズ | タスク | 工数（人日） | 難易度 |
|---------|-------|------------|--------|
| **Phase 1: 学習** | BAML学習とPoC | 3-5 | 中 |
| **Phase 2: 設計** | アーキテクチャ再設計 | 5-7 | 高 |
| **Phase 3: 実装** | |||
| | BAML型定義作成（.baml） | 3-5 | 中 |
| | LLMサービス層書き換え | 7-10 | 高 |
| | LangGraph置き換え | 10-15 | 高 |
| | プロンプト移行 | 3-5 | 中 |
| **Phase 4: テスト** | |||
| | 単体テスト | 5-7 | 中 |
| | 統合テスト | 7-10 | 高 |
| | E2Eテスト | 3-5 | 中 |
| **Phase 5: 移行** | |||
| | 段階的ロールアウト | 5-7 | 高 |
| | モニタリングと調整 | 3-5 | 中 |
| **合計** | | **54-81人日** | |

### 5.2 リスク要因

| リスク | 影響度 | 対策 |
|-------|-------|-----|
| LangGraphの代替が見つからない | 高 | 事前調査、代替アーキテクチャ設計 |
| 予期しない型変換の問題 | 中 | PoC段階で検証 |
| チームの学習曲線 | 中 | 事前トレーニング、ペアプログラミング |
| 本番環境での予期しない問題 | 高 | カナリアリリース、ロールバック計画 |
| BAML自体のバグや制限 | 中 | コミュニティ調査、サポート確保 |

### 5.3 コストベネフィット分析

#### 移行コスト
- 開発工数: **54-81人日** × 開発者単価（仮に$500/日）
- 合計コスト: **$27,000 - $40,500**

#### ベネフィット
- **直接的**: 年間$1-6のトークンコスト削減（控えめ～楽観的）
- **間接的**:
  - 開発効率向上（ボイラープレート削減）
  - エラーハンドリング自動化
  - より良い型安全性

**ROI（投資回収）**: 控えめな試算では**数千年**、楽観的でも**数千年**

**結論**: **純粋なコスト削減目的では正当化できない**

---

## 6. 判断基準と推奨アクション

### 6.1 判断マトリクス

| 評価軸 | Pydantic継続 | BAML移行 | 重み |
|-------|-------------|---------|-----|
| **トークンコスト** | ⚠️ 標準 | ✅ 80%削減 | 低 |
| **開発効率** | ⚠️ ボイラープレート多い | ✅ 自動生成 | 中 |
| **移行コスト** | ✅ $0 | ❌ $27k-40k | 高 |
| **学習コスト** | ✅ 既知 | ⚠️ 新ツール | 中 |
| **リスク** | ✅ 安定 | ⚠️ 未知の問題 | 高 |
| **エコシステム** | ✅ 成熟 | ⚠️ 発展途上 | 中 |
| **型安全性** | ✅ 十分 | ✅ より良い | 低 |
| **将来性** | ✅ 継続サポート | ✅ 成長中 | 中 |

### 6.2 推奨アクション

#### 短期（現在～3ヶ月）: Pydantic継続

**理由**:
- 既存システムは安定稼働中
- 移行コストがベネフィットを大幅に上回る
- LangChainとの統合が不可能
- チームの学習コストを避ける

**アクション**:
- ✅ Pydanticの最適化（より簡潔なスキーマ定義）
- ✅ プロンプトエンジニアリングでトークン削減
- ✅ LangChainのベストプラクティス適用

#### 中期（3～6ヶ月）: PoCで効果検証

**理由**:
- トークン削減効果を実測
- チームの学習機会
- リスクの実証的評価

**アクション**:
1. **小規模PoC実施**
   - 1つのユースケースでBAML実装（例: 議員抽出）
   - トークン使用量を実測
   - 開発効率を評価

2. **効果測定**
   - トークン削減率
   - 開発時間の削減
   - エラー率の変化

3. **判断基準**
   - トークン削減が50%以上 → 全面移行を検討
   - トークン削減が30-50% → 部分的移行を検討
   - トークン削減が30%未満 → Pydantic継続

#### 長期（6ヶ月～1年）: ROI次第で全面移行

**理由**:
- PoCの結果に基づく合理的判断
- チームのスキルアップ
- BAMLエコシステムの成熟を待つ

**アクション**:
- PoCで効果が証明された場合のみ、段階的全面移行
- LLMコストが大幅に増加した場合は再評価

### 6.3 代替アプローチ: Pydantic最適化

BAML移行の代わりに、Pydanticのまま最適化する方法：

1. **スキーマの簡素化**
   ```python
   # Before: 冗長な説明
   class ExtractedMember(BaseModel):
       name: str = Field(description="議員の氏名（姓名）")
       role: str | None = Field(description="役職（議長、副議長、委員長、委員など）")

   # After: 簡潔な説明
   class ExtractedMember(BaseModel):
       name: str
       role: str | None = None
   ```

2. **Few-shot promptingの活用**
   - 型定義を減らし、例示でLLMを誘導

3. **LangChainのキャッシング活用**
   - プロンプトキャッシングでコスト削減

**推定効果**: トークン削減10-20%、移行コスト$0

---

## 7. 結論

### 7.1 技術的結論

1. **BAMLは技術的に優れている** - トークン効率、開発体験、型安全性
2. **しかし、Polibaseでは移行コストが高すぎる** - LangChain全体の置き換え、$27k-40k
3. **ROIが非常に悪い** - 年間$1-6の削減 vs $27k-40kの投資

### 7.2 最終推奨

**短期**: Pydantic継続 + 最適化
**中期**: 小規模PoCで効果検証
**長期**: PoCの結果次第で判断

### 7.3 次のステップ

1. ✅ この調査レポートをIssue #729にコメント
2. ⏭️ チームでレビューと議論
3. ⏭️ PoC実施の可否を判断
4. ⏭️ Pydantic最適化のタスクを作成（短期対策）

---

## 付録

### A. 参考資料

- [BAML vs Pydantic比較](https://docs.boundaryml.com/guide/comparisons/baml-vs-pydantic)
- [BAML公式ドキュメント](https://docs.boundaryml.com)
- [LangChain Structured Output](https://python.langchain.com/docs/how_to/structured_output/)
- [Pydantic公式ドキュメント](https://docs.pydantic.dev/)

### B. 調査データ

#### Pydantic使用ファイル一覧（19ファイル）

1. `src/parliamentary_group_member_extractor/models.py`
2. `src/conference_member_extractor/models.py`
3. `src/conference_member_extractor/extractor.py`
4. `src/party_member_extractor/models.py`
5. `src/application/dtos/link_analysis_dto.py`
6. `src/application/usecases/review_extracted_member_usecase.py`
7. `src/infrastructure/persistence/proposal_parliamentary_group_judge_repository_impl.py`
8. `src/infrastructure/persistence/extracted_proposal_judge_repository_impl.py`
9. `src/infrastructure/persistence/proposal_repository_impl.py`
10. `src/infrastructure/persistence/conference_repository_impl.py`
11. `src/infrastructure/persistence/proposal_judge_repository_impl.py`
12. `src/domain/services/politician_matching_service.py`
13. `src/domain/services/speaker_matching_service.py`
14. `src/domain/services/interfaces/llm_link_classifier_service.py`
15. `src/services/chain_factory.py`
16. `src/services/llm_service.py`
17. `src/minutes_divide_processor/models.py`
18. `src/infrastructure/external/llm_service.py`
19. その他リポジトリ実装

#### LangChain統合箇所

- `src/infrastructure/external/llm_service.py:376`
  ```python
  return self._llm.with_structured_output(schema)
  ```

- `src/services/llm_service.py:125`
  ```python
  self._structured_llms[schema_name] = self.llm.with_structured_output(schema)
  ```

### C. 用語集

- **BAML**: BoundaryML - LLM構造化抽出のための専用フレームワーク
- **Pydantic**: Pythonデータ検証ライブラリ
- **LangChain**: LLMアプリケーション開発フレームワーク
- **LangGraph**: ステートフルなLLMワークフローを構築するライブラリ
- **Structured Output**: LLMから構造化されたデータを抽出する技術
- **JSONスキーマ**: JSON形式のデータ構造を定義するスキーマ
- **PoC**: Proof of Concept - 概念実証

---

**レポート作成者**: Claude Code
**レビュー待ち**: チーム
**最終更新**: 2025-11-08
