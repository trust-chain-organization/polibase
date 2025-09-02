"""同期的な発言者抽出処理

このモジュールは、Streamlitから呼び出される同期的な発言者抽出処理を提供します。
既存のConversationsから発言者を抽出し、Speakerレコードを作成します。
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.entities.speaker import Speaker
from src.domain.services.speaker_domain_service import SpeakerDomainService
from src.infrastructure.persistence.conversation_repository_impl import (
    ConversationRepositoryImpl as AsyncConversationRepo,
)
from src.infrastructure.persistence.minutes_repository_impl import (
    MinutesRepositoryImpl as AsyncMinutesRepo,
)
from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
from src.infrastructure.persistence.speaker_repository_impl import (
    SpeakerRepositoryImpl as AsyncSpeakerRepo,
)
from src.streamlit.utils.processing_logger import ProcessingLogger

logger = logging.getLogger(__name__)


@dataclass
class SyncSpeakerExtractionResult:
    """同期発言者抽出処理の結果"""

    meeting_id: int
    total_conversations: int
    unique_speakers: int
    new_speakers: int
    existing_speakers: int
    processing_time_seconds: float
    processed_at: datetime
    errors: list[str] | None = None


class SyncSpeakerExtractor:
    """同期的に発言者抽出処理を実行するクラス"""

    def __init__(self, meeting_id: int):
        """初期化

        Args:
            meeting_id: 処理対象の会議ID
        """
        self.meeting_id = meeting_id
        self.logger = ProcessingLogger()

    def process(self) -> SyncSpeakerExtractionResult:
        """発言者抽出処理を実行する

        Returns:
            処理結果
        """
        start_time = datetime.now()
        errors: list[str] = []

        try:
            self.logger.add_log(self.meeting_id, "処理を開始します", "info")
            self.logger.add_log(
                self.meeting_id,
                f"会議ID {self.meeting_id} の発言者抽出処理を実行します",
                "info",
            )

            # 同期リポジトリを使用
            self.logger.add_log(
                self.meeting_id, "データベースに接続しています...", "info"
            )
            minutes_repo = RepositoryAdapter(AsyncMinutesRepo)
            conversation_repo = RepositoryAdapter(AsyncConversationRepo)
            speaker_repo = RepositoryAdapter(AsyncSpeakerRepo)

            # ドメインサービスを初期化
            speaker_service = SpeakerDomainService()

            self.logger.add_log(
                self.meeting_id, "議事録情報を取得しています...", "info"
            )

            # 議事録を取得
            minutes = minutes_repo.get_by_meeting(self.meeting_id)
            if not minutes or not minutes.id:
                raise ValueError(f"No minutes found for meeting {self.meeting_id}")

            # ステップ1: 出席者一覧をLLMで抽出
            self.logger.add_log(
                self.meeting_id, "📋 出席者一覧を抽出しています...", "info"
            )
            attendees_mapping = self._extract_and_save_attendees_mapping(
                self.meeting_id, minutes
            )
            if attendees_mapping:
                mapping_dict = attendees_mapping.get("attendees_mapping", {})
                regular_list = attendees_mapping.get("regular_attendees", [])
                
                # すべての出席者を配列として集約
                all_attendees = []
                
                # 役職付き出席者を追加
                for role, name in mapping_dict.items():
                    if name:
                        all_attendees.append(f"{name} ({role})")
                
                # 一般出席者を追加
                all_attendees.extend(regular_list)
                
                # 出席者一覧をログに出力
                self.logger.add_log(
                    self.meeting_id,
                    f"✅ 出席者一覧を抽出しました (合計: {len(all_attendees)}人)",
                    "success",
                    details=str(all_attendees),  # 配列として表示
                )
                
                # 詳細情報を作成（折りたたみ用）
                details_lines = []
                if mapping_dict:
                    details_lines.append("【役職付き出席者】")
                    for role, name in mapping_dict.items():
                        if name:
                            details_lines.append(f"  • {role}: {name}")
                
                if regular_list:
                    details_lines.append("\n【一般出席者】")
                    for name in regular_list[:10]:  # 最初の10人まで表示
                        details_lines.append(f"  • {name}")
                    if len(regular_list) > 10:
                        details_lines.append(f"  ... 他{len(regular_list) - 10}人")
                
                self.logger.add_log(
                    self.meeting_id,
                    f"📊 出席者の内訳 "
                    f"(役職付き: {len(mapping_dict)}人, 一般出席者: {len(regular_list)}人)",
                    "info",
                    details="\n".join(details_lines) if details_lines else None,
                )
            else:
                self.logger.add_log(
                    self.meeting_id,
                    "⚠️ 出席者情報を抽出できませんでした",
                    "warning",
                )

            # ステップ2: Conversationsを取得
            conversations = conversation_repo.get_by_minutes(minutes.id)
            if not conversations:
                raise ValueError(
                    f"No conversations found for meeting {self.meeting_id}"
                )

            self.logger.add_log(
                self.meeting_id,
                f"📝 {len(conversations)}件の発言を取得しました",
                "info",
            )

            # 既存のSpeakers数をカウント
            conversations_with_speakers = [
                c for c in conversations if c.speaker_id is not None
            ]
            if conversations_with_speakers:
                raise ValueError(
                    f"Meeting {self.meeting_id} already has "
                    f"{len(conversations_with_speakers)} "
                    f"conversations with speakers linked"
                )

            # ステップ3: 発言者を抽出・作成
            self.logger.add_log(
                self.meeting_id, "🎤 発言者を抽出しています...", "info"
            )
            extraction_result = self._extract_and_create_speakers(
                conversations, speaker_repo, speaker_service
            )

            # ステップ4: 結果をログに記録（詳細付き）
            speaker_details = extraction_result.get("speaker_details", [])
            role_conversions = extraction_result.get("role_conversions", [])
            
            if speaker_details:
                # 発言者リストを作成
                speaker_summary = []
                speaker_summary.append("【抽出された発言者】")
                for i, (name, party, is_new) in enumerate(speaker_details[:10], 1):
                    status = "🆕 新規" if is_new else "📌 既存"
                    party_text = f" ({party})" if party else ""
                    speaker_summary.append(f"  {i}. {name}{party_text} - {status}")

                if len(speaker_details) > 10:
                    speaker_summary.append(f"  ... 他{len(speaker_details) - 10}人の発言者")

                # 役職名から人名への変換結果を追加
                if role_conversions:
                    speaker_summary.append("\n【役職名から人名への変換】")
                    for role, name in role_conversions[:10]:
                        speaker_summary.append(f"  • {role} → {name}")
                    if len(role_conversions) > 10:
                        speaker_summary.append(f"  ... 他{len(role_conversions) - 10}件の変換")

                self.logger.add_log(
                    self.meeting_id,
                    f"✅ {len(conversations)}件の発言から"
                    f"{extraction_result['unique_speakers']}人の発言者を抽出・変換しました",
                    "success",
                    details="\n".join(speaker_summary),
                )
            else:
                self.logger.add_log(
                    self.meeting_id,
                    f"✅ {len(conversations)}件の発言から"
                    f"{extraction_result['unique_speakers']}人の発言者を抽出しました",
                    "success",
                )

            self.logger.add_log(
                self.meeting_id,
                f"✅ 新規作成: {extraction_result['new_speakers']}人、"
                f"既存: {extraction_result['existing_speakers']}人",
                "info",
            )

            # 処理完了時間を計算
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()

            self.logger.add_log(self.meeting_id, "✅ 処理が完了しました", "success")
            self.logger.add_log(
                self.meeting_id, f"処理時間: {processing_time:.2f}秒", "info"
            )

            # リポジトリを閉じる
            minutes_repo.close()
            conversation_repo.close()
            speaker_repo.close()

            return SyncSpeakerExtractionResult(
                meeting_id=self.meeting_id,
                total_conversations=len(conversations),
                unique_speakers=extraction_result["unique_speakers"],
                new_speakers=extraction_result["new_speakers"],
                existing_speakers=extraction_result["existing_speakers"],
                processing_time_seconds=processing_time,
                processed_at=end_time,
                errors=errors if errors else None,
            )

        except Exception as e:
            error_msg = str(e)
            self.logger.add_log(
                self.meeting_id, f"❌ エラーが発生しました: {error_msg}", "error"
            )
            logger.error(
                f"Processing failed for meeting {self.meeting_id}: {e}", exc_info=True
            )

            # エラーでも結果を返す
            return SyncSpeakerExtractionResult(
                meeting_id=self.meeting_id,
                total_conversations=0,
                unique_speakers=0,
                new_speakers=0,
                existing_speakers=0,
                processing_time_seconds=(datetime.now() - start_time).total_seconds(),
                processed_at=datetime.now(),
                errors=[error_msg],
            )

    def _extract_and_create_speakers(
        self, conversations: list[Any], speaker_repo: Any, speaker_service: Any
    ) -> dict[str, Any]:
        """発言から一意な発言者を抽出し、発言者レコードを作成する

        Args:
            conversations: 発言エンティティのリスト
            speaker_repo: 発言者リポジトリ
            speaker_service: 発言者ドメインサービス

        Returns:
            dict: 抽出結果の統計情報
                - unique_speakers: ユニークな発言者数
                - new_speakers: 新規作成された発言者数
                - existing_speakers: 既存の発言者数
                - speaker_details: 発言者の詳細リスト [(名前, 政党, 新規フラグ), ...]
        """
        from src.config.database import get_db_session_context
        from src.infrastructure.persistence.meeting_repository_impl import (
            MeetingRepositoryImpl,
        )
        from src.infrastructure.persistence.repository_adapter import RepositoryAdapter

        speaker_names: set[tuple[str, str | None]] = set()
        role_conversions: list[tuple[str, str]] = []  # 役職名から人名への変換記録
        seen_conversions: set[str] = set()  # 重複を避けるため

        # 出席者マッピングを取得
        attendees_mapping = None
        if self.meeting_id:
            with get_db_session_context() as session:
                meeting_repo = RepositoryAdapter(MeetingRepositoryImpl, session)
                meeting = meeting_repo.get_by_id(self.meeting_id)
                attendees_mapping = meeting.attendees_mapping if meeting else None

        # 全conversationsから発言者名を抽出
        for conv in conversations:
            if conv.speaker_name:
                # 非人名の発言者を除外
                if speaker_service.is_non_person_speaker(conv.speaker_name):
                    continue

                # 役職名を実際の人名に変換
                original_name = conv.speaker_name
                resolved_name = speaker_service.resolve_speaker_with_attendees(
                    original_name, attendees_mapping
                )
                
                # 変換が行われた場合は記録（重複を避ける）
                if original_name != resolved_name and original_name not in seen_conversions:
                    role_conversions.append((original_name, resolved_name))
                    seen_conversions.add(original_name)

                # 名前から政党情報を抽出
                clean_name, party_info = speaker_service.extract_party_from_name(
                    resolved_name
                )
                speaker_names.add((clean_name, party_info))

        logger.info(f"Found {len(speaker_names)} unique speaker names")

        # 発言者レコードを作成
        new_speakers = 0
        existing_speakers = 0
        speaker_details = []  # 詳細情報を保存

        for name, party_info in speaker_names:
            # 既存の発言者をチェック
            existing = speaker_repo.get_by_name_party_position(name, party_info, None)

            if not existing:
                # 新規発言者を作成
                speaker = Speaker(
                    name=name,
                    political_party_name=party_info,
                    is_politician=bool(party_info),  # 政党があれば政治家と仮定
                )
                speaker_repo.create(speaker)
                new_speakers += 1
                speaker_details.append((name, party_info, True))  # True = 新規
                logger.debug(f"Created new speaker: {name}")
            else:
                existing_speakers += 1
                speaker_details.append((name, party_info, False))  # False = 既存
                logger.debug(f"Speaker already exists: {name}")

        logger.info(
            f"Speaker extraction complete - "
            f"New: {new_speakers}, Existing: {existing_speakers}"
        )

        return {
            "unique_speakers": len(speaker_names),
            "new_speakers": new_speakers,
            "existing_speakers": existing_speakers,
            "speaker_details": speaker_details,
            "role_conversions": role_conversions,  # 役職名から人名への変換記録を追加
        }

    def _extract_and_save_attendees_mapping(
        self, meeting_id: int, minutes: Any
    ) -> dict[str, Any] | None:
        """議事録から出席者マッピングを抽出して保存する

        Args:
            meeting_id: 会議ID
            minutes: 議事録エンティティ

        Returns:
            抽出された出席者マッピング、または既存のマッピング
        """
        from src.config import config
        from src.config.database import get_db_session_context
        from src.infrastructure.persistence.meeting_repository_impl import (
            MeetingRepositoryImpl,
        )
        from src.infrastructure.persistence.repository_adapter import RepositoryAdapter
        from src.minutes_divide_processor.minutes_divider import MinutesDivider
        from src.utils.gcs_storage import GCSStorage

        # 既存のマッピングを確認
        with get_db_session_context() as session:
            meeting_repo = RepositoryAdapter(MeetingRepositoryImpl, session)
            meeting = meeting_repo.get_by_id(meeting_id)
            
            # 既にマッピングがある場合はそれを返す（ただし空でない場合のみ）
            if meeting and meeting.attendees_mapping:
                existing_mapping = meeting.attendees_mapping.get("attendees_mapping", {})
                existing_regular = meeting.attendees_mapping.get("regular_attendees", [])
                
                # 既存のマッピングが空でない場合のみ使用
                if existing_mapping or existing_regular:
                    self.logger.add_log(
                        meeting_id,
                        f"📌 既存の出席者マッピングを使用します "
                        f"(役職: {len(existing_mapping)}人, 一般: {len(existing_regular)}人)",
                        "info",
                    )
                    return meeting.attendees_mapping
                else:
                    self.logger.add_log(
                        meeting_id,
                        "⚠️ 既存のマッピングが空のため、再抽出します",
                        "warning",
                    )

        # 議事録テキストを取得（GCSから）
        minutes_content = None
        if meeting and meeting.gcs_text_uri:
            self.logger.add_log(
                meeting_id,
                f"📥 GCSから議事録を取得中... (URI: {meeting.gcs_text_uri})",
                "info",
            )
            try:
                gcs_storage = GCSStorage(
                    bucket_name=config.GCS_BUCKET_NAME,
                    project_id=config.GCS_PROJECT_ID,
                )
                minutes_content = gcs_storage.download_content(meeting.gcs_text_uri)
                self.logger.add_log(
                    meeting_id,
                    f"✅ GCSから議事録を取得しました (サイズ: {len(minutes_content)} 文字)",
                    "success",
                )
            except Exception as e:
                logger.warning(f"Failed to download from GCS: {e}")
                self.logger.add_log(
                    meeting_id,
                    f"❌ GCSからの取得に失敗: {str(e)}",
                    "error",
                )
        else:
            if not meeting:
                self.logger.add_log(
                    meeting_id,
                    "⚠️ 会議情報が見つかりません",
                    "warning",
                )
            elif not meeting.gcs_text_uri:
                self.logger.add_log(
                    meeting_id,
                    "⚠️ GCS URIが設定されていません",
                    "warning",
                )
        
        if not minutes_content:
            logger.warning(f"No content available for meeting {meeting_id}")
            self.logger.add_log(
                meeting_id,
                "⚠️ 議事録コンテンツが利用できません",
                "warning",
            )
            return None

        try:
            # MinutesDividerを使って出席者情報を抽出
            divider = MinutesDivider()
            
            # 出席者と議事の境界を検出
            self.logger.add_log(
                meeting_id,
                "🔍 議事録から出席者情報の境界を検出中...",
                "info",
            )
            boundary_result = divider.detect_attendee_boundary(minutes_content)
            
            if boundary_result.boundary_found:
                self.logger.add_log(
                    meeting_id,
                    f"✅ 境界を検出しました (タイプ: {boundary_result.boundary_type})",
                    "success",
                )
                # 境界に基づいて議事録を分割
                attendees_text, speech_text = divider.split_minutes_by_boundary(
                    minutes_content, boundary_result
                )
                
                if attendees_text:
                    self.logger.add_log(
                        meeting_id,
                        f"📝 出席者情報を解析中... (テキストサイズ: {len(attendees_text)} 文字)",
                        "info",
                    )
                    
                    # 出席者テキストの先頭部分をデバッグログに出力
                    preview = attendees_text[:500] if len(attendees_text) > 500 else attendees_text
                    self.logger.add_log(
                        meeting_id,
                        "🔍 出席者テキストのプレビュー",
                        "info",
                        details=preview,
                    )
                    
                    # 出席者マッピングを抽出
                    attendees_mapping = divider.extract_attendees_mapping(attendees_text)
                    
                    # 抽出結果をデバッグログに出力
                    self.logger.add_log(
                        meeting_id,
                        f"📊 抽出結果: 役職マッピング={len(attendees_mapping.attendees_mapping)}件, "
                        f"一般出席者={len(attendees_mapping.regular_attendees)}人",
                        "info",
                    )
                    
                    # データベースに保存
                    with get_db_session_context() as session:
                        meeting_repo = RepositoryAdapter(MeetingRepositoryImpl, session)
                        meeting = meeting_repo.get_by_id(meeting_id)
                        if meeting:
                            meeting.attendees_mapping = {
                                "attendees_mapping": attendees_mapping.attendees_mapping,
                                "regular_attendees": attendees_mapping.regular_attendees,
                            }
                            meeting_repo.update(meeting)
                            
                            self.logger.add_log(
                                meeting_id,
                                "💾 出席者マッピングを保存しました",
                                "success",
                            )
                    
                    return {
                        "attendees_mapping": attendees_mapping.attendees_mapping,
                        "regular_attendees": attendees_mapping.regular_attendees,
                    }
                else:
                    self.logger.add_log(
                        meeting_id,
                        "⚠️ 出席者情報が空です",
                        "warning",
                    )
            else:
                self.logger.add_log(
                    meeting_id,
                    f"⚠️ 出席者情報の境界を検出できませんでした (理由: {boundary_result.reason})",
                    "warning",
                )
            
            logger.warning(f"Could not find attendees boundary for meeting {meeting_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract attendees mapping: {e}")
            self.logger.add_log(
                meeting_id,
                f"⚠️ 出席者マッピングの抽出に失敗しました: {str(e)}",
                "warning",
            )
            return None
