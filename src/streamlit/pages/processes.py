"""Streamlit page for process execution."""

from src.interfaces.web.streamlit.views.processes_view import render_processes_page


def execute_processes():
    """処理実行"""
    render_processes_page()
