import pytest
import sys
import streamlit as st  # noqa: TID251
from use_cases.session_models import UserSession
from unittest.mock import patch
import importlib

def test_imports():
    """Ensure core modules can be imported without crashing."""
    # Mock session state for app.py top-level execution
    st.session_state.auth_user = UserSession(
        id=1,
        full_name="Smoke Test",
        login="smoke",
        role="admin",
        status="approved",
    )
    st.session_state.is_admin = False
    st.session_state.admin_fullscreen = False
    st.session_state.auth_token = None

    import services.analytics_service  # noqa: F401
    import services.category_service  # noqa: F401
    import services.parsing_service  # noqa: F401
    import telegram_utils  # noqa: F401
    import auth  # noqa: F401
    import ui  # noqa: F401
    import views.login_view  # noqa: F401
    import views.admin_view  # noqa: F401

    if "app" in sys.modules:
        del sys.modules["app"]

    approved_user_row = (1, "Smoke Test", "smoke", "smoke@example.com", "+70000000000", "admin", "approved")
    with patch("auth.get_user_by_id", return_value=approved_user_row), patch(
        "auth.create_runtime_session", return_value="smoke_token"
    ):
        importlib.import_module("app")
