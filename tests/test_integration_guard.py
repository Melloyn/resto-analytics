import sys
import importlib
from unittest.mock import patch, MagicMock

def test_app_integration_guard():
    import streamlit as st
    st.session_state.clear()

    with patch('use_cases.bootstrap.run_startup') as mock_bootstrap, \
         patch('use_cases.auth_flow.ensure_authenticated_session') as mock_auth_flow, \
         patch('auth.create_runtime_session') as mock_create_session, \
         patch('auth.get_user_by_id') as mock_get_user:
         
        # Mock DB/auth behaviors
        mock_get_user.return_value = (1, "Test User", "test_user", "password_hash", "salt", "user", "approved")
        mock_create_session.return_value = "fake_auth_token"
        
        # We want bootstrap to trigger the init_session_state side-effects
        # so that our test can verify the session keys.
        from utils import session_manager
        def fake_bootstrap():
            session_manager.init_session_state()
            res = MagicMock()
            res.status = "CONTINUE"
            return res
            
        mock_bootstrap.side_effect = fake_bootstrap
        
        res_auth = MagicMock()
        res_auth.status = "CONTINUE"
        mock_auth_flow.return_value = res_auth
        
        # Simulate auth_flow side-effect
        st.session_state.auth_user = MagicMock(full_name="Test User")
        
        # Load or reload 'app' gracefully for the headless guard test
        if 'app' in sys.modules:
            importlib.reload(sys.modules['app'])
        else:
            import app
            
        # Verify integrations
        mock_bootstrap.assert_called()
        mock_auth_flow.assert_called()
        
        # Verify session state contract keys are present
        assert 'df_version' in st.session_state
        assert 'view_cache' in st.session_state
        assert 'yandex_path' in st.session_state
        assert 'session_diag_seen' in st.session_state
