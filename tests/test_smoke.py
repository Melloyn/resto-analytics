import pytest
import sys
import streamlit as st  # noqa: TID251

def test_imports():
    """Ensure core modules can be imported without crashing."""
    # Mock session state for app.py top-level execution
    st.session_state.auth_user = {"id": 1, "full_name": "Smoke Test", "role": "admin", "status": "approved"}
    st.session_state.is_admin = True
    st.session_state.admin_fullscreen = False

    import services.analytics_service
    import services.category_service
    import services.parsing_service
    import telegram_utils
    import auth
    import ui
    import app
    import views.login_view
    import views.admin_view
