from unittest.mock import patch

from use_cases import auth_flow, bootstrap


@patch("use_cases.auth_flow.session_manager.validate_current_session")
@patch("use_cases.auth_flow.session_manager.check_and_restore_session")
@patch("use_cases.auth_flow.session_manager.init_session_state")
def test_auth_flow_contract(_, __, ___) -> None:
    assert hasattr(auth_flow, "ensure_authenticated_session")
    auth_flow.session_manager.st.session_state.clear()
    result = auth_flow.ensure_authenticated_session()
    assert isinstance(result, auth_flow.AuthFlowResult)
    assert result.status in {"CONTINUE", "STOP"}


@patch("use_cases.bootstrap.category_service.sync_from_yandex")
@patch("use_cases.bootstrap.auth.sync_users_from_yandex")
@patch("use_cases.bootstrap.auth.bootstrap_admin")
@patch("use_cases.bootstrap.auth.init_auth_db")
@patch("use_cases.bootstrap.auth.get_secret", return_value=None)
@patch("use_cases.bootstrap.session_manager.init_session_state")
def test_bootstrap_contract(_, __, ___, ____, _____, ______) -> None:
    assert hasattr(bootstrap, "run_startup")
    bootstrap.session_manager.st.session_state.clear()
    bootstrap.session_manager.st.session_state.categories_synced = True
    bootstrap.session_manager.st.session_state.users_synced = True
    result = bootstrap.run_startup()
    assert isinstance(result, bootstrap.StartupResult)
    assert result.status in {"CONTINUE", "STOP"}
    assert isinstance(result.planned_steps, tuple)
