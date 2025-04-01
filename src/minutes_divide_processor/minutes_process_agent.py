import uuid
from typing import Optional
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from src.minutes_divide_processor.models import (
    SectionInfoList, SectionStringList, RedivideSectionStringList, RedividedSectionInfoList, SpeakerAndSpeechContentList, SectionString, MinutesProcessState
)
from src.minutes_divide_processor.minutes_dividor import MinutesDividor

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
