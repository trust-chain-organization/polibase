"""Constants for scraper prompts."""

PROPOSAL_EXTRACTION_PROMPT = (
    "以下の政府・議会のウェブページから議案情報を抽出してください。\n"
    "\n"
    "URL: {url}\n"
    "\n"
    "ページ内容:\n"
    "{text_content}\n"
    "\n"
    "以下の情報を抽出してください"
    "（見つからない場合は空文字列または null を返してください）：\n"
    "1. content: 議案名・法案名（タイトル）\n"
    "2. proposal_number: 議案番号（例：第210回国会第1号、議第15号など）\n"
    "3. submission_date: 提出日・上程日・議決日など\n"
    "   （日付として認識できるもの、例：2023年12月1日、令和5年12月1日）\n"
    "4. summary: 議案の概要・説明（あれば最初の200文字程度）\n"
    "\n"
    "JSON形式で返してください。日付はそのまま抽出された文字列で返してください（変換不要）。"
)

PROPOSAL_EXTRACTION_SYSTEM_PROMPT = (
    "あなたは日本の政府・議会ウェブサイトから情報を抽出する専門家です。"
)
