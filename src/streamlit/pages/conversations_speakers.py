"""Streamlit page for conversations and speakers management."""

from src.interfaces.web.streamlit.views.conversations_speakers_view import (
    render_conversations_speakers_page,
)


def manage_conversations_speakers():
    """発言・発言者管理"""
    render_conversations_speakers_page()
