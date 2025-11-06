"""Middleware modules for Streamlit application.

This package provides authentication middleware for protecting routes.
"""

from src.interfaces.web.streamlit.middleware.auth_middleware import (
    render_login_page,
    require_auth,
)

__all__ = ["require_auth", "render_login_page"]
