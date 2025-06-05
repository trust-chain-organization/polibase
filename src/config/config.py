import os
from dotenv import load_dotenv
load_dotenv()

LANGCHAIN_TRACING_V2 = os.getenv('LANGCHAIN_TRACING_V2')
LANGCHAIN_ENDPOINT = os.getenv('LANGCHAIN_ENDPOINT')
LANGCHAIN_API_KEY = os.getenv('LANGCHAIN_API_KEY')
LANGCHAIN_PROJECT = os.getenv('LANGCHAIN_PROJECT')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://polibase_user:polibase_password@localhost:5432/polibase_db')

# GCS Configuration
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'polibase-scraped-minutes')
GCS_PROJECT_ID = os.getenv('GCS_PROJECT_ID')  # Optional, uses default if not set
GCS_UPLOAD_ENABLED = os.getenv('GCS_UPLOAD_ENABLED', 'false').lower() == 'true'

def set_env():
    # 環境変数として設定
    os.environ['LANGCHAIN_TRACING_V2'] = LANGCHAIN_TRACING_V2
    os.environ['LANGCHAIN_ENDPOINT'] = LANGCHAIN_ENDPOINT
    os.environ['LANGCHAIN_API_KEY'] = LANGCHAIN_API_KEY
    os.environ['LANGCHAIN_PROJECT'] = LANGCHAIN_PROJECT
    os.environ['GOOGLE_API_KEY'] = GOOGLE_API_KEY
    os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY
    os.environ['TAVILY_API_KEY'] = TAVILY_API_KEY
    os.environ['DATABASE_URL'] = DATABASE_URL
