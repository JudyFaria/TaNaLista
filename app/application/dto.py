"""Modelos de leitura (DTOs) devolvidos pelos casos de uso.

Eles isolam a apresentação das entidades: a API nunca expõe, por exemplo,
o hash de senha ou o código de convite para quem não é membro.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from app.domain.entities import Role, User


@dataclass(frozen=True)
class UserView:
    id: str
    username: str
    display_name: str

    @classmethod
    def from_entity(cls, user: User) -> UserView:
        return cls(id=user.id, username=user.username, display_name=user.display_name)

    @classmethod
    def unknown(cls, user_id: str) -> UserView:
        return cls(id=user_id, username="", display_name="Usuário removido")


@dataclass(frozen=True)
class AuthResult:
    user: UserView
    access_token: str


@dataclass(frozen=True)
class MemberView:
    user: UserView
    role: Role
    joined_at: datetime


@dataclass(frozen=True)
class JoinRequestView:
    user: UserView
    via_invite: bool
    requested_at: datetime


@dataclass(frozen=True)
class GroupSummary:
    id: str
    name: str
    description: str
    is_public: bool
    member_count: int
    my_role: Role | None
    has_pending_request: bool
    pending_items: int | None = None
    pending_requests: int = 0


@dataclass(frozen=True)
class GroupDetails:
    id: str
    name: str
    description: str
    is_public: bool
    invite_code: str
    my_role: Role
    members: list[MemberView]
    join_requests: list[JoinRequestView]


@dataclass(frozen=True)
class ItemView:
    id: str
    name: str
    quantity: str
    unit: str
    brand: str
    category: str
    note: str
    added_by: UserView
    created_at: datetime
    bought_by: UserView | None
    bought_at: datetime | None


@dataclass(frozen=True)
class Notification:
    type: str
    title: str
    body: str
    group_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
