"""
LLMを活用した発言者名の高精度マッチングサービス
"""

import re

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
from sqlalchemy import text

from src.config.database import get_db_session


class SpeakerMatch(BaseModel):
    """マッチング結果のデータモデル"""

    matched: bool = Field(description="マッチングが成功したかどうか")
    speaker_id: int | None = Field(description="マッチしたspeakerのID", default=None)
    speaker_name: str | None = Field(
        description="マッチしたspeakerの名前", default=None
    )
    confidence: float = Field(description="マッチングの信頼度 (0.0-1.0)", default=0.0)
    reason: str = Field(description="マッチング判定の理由")


class SpeakerMatchingService:
    """LLMを活用した発言者名マッチングサービス"""

    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm
        self.session = get_db_session()
        self._setup_prompt()

    def _setup_prompt(self):
        """LLMプロンプトの設定"""
        self.prompt = ChatPromptTemplate.from_template("""
あなたは議事録の発言者名マッチング専門家です。
議事録から抽出された発言者名と、既存の発言者リストから最も適切なマッチを見つけてください。

# 抽出された発言者名
{speaker_name}

# 既存の発言者リスト
{available_speakers}

# マッチング基準
1. 完全一致を最優先
2. 括弧内の名前との一致（例: "委員長(平山たかお)" → "平山たかお"）
3. 記号除去後の一致（例: "◆委員(下村あきら)" → "委員(下村あきら)"）
4. 部分一致や音韻的類似性
5. 漢字の異なる読みや表記ゆれ

# 出力形式
以下のJSON形式で回答してください：
{{
    "matched": true/false,
    "speaker_id": マッチした場合のID (数値) または null,
    "speaker_name": マッチした場合の名前 (文字列) または null,
    "confidence": 信頼度 (0.0-1.0の小数),
    "reason": "マッチング判定の理由"
}}

# 重要な注意事項
- 確実性が低い場合は matched: false を返してください
- confidence は 0.8 以上の場合のみマッチとして扱ってください
- 複数の候補がある場合は最も確からしいものを選んでください
        """)

        self.output_parser = JsonOutputParser(pydantic_object=SpeakerMatch)
        self.chain = self.prompt | self.llm | self.output_parser

    def find_best_match(self, speaker_name: str) -> SpeakerMatch:
        """
        発言者名に最適なマッチを見つける

        Args:
            speaker_name: マッチングする発言者名

        Returns:
            SpeakerMatch: マッチング結果
        """
        # 既存の発言者リストを取得
        available_speakers = self._get_available_speakers()

        if not available_speakers:
            return SpeakerMatch(
                matched=False, confidence=0.0, reason="利用可能な発言者リストが空です"
            )

        # まず従来のルールベースマッチングを試行
        rule_based_match = self._rule_based_matching(speaker_name, available_speakers)
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            return rule_based_match

        # LLMによる高度なマッチング
        try:
            # 候補を絞り込み（パフォーマンス向上のため）
            filtered_speakers = self._filter_candidates(
                speaker_name, available_speakers
            )

            result = self.chain.invoke(
                {
                    "speaker_name": speaker_name,
                    "available_speakers": self._format_speakers_for_llm(
                        filtered_speakers
                    ),
                }
            )

            # 結果の検証
            if isinstance(result, dict):
                match_result = SpeakerMatch(**result)
            else:
                match_result = result

            # 信頼度が低い場合はマッチしないとして扱う
            if match_result.confidence < 0.8:
                match_result.matched = False
                match_result.speaker_id = None
                match_result.speaker_name = None

            return match_result

        except Exception as e:
            print(f"❌ LLMマッチングエラー: {e}")
            # エラー時はルールベースの結果を返す
            return rule_based_match

    def _get_available_speakers(self) -> list[dict]:
        """利用可能な発言者リストを取得"""
        query = text("SELECT id, name FROM speakers ORDER BY name")
        result = self.session.execute(query)

        speakers = []
        for row in result.fetchall():
            speakers.append({"id": row[0], "name": row[1]})

        return speakers

    def _rule_based_matching(
        self, speaker_name: str, available_speakers: list[dict]
    ) -> SpeakerMatch:
        """従来のルールベースマッチング"""

        # 1. 完全一致
        for speaker in available_speakers:
            if speaker["name"] == speaker_name:
                return SpeakerMatch(
                    matched=True,
                    speaker_id=speaker["id"],
                    speaker_name=speaker["name"],
                    confidence=1.0,
                    reason="完全一致",
                )

        # 2. 括弧内の名前を抽出して検索
        match = re.search(r"\(([^)]+)\)", speaker_name)
        if match:
            extracted_name = match.group(1)
            for speaker in available_speakers:
                if speaker["name"] == extracted_name:
                    return SpeakerMatch(
                        matched=True,
                        speaker_id=speaker["id"],
                        speaker_name=speaker["name"],
                        confidence=0.95,
                        reason=f"括弧内名前一致: {extracted_name}",
                    )

        # 3. 記号除去後の一致
        cleaned_name = re.sub(r"^[◆○◎]", "", speaker_name)
        if cleaned_name != speaker_name:
            return self._rule_based_matching(cleaned_name, available_speakers)

        # 4. 部分一致
        for speaker in available_speakers:
            if speaker["name"] in speaker_name or speaker_name in speaker["name"]:
                return SpeakerMatch(
                    matched=True,
                    speaker_id=speaker["id"],
                    speaker_name=speaker["name"],
                    confidence=0.8,
                    reason=f"部分一致: {speaker['name']}",
                )

        return SpeakerMatch(
            matched=False, confidence=0.0, reason="ルールベースマッチングでは一致なし"
        )

    def _filter_candidates(
        self,
        speaker_name: str,
        available_speakers: list[dict],
        max_candidates: int = 10,
    ) -> list[dict]:
        """候補を絞り込む（LLMの処理効率向上のため）"""
        candidates = []

        # 括弧内の名前を抽出
        extracted_name = None
        match = re.search(r"\(([^)]+)\)", speaker_name)
        if match:
            extracted_name = match.group(1)

        # 記号除去
        cleaned_name = re.sub(r"^[◆○◎]", "", speaker_name)

        for speaker in available_speakers:
            score = 0

            # 部分一致スコア
            if speaker["name"] in speaker_name or speaker_name in speaker["name"]:
                score += 3

            # 括弧内名前との一致
            if extracted_name and (
                speaker["name"] == extracted_name or extracted_name in speaker["name"]
            ):
                score += 5

            # 清理された名前との一致
            if speaker["name"] in cleaned_name or cleaned_name in speaker["name"]:
                score += 2

            # 文字列長の類似性
            len_diff = abs(len(speaker["name"]) - len(speaker_name))
            if len_diff <= 3:
                score += 1

            if score > 0:
                candidates.append({**speaker, "score": score})

        # スコア順にソート
        candidates.sort(key=lambda x: x["score"], reverse=True)

        # 最大候補数に制限
        return (
            candidates[:max_candidates]
            if candidates
            else available_speakers[:max_candidates]
        )

    def _format_speakers_for_llm(self, speakers: list[dict]) -> str:
        """発言者リストをLLM用にフォーマット"""
        formatted = []
        for speaker in speakers:
            formatted.append(f"ID: {speaker['id']}, 名前: {speaker['name']}")
        return "\n".join(formatted)

    def batch_update_speaker_links(self) -> dict[str, int]:
        """
        未マッチの会話レコードを一括でマッチング更新

        Returns:
            Dict[str, int]: 更新統計
        """
        try:
            # speaker_idがNULLのレコードを取得
            query = text("""
                SELECT id, speaker_name FROM conversations
                WHERE speaker_id IS NULL
                ORDER BY id
            """)

            result = self.session.execute(query)
            unlinked_conversations = result.fetchall()

            stats = {
                "total_processed": len(unlinked_conversations),
                "successfully_matched": 0,
                "high_confidence_matches": 0,
                "failed_matches": 0,
            }

            for conversation_id, speaker_name in unlinked_conversations:
                print(f"🔍 マッチング処理中: {speaker_name}")

                match_result = self.find_best_match(speaker_name)

                if match_result.matched and match_result.speaker_id:
                    # speaker_idを更新
                    update_query = text("""
                        UPDATE conversations
                        SET speaker_id = :speaker_id
                        WHERE id = :conversation_id
                    """)

                    self.session.execute(
                        update_query,
                        {
                            "speaker_id": match_result.speaker_id,
                            "conversation_id": conversation_id,
                        },
                    )

                    stats["successfully_matched"] += 1

                    if match_result.confidence >= 0.9:
                        stats["high_confidence_matches"] += 1

                    confidence_emoji = "🟢" if match_result.confidence >= 0.9 else "🟡"
                    print(
                        f"  {confidence_emoji} マッチ成功: {speaker_name} → "
                        f"{match_result.speaker_name} "
                        f"(信頼度: {match_result.confidence:.2f})"
                    )
                else:
                    stats["failed_matches"] += 1
                    print(f"  🔴 マッチ失敗: {speaker_name} ({match_result.reason})")

            self.session.commit()

            print("\n📊 マッチング結果:")
            print(f"   - 処理総数: {stats['total_processed']}件")
            print(f"   - マッチ成功: {stats['successfully_matched']}件")
            print(f"   - 高信頼度マッチ: {stats['high_confidence_matches']}件")
            print(f"   - マッチ失敗: {stats['failed_matches']}件")

            return stats

        except Exception as e:
            self.session.rollback()
            print(f"❌ 一括マッチング更新エラー: {e}")
            raise
        finally:
            self.session.close()
