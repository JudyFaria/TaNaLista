"""Dependências do FastAPI: acesso ao container e ao usuário autenticado."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.container import Container
from app.domain.entities import User
from app.domain.errors import AuthenticationError

_bearer = HTTPBearer(auto_error=False)


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    container: Annotated[Container, Depends(get_container)],
) -> User:
    if credentials is None:
        raise AuthenticationError("Faça login para continuar.")
    return container.auth.authenticate(credentials.credentials)


ContainerDep = Annotated[Container, Depends(get_container)]
CurrentUser = Annotated[User, Depends(get_current_user)]
