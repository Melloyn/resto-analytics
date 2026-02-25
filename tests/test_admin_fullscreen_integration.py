import sys
import importlib
from unittest.mock import patch, MagicMock
import pytest
import streamlit as st

from use_cases.bootstrap import StartupResult
from use_cases.auth_flow import AuthFlowResult

class MockStopException(Exception):
    pass

@patch("use_cases.bootstrap.run_startup")
@patch("use_cases.auth_flow.ensure_authenticated_session")
@patch("ui.setup_style")
@patch("ui.setup_parallax")
@patch("views.admin_view.render_admin_panel")
@patch("streamlit.stop")
@patch("auth.get_secret", return_value=None)
@patch("os.path.exists", return_value=False)
@patch("pandas.read_parquet")
@patch("services.data_loader.download_and_process_yandex")
def test_admin_fullscreen_headless_integration(
    mock_download,
    mock_read_parquet,
    mock_exists,
    mock_get_secret,
    mock_stop,
    mock_render_admin,
    mock_setup_parallax,
    mock_setup_style,
    mock_ensure_auth,
    mock_run_startup
):
    # Minimal session state setup for admin fullscreen
    st.session_state.clear()
    
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.full_name = "Smoke"
    mock_user.login = "smoke"
    mock_user.role = "admin"
    mock_user.status = "approved"

    st.session_state.auth_user = mock_user
    st.session_state.is_admin = True
    st.session_state.admin_fullscreen = True
    st.session_state.admin_fullscreen_tab = "misc"
    
    # Defaults needed just to import safely
    st.session_state.df_full = None
    st.session_state.edit_yandex_path = False
    st.session_state.yandex_path = "mock_path"
    
    # Mock returns for orchestration
    mock_run_startup.return_value = StartupResult(status="CONTINUE", planned_steps=())
    mock_ensure_auth.return_value = AuthFlowResult(status="CONTINUE", user_id=1, reason="authenticated")

    # Raise exception to truly halt execution like st.stop() does
    mock_stop.side_effect = MockStopException

    # Force re-importing app.py
    if "app" in sys.modules:
        del sys.modules["app"]
    
    # Import should halt on MockStopException
    try:
        importlib.import_module("app")
    except MockStopException:
        pass # Expected behavior
    except Exception as e:
        pytest.fail(f"app.py import failed with error: {e}")

    # Assert no IO/Data Loading happened
    mock_read_parquet.assert_not_called()
    mock_download.assert_not_called()
    
    # Verify the admin panel was rendered with expected arguments
    mock_render_admin.assert_called_once_with(None, default_tab="misc")
    
    # Verify st.stop was called to halt further execution
    mock_stop.assert_called_once()
    
    assert True
