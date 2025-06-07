from langchain import hub
from langchain_core.runnables import RunnablePassthrough
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import PoliticianInfoList


class PoliticianExtractor:
    def __init__(self, llm: ChatGoogleGenerativeAI, k: int = 5):
        self.politician_extract_llm = llm.with_structured_output(PoliticianInfoList)
        self.speaker_and_speech_content_formatted_llm = llm.with_structured_output(
            PoliticianInfoList
        )
        self.k = k

    def politician_extract_run(self, minutes: str) -> PoliticianInfoList:
        prompt_template = hub.pull("politician_extraction_prompt")
        runnable_prompt = prompt_template | self.politician_extract_llm
        # 議事録を分割するチェーンを作成
        chain = {"minutes": RunnablePassthrough()} | runnable_prompt
        # 引数に議事録を渡して実行
        result = chain.invoke(
            {
                "minutes": minutes,
            }
        )
        return result
