import sys
import importlib
from unittest.mock import patch, MagicMock
import pytest
import streamlit as st

from use_cases.bootstrap import StartupResult
from use_cases.auth_flow import AuthFlowResult

@patch("use_cases.bootstrap.run_startup")
@patch("use_cases.auth_flow.ensure_authenticated_session")
@patch("ui.setup_style")
@patch("ui.setup_parallax")
@patch("auth.get_secret", return_value=None)
@patch("os.path.exists", return_value=False)
@patch("pandas.read_parquet")
@patch("services.data_loader.download_and_process_yandex")
def test_app_startup_headless_integration(
    mock_download,
    mock_read_parquet,
    mock_exists,
    mock_get_secret,
    mock_setup_parallax,
    mock_setup_style,
    mock_ensure_auth,
    mock_run_startup
):
    # Minimal session state setup
    st.session_state.clear()
    st.session_state.df_full = None
    st.session_state.is_admin = False
    st.session_state.admin_fullscreen = False
    st.session_state.admin_fullscreen_tab = None
    st.session_state.auth_user = MagicMock()
    st.session_state.auth_user.full_name = "Test User"
    st.session_state.edit_yandex_path = False
    st.session_state.yandex_path = "mock_path"
    
    # Mock returns
    mock_run_startup.return_value = StartupResult(status="CONTINUE", planned_steps=())
    mock_ensure_auth.return_value = AuthFlowResult(status="CONTINUE", user_id=1, reason="authenticated")

    # Force re-importing app.py
    if "app" in sys.modules:
        del sys.modules["app"]
    
    # Import should not crash
    try:
        importlib.import_module("app")
    except Exception as e:
        pytest.fail(f"app.py import failed with error: {e}")

    # Assert no IO/Data Loading happened
    mock_read_parquet.assert_not_called()
    mock_download.assert_not_called()
    
    # Assert auth flow and startup were called
    mock_ensure_auth.assert_called_once()
    mock_run_startup.assert_called_once()

    assert True
