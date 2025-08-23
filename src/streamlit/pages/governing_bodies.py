"""Streamlit page for managing governing bodies."""

from src.interfaces.web.streamlit.views.governing_bodies_view import (
    render_governing_bodies_page,
)


def manage_governing_bodies():
    """開催主体管理（CRUD）"""
    render_governing_bodies_page()
