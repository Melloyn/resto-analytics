from unittest.mock import patch

from use_cases import bootstrap


@patch("use_cases.bootstrap.category_service.sync_from_yandex")
@patch("use_cases.bootstrap.auth.sync_users_from_yandex")
@patch("use_cases.bootstrap.auth.bootstrap_admin")
@patch("use_cases.bootstrap.auth.init_auth_db")
@patch("use_cases.bootstrap.auth.get_secret", return_value=None)
@patch("use_cases.bootstrap.os.getenv", return_value=None)
def test_run_startup_skips_autosync_when_flags_set(
    _mock_getenv,
    _mock_get_secret,
    _mock_init_db,
    _mock_bootstrap_admin,
    mock_sync_users,
    mock_sync_categories,
) -> None:
    bootstrap.session_manager.st.session_state.clear()
    bootstrap.session_manager.st.session_state.categories_synced = True
    bootstrap.session_manager.st.session_state.users_synced = True

    result = bootstrap.run_startup()

    assert result.status == "CONTINUE"
    mock_sync_categories.assert_not_called()
    mock_sync_users.assert_not_called()


@patch("use_cases.bootstrap.os.getenv", return_value=None)
@patch("use_cases.bootstrap.auth.get_secret", return_value="fake_token")
def test_run_startup_init_happens_before_autosync(_mock_get_secret, _mock_getenv) -> None:
    order = []
    bootstrap.session_manager.st.session_state.clear()
    bootstrap.session_manager.st.session_state.categories_synced = False
    bootstrap.session_manager.st.session_state.users_synced = False

    with patch("use_cases.bootstrap.auth.init_auth_db", side_effect=lambda: order.append("init_auth_db")), patch(
        "use_cases.bootstrap.auth.bootstrap_admin", side_effect=lambda: order.append("bootstrap_admin")
    ), patch(
        "use_cases.bootstrap.session_manager.init_session_state",
        side_effect=lambda: order.append("init_session_state"),
    ), patch(
        "use_cases.bootstrap.category_service.sync_from_yandex",
        side_effect=lambda _token: order.append("sync_categories"),
    ):
        def track_user_sync(*_args, **kwargs):
            if kwargs.get("force"):
                order.append("sync_users_boot")
            else:
                order.append("sync_users_auto")

        with patch(
            "use_cases.bootstrap.auth.sync_users_from_yandex",
            side_effect=track_user_sync,
        ):
            result = bootstrap.run_startup()

    assert result.status == "CONTINUE"
    assert "init_session_state" in order
    assert "sync_categories" in order
    assert "sync_users_auto" in order
    assert order.index("init_session_state") < order.index("sync_categories")
    assert order.index("init_session_state") < order.index("sync_users_auto")
