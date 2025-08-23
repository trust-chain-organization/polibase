"""Streamlit page for conversations list."""

from src.interfaces.web.streamlit.views.conversations_view import (
    render_conversations_page,
)


def manage_conversations():
    """発言レコード一覧"""
    render_conversations_page()
