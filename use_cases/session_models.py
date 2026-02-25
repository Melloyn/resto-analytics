"""Session DTOs shared across application layers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class UserSession:
    id: int
    full_name: str
    login: str
    role: str
    status: str
