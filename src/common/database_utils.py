"""
データベース操作に関する共通処理
"""
from typing import List, Dict, Any, Protocol
from abc import ABC, abstractmethod


class DatabaseRepository(Protocol):
    """データベースリポジトリの共通インターフェース"""
    
    def get_count(self) -> int:
        """レコード数を取得する"""
        ...
    
    def get_all(self) -> List[Dict[str, Any]]:
        """全レコードを取得する"""
        ...


def display_repository_status(repo: DatabaseRepository, table_name: str, 
                            additional_stats: Dict[str, Any] = None) -> None:
    """
    データベースリポジトリの状態を表示する共通処理
    
    Args:
        repo: データベースリポジトリ
        table_name: テーブル名
        additional_stats: 追加統計情報
    """
    try:
        count = repo.get_count()
        print(f"📊 現在の{table_name}テーブルレコード数: {count}件")
        
        # 追加統計情報の表示
        if additional_stats:
            for key, value in additional_stats.items():
                print(f"   - {key}: {value}件")
        
        # サンプルレコードの表示
        if count > 0:
            print(f"\n📋 最新の5件のレコード:")
            records = repo.get_all()[:5]
            for i, record in enumerate(records, 1):
                _display_record_summary(record, i)
                
    except Exception as e:
        print(f"❌ データベース状態確認エラー: {e}")


def _display_record_summary(record: Dict[str, Any], index: int) -> None:
    """レコードのサマリーを表示する（内部使用）"""
    print(f"  {index}. ID: {record.get('id', 'N/A')}")
    for key, value in record.items():
        if key != 'id' and value is not None:
            if isinstance(value, str) and len(value) > 50:
                print(f"      {key}: {value[:50]}...")
            else:
                print(f"      {key}: {value}")


def save_data_with_logging(save_func, data, data_type: str) -> List[int]:
    """
    データ保存処理の共通ラッパー
    
    Args:
        save_func: 保存処理を行う関数
        data: 保存するデータ
        data_type: データの種類（ログメッセージ用）
        
    Returns:
        List[int]: 保存されたレコードのIDリスト
    """
    try:
        saved_ids = save_func(data)
        print(f"💾 データベース保存完了: {len(saved_ids)}件の{data_type}レコードを保存しました")
        return saved_ids
    except Exception as e:
        print(f"❌ データベース保存エラー: {e}")
        raise
