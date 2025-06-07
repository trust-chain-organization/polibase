import operator
from typing import Annotated

from pydantic import BaseModel, Field


class SectionInfo(BaseModel):
    chapter_number: int = Field(
        default=1, description="分割した文字列を前から順に割り振った番号"
    )
    keyword: str = Field(
        ..., description="分割した文字列の先頭30文字をそのまま抽出した文字列"
    )


class SectionInfoList(BaseModel):
    section_info_list: list[SectionInfo] = Field(
        default_factory=list, description="各小節ごとのキーワード情報"
    )


class SectionString(BaseModel):
    chapter_number: int = Field(
        default=1, description="分割した文字列を前から順に割り振った番号"
    )
    sub_chapter_number: int = Field(default=1, description="再分割した場合の文字列番号")
    section_string: str = Field(..., description="分割した文字列")


class SectionStringList(BaseModel):
    section_string_list: list[SectionString] = Field(
        default_factory=list, description="各小節ごとの文字列リスト"
    )


class RedivideSectionString(BaseModel):
    redivide_section_string: SectionString = Field(
        ..., description="再分割対象の文字列"
    )
    redivide_section_string_bytes: int = Field(
        ..., description="再分割対象の文字列のバイト数"
    )
    original_index: int = Field(default=1, description="元のindex")


class RedivideSectionStringList(BaseModel):
    redivide_section_string_list: list[RedivideSectionString] = Field(
        default_factory=list, description="再分割対象の文字列リスト"
    )


class RedividedSectionInfo(BaseModel):
    chapter_number: int = Field(default=1, description="再分割前の順番を表す番号")
    sub_chapter_number: int = Field(
        default=1, description="再分割した中での順番を表す番号"
    )
    keyword: str = Field(
        ..., description="分割した文字列の先頭30文字をそのまま抽出した文字列"
    )


class RedividedSectionInfoList(BaseModel):
    redivided_section_info_list: list[RedividedSectionInfo] = Field(
        default_factory=list, description="再分割されたキーワードリスト"
    )


class SpeakerAndSpeechContent(BaseModel):
    speaker: str = Field(..., description="発言者")
    speech_content: str = Field(..., description="発言内容")
    chapter_number: int = Field(
        default=1, description="分割した文字列を前から順に割り振った番号"
    )
    sub_chapter_number: int = Field(default=1, description="再分割した場合の文字列番号")
    speech_order: int = Field(default=1, description="発言順")


class SpeakerAndSpeechContentList(BaseModel):
    speaker_and_speech_content_list: list[SpeakerAndSpeechContent] = Field(
        default_factory=list, description="各発言者と発言内容のリスト"
    )


class MinutesProcessState(BaseModel):
    original_minutes: str = Field(..., description="元の議事録全体")
    processed_minutes_memory_id: str = Field(
        default="", description="LLMに渡す前処理を施した議事録を保存したメモリID"
    )
    section_info_list: Annotated[list[SectionInfo], operator.add] = Field(
        default_factory=list, description="分割された各小節ごとのキーワード情報"
    )
    section_string_list_memory_id: str = Field(
        default="", description="分割された各小節ごとの文字列リストを保存したメモリID"
    )
    redivide_section_string_list: Annotated[
        list[RedivideSectionString], operator.add
    ] = Field(default_factory=list, description="再分割対象の文字列リスト")
    divided_speech_list_memory_id: str = Field(
        default="", description="分割された各発言者と発言内容のリストを保存したメモリID"
    )
    section_list_length: int = Field(default=0, description="分割できたsectionnの数")
    index: int = Field(default=1, description="現在処理しているsection数")
