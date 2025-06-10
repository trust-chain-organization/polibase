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
1. 【会議体所属議員】とマークされた発言者を優先的に考慮
2. 完全一致を最優先
3. 括弧内の名前との一致（例: "委員長(平山たかお)" → "平山たかお"）
4. 記号除去後の一致（例: "◆委員(下村あきら)" → "委員(下村あきら)"）
5. 部分一致や音韻的類似性
6. 漢字の異なる読みや表記ゆれ
7. 役職が記載されている場合は、その役職との整合性も考慮

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
- 【会議体所属議員】とマークされた候補者は、その会議体のメンバーとして
  登録されているため、優先的にマッチングしてください
- 確実性が低い場合は matched: false を返してください
- confidence は 0.8 以上の場合のみマッチとして扱ってください
- 複数の候補がある場合は最も確からしいものを選んでください
        """)

        self.output_parser = JsonOutputParser(pydantic_object=SpeakerMatch)
        self.chain = self.prompt | self.llm | self.output_parser

    def find_best_match(
        self,
        speaker_name: str,
        meeting_date: str | None = None,
        conference_id: int | None = None,
    ) -> SpeakerMatch:
        """
        発言者名に最適なマッチを見つける

        Args:
            speaker_name: マッチングする発言者名
            meeting_date: 会議開催日（YYYY-MM-DD形式）
            conference_id: 会議体ID

        Returns:
            SpeakerMatch: マッチング結果
        """
        # 既存の発言者リストを取得
        available_speakers = self._get_available_speakers()

        if not available_speakers:
            return SpeakerMatch(
                matched=False, confidence=0.0, reason="利用可能な発言者リストが空です"
            )

        # PoliticianAffiliationsを考慮した発言者リストを取得
        if meeting_date and conference_id:
            affiliated_speakers = self._get_affiliated_speakers(
                meeting_date, conference_id
            )
            # アフィリエーション情報を既存のスピーカーリストに追加
            speaker_dict = {s["id"]: s for s in available_speakers}
            for affiliated in affiliated_speakers:
                if affiliated["speaker_id"] in speaker_dict:
                    speaker_dict[affiliated["speaker_id"]]["is_affiliated"] = True
                    speaker_dict[affiliated["speaker_id"]]["politician_id"] = (
                        affiliated["politician_id"]
                    )
                    speaker_dict[affiliated["speaker_id"]]["role"] = affiliated.get(
                        "role"
                    )
            available_speakers = list(speaker_dict.values())

        # まず従来のルールベースマッチングを試行
        rule_based_match = self._rule_based_matching(speaker_name, available_speakers)
        if rule_based_match.matched and rule_based_match.confidence >= 0.9:
            return rule_based_match

        # LLMによる高度なマッチング
        try:
            # 候補を絞り込み（アフィリエーション情報を優先）
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

    def _get_affiliated_speakers(
        self, meeting_date: str, conference_id: int
    ) -> list[dict]:
        """
        指定された会議日と会議体IDに基づいて、その時点でアクティブな所属を持つ発言者を取得

        Args:
            meeting_date: 会議開催日（YYYY-MM-DD形式）
            conference_id: 会議体ID

        Returns:
            List[dict]: アフィリエーション情報を含む発言者リスト
        """
        query = text("""
            SELECT DISTINCT
                s.id as speaker_id,
                s.name as speaker_name,
                p.id as politician_id,
                p.name as politician_name,
                pa.role as role
            FROM politician_affiliations pa
            JOIN politicians p ON pa.politician_id = p.id
            JOIN speakers s ON p.speaker_id = s.id
            WHERE pa.conference_id = :conference_id
                AND pa.start_date <= CAST(:meeting_date AS date)
                AND (pa.end_date IS NULL OR pa.end_date >= CAST(:meeting_date AS date))
            ORDER BY s.name
        """)

        result = self.session.execute(
            query, {"conference_id": conference_id, "meeting_date": meeting_date}
        )

        affiliated_speakers = []
        for row in result.fetchall():
            affiliated_speakers.append(
                {
                    "speaker_id": row[0],
                    "speaker_name": row[1],
                    "politician_id": row[2],
                    "politician_name": row[3],
                    "role": row[4],
                }
            )

        return affiliated_speakers

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

            # アフィリエーション優先ボーナス
            if speaker.get("is_affiliated"):
                score += 10  # 会議体に所属している議員を優先

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
            info = f"ID: {speaker['id']}, 名前: {speaker['name']}"
            if speaker.get("is_affiliated"):
                info += " 【会議体所属議員】"
                if speaker.get("role"):
                    info += f" 役職: {speaker['role']}"
            formatted.append(info)
        return "\n".join(formatted)

    def batch_update_speaker_links(self) -> dict[str, int]:
        """
        未マッチの会話レコードを一括でマッチング更新

        Returns:
            Dict[str, int]: 更新統計
        """
        try:
            # speaker_idがNULLのレコードを会議情報と共に取得
            query = text("""
                SELECT
                    c.id as conversation_id,
                    c.speaker_name,
                    m.date as meeting_date,
                    conf.id as conference_id,
                    conf.name as conference_name
                FROM conversations c
                LEFT JOIN minutes min ON c.minutes_id = min.id
                LEFT JOIN meetings m ON min.meeting_id = m.id
                LEFT JOIN conferences conf ON m.conference_id = conf.id
                WHERE c.speaker_id IS NULL
                ORDER BY c.id
            """)

            result = self.session.execute(query)
            unlinked_conversations = result.fetchall()

            stats = {
                "total_processed": len(unlinked_conversations),
                "successfully_matched": 0,
                "high_confidence_matches": 0,
                "failed_matches": 0,
                "with_affiliation_info": 0,
            }

            for row in unlinked_conversations:
                conversation_id = row[0]
                speaker_name = row[1]
                meeting_date = row[2].strftime("%Y-%m-%d") if row[2] else None
                conference_id = row[3]
                conference_name = row[4]

                print(f"🔍 マッチング処理中: {speaker_name}")
                if meeting_date and conference_id:
                    print(f"   📅 会議日: {meeting_date}, 会議体: {conference_name}")
                    stats["with_affiliation_info"] += 1

                match_result = self.find_best_match(
                    speaker_name, meeting_date, conference_id
                )

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
            print(
                f"   - アフィリエーション情報あり: {stats['with_affiliation_info']}件"
            )

            return stats

        except Exception as e:
            self.session.rollback()
            print(f"❌ 一括マッチング更新エラー: {e}")
            raise
        finally:
            self.session.close()
