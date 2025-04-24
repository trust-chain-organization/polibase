# Use absolute import from the 'src' package when running as a module
import src.config.config as config
from src.utils.text_extractor import extract_text_from_pdf
import duckdb
import csv
from langchain_google_genai import ChatGoogleGenerativeAI
# Relative import for modules within the same subpackage is fine
from .minutes_divide_processor.minutes_process_agent import MinutesProcessAgent
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
  llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
  agent = MinutesProcessAgent(llm=llm)
  speaker_and_speech_content_list = agent.run(original_minutes=extracted_text)
  # CSVファイルに変換
  output_file = 'output.csv'
  convert_to_csv(speaker_and_speech_content_list, output_file)
  print(f"CSVファイルに変換しました: data/output/{output_file}")
  return speaker_and_speech_content_list

if __name__ == "__main__":
    speaker_and_speech_content_list = main()
    print("--------結果出力--------")
    print(speaker_and_speech_content_list)
    print('全部終わったよ')
