"""Tabelas do banco relacional (SQLAlchemy 2.0).

Os modelos ORM ficam na infraestrutura e são convertidos para as entidades
de domínio nos repositórios — o domínio continua sem depender do SQLAlchemy.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, TypeDecorator
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class UTCDateTime(TypeDecorator[datetime]):
    """Garante datas sempre com fuso UTC (o SQLite não guarda fuso)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect) -> datetime | None:
        return value.astimezone(UTC) if value else None

    def process_result_value(self, value: datetime | None, dialect) -> datetime | None:
        if value is None:
            return None
        return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class Base(DeclarativeBase):
    pass


class UserModel(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    username: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(50))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())


class GroupModel(Base):
    __tablename__ = "groups"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(60), index=True)
    description: Mapped[str] = mapped_column(String(200))
    is_public: Mapped[bool] = mapped_column(Boolean, index=True)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())

    members: Mapped[list[MembershipModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )
    join_requests: Mapped[list[JoinRequestModel]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class MembershipModel(Base):
    __tablename__ = "memberships"

    group_id: Mapped[str] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(String(10))
    joined_at: Mapped[datetime] = mapped_column(UTCDateTime())


class JoinRequestModel(Base):
    __tablename__ = "join_requests"

    group_id: Mapped[str] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    via_invite: Mapped[bool] = mapped_column(Boolean)
    requested_at: Mapped[datetime] = mapped_column(UTCDateTime())


class ItemModel(Base):
    __tablename__ = "items"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    group_id: Mapped[str] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    quantity: Mapped[str] = mapped_column(String(30))
    note: Mapped[str] = mapped_column(String(140))
    added_by: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime())
    bought_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bought_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
