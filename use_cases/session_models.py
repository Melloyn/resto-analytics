"""Session DTOs shared across application layers."""

from dataclasses import dataclass
from typing import Literal

Role = Literal["admin", "user"]
AccountStatus = Literal["approved", "pending", "rejected", "blocked"]


@dataclass(frozen=True)
class UserSession:
    id: int
    full_name: str
    login: str
    role: Role
    status: AccountStatus


def is_admin(user: UserSession) -> bool:
    return user.role == "admin"


def is_approved(user: UserSession) -> bool:
    return user.status == "approved"
