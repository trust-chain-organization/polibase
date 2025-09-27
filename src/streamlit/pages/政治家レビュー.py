"""Streamlit page for reviewing extracted politicians."""

from src.interfaces.web.streamlit.views.extracted_politicians_view import (
    render_extracted_politicians_page,
)


def review_extracted_politicians():
    """政治家レビュー"""
    render_extracted_politicians_page()
