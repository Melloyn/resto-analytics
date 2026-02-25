"""Startup orchestration for application bootstrap and autosync."""

from dataclasses import dataclass
from typing import Literal, Tuple

import os

import auth
from services import category_service
from utils import session_manager

StartupStatus = Literal["CONTINUE", "STOP"]


@dataclass(frozen=True)
class StartupResult:
    """Result contract for startup/bootstrap orchestration."""

    status: StartupStatus
    planned_steps: Tuple[str, ...]


def run_startup() -> StartupResult:
    """Run startup bootstrap and autosync side-effects."""
    executed_steps = []

    auth.init_auth_db()
    executed_steps.append("init_auth_db_pre_sync")

    # Pull users DB from cloud before auth checks, so registered users survive restarts.
    yd_boot_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
    if yd_boot_token:
        auth.sync_users_from_yandex(yd_boot_token, force=True)
        executed_steps.append("sync_users_from_yandex_force")

    # Ensure schema exists after possible DB overwrite.
    auth.init_auth_db()
    executed_steps.append("init_auth_db_post_sync")
    auth.bootstrap_admin()
    executed_steps.append("bootstrap_admin")

    # Session state flags are needed for autosync idempotency.
    session_manager.init_session_state()
    executed_steps.append("init_session_state")

    if not session_manager.st.session_state.categories_synced:
        yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
        if yd_token:
            category_service.sync_from_yandex(yd_token)
            executed_steps.append("sync_categories_from_yandex")
        session_manager.st.session_state.categories_synced = True
        executed_steps.append("set_categories_synced_true")

    if not session_manager.st.session_state.users_synced:
        yd_token = auth.get_secret("YANDEX_TOKEN") or os.getenv("YANDEX_TOKEN")
        if yd_token:
            auth.sync_users_from_yandex(yd_token)
            executed_steps.append("sync_users_from_yandex")
        session_manager.st.session_state.users_synced = True
        executed_steps.append("set_users_synced_true")

    return StartupResult(status="CONTINUE", planned_steps=tuple(executed_steps))
