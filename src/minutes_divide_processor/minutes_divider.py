import json
import logging
import re
import unicodedata
from typing import Any

from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from ..services.llm_factory import LLMServiceFactory

# Use relative import for modules within the same package
from .models import (
    RedividedSectionInfoList,
    RedivideSectionString,
    RedivideSectionStringList,
    SectionInfoList,
    SectionString,
    SectionStringList,
    SpeakerAndSpeechContentList,
)

logger = logging.getLogger(__name__)


class MinutesDivider:
    def __init__(self, llm_service: Any = None, k: int = 5):
        """
        Initialize MinutesDivider

        Args:
            llm_service: LLMService instance (creates default if not provided)
            k: Number of sections (default 5)
        """
        if llm_service is None:
            factory = LLMServiceFactory()
            llm_service = factory.create_advanced()

        self.llm_service = llm_service
        self.section_info_list_formatted_llm = llm_service.get_structured_llm(
            SectionInfoList
        )
        self.speaker_and_speech_content_formatted_llm = llm_service.get_structured_llm(
            SpeakerAndSpeechContentList
        )
        self.k = k

    # 議事録の文字列に対する前処理を行う
    def pre_process(self, original_minutes: str) -> str:
        # 議事録の改行とスペースを削除します
        processed_minutes = original_minutes.replace("\r\n", "\n")  # Windows改行を統一
        processed_minutes = processed_minutes.replace("（", "(").replace(
            "）", ")"
        )  # 丸括弧を半角に統一
        # 全角スペースを半角スペースに統一
        processed_minutes = re.sub(r"[　]", " ", processed_minutes)
        # 連続するスペースを1つのスペースに置換し、前後の空白を削除
        processed_minutes = re.sub(r"[ ]+", " ", processed_minutes).strip()
        # 制御文字を削除
        processed_minutes = "".join(
            ch for ch in processed_minutes if unicodedata.category(ch)[0] != "C"
        )
        # 区切り記号を削除
        processed_minutes = "".join(
            ch for ch in processed_minutes if unicodedata.category(ch)[0] != "Z"
        )
        return processed_minutes

    def do_divide(
        self,
        processed_minutes: str,
        section_info_list: SectionInfoList | list[Any],
    ) -> SectionStringList:
        if not processed_minutes:
            return SectionStringList(section_string_list=[])

        # JSON文字列をPythonのリストに変換
        if isinstance(section_info_list, str):
            section_info_list = json.loads(section_info_list)

        # section_info_listがすでにリストの場合はそのまま使用
        if isinstance(section_info_list, list):
            section_info_list_data = section_info_list
        else:
            section_info_list_data = section_info_list.section_info_list

        split_minutes_list: list[SectionString] = []
        start_index = 0
        skipped_keywords: list[str] = []
        i = 0
        output_order = 1  # 出現順を記録する変数
        while i < len(section_info_list_data):
            section_info = section_info_list_data[i]
            keyword = section_info.keyword
            # 最初のキーワードの場合、議事録の先頭から検索を開始
            if i == 0 and start_index == 0:
                start_index = processed_minutes.find(keyword)
                if start_index == -1:
                    start_index = 0
                    print(
                        f"最初のキーワード '{keyword}' が見つからないため、"
                        + "議事録の先頭から開始します"
                    )
            # キーワードが見つからない場合はスキップ
            if start_index == -1:
                print(
                    f"警告: キーワード '{keyword}' が議事録に見つかりません。"
                    + "スキップします。"
                )
                skipped_keywords.append(keyword)
                i += 1
                continue
            # 次のキーワードの開始位置を検索
            next_keyword_index = -1
            j = i + 1
            while j < len(section_info_list_data):
                next_keyword = section_info_list_data[j].keyword
                next_keyword_index = processed_minutes.find(
                    next_keyword, start_index + len(keyword)
                )
                if next_keyword_index != -1:
                    break
                else:
                    print(
                        f"警告: キーワード '{next_keyword}' が議事録に"
                        + "見つかりません。スキップします。"
                    )
                    skipped_keywords.append(next_keyword)
                    j += 1
            if next_keyword_index == -1:
                end_index = len(processed_minutes)
            else:
                end_index = next_keyword_index
            # 分割された文字列を取得
            split_text = processed_minutes[start_index:end_index].strip()
            # SectionStringインスタンスを作成してlistにappend
            split_minutes_list.append(
                SectionString(
                    chapter_number=section_info.chapter_number,
                    sub_chapter_number=1,
                    section_string=split_text,
                )
            )
            # 次の検索開始位置を更新
            start_index = end_index
            # インデックスと出現順を更新
            i = j
            output_order += 1
        return SectionStringList(section_string_list=split_minutes_list)

    # 議事録の情報をベースに議事録を30分割する
    def section_divide_run(self, minutes: str) -> SectionInfoList:
        # Try to get prompt from hub first, fallback to local
        try:
            prompt_template = hub.pull("divide_chapter_prompt")
        except Exception as e:
            logger.warning(f"Failed to pull prompt from hub: {e}. Using local prompt.")
            prompt_template = self.llm_service.get_prompt("minutes_divide")

        runnable_prompt = prompt_template | self.section_info_list_formatted_llm
        # 議事録を分割するチェーンを作成
        chain = {"minutes": RunnablePassthrough()} | runnable_prompt
        # 引数に議事録を渡して実行
        result = self.llm_service.invoke_with_retry(
            chain,
            {
                "minutes": minutes,
            },
        )

        # resultがSectionInfoList型でない場合の処理を追加
        if not isinstance(result, SectionInfoList):
            if isinstance(result, dict) and "section_info_list" in result:
                result = SectionInfoList(**result)
            elif isinstance(result, list):
                result = SectionInfoList(section_info_list=result)
            else:
                raise TypeError(f"Unexpected result type: {type(result)}")

        # section_info_listのchapter_numberを確認して、連番になっているか確認
        last_chapter_number = 0
        for section_info in result.section_info_list:
            if section_info.chapter_number != last_chapter_number + 1:
                print("section_infoのchapter_numberが連番になっていません。")
                # 連番になっていない場合はsection_info.chapter_numberを
                # last_chapter_number + 1で上書きする
                section_info.chapter_number = last_chapter_number + 1
            last_chapter_number = section_info.chapter_number

        return result

    def check_length(
        self, section_string_list: SectionStringList
    ) -> RedivideSectionStringList:
        redivide_list: list[RedivideSectionString] = []
        for index, section_string in enumerate(section_string_list.section_string_list):
            size_in_bytes = len(section_string.section_string.encode("utf-8"))
            print(f"size_in_bytes: {size_in_bytes}")
            if size_in_bytes > 6000:  # 6000文字より多いか確認
                print("section_stringの文字数が6000文字を超えています。再分割します。")
                redivide_dict = RedivideSectionString(
                    original_index=index,
                    redivide_section_string_bytes=size_in_bytes,
                    redivide_section_string=section_string,
                )
                redivide_list.append(redivide_dict)
        return RedivideSectionStringList(redivide_section_string_list=redivide_list)

    def do_redivide(
        self, redivide_section_string_list: RedivideSectionStringList
    ) -> RedividedSectionInfoList:
        # Try to get prompt from hub first, fallback to local
        try:
            prompt_template = hub.pull("redivide_chapter_prompt")
        except Exception as e:
            logger.warning(f"Failed to pull prompt from hub: {e}. Using local prompt.")
            # Create a fallback prompt similar to redivide
            prompt_template = ChatPromptTemplate.from_template(
                "セクションを{divide_counter}個に再分割してください。\n"
                + "元のインデックス: {original_index}\n\n"
                + "セクション内容:\n{minutes}"
            )

        runnable_prompt = prompt_template | self.section_info_list_formatted_llm
        # 議事録を分割するチェーンを作成
        chain = {"minutes": RunnablePassthrough()} | runnable_prompt

        section_info_list: list[Any] = []
        for (
            redivide_section_string
        ) in redivide_section_string_list.redivide_section_string_list:
            divide_counter = (
                redivide_section_string.redivide_section_string_bytes // 20000000
            )
            divide_counter = divide_counter + 2

            # 引数に議事録を渡して実行
            result = self.llm_service.invoke_with_retry(
                chain,
                {
                    "minutes": (
                        redivide_section_string.redivide_section_string.section_string
                    ),
                    "original_index": redivide_section_string.original_index,
                    "divide_counter": divide_counter,
                },
            )
            if isinstance(result, SectionInfoList):
                section_info_list.extend(result.section_info_list)
            elif isinstance(result, list):
                section_info_list.extend(result)
            else:
                logger.warning(f"Unexpected result type: {type(result)}")
        return RedividedSectionInfoList(redivided_section_info_list=section_info_list)

    # 発言者と発言内容に分割する
    def speech_divide_run(
        self, section_string: SectionString
    ) -> SpeakerAndSpeechContentList:
        # 国会議事録向けのプロンプトを使用
        prompt_template = self.llm_service.get_prompt("speech_divide_kokkai")

        runnable_prompt = (
            prompt_template | self.speaker_and_speech_content_formatted_llm
        )
        chain = {"section_string": RunnablePassthrough()} | runnable_prompt
        result = self.llm_service.invoke_with_retry(
            chain,
            {
                "section_string": (
                    section_string.section_string
                ),  # section_stringオブジェクトから文字列を抽出
            },
        )
        if result is None:
            print("Error: result is None")
            return SpeakerAndSpeechContentList(speaker_and_speech_content_list=[])
        # resultがSectionInfoList型であることを確認
        if isinstance(result, SpeakerAndSpeechContentList):
            speaker_and_speech_content_list = result.speaker_and_speech_content_list
        else:
            raise TypeError("Expected result to be of type SpeakerAndSpeechContentList")
        # speaker_and_speech_content_listのspeech_orderを確認して、
        # 連番になっているか確認
        last_speech_order = 0
        for speaker_and_speech_content in speaker_and_speech_content_list:
            if speaker_and_speech_content.speech_order != last_speech_order + 1:
                print(
                    "speaker_and_speech_contentのspeech_orderが連番になっていません。"
                )
                # 連番になっていない場合は
                # speaker_and_speech_content.speech_orderを
                # last_chapter_number + 1で上書きする
                speaker_and_speech_content.speech_order = last_speech_order + 1
            last_speech_order = speaker_and_speech_content.speech_order
        return SpeakerAndSpeechContentList(
            speaker_and_speech_content_list=speaker_and_speech_content_list
        )
