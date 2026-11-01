"""Entidades e regras de negócio.

Este módulo é Python puro: não depende de framework, banco ou HTTP.
O ``Group`` é o agregado central — toda mudança de membros e pedidos de
entrada passa por ele, garantindo as invariantes (ex.: só o dono aprova).
"""

from __future__ import annotations

import re
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.domain.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

USERNAME_PATTERN = re.compile(r"^[a-z0-9_.]{3,30}$")
MAX_DISPLAY_NAME = 50
MAX_GROUP_NAME = 60
MAX_GROUP_DESCRIPTION = 200
MAX_ITEM_NAME = 80
MAX_ITEM_QUANTITY = 30
MAX_ITEM_BRAND = 40
MAX_ITEM_NOTE = 140


def utc_now() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid.uuid4().hex


def new_invite_code() -> str:
    return secrets.token_urlsafe(9)


def _clean_text(value: str, *, field_name: str, max_length: int, required: bool) -> str:
    cleaned = " ".join((value or "").split())
    if required and not cleaned:
        raise ValidationError(f"{field_name} é obrigatório.")
    if len(cleaned) > max_length:
        raise ValidationError(f"{field_name} deve ter no máximo {max_length} caracteres.")
    return cleaned


# --------------------------------------------------------------------------- #
# Usuário
# --------------------------------------------------------------------------- #
@dataclass
class User:
    username: str
    display_name: str
    password_hash: str
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utc_now)

    @staticmethod
    def normalize_username(username: str) -> str:
        return (username or "").strip().lower()

    @classmethod
    def create(cls, username: str, display_name: str, password_hash: str) -> User:
        normalized = cls.normalize_username(username)
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValidationError(
                "Usuário deve ter de 3 a 30 caracteres: letras, números, '_' ou '.'."
            )
        name = _clean_text(
            display_name, field_name="Nome", max_length=MAX_DISPLAY_NAME, required=True
        )
        return cls(username=normalized, display_name=name, password_hash=password_hash)


# --------------------------------------------------------------------------- #
# Grupo (lista compartilhada)
# --------------------------------------------------------------------------- #
class Role(StrEnum):
    OWNER = "owner"
    MEMBER = "member"


@dataclass
class Membership:
    user_id: str
    role: Role
    joined_at: datetime = field(default_factory=utc_now)


@dataclass
class JoinRequest:
    user_id: str
    via_invite: bool
    requested_at: datetime = field(default_factory=utc_now)


@dataclass
class Group:
    name: str
    description: str
    is_public: bool
    id: str = field(default_factory=new_id)
    invite_code: str = field(default_factory=new_invite_code)
    created_at: datetime = field(default_factory=utc_now)
    members: dict[str, Membership] = field(default_factory=dict)
    join_requests: dict[str, JoinRequest] = field(default_factory=dict)

    @classmethod
    def create(cls, *, name: str, description: str, is_public: bool, owner_id: str) -> Group:
        group = cls(
            name=_clean_text(name, field_name="Nome da lista", max_length=MAX_GROUP_NAME, required=True),
            description=_clean_text(
                description, field_name="Descrição", max_length=MAX_GROUP_DESCRIPTION, required=False
            ),
            is_public=is_public,
        )
        group.members[owner_id] = Membership(user_id=owner_id, role=Role.OWNER)
        return group

    # --- consultas ------------------------------------------------------- #
    @property
    def owner_id(self) -> str:
        return next(m.user_id for m in self.members.values() if m.role is Role.OWNER)

    def is_member(self, user_id: str) -> bool:
        return user_id in self.members

    def is_owner(self, user_id: str) -> bool:
        membership = self.members.get(user_id)
        return membership is not None and membership.role is Role.OWNER

    def role_of(self, user_id: str) -> Role | None:
        membership = self.members.get(user_id)
        return membership.role if membership else None

    def has_pending_request(self, user_id: str) -> bool:
        return user_id in self.join_requests

    # --- guardas --------------------------------------------------------- #
    def ensure_member(self, user_id: str) -> None:
        if not self.is_member(user_id):
            # Não revela a existência da lista para quem não participa.
            raise NotFoundError("Lista não encontrada.")

    def ensure_owner(self, user_id: str) -> None:
        self.ensure_member(user_id)
        if not self.is_owner(user_id):
            raise PermissionDeniedError("Apenas o dono da lista pode fazer isso.")

    # --- comandos -------------------------------------------------------- #
    def update_details(
        self, actor_id: str, *, name: str, description: str, is_public: bool
    ) -> None:
        self.ensure_owner(actor_id)
        self.name = _clean_text(name, field_name="Nome da lista", max_length=MAX_GROUP_NAME, required=True)
        self.description = _clean_text(
            description, field_name="Descrição", max_length=MAX_GROUP_DESCRIPTION, required=False
        )
        self.is_public = is_public

    def request_to_join(self, user_id: str, *, via_invite: bool) -> JoinRequest:
        if self.is_member(user_id):
            raise ConflictError("Você já participa desta lista.")
        if self.has_pending_request(user_id):
            raise ConflictError("Seu pedido já foi enviado. Aguarde a aprovação.")
        if not via_invite and not self.is_public:
            raise NotFoundError("Lista não encontrada.")
        request = JoinRequest(user_id=user_id, via_invite=via_invite)
        self.join_requests[user_id] = request
        return request

    def approve_request(self, actor_id: str, user_id: str) -> Membership:
        self.ensure_owner(actor_id)
        if self.join_requests.pop(user_id, None) is None:
            raise NotFoundError("Pedido não encontrado.")
        membership = Membership(user_id=user_id, role=Role.MEMBER)
        self.members[user_id] = membership
        return membership

    def reject_request(self, actor_id: str, user_id: str) -> None:
        self.ensure_owner(actor_id)
        if self.join_requests.pop(user_id, None) is None:
            raise NotFoundError("Pedido não encontrado.")

    def cancel_request(self, user_id: str) -> None:
        if self.join_requests.pop(user_id, None) is None:
            raise NotFoundError("Pedido não encontrado.")

    def remove_member(self, actor_id: str, user_id: str) -> None:
        self.ensure_owner(actor_id)
        if user_id == actor_id:
            raise ConflictError("O dono não pode remover a si mesmo.")
        if self.members.pop(user_id, None) is None:
            raise NotFoundError("Membro não encontrado.")

    def leave(self, user_id: str) -> None:
        self.ensure_member(user_id)
        if self.is_owner(user_id):
            raise ConflictError("O dono não pode sair da lista. Exclua a lista, se preferir.")
        del self.members[user_id]

    def regenerate_invite_code(self, actor_id: str) -> str:
        self.ensure_owner(actor_id)
        self.invite_code = new_invite_code()
        return self.invite_code


# --------------------------------------------------------------------------- #
# Item da lista de compras
# --------------------------------------------------------------------------- #
class Category(StrEnum):
    """Seções do mercado, na ordem em que a lista é exibida."""

    HORTIFRUTI = "hortifruti"
    ACOUGUE = "acougue"
    FRIOS = "frios"
    PADARIA = "padaria"
    MANTIMENTOS = "mantimentos"
    BEBIDAS = "bebidas"
    CONGELADOS = "congelados"
    LIMPEZA = "limpeza"
    HIGIENE = "higiene"
    OUTROS = "outros"


class Unit(StrEnum):
    UNIDADE = "un"
    QUILO = "kg"
    GRAMA = "g"
    LITRO = "l"
    MILILITRO = "ml"
    PACOTE = "pct"
    CAIXA = "cx"
    DUZIA = "dz"


@dataclass
class ShoppingItem:
    group_id: str
    name: str
    added_by: str
    quantity: str = ""
    note: str = ""
    brand: str = ""
    unit: Unit = Unit.UNIDADE
    category: Category = Category.OUTROS
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utc_now)
    bought_by: str | None = None
    bought_at: datetime | None = None

    @classmethod
    def create(cls, *, group_id: str, added_by: str, **details) -> ShoppingItem:
        return cls(group_id=group_id, added_by=added_by, **cls._clean_details(**details))

    def update_details(self, **details) -> None:
        for key, value in self._clean_details(**details).items():
            setattr(self, key, value)

    @staticmethod
    def _clean_details(
        *,
        name: str,
        quantity: str = "",
        unit: str = Unit.UNIDADE,
        brand: str = "",
        category: str = Category.OUTROS,
        note: str = "",
    ) -> dict:
        try:
            unit, category = Unit(unit), Category(category)
        except ValueError as error:
            raise ValidationError("Medida ou categoria inválida.") from error
        return {
            "name": _clean_text(name, field_name="Item", max_length=MAX_ITEM_NAME, required=True),
            "quantity": _clean_text(
                quantity, field_name="Quantidade", max_length=MAX_ITEM_QUANTITY, required=False
            ),
            "unit": unit,
            "brand": _clean_text(brand, field_name="Marca", max_length=MAX_ITEM_BRAND, required=False),
            "category": category,
            "note": _clean_text(note, field_name="Observação", max_length=MAX_ITEM_NOTE, required=False),
        }

    @property
    def is_bought(self) -> bool:
        return self.bought_at is not None

    def same_name_as(self, name: str) -> bool:
        return self.name.casefold() == " ".join(name.split()).casefold()

    def mark_bought(self, user_id: str) -> None:
        self.bought_by = user_id
        self.bought_at = utc_now()

    def mark_pending(self) -> None:
        self.bought_by = None
        self.bought_at = None
