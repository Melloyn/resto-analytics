import pytest
from unittest.mock import patch
import streamlit as st
from use_cases.session_models import UserSession
from utils import session_manager

def test_init_session_state():
    st.session_state.clear()
    session_manager.init_session_state()
    assert 'df_full' in st.session_state
    assert st.session_state.is_admin is False
    assert st.session_state.auth_user is None
    assert st.session_state.df_version == 0
    assert 'categories_synced' in st.session_state

def test_init_session_state_sets_session_diag_seen_default():
    st.session_state.clear()
    session_manager.init_session_state()
    assert "session_diag_seen" in st.session_state
    assert st.session_state.session_diag_seen is False

@patch('streamlit.rerun')
@patch('utils.session_manager.clear_browser_auth_token')
@patch('auth.drop_runtime_session')
def test_logout(mock_drop, mock_clear, mock_rerun):
    st.session_state.auth_user = UserSession(
        id=1,
        full_name="Test User",
        login="test",
        role="user",
        status="approved",
    )
    st.session_state.auth_token = "fake_token"
    
    session_manager.logout()
    
    mock_drop.assert_called_once_with("fake_token")
    mock_clear.assert_called_once()
    mock_rerun.assert_called_once()
    assert st.session_state.auth_user is None
    assert st.session_state.auth_token is None
