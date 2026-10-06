"""Repositórios sobre SQLAlchemy (PostgreSQL em produção, SQLite se quiser localmente).

Implementam as mesmas portas dos repositórios JSON, então os casos de uso
não percebem a troca.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import create_engine, delete, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.domain.entities import Group, JoinRequest, Membership, Role, ShoppingItem, User
from app.infrastructure.persistence.sql_models import (
    Base,
    GroupModel,
    ItemModel,
    JoinRequestModel,
    MembershipModel,
    UserModel,
)

SessionFactory = sessionmaker[Session]


def create_session_factory(database_url: str) -> SessionFactory:
    engine: Engine = create_engine(database_url, pool_pre_ping=True)
    # Cria as tabelas que ainda não existem. Para evoluir o esquema com
    # dados em produção, o próximo passo seria adotar migrações (Alembic).
    Base.metadata.create_all(engine)
    return sessionmaker(engine, expire_on_commit=False)


# --------------------------------------------------------------------------- #
# Usuários
# --------------------------------------------------------------------------- #
class SqlUserRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    def add(self, user: User) -> None:
        with self._sessions.begin() as session:
            session.add(
                UserModel(
                    id=user.id,
                    username=user.username,
                    display_name=user.display_name,
                    password_hash=user.password_hash,
                    created_at=user.created_at,
                )
            )

    def get(self, user_id: str) -> User | None:
        with self._sessions() as session:
            row = session.get(UserModel, user_id)
            return _user(row) if row else None

    def get_by_username(self, username: str) -> User | None:
        with self._sessions() as session:
            row = session.scalar(select(UserModel).where(UserModel.username == username))
            return _user(row) if row else None

    def get_many(self, user_ids: Iterable[str]) -> dict[str, User]:
        ids = set(user_ids)
        if not ids:
            return {}
        with self._sessions() as session:
            rows = session.scalars(select(UserModel).where(UserModel.id.in_(ids)))
            return {row.id: _user(row) for row in rows}


# --------------------------------------------------------------------------- #
# Grupos
# --------------------------------------------------------------------------- #
class SqlGroupRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    def save(self, group: Group) -> None:
        with self._sessions.begin() as session:
            row = session.get(GroupModel, group.id)
            if row is None:
                row = GroupModel(id=group.id, created_at=group.created_at)
                session.add(row)
            row.name = group.name
            row.description = group.description
            row.is_public = group.is_public
            row.invite_code = group.invite_code
            _sync_members(row, group)
            _sync_requests(row, group)

    def get(self, group_id: str) -> Group | None:
        with self._sessions() as session:
            row = session.get(GroupModel, group_id)
            return _group(row) if row else None

    def get_by_invite_code(self, code: str) -> Group | None:
        if not code:
            return None
        with self._sessions() as session:
            row = session.scalar(select(GroupModel).where(GroupModel.invite_code == code))
            return _group(row) if row else None

    def list_for_user(self, user_id: str) -> list[Group]:
        with self._sessions() as session:
            rows = session.scalars(
                select(GroupModel)
                .join(MembershipModel, MembershipModel.group_id == GroupModel.id)
                .where(MembershipModel.user_id == user_id)
            )
            return [_group(row) for row in rows]

    def search_public(self, query: str, limit: int) -> list[Group]:
        pattern = f"%{_escape_like(query)}%"
        with self._sessions() as session:
            rows = session.scalars(
                select(GroupModel)
                .where(GroupModel.is_public.is_(True), GroupModel.name.ilike(pattern, escape="\\"))
                .order_by(GroupModel.name)
                .limit(limit)
            )
            groups = [_group(row) for row in rows]
        needle = query.casefold()
        groups.sort(key=lambda g: (not g.name.casefold().startswith(needle), g.name.casefold()))
        return groups

    def delete(self, group_id: str) -> None:
        with self._sessions.begin() as session:
            row = session.get(GroupModel, group_id)
            if row is not None:
                session.delete(row)


# --------------------------------------------------------------------------- #
# Itens
# --------------------------------------------------------------------------- #
class SqlItemRepository:
    def __init__(self, sessions: SessionFactory) -> None:
        self._sessions = sessions

    def save(self, item: ShoppingItem) -> None:
        with self._sessions.begin() as session:
            row = session.get(ItemModel, item.id) or ItemModel(id=item.id)
            row.group_id = item.group_id
            row.name = item.name
            row.quantity = item.quantity
            row.note = item.note
            row.added_by = item.added_by
            row.created_at = item.created_at
            row.bought_by = item.bought_by
            row.bought_at = item.bought_at
            session.add(row)

    def get(self, item_id: str) -> ShoppingItem | None:
        with self._sessions() as session:
            row = session.get(ItemModel, item_id)
            return _item(row) if row else None

    def list_by_group(self, group_id: str) -> list[ShoppingItem]:
        with self._sessions() as session:
            rows = session.scalars(select(ItemModel).where(ItemModel.group_id == group_id))
            return [_item(row) for row in rows]

    def delete(self, item_id: str) -> None:
        with self._sessions.begin() as session:
            session.execute(delete(ItemModel).where(ItemModel.id == item_id))

    def delete_by_group(self, group_id: str) -> None:
        with self._sessions.begin() as session:
            session.execute(delete(ItemModel).where(ItemModel.group_id == group_id))


# --------------------------------------------------------------------------- #
# Conversões ORM <-> domínio
# --------------------------------------------------------------------------- #
def _user(row: UserModel) -> User:
    return User(
        id=row.id,
        username=row.username,
        display_name=row.display_name,
        password_hash=row.password_hash,
        created_at=row.created_at,
    )


def _group(row: GroupModel) -> Group:
    return Group(
        id=row.id,
        name=row.name,
        description=row.description,
        is_public=row.is_public,
        invite_code=row.invite_code,
        created_at=row.created_at,
        members={
            m.user_id: Membership(user_id=m.user_id, role=Role(m.role), joined_at=m.joined_at)
            for m in row.members
        },
        join_requests={
            r.user_id: JoinRequest(user_id=r.user_id, via_invite=r.via_invite, requested_at=r.requested_at)
            for r in row.join_requests
        },
    )


def _item(row: ItemModel) -> ShoppingItem:
    return ShoppingItem(
        id=row.id,
        group_id=row.group_id,
        name=row.name,
        quantity=row.quantity,
        note=row.note,
        added_by=row.added_by,
        created_at=row.created_at,
        bought_by=row.bought_by,
        bought_at=row.bought_at,
    )


def _sync_members(row: GroupModel, group: Group) -> None:
    existing = {m.user_id: m for m in row.members}
    row.members[:] = [m for m in row.members if m.user_id in group.members]
    for membership in group.members.values():
        current = existing.get(membership.user_id)
        if current is None:
            row.members.append(
                MembershipModel(
                    user_id=membership.user_id,
                    role=membership.role.value,
                    joined_at=membership.joined_at,
                )
            )
        else:
            current.role = membership.role.value


def _sync_requests(row: GroupModel, group: Group) -> None:
    existing = {r.user_id for r in row.join_requests}
    row.join_requests[:] = [r for r in row.join_requests if r.user_id in group.join_requests]
    for request in group.join_requests.values():
        if request.user_id not in existing:
            row.join_requests.append(
                JoinRequestModel(
                    user_id=request.user_id,
                    via_invite=request.via_invite,
                    requested_at=request.requested_at,
                )
            )


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
