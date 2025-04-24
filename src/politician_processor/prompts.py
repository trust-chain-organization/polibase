from langchain.prompts import PromptTemplate

POLITICIAN_EXTRACTION_TEMPLATE = """以下の議事録から政治家の情報を抽出してください。

議事録:
{minutes}

以下の情報を抽出してください：
1. 政治家の名前
2. 所属政党（分かる場合）
3. 役職（分かる場合）
4. 発言回数
5. 発言内容

抽出した情報は、以下の形式で構造化データとして返してください：
- 政治家の名前は必須です
- 所属政党と役職は分かる場合のみ含めてください
- 発言回数は数値で返してください
- 発言内容はリスト形式で返してください

注意点：
- 同じ政治家が複数回発言している場合は、1つのエントリにまとめてください
- 発言内容は要約せず、そのまま抽出してください
- 政治家の名前は、敬称（「さん」「議員」など）を含めないでください
- 所属政党は、正式名称で記載してください
"""

politician_extraction_prompt = PromptTemplate.from_template(POLITICIAN_EXTRACTION_TEMPLATE) 