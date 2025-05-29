"""
PostgreSQL データベース設定ファイル
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# データベース接続設定
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://polibase_user:polibase_password@localhost:5432/polibase_db')

def get_db_engine():
    """PostgreSQLデータベースエンジンを取得"""
    return create_engine(DATABASE_URL)

def get_db_session():
    """データベースセッションを取得"""
    engine = get_db_engine()
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def test_connection():
    """データベース接続をテスト"""
    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            result = connection.execute("SELECT 1")
            print("PostgreSQL データベース接続成功")
            return True
    except Exception as e:
        print(f"PostgreSQL データベース接続エラー: {e}")
        return False

if __name__ == "__main__":
    test_connection()
