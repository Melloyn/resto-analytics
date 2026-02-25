from unittest.mock import patch

import streamlit as st

from use_cases import auth_flow


@patch("use_cases.auth_flow.session_manager.validate_current_session")
@patch("use_cases.auth_flow.session_manager.check_and_restore_session")
@patch("use_cases.auth_flow.session_manager.init_session_state")
def test_ensure_authenticated_session_stop_without_user(
    mock_init,
    mock_restore,
    mock_validate,
):
    st.session_state.clear()
    result = auth_flow.ensure_authenticated_session()

    assert result.status == "STOP"
    mock_init.assert_called_once()
    mock_restore.assert_called_once()
    mock_validate.assert_not_called()


@patch("use_cases.auth_flow.session_manager.validate_current_session")
@patch("use_cases.auth_flow.session_manager.check_and_restore_session")
@patch("use_cases.auth_flow.session_manager.init_session_state")
def test_ensure_authenticated_session_continue_with_user(
    mock_init,
    mock_restore,
    mock_validate,
):
    st.session_state.clear()

    def set_user():
        st.session_state.auth_user = {"id": 42, "full_name": "Tester"}

    mock_restore.side_effect = set_user
    result = auth_flow.ensure_authenticated_session()

    assert result.status == "CONTINUE"
    assert result.user_id == 42
    mock_init.assert_called_once()
    mock_restore.assert_called_once()
    mock_validate.assert_called_once()
