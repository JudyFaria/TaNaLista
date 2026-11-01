"""Conversão entre entidades de domínio e dicionários serializáveis em JSON."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.domain.entities import (
    Category,
    Group,
    JoinRequest,
    Membership,
    Role,
    ShoppingItem,
    Unit,
    User,
)


def _dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def user_to_dict(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "password_hash": user.password_hash,
        "created_at": _dt(user.created_at),
    }


def user_from_dict(data: dict[str, Any]) -> User:
    return User(
        id=data["id"],
        username=data["username"],
        display_name=data["display_name"],
        password_hash=data["password_hash"],
        created_at=_parse_dt(data["created_at"]),
    )


def group_to_dict(group: Group) -> dict[str, Any]:
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "is_public": group.is_public,
        "invite_code": group.invite_code,
        "created_at": _dt(group.created_at),
        "members": [
            {"user_id": m.user_id, "role": m.role.value, "joined_at": _dt(m.joined_at)}
            for m in group.members.values()
        ],
        "join_requests": [
            {"user_id": r.user_id, "via_invite": r.via_invite, "requested_at": _dt(r.requested_at)}
            for r in group.join_requests.values()
        ],
    }


def group_from_dict(data: dict[str, Any]) -> Group:
    return Group(
        id=data["id"],
        name=data["name"],
        description=data["description"],
        is_public=data["is_public"],
        invite_code=data["invite_code"],
        created_at=_parse_dt(data["created_at"]),
        members={
            m["user_id"]: Membership(
                user_id=m["user_id"], role=Role(m["role"]), joined_at=_parse_dt(m["joined_at"])
            )
            for m in data["members"]
        },
        join_requests={
            r["user_id"]: JoinRequest(
                user_id=r["user_id"],
                via_invite=r["via_invite"],
                requested_at=_parse_dt(r["requested_at"]),
            )
            for r in data["join_requests"]
        },
    )


def item_to_dict(item: ShoppingItem) -> dict[str, Any]:
    return {
        "id": item.id,
        "group_id": item.group_id,
        "name": item.name,
        "quantity": item.quantity,
        "unit": item.unit.value,
        "brand": item.brand,
        "category": item.category.value,
        "note": item.note,
        "added_by": item.added_by,
        "created_at": _dt(item.created_at),
        "bought_by": item.bought_by,
        "bought_at": _dt(item.bought_at),
    }


def item_from_dict(data: dict[str, Any]) -> ShoppingItem:
    return ShoppingItem(
        id=data["id"],
        group_id=data["group_id"],
        name=data["name"],
        quantity=data["quantity"],
        # Itens gravados antes destes campos existirem recebem os valores padrão.
        unit=Unit(data.get("unit", Unit.UNIDADE)),
        brand=data.get("brand", ""),
        category=Category(data.get("category", Category.OUTROS)),
        note=data["note"],
        added_by=data["added_by"],
        created_at=_parse_dt(data["created_at"]),
        bought_by=data["bought_by"],
        bought_at=_parse_dt(data["bought_at"]),
    )
