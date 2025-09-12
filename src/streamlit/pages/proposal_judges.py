"""Streamlit page for proposal judges (voting information) management."""

from src.interfaces.web.streamlit.views.proposal_judges_view import (
    render_proposal_judges_page,
)


def manage_proposal_judges():
    """議案賛否情報管理"""
    render_proposal_judges_page()
