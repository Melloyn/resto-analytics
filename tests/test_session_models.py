from use_cases.session_models import UserSession, is_admin, is_approved


def test_is_admin() -> None:
    admin_user = UserSession(id=1, full_name="Admin", login="admin", role="admin", status="approved")
    regular_user = UserSession(id=2, full_name="User", login="user", role="user", status="approved")
    assert is_admin(admin_user) is True
    assert is_admin(regular_user) is False


def test_is_approved() -> None:
    approved_user = UserSession(id=1, full_name="Ok", login="ok", role="user", status="approved")
    pending_user = UserSession(id=2, full_name="Wait", login="wait", role="user", status="pending")
    assert is_approved(approved_user) is True
    assert is_approved(pending_user) is False
