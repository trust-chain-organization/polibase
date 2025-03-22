from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
from langchain_core.runnables import RunnablePassthrough
import re
import unicodedata
import json
from models import (
    SectionInfoList, SectionStringList, RedivideSectionStringList, RedividedSectionInfoList, SpeakerAndSpeechContentList, SectionString
)

class MinutesDividor:
  def __init__(self, llm: ChatGoogleGenerativeAI, k: int = 5):
    self.section_info_list_formatted_llm = llm.with_structured_output(SectionInfoList)
    self.speaker_and_speech_content_formatted_llm = llm.with_structured_output(SpeakerAndSpeechContentList)
    self.k = 5

  # 議事録の文字列に対する前処理を行う
  def pre_process(self, original_minutes: str) -> str:
    # 議事録の改行とスペースを削除します
    processed_minutes = original_minutes.replace('\r\n', '\n')  # Windows改行を統一
    processed_minutes = processed_minutes.replace('（', '(').replace('）', ')') # 丸括弧を半角に統一
    processed_minutes = re.sub(r'[　]', ' ', processed_minutes) # 全角スペースを半角スペースに統一
    processed_minutes = re.sub(r'[ ]+', ' ', processed_minutes).strip() # 連続するスペースを1つのスペースに置換し、前後の空白を削除
    processed_minutes = ''.join(ch for ch in processed_minutes if unicodedata.category(ch)[0] != 'C') # 制御文字を削除
    processed_minutes = ''.join(ch for ch in processed_minutes if unicodedata.category(ch)[0] != 'Z') # 区切り記号を削除
    return processed_minutes

  def do_divide(self, processed_minutes: str, section_info_list: SectionInfoList) -> SectionStringList:
    # キーワードをベースに分割を実施
    """
    section_info_listは以下のような形式で渡されます
    section_info_list = [
      SectionInfo(chapter_number=38, keyword='◎高速鉄道部長(塩見康裕)今御紹介があ'),
      ....
    ]
    processed_minutesをkeywordから始まって次のchapter_numberのkeywordの手前まで抽出する
    最終的に以下のような形式のsection_string_listを作成する
    section_string_list = [
      SectionStringList(chapter_number=38, section_string='◎高速鉄道部長(塩見康裕)今御紹介がありました。高速鉄道部長の塩見康弘です.....'),
      ...
    ]
    """
    # JSON文字列をPythonのリストに変換
    if isinstance(section_info_list, str):
      section_info_list = json.loads(section_info_list)
    else:
      section_info_list = section_info_list
    split_minutes_list = []
    start_index = 0
    skipped_keywords = []
    i = 0
    output_order = 1 # 出現順を記録する変数
    while i < len(section_info_list):
      section_info = section_info_list[i]
      keyword = section_info.keyword
      # 最初のキーワードの場合、議事録の先頭から検索を開始
      if i == 0 and start_index == 0:
          start_index = processed_minutes.find(keyword)
          if start_index == -1:
            start_index = 0
            print(f"最初のキーワード '{keyword}' が見つからないため、議事録の先頭から開始します")
      # キーワードが見つからない場合はスキップ
      if start_index == -1:
        print(f"警告: キーワード '{keyword}' が議事録に見つかりません。スキップします。")
        skipped_keywords.append(keyword)
        i += 1
        continue
      # 次のキーワードの開始位置を検索
      next_keyword_index = -1
      j = i + 1
      while j < len(section_info_list):
        next_keyword = section_info_list[j].keyword
        next_keyword_index = processed_minutes.find(next_keyword, start_index + len(keyword))
        if next_keyword_index != -1:
          break
        else:
          print(f"警告: キーワード '{next_keyword}' が議事録に見つかりません。スキップします。")
          skipped_keywords.append(next_keyword)
          j += 1
      if next_keyword_index == -1:
          end_index = len(processed_minutes)
      else:
          end_index = next_keyword_index
      # 分割された文字列を取得
      split_text = processed_minutes[start_index:end_index].strip()
      # SectionStringインスタンスを作成してlistにappend
      split_minutes_list.append(SectionString(chapter_number=output_order, section_string=split_text))
      # 次の検索開始位置を更新
      start_index = end_index
      # インデックスと出現順を更新
      i = j
      output_order += 1
    return split_minutes_list
  
  # 議事録の情報をベースに議事録を30分割する
  def section_divide_run(self, minutes: str) -> SectionInfoList:
    prompt_template = hub.pull("divide_chapter_prompt")
    runnable_prompt = prompt_template | self.section_info_list_formatted_llm
    # 議事録を分割するチェーンを作成
    chain = {"minutes": RunnablePassthrough()} | runnable_prompt
    # 引数に議事録を渡して実行
    result = chain.invoke(
        {
            "minutes": minutes,
        }
    )
    # resultがSectionInfoList型であることを確認
    if isinstance(result, SectionInfoList):
        section_info_list = result.section_info_list
    else:
        raise TypeError("Expected result to be of type SectionInfoList")
    # section_info_listのchapter_numberを確認して、連番になっているか確認
    last_chapter_number = 0
    for section_info in section_info_list:
      if section_info.chapter_number != last_chapter_number + 1:
        print(f"section_infoのchapter_numberが連番になっていません。")
        # 連番になっていない場合はsection_info.chapter_numberをlast_chapter_number + 1で上書きする
        section_info.chapter_number = last_chapter_number + 1
      last_chapter_number = section_info.chapter_number
    # 連番が上書きされたsection_info_listを返す
    return SectionInfoList(section_info_list=section_info_list)

  def check_length(self, section_string_list: SectionStringList) -> RedivideSectionStringList:
    redivide_list = []
    for index, section_string in enumerate(section_string_list):
      size_in_bytes = len(section_string.section_string.encode('utf-8'))
      print(f"size_in_bytes: {size_in_bytes}")
      if size_in_bytes > 6000:  # 6000文字より多いか確認
        print(f"section_stringの文字数が6000文字を超えています。再分割します。")
        redivide_dict = {"original_index": index, "redivide_section_string_bytes": size_in_bytes, "redivide_section_string": section_string}
        redivide_list.append(redivide_dict)
    return redivide_list
  
  def do_redivide(self, redivide_section_string_list: RedivideSectionStringList) -> RedividedSectionInfoList:
    prompt_template = hub.pull("redivide_chapter_prompt")
    runnable_prompt = prompt_template | self.section_info_list_formatted_llm
    # 議事録を分割するチェーンを作成
    chain = {"minutes": RunnablePassthrough()} | runnable_prompt

    section_string_list = []
    for index, redivide_section_string in redivide_section_string_list:
      divide_counter = redivide_section_string.redivide_section_string_bytes // 20000000
      divide_counter = divide_counter + 2 

      # 引数に議事録を渡して実行
      result = chain.invoke(
          {
              "minutes": redivide_section_string.redivide_section_string,
              "original_index": redivide_section_string.original_index,
              "divide_counter": divide_counter
          }
      )
      section_string_list = section_string_list + result
    return section_string_list

  # 発言者と発言内容に分割する
  def speech_divide_run(self, section_string: SectionString) -> SpeakerAndSpeechContentList:
    prompt_template = hub.pull("comment_divide_prompt")
    runnable_prompt = prompt_template | self.speaker_and_speech_content_formatted_llm
    chain = {"section_string": RunnablePassthrough()} | runnable_prompt
    result = chain.invoke(
        {
            "section_string": section_string,
        }
    )
    if result is None:
        print("Error: result is None")
        return SpeakerAndSpeechContentList(speaker_and_speech_content_list=[])
    # resultがSectionInfoList型であることを確認
    if isinstance(result, SpeakerAndSpeechContentList):
        speaker_and_speech_content_list = result.speaker_and_speech_content_list
    else:
        raise TypeError("Expected result to be of type SpeakerAndSpeechContentList")
    # speaker_and_speech_content_listのspeech_orderを確認して、連番になっているか確認
    last_speech_order = 0
    for speaker_and_speech_content in speaker_and_speech_content_list:
      if speaker_and_speech_content.speech_order != last_speech_order + 1:
        print(f"speaker_and_speech_contentのspeech_orderが連番になっていません。")
        # 連番になっていない場合はspeaker_and_speech_content.speech_orderをlast_chapter_number + 1で上書きする
        speaker_and_speech_content.speech_order = last_speech_order + 1
      last_speech_order = speaker_and_speech_content.speech_order
    return SpeakerAndSpeechContentList(speaker_and_speech_content_list=speaker_and_speech_content_list)