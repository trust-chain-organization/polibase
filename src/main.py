import src.config.config as config
from utils.text_extractor import extract_text_from_pdf
import duckdb
import csv
from langchain_google_genai import ChatGoogleGenerativeAI
from src.minutes_divide_processor.models import (
    SectionInfo, SectionInfoList, SectionString, SectionStringList, RedivideSectionString, RedivideSectionStringList,
    RedividedSectionInfo, RedividedSectionInfoList, SpeakerAndSpeechContent, SpeakerAndSpeechContentList, MinutesProcessState
)
from src.minutes_divide_processor.minutes_process_agent import MinutesProcessAgent

# config.pyを呼び出して環境変数を設定
config.set_env()

# PDF ファイルを読み込み
try:
    with open('minutes.pdf', 'rb') as f:
        file_content = f.read()
except FileNotFoundError:
    print(f"File not found: {pdf_path}")
    exit()
extracted_text = extract_text_from_pdf(file_content)

def convert_to_csv(speaker_and_speech_content_list, output_file):
    with open(output_file, mode='w', newline='', encoding='utf-8') as file:
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
  print(f"CSVファイルに変換しました: {output_file}")
  pop = duckdb.read_csv("output.csv")
  return speaker_and_speech_content_list

speaker_and_speech_content_list = main()
print("--------結果出力--------")
print(speaker_and_speech_content_list)
print('全部終わったよ')
