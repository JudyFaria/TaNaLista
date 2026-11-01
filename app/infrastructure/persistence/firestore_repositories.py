"""Repositórios sobre o Cloud Firestore (Firebase).

Implementam as mesmas portas dos repositórios JSON. Coleções:

- ``users``: um documento por usuário (id = ``user.id``);
- ``usernames``: reserva do nome de usuário (id = ``username``), garante unicidade;
- ``groups``: listas, com ``member_ids`` para buscar as listas de um usuário;
- ``items``: itens, com ``group_id`` para buscar os itens de uma lista;
- ``item_imgs``: a foto (opcional) de cada item, já reduzida pelo celular.

Os documentos usam o mesmo formato do banco JSON (``mappers``).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from google.api_core.exceptions import AlreadyExists
from google.cloud.firestore_v1.base_query import FieldFilter

from app.domain.entities import USERNAME_PATTERN, Group, ItemImage, ShoppingItem, User
from app.domain.errors import ConflictError
from app.infrastructure.persistence import mappers

BATCH_LIMIT = 500  # máximo de operações por gravação em lote no Firestore


def create_firestore_client(credentials: str) -> Any:
    """Cria o cliente a partir da chave da conta de serviço (conteúdo JSON ou caminho do arquivo)."""
    import firebase_admin
    from firebase_admin import credentials as fb_credentials
    from firebase_admin import firestore

    raw = credentials.strip()
    info = json.loads(raw if raw.startswith("{") else Path(raw).read_text(encoding="utf-8"))
    name = f"lista-de-compras-{info['project_id']}"
    try:
        app = firebase_admin.get_app(name)
    except ValueError:
        app = firebase_admin.initialize_app(fb_credentials.Certificate(info), name=name)
    return firestore.client(app)


def _where(field: str, op: str, value: Any) -> dict[str, FieldFilter]:
    return {"filter": FieldFilter(field, op, value)}


# --------------------------------------------------------------------------- #
# Usuários
# --------------------------------------------------------------------------- #
class FirestoreUserRepository:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._users = client.collection("users")
        self._usernames = client.collection("usernames")

    def add(self, user: User) -> None:
        batch = self._client.batch()
        batch.create(self._usernames.document(user.username), {"user_id": user.id})
        batch.set(self._users.document(user.id), mappers.user_to_dict(user))
        try:
            batch.commit()
        except AlreadyExists as error:
            raise ConflictError("Este nome de usuário já está em uso.") from error

    def get(self, user_id: str) -> User | None:
        snap = self._users.document(user_id).get()
        return mappers.user_from_dict(snap.to_dict()) if snap.exists else None

    def get_by_username(self, username: str) -> User | None:
        # Nomes fora do padrão não existem (e poderiam ser IDs inválidos, como "a/b").
        if not USERNAME_PATTERN.fullmatch(username or ""):
            return None
        snap = self._usernames.document(username).get()
        return self.get(snap.to_dict()["user_id"]) if snap.exists else None

    def get_many(self, user_ids: Iterable[str]) -> dict[str, User]:
        refs = [self._users.document(uid) for uid in set(user_ids)]
        if not refs:
            return {}
        return {
            snap.id: mappers.user_from_dict(snap.to_dict())
            for snap in self._client.get_all(refs)
            if snap.exists
        }


# --------------------------------------------------------------------------- #
# Grupos
# --------------------------------------------------------------------------- #
class FirestoreGroupRepository:
    def __init__(self, client: Any) -> None:
        self._groups = client.collection("groups")

    def save(self, group: Group) -> None:
        data = mappers.group_to_dict(group)
        data["member_ids"] = list(group.members)
        self._groups.document(group.id).set(data)

    def get(self, group_id: str) -> Group | None:
        snap = self._groups.document(group_id).get()
        return mappers.group_from_dict(snap.to_dict()) if snap.exists else None

    def get_by_invite_code(self, code: str) -> Group | None:
        if not code:
            return None
        snaps = self._groups.where(**_where("invite_code", "==", code)).limit(1).stream()
        return next((mappers.group_from_dict(s.to_dict()) for s in snaps), None)

    def list_for_user(self, user_id: str) -> list[Group]:
        snaps = self._groups.where(**_where("member_ids", "array_contains", user_id)).stream()
        return [mappers.group_from_dict(s.to_dict()) for s in snaps]

    def search_public(self, query: str, limit: int) -> list[Group]:
        # O Firestore não busca por trecho do texto; filtramos as listas públicas aqui.
        # Bom para centenas de listas; com muito mais, use um índice de busca.
        needle = query.casefold()
        snaps = self._groups.where(**_where("is_public", "==", True)).stream()
        matches = [d for d in (s.to_dict() for s in snaps) if needle in d["name"].casefold()]
        matches.sort(key=lambda g: (not g["name"].casefold().startswith(needle), g["name"].casefold()))
        return [mappers.group_from_dict(g) for g in matches[:limit]]

    def delete(self, group_id: str) -> None:
        self._groups.document(group_id).delete()


# --------------------------------------------------------------------------- #
# Itens
# --------------------------------------------------------------------------- #
class FirestoreItemRepository:
    def __init__(self, client: Any) -> None:
        self._client = client
        self._items = client.collection("items")

    def save(self, item: ShoppingItem) -> None:
        self._items.document(item.id).set(mappers.item_to_dict(item))

    def get(self, item_id: str) -> ShoppingItem | None:
        snap = self._items.document(item_id).get()
        return mappers.item_from_dict(snap.to_dict()) if snap.exists else None

    def list_by_group(self, group_id: str) -> list[ShoppingItem]:
        snaps = self._items.where(**_where("group_id", "==", group_id)).stream()
        return [mappers.item_from_dict(s.to_dict()) for s in snaps]

    def delete(self, item_id: str) -> None:
        self._items.document(item_id).delete()

    def delete_by_group(self, group_id: str) -> None:
        _delete_where_group(self._client, self._items, group_id)


# --------------------------------------------------------------------------- #
# Fotos dos itens
# --------------------------------------------------------------------------- #
class FirestoreItemImageRepository:
    """Uma foto por item, na coleção ``item_imgs`` (id do documento = id do item).

    Fica separada de ``items`` para que listar os itens não baixe as fotos.
    """

    def __init__(self, client: Any) -> None:
        self._client = client
        self._images = client.collection("item_imgs")

    def save(self, image: ItemImage) -> None:
        self._images.document(image.item_id).set(mappers.image_to_dict(image))

    def get(self, item_id: str) -> ItemImage | None:
        snap = self._images.document(item_id).get()
        return mappers.image_from_dict(snap.to_dict()) if snap.exists else None

    def delete(self, item_id: str) -> None:
        self._images.document(item_id).delete()

    def delete_by_group(self, group_id: str) -> None:
        _delete_where_group(self._client, self._images, group_id)


def _delete_where_group(client: Any, collection: Any, group_id: str) -> None:
    refs = [s.reference for s in collection.where(**_where("group_id", "==", group_id)).stream()]
    for start in range(0, len(refs), BATCH_LIMIT):
        batch = client.batch()
        for ref in refs[start : start + BATCH_LIMIT]:
            batch.delete(ref)
        batch.commit()
