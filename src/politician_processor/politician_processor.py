from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
from langchain_core.runnables import RunnablePassthrough
from langgraph.graph import Graph, StateGraph
from typing import Annotated, Dict, TypedDict
import re
import unicodedata
from src.politician_processor.models import (
    PoliticianInfo,
    PoliticianInfoList,
    PoliticianProcessState
)

class PoliticianProcessor:
    def __init__(self, llm: ChatGoogleGenerativeAI):
        self.llm = llm
        self.politician_info_formatted_llm = llm.with_structured_output(PoliticianInfoList)

    def pre_process(self, state: PoliticianProcessState) -> PoliticianProcessState:
        """議事録の前処理を行う"""
        original_minutes = state["original_minutes"]
        
        # 議事録の改行とスペースを削除
        processed_minutes = original_minutes.replace('\r\n', '\n')
        processed_minutes = processed_minutes.replace('（', '(').replace('）', ')')
        processed_minutes = re.sub(r'[　]', ' ', processed_minutes)
        processed_minutes = re.sub(r'[ ]+', ' ', processed_minutes).strip()
        processed_minutes = ''.join(ch for ch in processed_minutes if unicodedata.category(ch)[0] != 'C')
        processed_minutes = ''.join(ch for ch in processed_minutes if unicodedata.category(ch)[0] != 'Z')
        
        state["processed_minutes"] = processed_minutes
        return state

    def extract_politician_info(self, state: PoliticianProcessState) -> PoliticianProcessState:
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

    def create_graph(self) -> Graph:
        """LangGraphを使用して処理フローを定義する"""
        workflow = StateGraph(PoliticianProcessState)
        
        # ノードの追加
        workflow.add_node("pre_process", self.pre_process)
        workflow.add_node("extract_politician_info", self.extract_politician_info)
        
        # エッジの追加
        workflow.add_edge("pre_process", "extract_politician_info")
        
        # 開始ノードと終了ノードの設定
        workflow.set_entry_point("pre_process")
        workflow.set_finish_point("extract_politician_info")
        
        return workflow.compile()

    def process_minutes(self, minutes: str) -> PoliticianInfoList:
        """議事録を処理して政治家情報を抽出する"""
        # 初期状態の作成
        initial_state = PoliticianProcessState(
            original_minutes=minutes,
            processed_minutes="",
            politician_info_list=[],
            current_section="",
            section_index=0
        )
        
        # グラフの作成と実行
        graph = self.create_graph()
        final_state = graph.invoke(initial_state)
        
        return PoliticianInfoList(politician_info_list=final_state["politician_info_list"]) 