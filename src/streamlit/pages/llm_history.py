"""LLM processing history management page."""

from src.interfaces.web.streamlit.views.llm_history_view import (
    render_llm_history_page,
)


def manage_llm_history():
    """LLM履歴管理のエントリーポイント"""
    render_llm_history_page()
