"""Streamlit page for politician management."""

from src.interfaces.web.streamlit.views.politicians_view import render_politicians_page


def manage_politicians():
    """政治家管理"""
    render_politicians_page()
