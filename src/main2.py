# Use absolute import from the 'src' package when running as a module
import src.config.config as config
from src.utils.text_extractor import extract_text_from_pdf
import duckdb
import csv
from langchain_google_genai import ChatGoogleGenerativeAI
# ↓↓↓ インポート元を __init__.py 経由に変更 ↓↓↓
from src.politician_extract_processor import PoliticianProcessAgent
import os

# config.pyを呼び出して環境変数を設定
config.set_env()

# PDF ファイルを読み込み
try:
    with open('data/minutes.pdf', 'rb') as f:
        file_content = f.read()
except FileNotFoundError:
    print("Source file not found: data/minutes.pdf")
    exit()
extracted_text = extract_text_from_pdf(file_content)

def convert_to_csv(speaker_and_speech_content_list, output_file):
    output_path = f'data/output/{output_file}'
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Speaker', 'Speech Content', 'Speech Order'])
        for item in speaker_and_speech_content_list:
            writer.writerow([item.speaker, item.speech_content, item.speech_order])

def main():
  llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0) # モデル名を修正
  agent = PoliticianProcessAgent(llm=llm)
  # ↓↓↓ agent.run の戻り値の型が不明なため、一旦変数名を変更（必要に応じて修正） ↓↓↓
  politician_info_result = agent.run(original_minutes=extracted_text)
  # CSVファイルに変換 (PoliticianInfoList を想定した仮実装、要調整)
  output_file = 'politician_output.csv'
  # convert_to_csv(politician_info_result, output_file) # PoliticianInfoList 用のCSV変換関数が必要
  print(f"政治家情報の抽出が完了しました。結果は変数 politician_info_result を確認してください。") # CSV出力は未実装
  # ↓↓↓ 戻り値の型に合わせて修正 ↓↓↓
  return politician_info_result

if __name__ == "__main__":
    # ↓↓↓ main() の戻り値に合わせて変数名を変更 ↓↓↓
    politician_info_result = main()
    print("--------結果出力--------")
    # ↓↓↓ 変数名を変更 ↓↓↓
    print(politician_info_result)
    print('全部終わったよ')
