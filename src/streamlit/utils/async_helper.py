"""Streamlit用の非同期ヘルパー関数"""

import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import Any


def run_async_in_streamlit(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Streamlit環境で非同期処理を安全に実行するヘルパー関数

    Streamlitアプリケーション内で非同期関数を実行する際、
    既存のイベントループとの競合を避けるために別スレッドで実行します。

    Args:
        coro: 実行する非同期コルーチン

    Returns:
        非同期処理の結果

    Example:
        >>> async def fetch_data():
        ...     async with get_async_session() as session:
        ...         return await repository.get_all()
        >>>
        >>> data = run_async_in_streamlit(fetch_data())
    """
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()
