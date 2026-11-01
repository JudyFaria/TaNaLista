"""Contratos HTTP (entrada e saída) da API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.domain.entities import Category, Role, Unit


# --- entrada ---------------------------------------------------------------- #
class RegisterIn(BaseModel):
    username: str = Field(max_length=30)
    display_name: str = Field(max_length=50)
    password: str = Field(max_length=128)


class LoginIn(BaseModel):
    username: str = Field(max_length=30)
    password: str = Field(max_length=128)


class GroupIn(BaseModel):
    name: str = Field(max_length=60)
    description: str = Field(default="", max_length=200)
    is_public: bool = True


class ItemIn(BaseModel):
    name: str = Field(max_length=80)
    quantity: str = Field(default="", max_length=30)
    unit: Unit = Unit.UNIDADE
    brand: str = Field(default="", max_length=40)
    category: Category = Category.OUTROS
    note: str = Field(default="", max_length=140)


class ItemStatusIn(BaseModel):
    bought: bool


# --- saída ------------------------------------------------------------------ #
class UserOut(BaseModel):
    id: str
    username: str
    display_name: str


class AuthOut(BaseModel):
    user: UserOut
    access_token: str
    token_type: str = "bearer"


class MemberOut(BaseModel):
    user: UserOut
    role: Role
    joined_at: datetime


class JoinRequestOut(BaseModel):
    user: UserOut
    via_invite: bool
    requested_at: datetime


class GroupSummaryOut(BaseModel):
    id: str
    name: str
    description: str
    is_public: bool
    member_count: int
    my_role: Role | None
    has_pending_request: bool
    pending_items: int | None
    pending_requests: int


class GroupDetailsOut(BaseModel):
    id: str
    name: str
    description: str
    is_public: bool
    invite_code: str
    my_role: Role
    members: list[MemberOut]
    join_requests: list[JoinRequestOut]


class ItemOut(BaseModel):
    id: str
    name: str
    quantity: str
    unit: Unit
    brand: str
    category: Category
    note: str
    added_by: UserOut
    created_at: datetime
    bought_by: UserOut | None
    bought_at: datetime | None


class ClearedOut(BaseModel):
    removed: int
