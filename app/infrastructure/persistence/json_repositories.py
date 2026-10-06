"""Implementações dos repositórios sobre o ``JsonDatabase``."""

from __future__ import annotations

from collections.abc import Iterable

from app.domain.entities import Group, ShoppingItem, User
from app.infrastructure.persistence import mappers
from app.infrastructure.persistence.json_database import JsonDatabase


class JsonUserRepository:
    def __init__(self, db: JsonDatabase) -> None:
        self._db = db

    def add(self, user: User) -> None:
        with self._db.transaction() as data:
            data["users"][user.id] = mappers.user_to_dict(user)

    def get(self, user_id: str) -> User | None:
        with self._db.read() as data:
            raw = data["users"].get(user_id)
            return mappers.user_from_dict(raw) if raw else None

    def get_by_username(self, username: str) -> User | None:
        with self._db.read() as data:
            raw = next((u for u in data["users"].values() if u["username"] == username), None)
            return mappers.user_from_dict(raw) if raw else None

    def get_many(self, user_ids: Iterable[str]) -> dict[str, User]:
        with self._db.read() as data:
            users = data["users"]
            return {uid: mappers.user_from_dict(users[uid]) for uid in set(user_ids) if uid in users}


class JsonGroupRepository:
    def __init__(self, db: JsonDatabase) -> None:
        self._db = db

    def save(self, group: Group) -> None:
        with self._db.transaction() as data:
            data["groups"][group.id] = mappers.group_to_dict(group)

    def get(self, group_id: str) -> Group | None:
        with self._db.read() as data:
            raw = data["groups"].get(group_id)
            return mappers.group_from_dict(raw) if raw else None

    def get_by_invite_code(self, code: str) -> Group | None:
        if not code:
            return None
        with self._db.read() as data:
            raw = next((g for g in data["groups"].values() if g["invite_code"] == code), None)
            return mappers.group_from_dict(raw) if raw else None

    def list_for_user(self, user_id: str) -> list[Group]:
        with self._db.read() as data:
            return [
                mappers.group_from_dict(g)
                for g in data["groups"].values()
                if any(m["user_id"] == user_id for m in g["members"])
            ]

    def search_public(self, query: str, limit: int) -> list[Group]:
        needle = query.casefold()
        with self._db.read() as data:
            matches = [
                g for g in data["groups"].values()
                if g["is_public"] and needle in g["name"].casefold()
            ]
        matches.sort(key=lambda g: (not g["name"].casefold().startswith(needle), g["name"].casefold()))
        return [mappers.group_from_dict(g) for g in matches[:limit]]

    def delete(self, group_id: str) -> None:
        with self._db.transaction() as data:
            data["groups"].pop(group_id, None)


class JsonItemRepository:
    def __init__(self, db: JsonDatabase) -> None:
        self._db = db

    def save(self, item: ShoppingItem) -> None:
        with self._db.transaction() as data:
            data["items"][item.id] = mappers.item_to_dict(item)

    def get(self, item_id: str) -> ShoppingItem | None:
        with self._db.read() as data:
            raw = data["items"].get(item_id)
            return mappers.item_from_dict(raw) if raw else None

    def list_by_group(self, group_id: str) -> list[ShoppingItem]:
        with self._db.read() as data:
            return [
                mappers.item_from_dict(i) for i in data["items"].values() if i["group_id"] == group_id
            ]

    def delete(self, item_id: str) -> None:
        with self._db.transaction() as data:
            data["items"].pop(item_id, None)

    def delete_by_group(self, group_id: str) -> None:
        with self._db.transaction() as data:
            for item_id in [k for k, v in data["items"].items() if v["group_id"] == group_id]:
                del data["items"][item_id]
