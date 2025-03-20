import config
from utils.text_extractor import extract_text_from_pdf
import operator
import uuid
from typing import Annotated, List, Dict, Optional
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
# from langchain_core.stores import BaseStore, InMemoryStore
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
import json
import csv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import ConfigurableField, RunnablePassthrough
from langgraph.checkpoint.memory import MemorySaver
from langchain import hub
import re
import unicodedata

# config.pyを呼び出して環境変数を設定
config.set_env()

# PDF ファイルを読み込み
try:
    with open('minutes.pdf', 'rb') as f:
        file_content = f.read()
except FileNotFoundError:
    print(f"File not found: {pdf_path}")
    exit()
extracted_text = extract_text_from_pdf(file_content)

class SectionInfo(BaseModel):
    chapter_number: int = Field(..., description="分割した文字列を前から順に割り振った番号")
    keyword: str = Field(..., description="分割した文字列の先頭30文字をそのまま抽出した文字列")
class SectionInfoList(BaseModel):
    section_info_list: list[SectionInfo] = Field(default_factory=list, description="各小節ごとのキーワード情報")

class SectionString(BaseModel):
    chapter_number: int = Field(..., description="分割した文字列を前から順に割り振った番号")
    sub_chapter_number: int = Field(default=0, description="再分割した場合の文字列番号")
    section_string: str = Field(..., description="分割した文字列")
class SectionStringList(BaseModel):
    section_string_list: List[SectionString] = Field(default_factory=list, description="各小節ごとの文字列リスト")

class RedivideSectionString(BaseModel):
    redivide_section_string: SectionString = Field(..., description="再分割対象の文字列")
    redivide_section_string_bytes: int = Field(..., description="再分割対象の文字列のバイト数")
    original_index: int = Field(..., description="元のindex")
class RedivideSectionStringList(BaseModel):
    redivide_section_string_list: List[RedivideSectionString] = Field(default_factory=list, description="再分割対象の文字列リスト")

class RedividedSectionInfo(BaseModel):
    chapter_number: int = Field(..., description="再分割前の順番を表す番号")
    sub_chapter_number: int = Field(..., description="再分割した中での順番を表す番号")
    keyword: str = Field(..., description="分割した文字列の先頭30文字をそのまま抽出した文字列")
class RedividedSectionInfoList(BaseModel):
    redivided_section_info_list: List[RedividedSectionInfo] = Field(default_factory=list, description="再分割されたキーワードリスト")

class SpeakerAndSpeechContent(BaseModel):
    speaker: str = Field(..., description="発言者")
    speech_content: str = Field(..., description="発言内容")
    speech_order: int = Field(..., description="発言順")
class SpeakerAndSpeechContentList(BaseModel):
    speaker_and_speech_content_list: List[SpeakerAndSpeechContent] = Field(default_factory=list, description="各発言者と発言内容のリスト")

class MinutesProcessState(BaseModel):
    original_minutes: str = Field(..., description="元の議事録全体")
    processed_minutes_memory_id: str = Field(default="", description="LLMに渡す前処理を施した議事録を保存したメモリID")
    section_info_list: Annotated[list[SectionInfo], operator.add] = Field(default_factory=list, description="分割された各小節ごとのキーワード情報")
    section_string_list_memory_id: str = Field(default="", description="分割された各小節ごとの文字列リストを保存したメモリID")
    redivide_section_string_list: Annotated[list[RedivideSectionString], operator.add] = Field(default_factory=list, description="再分割対象の文字列リスト")
    # speaker_and_speech_content_list: Annotated[list[SpeakerAndSpeechContent], operator.add] = Field(default_factory=list, description="各発言者と発言内容のリスト")
    divided_speech_list_memory_id: str = Field(default="", description="分割された各発言者と発言内容のリストを保存したメモリID")
    section_list_length: int = Field(default=0, description="分割できたsectionnの数")
    index: int = Field(default=1, description="現在処理しているsection数")


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
    return result

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
    return result

# 議事録処理AIエージェントのクラス
class MinutesProcessAgent:
  def __init__(self, llm: ChatGoogleGenerativeAI, k: Optional[int] = None):
    # 各種ジェネレータの初期化
    self.minutes_devidor = MinutesDividor(llm=llm, k=k)
    self.in_memory_store = InMemoryStore()
    self.graph = self._create_graph()

  def _create_graph(self) -> StateGraph:
    # グラフの初期化
    workflow = StateGraph(MinutesProcessState)
    checkpointer = MemorySaver()

    workflow.add_node("process_minutes", self._process_minutes)
    workflow.add_node("divide_minutes_to_keyword", self._divide_minutes_to_keyword)
    workflow.add_node("divide_minutes_to_string", self._divide_minutes_to_string)
    workflow.add_node("check_length", self._check_length)
    workflow.add_node("divide_speech", self._divide_speech)
    workflow.set_entry_point("process_minutes")
    workflow.add_edge("process_minutes", "divide_minutes_to_keyword")
    workflow.add_edge("divide_minutes_to_keyword", "divide_minutes_to_string")
    workflow.add_edge("divide_minutes_to_string", "check_length")
    workflow.add_edge("check_length", "divide_speech")
    workflow.add_conditional_edges(
        "divide_speech",
        lambda state: state.index < state.section_list_length,
        {True: "divide_speech", False: END}
    )

    return workflow.compile(checkpointer=checkpointer, store=self.in_memory_store)

  def _get_from_memory(self, namespace: tuple, memory_id: str) -> dict:
    namespace_for_memory = ("1", namespace)
    memory_item = self.in_memory_store.get(namespace_for_memory, memory_id)
    if memory_item is None:
      return None
    else:
      return memory_item.value[namespace]

  def _put_to_memory(self, namespace: tuple, memory: dict) -> None:
    user_id = "1"
    namespace_for_memory = (user_id, namespace)
    memory_id = str(uuid.uuid4())
    # https://langchain-ai.github.io/langgraph/concepts/persistence/#basic-usage
    self.in_memory_store.put(namespace_for_memory, memory_id, memory)
    return memory_id

  def _process_minutes(self, state: MinutesProcessState) -> dict:
    # 議事録の文字列に対する前処理を行う
    processed_minutes = self.minutes_devidor.pre_process(state.original_minutes)
    memory = {'processed_minutes': processed_minutes}
    memory_id = self._put_to_memory(namespace="processed_minutes", memory=memory)
    return {
      "processed_minutes_memory_id": memory_id
    }
  def _divide_minutes_to_keyword(self, state: MinutesProcessState) -> dict:
    memory_id = state.processed_minutes_memory_id
    processed_minutes = self._get_from_memory(namespace="processed_minutes", memory_id=memory_id)
    # 議事録を分割する
    section_info_list = self.minutes_devidor.section_divide_run(processed_minutes)
    section_list_length = len(section_info_list.section_info_list)
    print("divide_minutes_to_keyword_done")
    return {
        "section_info_list": section_info_list.section_info_list, # SectionInfoList ではなく SectionInfo のリストを返す
        "section_list_length": section_list_length
    }
  def _divide_minutes_to_string(self, state: MinutesProcessState) -> dict:
    memory_id = state.processed_minutes_memory_id
    processed_minutes = self._get_from_memory("processed_minutes", memory_id)
    # 議事録を分割する
    section_string_list = self.minutes_devidor.do_divide(processed_minutes, state.section_info_list)
    memory = {'section_string_list': section_string_list}
    memory_id = self._put_to_memory(namespace="section_string_list", memory=memory)
    return {
        "section_string_list_memory_id": memory_id
    }
  def _check_length(self, state: MinutesProcessState) -> dict:
    memory_id = state.section_string_list_memory_id
    section_string_list = self._get_from_memory("section_string_list", memory_id)
    # 文字列のバイト数をチェックする
    redivide_section_string_list = self.minutes_devidor.check_length(section_string_list)
    memory = {'redivide_section_string_list': redivide_section_string_list}
    memory_id = self._put_to_memory(namespace="redivide_section_string_list", memory=memory)
    print("check_length_done")
    return {
        "redivide_section_string_list_memory_id": memory_id
    }

  def _divide_speech(self, state: MinutesProcessState) -> dict:
    memory_id = state.section_string_list_memory_id
    section_string_list = self._get_from_memory("section_string_list", memory_id)
    if state.index - 1 < len(section_string_list):
        if state.index - 1 in [0,1,2,3]:
            # 発言者と発言内容に分割する
            speaker_and_speech_content_list = self.minutes_devidor.speech_divide_run(section_string_list[state.index - 1])
        else:
            speaker_and_speech_content_list = None
    else:
        print(f"Warning: Index {state.index - 1} is out of range for section_string_list.")
        speaker_and_speech_content_list = None
    print(f"divide_speech_done on index_number: {state.index} all_length: {state.section_list_length}")
    # 現在のdivide_speech_listを取得
    memory_id = state.divided_speech_list_memory_id
    divided_speech_list = self._get_from_memory("divided_speech_list", memory_id)
    # 初回はNULLなのでその場合は空配列を作成
    if divided_speech_list is None:
        divided_speech_list = []
    # もしspeaker_and_speech_content_listがNoneの場合は、現在のリストを更新用リストとして返す
    if speaker_and_speech_content_list is None:
        print("Warning: speaker_and_speech_content_list is None. Skipping this section.")
        updated_speaker_and_speech_content_list = divided_speech_list
    else:
      if state.index - 1 in [0,1,2,3]:
        updated_speaker_and_speech_content_list = divided_speech_list + speaker_and_speech_content_list.speaker_and_speech_content_list
        memory = {'divided_speech_list': updated_speaker_and_speech_content_list}
        memory_id = self._put_to_memory(namespace="divided_speech_list", memory=memory)
      else:
        updated_speaker_and_speech_content_list = divided_speech_list
        memory = {'divided_speech_list': updated_speaker_and_speech_content_list}
        memory_id = self._put_to_memory(namespace="divided_speech_list", memory=memory)
    incremented_index = state.index + 1
    print(f"incremented_speech_divide_index: {incremented_index}")
    return {
        "divided_speech_list_memory_id": memory_id,
        "index": incremented_index
    }

  def run(self, original_minutes: str) -> str:
    # 初期状態の設定
    initial_state = MinutesProcessState(original_minutes=original_minutes)
    # グラフの実行
    final_state = self.graph.invoke(initial_state, config={"recursion_limit": 300,"thread_id": "example-1"})
    # 分割結果の取得
    memory_id = final_state["divided_speech_list_memory_id"]
    divided_speech_list = self._get_from_memory("divided_speech_list", memory_id)
    return divided_speech_list

def convert_to_csv(speaker_and_speech_content_list, output_file):
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Speaker', 'Speech Content', 'Speech Order'])
        for item in speaker_and_speech_content_list:
            writer.writerow([item.speaker, item.speech_content, item.speech_order])
def main():
  llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
  agent = MinutesProcessAgent(llm=llm)
  speaker_and_speech_content_list = agent.run(original_minutes=extracted_text)
  # CSVファイルに変換
  output_file = 'output.csv'
  convert_to_csv(speaker_and_speech_content_list, output_file)
  print(f"CSVファイルに変換しました: {output_file}")
  pop = duckdb.read_csv("output.csv")
  return speaker_and_speech_content_list

speaker_and_speech_content_list = main()
print("--------結果出力--------")
print(speaker_and_speech_content_list)
print('全部終わったよ')
