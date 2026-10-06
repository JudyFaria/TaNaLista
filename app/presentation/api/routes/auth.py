from __future__ import annotations

from fastapi import APIRouter, status

from app.application.dto import AuthResult, UserView
from app.presentation.api.dependencies import ContainerDep, CurrentUser
from app.presentation.api.schemas import AuthOut, LoginIn, RegisterIn, UserOut

router = APIRouter(prefix="/auth", tags=["conta"])


@router.post("/register", response_model=AuthOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, container: ContainerDep) -> AuthResult:
    return container.auth.register(body.username, body.display_name, body.password)


@router.post("/login", response_model=AuthOut)
def login(body: LoginIn, container: ContainerDep) -> AuthResult:
    return container.auth.login(body.username, body.password)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> UserView:
    return UserView.from_entity(user)
