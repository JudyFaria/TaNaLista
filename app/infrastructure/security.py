"""Hash de senha (scrypt) e tokens de acesso (JWT)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.domain.errors import AuthenticationError


class ScryptPasswordHasher:
    """Formato armazenado: ``scrypt$n$r$p$salt$hash`` (base64)."""

    def __init__(self, n: int = 2**14, r: int = 8, p: int = 1) -> None:
        self._n, self._r, self._p = n, r, p

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        digest = self._derive(password, salt, self._n, self._r, self._p)
        return "$".join(
            ["scrypt", str(self._n), str(self._r), str(self._p), _b64(salt), _b64(digest)]
        )

    def verify(self, password: str, password_hash: str) -> bool:
        try:
            scheme, n, r, p, salt, digest = password_hash.split("$")
            if scheme != "scrypt":
                return False
            candidate = self._derive(password, _unb64(salt), int(n), int(r), int(p))
        except (ValueError, TypeError):
            return False
        return hmac.compare_digest(candidate, _unb64(digest))

    @staticmethod
    def _derive(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
        return hashlib.scrypt(password.encode(), salt=salt, n=n, r=r, p=p, dklen=32)


class JwtTokenService:
    ALGORITHM = "HS256"

    def __init__(self, secret_key: str, ttl: timedelta) -> None:
        self._secret = secret_key
        self._ttl = ttl

    def issue(self, user_id: str) -> str:
        now = datetime.now(UTC)
        payload = {"sub": user_id, "iat": now, "exp": now + self._ttl}
        return jwt.encode(payload, self._secret, algorithm=self.ALGORITHM)

    def verify(self, token: str) -> str:
        try:
            payload = jwt.decode(token, self._secret, algorithms=[self.ALGORITHM])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Sua sessão expirou. Entre novamente.") from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Sessão inválida. Entre novamente.") from exc
        return str(payload["sub"])


def _b64(raw: bytes) -> str:
    return base64.b64encode(raw).decode()


def _unb64(text: str) -> bytes:
    return base64.b64decode(text.encode())
