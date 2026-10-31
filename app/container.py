"""Raiz de composição: o único lugar que conhece as implementações concretas.

O tipo de banco é escolhido aqui: com ``FIREBASE_CREDENTIALS`` usa o Firestore;
sem ela, o banco JSON local. O resto do sistema não muda.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.auth_service import AuthService
from app.application.group_service import GroupService
from app.application.item_service import ItemService
from app.application.ports import GroupRepository, ItemRepository, UserRepository
from app.config import Settings
from app.infrastructure.event_broker import InMemoryEventBroker
from app.infrastructure.persistence.firestore_repositories import (
    FirestoreGroupRepository,
    FirestoreItemRepository,
    FirestoreUserRepository,
    create_firestore_client,
)
from app.infrastructure.persistence.json_database import JsonDatabase
from app.infrastructure.persistence.json_repositories import (
    JsonGroupRepository,
    JsonItemRepository,
    JsonUserRepository,
)
from app.infrastructure.security import JwtTokenService, ScryptPasswordHasher


@dataclass(frozen=True)
class Container:
    auth: AuthService
    groups: GroupService
    items: ItemService
    broker: InMemoryEventBroker


def build_repositories(
    settings: Settings,
) -> tuple[UserRepository, GroupRepository, ItemRepository]:
    if settings.firebase_credentials:
        client = create_firestore_client(settings.firebase_credentials)
        return (
            FirestoreUserRepository(client),
            FirestoreGroupRepository(client),
            FirestoreItemRepository(client),
        )
    db = JsonDatabase(settings.database_path)
    return JsonUserRepository(db), JsonGroupRepository(db), JsonItemRepository(db)


def build_container(settings: Settings) -> Container:
    users, groups, items = build_repositories(settings)
    broker = InMemoryEventBroker()

    return Container(
        auth=AuthService(
            users, ScryptPasswordHasher(), JwtTokenService(settings.secret_key, settings.token_ttl)
        ),
        groups=GroupService(groups, users, items, broker),
        items=ItemService(groups, items, users, broker),
        broker=broker,
    )
