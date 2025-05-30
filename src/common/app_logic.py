"""
アプリケーション共通ロジック
"""
from typing import List, Optional, Any
import src.config.config as config
from src.utils.text_extractor import extract_text_from_pdf
from src.config.database import test_connection


def setup_environment() -> None:
    """環境変数を設定する"""
    config.set_env()


def load_pdf_text(file_path: str = 'data/minutes.pdf') -> str:
    """
    PDFファイルからテキストを読み込む
    
    Args:
        file_path: PDFファイルのパス
        
    Returns:
        str: 抽出されたテキスト
        
    Raises:
        FileNotFoundError: ファイルが見つからない場合
    """
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
    except FileNotFoundError:
        print(f"Source file not found: {file_path}")
        raise
    
    return extract_text_from_pdf(file_content)


def validate_database_connection() -> bool:
    """
    データベース接続をテストする
    
    Returns:
        bool: 接続が成功した場合True
    """
    print("🔍 データベース接続テストを開始...")
    if not test_connection():
        print("❌ データベースに接続できません。docker compose でPostgreSQLが起動していることを確認してください。")
        return False
    return True


def run_main_process(process_func, process_name: str, display_status_func, save_func, *args, **kwargs) -> Any:
    """
    メイン処理の共通フロー
    
    Args:
        process_func: 実行する処理関数
        process_name: 処理名（ログ用）
        display_status_func: データベース状態表示関数
        save_func: データベース保存関数
        *args, **kwargs: process_funcに渡す引数
        
    Returns:
        Any: 処理結果
    """
    try:
        # データベース接続テスト
        if not validate_database_connection():
            return None
        
        print("📊 処理前のデータベース状態:")
        display_status_func()
        
        # メイン処理の実行
        result = process_func(*args, **kwargs)
        
        # データベースに保存
        saved_ids = save_func(result)
        print(f"💾 データベース保存完了: {len(saved_ids)}件の{process_name}レコードを保存しました")
        print(f"{process_name}の抽出が完了しました。{len(saved_ids)}件のレコードをデータベースに保存しました。")
        
        print("\n📊 処理後のデータベース状態:")
        display_status_func()
        
        return result
        
    except Exception as e:
        print(f"❌ {process_name}処理エラー: {e}")
        raise


def print_completion_message(result_data: Any, process_name: str = "処理") -> None:
    """
    処理完了メッセージを表示する
    
    Args:
        result_data: 処理結果データ
        process_name: 処理名
    """
    print("--------結果出力--------")
    print(result_data)
    print(f'{process_name}が全部終わったよ')
