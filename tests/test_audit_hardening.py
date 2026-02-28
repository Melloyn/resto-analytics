import pytest
from unittest.mock import MagicMock, patch
from use_cases import rbac_policy
from use_cases.session_models import UserSession
from infrastructure.repositories.sqlite_audit_repository import AuditAction, SQLiteAuditRepository
import auth

@patch("auth.get_audit_repo")
def test_rbac_deny_logs_audit(mock_get_audit_repo):
    # Mock the audit repo
    mock_repo = MagicMock()
    mock_get_audit_repo.return_value = mock_repo
    
    # Create a user with insufficient privileges (user trying admin action)
    user = UserSession(id=1, role="user", login="test_user", full_name="Test", status="approved")
    
    # Attempt an action that requires admin
    result = rbac_policy.enforce(user, "SYNC_DATA")
    
    # Assert it was denied
    assert result is False
    
    # Assert audit log was called with RBAC_DENIED
    mock_repo.log_action.assert_called_once()
    call_args, call_kwargs = mock_repo.log_action.call_args
    assert call_args[0] == AuditAction.RBAC_DENIED
    assert call_kwargs.get("result") == "deny"
    assert call_kwargs.get("target_type") == "rbac"
    assert call_kwargs.get("actor_user_id") == 1
    assert call_kwargs.get("actor_role") == "user"
    assert "target_action" in call_kwargs.get("metadata", {})
    assert call_kwargs.get("metadata", {})["target_action"] == "SYNC_DATA"


@patch("auth.get_audit_repo")
@patch("auth.get_user_repo")
def test_audit_log_failure_does_not_crash_main_operation(mock_get_user_repo, mock_get_audit_repo, tmp_path):
    # Testing that internal audit failure is swallowed
    db_file = tmp_path / "temp_audit.db"
    real_repo = SQLiteAuditRepository(str(db_file))
    
    # Force the _conn property to raise an exception reflecting a DB outage
    with patch.object(real_repo, '_conn', side_effect=RuntimeError("Database is completely down")):
        mock_get_audit_repo.return_value = real_repo
        
        # We will test update_user_status which attempts to hit the user_repo and audit_repo.
        # We mock the user_repo to just return normally.
        mock_user_repo = MagicMock()
        mock_get_user_repo.return_value = mock_user_repo
        
        import streamlit as st
        mock_session_state = MagicMock()
        mock_session_state.auth_user = UserSession(id=99, role="admin", login="admin", full_name="admin", status="approved")
        mock_session_state.get.return_value = mock_session_state.auth_user
        with patch.object(st, "session_state", mock_session_state):
            # Run the operation - it should not raise the RuntimeError
            try:
                auth.update_user_status(1, "approved")
                passed = True
            except Exception as e:
                passed = False
                pytest.fail(f"Audit failure propagated and crashed main flow: {e}")
                
            assert passed
            # Ensure the user repo actually did its job
            mock_user_repo.update_user_status.assert_called_once_with(1, "approved")
