"""Centralized Role-Based Access Control logic."""

from typing import Optional
from use_cases.session_models import UserSession

def enforce(user: Optional[UserSession], action: str) -> bool:
    """
    Evaluates if the user is authorized to perform the action.
    Returns True if authorized, False otherwise.
    """
    import auth
    from infrastructure.repositories.sqlite_audit_repository import AuditAction

    authorized = False
    
    # System actions without user contexts
    if user is not None:
        # Admins get overarching rights to everything
        if user.role == "admin":
            authorized = True
        # Standard users
        elif user.role == "user" and action == "VIEW_REPORTS":
            authorized = True

    if not authorized:
        auth.get_audit_repo().log_action(
             AuditAction.RBAC_DENIED, 
             target_type="rbac", 
             actor_user_id=user.id if user else None,
             actor_role=user.role if user else None,
             metadata={"target_action": action, "reason": "insufficient_rights"},
             result="deny"
        )

    return authorized
