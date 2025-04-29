from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import Graph, StateGraph
from langgraph.store.memory import InMemoryStore
from typing import Annotated, Dict, TypedDict, Optional
import re
import unicodedata
from src.politician_extract_processor.models import (
    PoliticianInfo,
    PoliticianInfoList,
    PoliticianProcessState
)
from .politician_extractor import PoliticianExtractor

class PoliticianProcessor:
    def __init__(self, llm: ChatGoogleGenerativeAI, k: Optional[int] = None):
        self.minutes_devidor = PoliticianExtractor(llm=llm, k=k)
        self.in_memory_store = InMemoryStore()
        self.graph = self._create_graph()

    def _extract_politician_info(self, state: PoliticianProcessState) -> PoliticianProcessState:
        """議事録から政治家情報を抽出する"""
        prompt_template = hub.pull("politician_extraction_prompt")
        runnable_prompt = prompt_template | self.politician_info_formatted_llm
        
        chain = {"minutes": RunnablePassthrough()} | runnable_prompt
        
        result = chain.invoke({
            "minutes": state["processed_minutes"]
        })
        
        if isinstance(result, PoliticianInfoList):
            state["politician_info_list"] = result.politician_info_list
        else:
            raise TypeError("Expected result to be of type PoliticianInfoList")
        
        return state

    def _check_politician_info(self, state: PoliticianProcessState) -> PoliticianProcessState:

        """政治家情報を確認する"""


        return state

    def create_graph(self) -> Graph:
        """LangGraphを使用して処理フローを定義する"""
        workflow = StateGraph(PoliticianProcessState)

        # ノードの追加
        workflow.add_node("extract_politician_info", self._extract_politician_info)
        workflow.add_node("check_politician_info", self._check_politician_info)

        # エッジの追加
        workflow.add_edge("extract_politician_info", "check_politician_info")

        # 開始ノードと終了ノードの設定
        workflow.set_entry_point("extract_politician_info")
        workflow.set_finish_point("check_politician_info")

        return workflow.compile()

    def run(self, original_minutes: str) -> str:
        # 初期状態の設定
        initial_state = PoliticianProcessState(original_minutes=original_minutes)
        # グラフの実行
        final_state = self.graph.invoke(initial_state, config={"recursion_limit": 300,"thread_id": "example-1"})
        # 分割結果の取得
        memory_id = final_state["divided_speech_list_memory_id"]
        divided_speech_list = self._get_from_memory("divided_speech_list", memory_id)
        return divided_speech_list
