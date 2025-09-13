"""Streamlit page for proposal management."""

from src.interfaces.web.streamlit.views.proposals_view import render_proposals_page


def manage_proposals():
    """議案管理"""
    render_proposals_page()
