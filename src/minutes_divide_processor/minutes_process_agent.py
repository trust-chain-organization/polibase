import uuid
from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.store.memory import InMemoryStore

from ..infrastructure.external.instrumented_llm_service import InstrumentedLLMService
from ..infrastructure.interfaces.llm_service import ILLMService
from .minutes_divider import MinutesDivider

# Use relative import for modules within the same package
from .models import (
    MinutesProcessState,
    SectionStringList,
    SpeakerAndSpeechContent,
)


class MinutesProcessAgent:
    def __init__(
        self,
        llm_service: ILLMService | InstrumentedLLMService | None = None,
        k: int | None = None,
    ):
        """
        Initialize MinutesProcessAgent

        Args:
            llm_service: LLMService instance (creates default if not provided)
                Can be ILLMService or InstrumentedLLMService
            k: Number of sections
        """
        # 各種ジェネレータの初期化
        self.minutes_divider = MinutesDivider(llm_service=llm_service, k=k or 5)
        self.in_memory_store = InMemoryStore()
        self.graph = self._create_graph()

    def _create_graph(self) -> Any:
        # グラフの初期化
        workflow = StateGraph(MinutesProcessState)
        checkpointer = MemorySaver()

        workflow.add_node("process_minutes", self._process_minutes)  # type: ignore[arg-type]
        workflow.add_node("divide_minutes_to_keyword", self._divide_minutes_to_keyword)  # type: ignore[arg-type]
        workflow.add_node("divide_minutes_to_string", self._divide_minutes_to_string)  # type: ignore[arg-type]
        workflow.add_node("check_length", self._check_length)  # type: ignore[arg-type]
        workflow.add_node("divide_speech", self._divide_speech)  # type: ignore[arg-type]
        workflow.set_entry_point("process_minutes")
        workflow.add_edge("process_minutes", "divide_minutes_to_keyword")
        workflow.add_edge("divide_minutes_to_keyword", "divide_minutes_to_string")
        workflow.add_edge("divide_minutes_to_string", "check_length")
        workflow.add_edge("check_length", "divide_speech")
        workflow.add_conditional_edges(
            "divide_speech",
            lambda state: state.index < state.section_list_length,  # type: ignore[arg-type, no-any-return]
            {True: "divide_speech", False: END},
        )

        return workflow.compile(checkpointer=checkpointer, store=self.in_memory_store)  # type: ignore[return-value]

    def _get_from_memory(self, namespace: str, memory_id: str) -> Any | None:
        namespace_for_memory = ("1", namespace)
        memory_item = self.in_memory_store.get(namespace_for_memory, memory_id)
        if memory_item is None:
            return None
        else:
            return memory_item.value

    def _put_to_memory(self, namespace: str, memory: dict[str, Any]) -> str:
        user_id = "1"
        namespace_for_memory = (user_id, namespace)
        memory_id = str(uuid.uuid4())
        # https://langchain-ai.github.io/langgraph/concepts/persistence/#basic-usage
        self.in_memory_store.put(namespace_for_memory, memory_id, memory)
        return memory_id

    def _process_minutes(self, state: MinutesProcessState) -> dict[str, str]:
        # 議事録の文字列に対する前処理を行う
        processed_minutes = self.minutes_divider.pre_process(state.original_minutes)
        memory = {"processed_minutes": processed_minutes}
        memory_id = self._put_to_memory(namespace="processed_minutes", memory=memory)
        return {"processed_minutes_memory_id": memory_id}

    def _divide_minutes_to_keyword(self, state: MinutesProcessState) -> dict[str, Any]:
        memory_id = state.processed_minutes_memory_id
        memory_data = self._get_from_memory(
            namespace="processed_minutes", memory_id=memory_id
        )
        if memory_data is None or "processed_minutes" not in memory_data:
            raise ValueError("Failed to retrieve processed_minutes from memory")

        processed_minutes = memory_data["processed_minutes"]
        if not isinstance(processed_minutes, str):
            raise TypeError("processed_minutes must be a string")

        # 議事録を分割する
        section_info_list = self.minutes_divider.section_divide_run(processed_minutes)
        section_list_length = len(section_info_list.section_info_list)
        print("divide_minutes_to_keyword_done")
        return {
            # リストとして返す
            "section_info_list": section_info_list.section_info_list,
            "section_list_length": section_list_length,
        }

    def _divide_minutes_to_string(self, state: MinutesProcessState) -> dict[str, str]:
        memory_id = state.processed_minutes_memory_id
        memory_data = self._get_from_memory("processed_minutes", memory_id)
        if memory_data is None or "processed_minutes" not in memory_data:
            raise ValueError("Failed to retrieve processed_minutes from memory")

        processed_minutes = memory_data["processed_minutes"]
        if not isinstance(processed_minutes, str):
            raise TypeError("processed_minutes must be a string")

        # 議事録を分割する
        section_string_list = self.minutes_divider.do_divide(
            processed_minutes, state.section_info_list
        )
        memory = {"section_string_list": section_string_list}
        memory_id = self._put_to_memory(namespace="section_string_list", memory=memory)
        return {"section_string_list_memory_id": memory_id}

    def _check_length(self, state: MinutesProcessState) -> dict[str, str]:
        memory_id = state.section_string_list_memory_id
        memory_data = self._get_from_memory("section_string_list", memory_id)
        if memory_data is None or "section_string_list" not in memory_data:
            raise ValueError("Failed to retrieve section_string_list from memory")

        section_string_list = memory_data["section_string_list"]
        if not isinstance(section_string_list, SectionStringList):
            raise TypeError("section_string_list must be a SectionStringList instance")

        # 文字列のバイト数をチェックする
        redivide_section_string_list = self.minutes_divider.check_length(
            section_string_list
        )
        memory = {"redivide_section_string_list": redivide_section_string_list}
        memory_id = self._put_to_memory(
            namespace="redivide_section_string_list", memory=memory
        )
        print("check_length_done")
        return {"redivide_section_string_list_memory_id": memory_id}

    def _divide_speech(self, state: MinutesProcessState) -> dict[str, Any]:
        memory_id = state.section_string_list_memory_id
        memory_data = self._get_from_memory("section_string_list", memory_id)
        if memory_data is None or "section_string_list" not in memory_data:
            raise ValueError("Failed to retrieve section_string_list from memory")

        section_string_list = memory_data["section_string_list"]
        if not isinstance(section_string_list, SectionStringList):
            raise TypeError("section_string_list must be a SectionStringList instance")

        if state.index - 1 < len(section_string_list.section_string_list):
            # すべてのセクションを処理する（0, 1, 2, 3の制限を削除）
            # 発言者と発言内容に分割する
            speaker_and_speech_content_list = self.minutes_divider.speech_divide_run(
                section_string_list.section_string_list[state.index - 1]
            )
        else:
            print(
                f"Warning: Index {state.index - 1} is out of range "
                + "for section_string_list."
            )
            speaker_and_speech_content_list = None
        print(
            f"divide_speech_done on index_number: {state.index} "
            + f"all_length: {state.section_list_length}"
        )
        # 現在のdivide_speech_listを取得
        memory_id = state.divided_speech_list_memory_id
        memory_data = self._get_from_memory("divided_speech_list", memory_id)

        # 初回はNULLなのでその場合は空配列を作成
        if memory_data is None or "divided_speech_list" not in memory_data:
            divided_speech_list: list[SpeakerAndSpeechContent] = []
        else:
            divided_speech_list = memory_data["divided_speech_list"]
            if not isinstance(divided_speech_list, list):
                raise TypeError("divided_speech_list must be a list")
            # Cast to proper type after type check
            divided_speech_list = divided_speech_list

        # もしspeaker_and_speech_content_listがNoneの場合は、
        # 現在のリストを更新用リストとして返す
        if speaker_and_speech_content_list is None:
            print(
                "Warning: speaker_and_speech_content_list is None. "
                + "Skipping this section."
            )
            updated_speaker_and_speech_content_list = divided_speech_list
            memory: dict[str, list[SpeakerAndSpeechContent]] = {
                "divided_speech_list": updated_speaker_and_speech_content_list
            }
            memory_id = self._put_to_memory(
                namespace="divided_speech_list", memory=memory
            )
        else:
            # すべてのセクションの結果を追加
            updated_speaker_and_speech_content_list: list[SpeakerAndSpeechContent] = (
                divided_speech_list
                + speaker_and_speech_content_list.speaker_and_speech_content_list
            )
            memory: dict[str, list[SpeakerAndSpeechContent]] = {
                "divided_speech_list": updated_speaker_and_speech_content_list
            }
            memory_id = self._put_to_memory(
                namespace="divided_speech_list", memory=memory
            )
        incremented_index = state.index + 1
        print(f"incremented_speech_divide_index: {incremented_index}")
        return {"divided_speech_list_memory_id": memory_id, "index": incremented_index}

    def run(self, original_minutes: str) -> list[SpeakerAndSpeechContent]:
        # 初期状態の設定
        initial_state = MinutesProcessState(original_minutes=original_minutes)
        # グラフの実行
        final_state = self.graph.invoke(
            initial_state, config={"recursion_limit": 300, "thread_id": "example-1"}
        )
        # 分割結果の取得
        memory_id = final_state["divided_speech_list_memory_id"]
        memory_data = self._get_from_memory("divided_speech_list", memory_id)
        if memory_data is None or "divided_speech_list" not in memory_data:
            raise ValueError("Failed to retrieve divided_speech_list from memory")

        divided_speech_list = memory_data["divided_speech_list"]
        if not isinstance(divided_speech_list, list):
            raise TypeError("divided_speech_list must be a list")

        print(f"DEBUG: Retrieved {len(divided_speech_list)} speeches from memory")

        # Filter out invalid speeches at the aggregate level
        print(f"Filtering speeches from {len(divided_speech_list)} items...")
        filtered_list = []
        seen_contents = {}

        for item in divided_speech_list:
            # Skip if speech content is empty or too short (likely a section title)
            if not item.speech_content or len(item.speech_content.strip()) < 20:
                content_preview = (
                    item.speech_content[:50] if item.speech_content else ""
                )
                print(
                    f"Filtering out short/empty speech: "
                    f"{item.speaker} - '{content_preview}'"
                )
                continue

            # Skip if speech content matches common section titles or patterns
            section_titles = [
                "正副委員長の互選",
                "開会",
                "閉会",
                "議事",
                "出席委員",
                "欠席委員",
                "委員会記録",
                "配付資料",
                "要求資料",
                "特記事項",
            ]
            if item.speech_content in section_titles:
                print(
                    f"Filtering out section title: "
                    f"{item.speaker} - {item.speech_content}"
                )
                continue

            # Skip if this looks like a misattributed closing statement
            # (common pattern: chairman's name appears after closing statement)
            if (
                "散会" in item.speech_content or "閉会" in item.speech_content
            ) and "委員長" in item.speaker:
                print(
                    f"Filtering out likely misattributed closing: "
                    f"{item.speaker} - {item.speech_content[:50]}"
                )
                continue

            # Track how many times we've seen this exact content
            content_key = item.speech_content.strip()
            seen_contents[content_key] = seen_contents.get(content_key, 0) + 1

            filtered_list.append(item)

        # Second pass: remove speeches where the same content appears for many speakers
        final_list = []
        for item in filtered_list:
            content_key = item.speech_content.strip()
            # If more than 5 speakers have the exact same content, it's likely an error
            if seen_contents[content_key] > 5:
                print(
                    f"Filtering out duplicate speech "
                    f"({seen_contents[content_key]} occurrences): {item.speaker}"
                )
                continue
            final_list.append(item)

        # Re-number speech_order for remaining items
        for i, item in enumerate(final_list):
            item.speech_order = i + 1

        print(f"Filtered speeches: {len(divided_speech_list)} -> {len(final_list)}")

        return final_list  # type: ignore[return-value]
