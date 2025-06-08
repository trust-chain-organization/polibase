from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import Graph, StateGraph
from langgraph.store.memory import InMemoryStore

from src.politician_extract_processor.models import (
    PoliticianInfo,
    PoliticianInfoList,
    PoliticianProcessState,
)

from .politician_extractor import PoliticianExtractor


class PoliticianProcessAgent:
    def __init__(self, llm: ChatGoogleGenerativeAI, k: int | None = None):
        self.politician_extractor = PoliticianExtractor(
            llm=llm, k=k if k is not None else 5
        )  # kのデフォルト値を考慮
        self.in_memory_store = InMemoryStore()
        self.graph = self._create_graph()

    def _extract_politician_info(
        self, state: PoliticianProcessState
    ) -> dict:  # 戻り値の型を Dict に変更
        """議事録から政治家情報を抽出する"""
        original_minutes = state.original_minutes  # Pydanticモデルの属性としてアクセス
        result = self.politician_extractor.politician_extract_run(original_minutes)

        if isinstance(result, PoliticianInfoList):
            # 更新するフィールドとその値を辞書で返す
            return {"politician_info_list": result.politician_info_list}
        else:
            # このエラーは通常発生しないはず (Pydanticのバリデーションによる)
            raise TypeError(
                "Expected politician_extract_run to return PoliticianInfoList"
            )

    def _check_politician_info(
        self, state: PoliticianProcessState
    ) -> dict:  # 戻り値の型を Dict に変更
        """政治家情報を確認する"""
        # 現状は状態を変更しないため、空の辞書を返す
        # 将来的にこのノードで状態を利用・変更する場合は、
        # state.politician_info_list などでアクセスし、
        # 更新内容を辞書で返す。
        return {}

    def _create_graph(self) -> Graph:
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

    def run(self, original_minutes: str) -> PoliticianInfoList:
        # 初期状態の設定
        initial_state: PoliticianProcessState = {
            "original_minutes": original_minutes,
            "politician_info_list": [],  # None から空リスト [] に修正
        }
        # グラフの実行
        # configのthread_idは永続化ストアを利用する場合に特に意味を持つが、
        # InMemoryStoreでも実行の区別に使える
        final_state_dict = self.graph.invoke(
            initial_state, config={"recursion_limit": 300, "thread_id": "example-1"}
        )

        # final_state_dict は PoliticianProcessState と同じキーを持つ辞書
        politician_info_list_data: list[PoliticianInfo] | None = final_state_dict.get(
            "politician_info_list"
        )

        if politician_info_list_data is not None:
            return PoliticianInfoList(politician_info_list=politician_info_list_data)
        else:
            # 抽出結果がなかった場合、空のリストを持つ PoliticianInfoList を返す
            return PoliticianInfoList(politician_info_list=[])
