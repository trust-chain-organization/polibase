#!/usr/bin/env python3
"""
議事録から発言者を抽出してspeakerテーブルに格納し、
politicianテーブルと紐付ける処理
"""

import argparse
import logging
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.database import DATABASE_URL
from src.database.conversation_repository import ConversationRepository
from src.database.meeting_repository import MeetingRepository
from src.database.politician_repository import PoliticianRepository
from src.database.speaker_matching_service import SpeakerMatchingService
from src.database.speaker_repository import SpeakerRepository

# ロギング設定
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SpeakerExtractorFromMinutes:
    """議事録から発言者を抽出し、speakerテーブルに格納するクラス"""

    def __init__(self, session: Session):
        self.session = session
        self.speaker_repo = SpeakerRepository()
        self.politician_repo = PoliticianRepository()
        self.conversation_repo = ConversationRepository()
        self.meeting_repo = MeetingRepository()
        # Speaker matching service will be initialized when needed with LLM

    def extract_speakers_from_minutes(self, minutes_id: int | None = None) -> None:
        """
        議事録から発言者を抽出してspeakerテーブルに格納

        Args:
            minutes_id: 特定の議事録IDを処理する場合に指定
        """
        logger.info("議事録から発言者を抽出開始")

        # 対象の議事録を取得
        if minutes_id:
            conversations = self.conversation_repo.get_conversations_by_minutes_id(
                minutes_id
            )
            logger.info(
                f"議事録ID {minutes_id} の処理を開始（{len(conversations)}件の発言）"
            )
        else:
            conversations = (
                self.conversation_repo.get_all_conversations_without_speaker_id()
            )
            logger.info(f"全議事録の未処理発言を処理開始（{len(conversations)}件）")

        # 発言者名を抽出（重複を除く）
        unique_speaker_names: set[str] = set()
        for conv in conversations:
            # convが辞書の場合とオブジェクトの場合の両方に対応
            speaker_name = (
                conv.get("speaker_name")
                if isinstance(conv, dict)
                else getattr(conv, "speaker_name", None)
            )
            if speaker_name:
                unique_speaker_names.add(speaker_name)

        logger.info(f"ユニークな発言者名: {len(unique_speaker_names)}件")

        # 各発言者をspeakerテーブルに格納
        created_count = 0
        existing_count = 0

        for speaker_name in unique_speaker_names:
            # 既存のspeakerを検索
            existing_speaker = self.speaker_repo.find_by_name(speaker_name)

            if existing_speaker:
                speaker_id = existing_speaker.id
                logger.debug(f"既存の発言者: {speaker_name} (ID: {speaker_id})")
                existing_count += 1
            else:
                # 新規作成
                try:
                    query = """
                        INSERT INTO speakers (name, type, is_politician)
                        VALUES (:name, :type, :is_politician)
                        RETURNING id
                    """
                    result = self.speaker_repo.execute_query(
                        query,
                        {
                            "name": speaker_name,
                            "type": "未分類",  # 後で分類
                            "is_politician": False,  # 後で判定
                        },
                    )
                    row = result.fetchone()
                    if row:
                        speaker_id = row[0]
                        logger.info(
                            f"新規発言者を作成: {speaker_name} (ID: {speaker_id})"
                        )
                        created_count += 1
                except Exception as e:
                    logger.error(f"発言者作成エラー: {speaker_name} - {e}")

        self.session.commit()
        logger.info(
            f"発言者抽出完了 - 新規: {created_count}件, 既存: {existing_count}件"
        )

    def link_speakers_to_politicians(self, use_llm: bool = False) -> None:
        """speakerとpoliticianを紐付ける処理

        Args:
            use_llm: LLMを使用した高度なマッチングを行うかどうか
        """
        logger.info("speaker-politician紐付け処理開始")

        if use_llm:
            # LLMを使用した高度なマッチング
            from src.database.politician_matching_service import (
                PoliticianMatchingService,
            )

            matching_service = PoliticianMatchingService()

            stats = matching_service.batch_link_speakers_to_politicians()
            logger.info(
                f"LLMマッチング完了 - 成功: {stats['successfully_matched']}件, "
                f"失敗: {stats['failed_matches']}件"
            )
        else:
            # 従来のルールベースマッチング
            # is_politician=Falseのspeakerを取得
            query = "SELECT * FROM speakers WHERE is_politician = FALSE"
            result = self.speaker_repo.execute_query(query)
            rows = result.fetchall()
            columns = result.keys()
            speakers = [dict(zip(columns, row, strict=False)) for row in rows]
            logger.info(f"未紐付けのspeaker: {len(speakers)}件")

            linked_count = 0

            for speaker in speakers:
                # 名前でpoliticianを検索
                politicians = self.politician_repo.find_by_name(speaker["name"])

                if len(politicians) == 1:
                    # 1件だけ見つかった場合は自動的に紐付け
                    politician = politicians[0]
                    # speakerを更新
                    update_query = """
                        UPDATE speakers
                        SET is_politician = TRUE,
                            political_party_name = :party_name
                        WHERE id = :id
                    """
                    # politicianが辞書の場合とオブジェクトの場合の両方に対応
                    politician_id: int | None
                    party_name: str | None
                    if isinstance(politician, dict):
                        pol_id: Any = politician.get("id")
                        politician_id = pol_id if isinstance(pol_id, int) else None
                        party_name_val: Any = politician.get("political_party_name")
                        party_name = (
                            party_name_val if isinstance(party_name_val, str) else None
                        )
                    else:
                        politician_id = politician.id
                        party_name = None
                        # Get party name by joining with political_parties table
                        if (
                            hasattr(politician, "political_party_id")
                            and politician.political_party_id
                        ):
                            party_query = """
                                SELECT name FROM political_parties
                                WHERE id = :party_id
                            """
                            result = self.politician_repo.execute_query(
                                party_query, {"party_id": politician.political_party_id}
                            )
                            rows = result.fetchall()
                            if rows:
                                party_name = rows[0][0]

                    self.speaker_repo.execute_query(
                        update_query,
                        {
                            "id": speaker["id"],
                            "party_name": party_name,
                        },
                    )
                    logger.info(
                        f"自動紐付け: {speaker['name']} -> 政治家ID: {politician_id}"
                    )
                    linked_count += 1

                elif len(politicians) > 1:
                    # 複数見つかった場合は政党名で絞り込み
                    if speaker.get("political_party_name"):
                        matched_politicians: list[Any] = []
                        for p in politicians:
                            if isinstance(p, dict):
                                party_name_from_dict: Any = p.get(
                                    "political_party_name"
                                )
                                if (
                                    party_name_from_dict
                                    == speaker["political_party_name"]
                                ):
                                    matched_politicians.append(p)
                            else:
                                # For Politician objects, get party name from party_id
                                if (
                                    hasattr(p, "political_party_id")
                                    and p.political_party_id
                                ):
                                    party_query = """
                                        SELECT name FROM political_parties
                                        WHERE id = :party_id
                                    """
                                    result = self.politician_repo.execute_query(
                                        party_query, {"party_id": p.political_party_id}
                                    )
                                    rows = result.fetchall()
                                    if (
                                        rows
                                        and rows[0][0]
                                        == speaker["political_party_name"]
                                    ):
                                        matched_politicians.append(p)
                        if len(matched_politicians) == 1:
                            politician = matched_politicians[0]
                            # speakerを更新
                            update_query = (
                                "UPDATE speakers SET is_politician = TRUE "
                                "WHERE id = :id"
                            )
                            self.speaker_repo.execute_query(
                                update_query, {"id": speaker["id"]}
                            )
                            # politicianが辞書の場合とオブジェクトの場合の両方に対忎
                            if isinstance(politician, dict):
                                pol_id: Any = politician.get("id")
                                matched_politician_id: int | None = (
                                    pol_id if isinstance(pol_id, int) else None
                                )
                            else:
                                matched_politician_id = politician.id
                            logger.info(
                                f"政党名で絞り込み紐付け: {speaker['name']} "
                                f"({speaker['political_party_name']}) -> "
                                f"政治家ID: {matched_politician_id}"
                            )
                            linked_count += 1
                        else:
                            logger.warning(
                                f"複数の政治家候補が存在: {speaker['name']} "
                                f"({len(politicians)}件)"
                            )
                    else:
                        logger.warning(
                            f"政党名が不明で複数の政治家候補が存在: "
                            f"{speaker['name']} ({len(politicians)}件)"
                        )

            self.session.commit()
            logger.info(f"speaker-politician紐付け完了: {linked_count}件")

    def update_conversation_speaker_links(self, use_llm: bool = False) -> None:
        """conversationテーブルのspeaker_idを更新"""
        logger.info("conversation-speaker紐付け処理開始")

        if use_llm:
            # LLMを使用した高度なマッチング
            unlinked_conversations = (
                self.conversation_repo.get_all_conversations_without_speaker_id()
            )

            logger.info(f"LLMを使用して{len(unlinked_conversations)}件の発言を処理")

            for conversation in unlinked_conversations:
                # conversationが辞書の場合とオブジェクトの場合の両方に対応
                speaker_name = (
                    conversation.get("speaker_name")
                    if isinstance(conversation, dict)
                    else getattr(conversation, "speaker_name", None)
                )
                if not speaker_name:
                    continue

                # マッチング実行
                matching_service = SpeakerMatchingService()
                match_result = matching_service.find_best_match(speaker_name)
                matched_speaker: dict[str, Any] | None = None

                if match_result.matched and match_result.speaker_id:
                    # Get speaker details
                    query = "SELECT * FROM speakers WHERE id = :id"
                    result = self.speaker_repo.execute_query(
                        query, {"id": match_result.speaker_id}
                    )
                    rows = result.fetchall()
                    if rows:
                        columns = result.keys()
                        matched_speaker = dict(zip(columns, rows[0], strict=False))

                if matched_speaker:
                    # conversationオブジェクトへのspeaker_id設定
                    conversation_id = (
                        conversation.get("id")
                        if isinstance(conversation, dict)
                        else conversation.id
                    )
                    update_query = (
                        "UPDATE conversations SET speaker_id = :speaker_id "
                        "WHERE id = :id"
                    )
                    self.conversation_repo.execute_query(
                        update_query,
                        {"speaker_id": matched_speaker["id"], "id": conversation_id},
                    )
                    logger.debug(
                        f"LLMマッチング成功: '{speaker_name}' -> "
                        f"Speaker ID: {matched_speaker['id']}"
                    )
                else:
                    logger.debug(f"LLMマッチング失敗: '{speaker_name}'")

        else:
            # 単純な名前マッチング
            conversations = (
                self.conversation_repo.get_all_conversations_without_speaker_id()
            )
            logger.info(f"単純マッチングで{len(conversations)}件の発言を処理")

            linked_count = 0
            for conv in conversations:
                # convが辞書の場合とオブジェクトの場合の両方に対応
                speaker_name = (
                    conv.get("speaker_name")
                    if isinstance(conv, dict)
                    else getattr(conv, "speaker_name", None)
                )
                if speaker_name:
                    query = "SELECT id FROM speakers WHERE name = :name LIMIT 1"
                    result = self.speaker_repo.execute_query(
                        query, {"name": speaker_name}
                    )
                    rows = result.fetchall()
                    if rows:
                        columns = result.keys()
                        speakers = [
                            dict(zip(columns, row, strict=False)) for row in rows
                        ]
                        # conversationのIDを取得してUPDATEクエリで更新
                        conversation_id = (
                            conv.get("id") if isinstance(conv, dict) else conv.id
                        )
                        update_query = (
                            "UPDATE conversations SET speaker_id = :speaker_id "
                            "WHERE id = :id"
                        )
                        self.conversation_repo.execute_query(
                            update_query,
                            {"speaker_id": speakers[0]["id"], "id": conversation_id},
                        )
                        linked_count += 1

            logger.info(f"単純マッチング完了: {linked_count}件")

        self.session.commit()
        logger.info("conversation-speaker紐付け処理完了")


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="議事録から発言者を抽出してspeaker/politicianと紐付ける"
    )
    parser.add_argument("--minutes-id", type=int, help="特定の議事録IDのみを処理")
    parser.add_argument(
        "--use-llm", action="store_true", help="LLMを使用した高度なマッチングを行う"
    )
    parser.add_argument(
        "--skip-extraction",
        action="store_true",
        help="発言者抽出をスキップ（紐付けのみ実行）",
    )
    parser.add_argument(
        "--skip-politician-link", action="store_true", help="politician紐付けをスキップ"
    )
    parser.add_argument(
        "--skip-conversation-link",
        action="store_true",
        help="conversation紐付けをスキップ",
    )

    args = parser.parse_args()

    # データベース接続
    engine = create_engine(DATABASE_URL)
    session_local = sessionmaker(bind=engine)

    with session_local() as session:
        extractor = SpeakerExtractorFromMinutes(session)

        try:
            # 1. 発言者抽出
            if not args.skip_extraction:
                extractor.extract_speakers_from_minutes(args.minutes_id)

            # 2. speaker-politician紐付け
            if not args.skip_politician_link:
                extractor.link_speakers_to_politicians(use_llm=args.use_llm)

            # 3. conversation-speaker紐付け
            if not args.skip_conversation_link:
                extractor.update_conversation_speaker_links(use_llm=args.use_llm)

            logger.info("全処理が完了しました")

        except Exception as e:
            logger.error(f"エラーが発生しました: {e}", exc_info=True)
            session.rollback()
            raise


if __name__ == "__main__":
    main()
