"""Authentication flow orchestration (application layer)."""

from dataclasses import dataclass
from typing import Literal, Optional

from utils import session_manager

AuthFlowStatus = Literal["CONTINUE", "STOP"]


@dataclass(frozen=True)
class AuthFlowResult:
    """Result contract for auth flow orchestration."""

    status: AuthFlowStatus
    reason: str
    user_id: Optional[int] = None


def ensure_authenticated_session() -> AuthFlowResult:
    """Run auth-gate orchestration and return a control-flow status."""
    session_manager.init_session_state()
    session_manager.check_and_restore_session()

    auth_user = session_manager.st.session_state.get("auth_user")
    if auth_user is None:
        return AuthFlowResult(status="STOP", reason="auth_required")

    session_manager.validate_current_session()
    auth_user = session_manager.st.session_state.get("auth_user")
    user_id = auth_user.id if auth_user is not None else None
    return AuthFlowResult(status="CONTINUE", reason="authenticated", user_id=user_id)
