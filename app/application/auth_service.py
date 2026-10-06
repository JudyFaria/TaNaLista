"""Casos de uso de conta: cadastro, login e autenticação por token."""

from __future__ import annotations

from app.application.dto import AuthResult, UserView
from app.application.ports import PasswordHasher, TokenService, UserRepository
from app.domain.entities import User
from app.domain.errors import AuthenticationError, ConflictError, ValidationError

MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128


class AuthService:
    def __init__(
        self, users: UserRepository, hasher: PasswordHasher, tokens: TokenService
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens

    def register(self, username: str, display_name: str, password: str) -> AuthResult:
        self._validate_password(password)
        if self._users.get_by_username(User.normalize_username(username)):
            raise ConflictError("Este nome de usuário já está em uso.")

        user = User.create(username, display_name, self._hasher.hash(password))
        self._users.add(user)
        return self._auth_result(user)

    def login(self, username: str, password: str) -> AuthResult:
        user = self._users.get_by_username(User.normalize_username(username))
        # Mensagem genérica: não revela se o usuário existe.
        if user is None or not self._hasher.verify(password, user.password_hash):
            raise AuthenticationError("Usuário ou senha incorretos.")
        return self._auth_result(user)

    def authenticate(self, token: str) -> User:
        user_id = self._tokens.verify(token)
        user = self._users.get(user_id)
        if user is None:
            raise AuthenticationError("Sessão inválida. Entre novamente.")
        return user

    def _auth_result(self, user: User) -> AuthResult:
        return AuthResult(user=UserView.from_entity(user), access_token=self._tokens.issue(user.id))

    @staticmethod
    def _validate_password(password: str) -> None:
        if not MIN_PASSWORD_LENGTH <= len(password or "") <= MAX_PASSWORD_LENGTH:
            raise ValidationError(
                f"A senha deve ter entre {MIN_PASSWORD_LENGTH} e {MAX_PASSWORD_LENGTH} caracteres."
            )
