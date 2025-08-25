"""Streamlit page for managing parliamentary groups."""

from src.interfaces.web.streamlit.views.parliamentary_groups_view import (
    render_parliamentary_groups_page,
)


def manage_parliamentary_groups():
    """議員団管理（CRUD）"""
    render_parliamentary_groups_page()
