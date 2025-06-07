"""Speaker information extraction"""

import logging
import re

from bs4 import BeautifulSoup

from ..models import SpeakerData


class SpeakerExtractor:
    """発言者情報抽出器"""

    # 発言者パターン
    SPEAKER_PATTERNS = [
        # 【山田太郎議員】
        (
            re.compile(
                r"【([^】]+(?:議員|委員|市長|町長|村長|知事|局長|部長|課長|理事|次長|参事|主幹))】"
            ),
            True,
        ),
        (re.compile(r"【([^】]+)】"), False),  # 役職なしパターン
        # ○山田太郎議員
        (
            re.compile(
                r"○\s*([^（\s]+(?:議員|委員|市長|町長|村長|知事|局長|部長|課長|理事|次長|参事|主幹))"
            ),
            True,
        ),
        (re.compile(r"○\s*([^（\s：]+)"), False),
        # 山田太郎議員：
        (
            re.compile(
                r"^([^：\s]+(?:議員|委員|市長|町長|村長|知事|局長|部長|課長|理事|次長|参事|主幹))："
            ),
            True,
        ),
        (re.compile(r"^([^：\s]+)："), False),
        # （山田太郎議員）
        (
            re.compile(
                r"（([^）]+(?:議員|委員|市長|町長|村長|知事|局長|部長|課長|理事|次長|参事|主幹))）"
            ),
            True,
        ),
        # 山田太郎議員 （改行や空白の後）
        (
            re.compile(
                r"^\s*([^（\s]+(?:議員|委員|市長|町長|村長|知事|局長|部長|課長|理事|次長|参事|主幹))\s*$"
            ),
            True,
        ),
    ]

    # 役職パターン
    ROLE_PATTERNS = [
        "議員",
        "委員",
        "市長",
        "町長",
        "村長",
        "知事",
        "局長",
        "部長",
        "課長",
        "理事",
        "次長",
        "参事",
        "主幹",
        "議長",
        "副議長",
        "委員長",
        "副委員長",
    ]

    def __init__(self, logger: logging.Logger | None = None):
        self.logger = logger or logging.getLogger(__name__)

    def extract_speakers(self, content: str) -> list[SpeakerData]:
        """コンテンツから発言者情報を抽出

        Args:
            content: 議事録テキスト

        Returns:
            発言者データのリスト
        """
        speakers = []
        lines = content.split("\n")

        current_speaker = None
        current_role = None
        current_content = []

        for _i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            # 発言者を検出
            speaker_info = self._detect_speaker(line)

            if speaker_info:
                # 前の発言者の内容を保存
                if current_speaker and current_content:
                    speaker_data = SpeakerData(
                        name=current_speaker,
                        content="\n".join(current_content).strip(),
                        role=current_role,
                    )
                    speakers.append(speaker_data)

                # 新しい発言者を設定
                current_speaker = speaker_info["name"]
                current_role = speaker_info.get("role")
                current_content = []

                # 発言者マーカーの後の内容を追加
                remaining_text = speaker_info.get("remaining_text", "").strip()
                if remaining_text:
                    current_content.append(remaining_text)
            else:
                # 発言者が見つからない場合は現在の発言に追加
                if current_speaker:
                    current_content.append(line)

        # 最後の発言者の内容を保存
        if current_speaker and current_content:
            speaker_data = SpeakerData(
                name=current_speaker,
                content="\n".join(current_content).strip(),
                role=current_role,
            )
            speakers.append(speaker_data)

        return speakers

    def _detect_speaker(self, line: str) -> dict[str, str] | None:
        """行から発言者を検出

        Returns:
            {'name': '発言者名', 'role': '役職', 
             'remaining_text': '残りのテキスト'} or None
        """
        for pattern, has_role in self.SPEAKER_PATTERNS:
            match = pattern.search(line)
            if match:
                full_name = match.group(1).strip()

                # 役職を抽出
                role = None
                name = full_name

                if has_role:
                    for role_pattern in self.ROLE_PATTERNS:
                        if role_pattern in full_name:
                            role = role_pattern
                            name = full_name.replace(role_pattern, "").strip()
                            break

                # マッチ後の残りのテキスト
                remaining_text = line[match.end() :].strip()

                return {"name": name, "role": role, "remaining_text": remaining_text}

        return None

    def extract_speakers_with_context(self, soup: BeautifulSoup) -> list[SpeakerData]:
        """HTMLから構造を考慮して発言者情報を抽出

        Args:
            soup: BeautifulSoup object

        Returns:
            発言者データのリスト
        """
        speakers = []

        # 発言ブロックを探す（dlタグやdivタグで構造化されている場合）
        speech_blocks = self._find_speech_blocks(soup)

        if speech_blocks:
            for block in speech_blocks:
                speaker_data = self._extract_from_block(block)
                if speaker_data:
                    speakers.append(speaker_data)
        else:
            # 構造化されていない場合はテキストベースで抽出
            content = soup.get_text(separator="\n", strip=True)
            speakers = self.extract_speakers(content)

        return speakers

    def _find_speech_blocks(self, soup: BeautifulSoup) -> list[BeautifulSoup]:
        """発言ブロックを検索"""
        blocks = []

        # dlタグ（定義リスト）で構造化されている場合
        dl_blocks = soup.find_all("dl", class_=re.compile("speech|statement|remark"))
        blocks.extend(dl_blocks)

        # divタグで構造化されている場合
        div_blocks = soup.find_all("div", class_=re.compile("speech|statement|remark"))
        blocks.extend(div_blocks)

        # 特定の属性を持つ要素
        speaker_elements = soup.find_all(attrs={"data-speaker": True})
        blocks.extend(speaker_elements)

        return blocks

    def _extract_from_block(self, block: BeautifulSoup) -> SpeakerData | None:
        """構造化されたブロックから発言者情報を抽出"""
        # dtタグから発言者名を取得
        dt = block.find("dt")
        if dt:
            speaker_text = dt.get_text(strip=True)
            speaker_info = self._detect_speaker(speaker_text)

            # ddタグから発言内容を取得
            dd = block.find("dd")
            if dd and speaker_info:
                content = dd.get_text(separator="\n", strip=True)
                return SpeakerData(
                    name=speaker_info["name"],
                    content=content,
                    role=speaker_info.get("role"),
                )

        # data-speaker属性から発言者名を取得
        speaker_name = block.get("data-speaker")
        if speaker_name:
            content = block.get_text(separator="\n", strip=True)
            role = self._extract_role_from_name(speaker_name)
            name = speaker_name
            for role_pattern in self.ROLE_PATTERNS:
                if role_pattern in speaker_name:
                    name = speaker_name.replace(role_pattern, "").strip()
                    break

            return SpeakerData(name=name, content=content, role=role)

        return None

    def _extract_role_from_name(self, name: str) -> str | None:
        """名前から役職を抽出"""
        for role in self.ROLE_PATTERNS:
            if role in name:
                return role
        return None

    def merge_continuous_speeches(
        self, speakers: list[SpeakerData]
    ) -> list[SpeakerData]:
        """同じ発言者の連続した発言をマージ

        Args:
            speakers: 発言者データのリスト

        Returns:
            マージされた発言者データのリスト
        """
        if not speakers:
            return []

        merged = []
        current = speakers[0]

        for speaker in speakers[1:]:
            if speaker.name == current.name and speaker.role == current.role:
                # 同じ発言者の場合はコンテンツをマージ
                current = SpeakerData(
                    name=current.name,
                    content=current.content + "\n\n" + speaker.content,
                    role=current.role,
                )
            else:
                # 異なる発言者の場合は現在の発言者を保存
                merged.append(current)
                current = speaker

        # 最後の発言者を保存
        merged.append(current)

        return merged
