"""Configurações lidas de variáveis de ambiente (com padrões para desenvolvimento)."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    data_dir: Path
    secret_key: str
    token_ttl: timedelta
    database_url: str | None = None  # vazio = banco JSON local em ``data_dir``

    @property
    def database_path(self) -> Path:
        return self.data_dir / "db.json"

    @classmethod
    def from_env(cls) -> Settings:
        data_dir = Path(os.getenv("APP_DATA_DIR", PROJECT_ROOT / "data"))
        return cls(
            data_dir=data_dir,
            secret_key=os.getenv("APP_SECRET_KEY") or _local_secret(data_dir),
            token_ttl=timedelta(days=int(os.getenv("APP_TOKEN_TTL_DAYS", "30"))),
            database_url=_normalize_database_url(os.getenv("DATABASE_URL")),
        )


def _normalize_database_url(url: str | None) -> str | None:
    """Aceita URLs no formato dos provedores (``postgres://``) e usa o driver psycopg 3."""
    if not url:
        return None
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url.removeprefix(prefix)
    return url


def _local_secret(data_dir: Path) -> str:
    """Gera (uma vez) e reaproveita uma chave local, para o login sobreviver a reinícios.

    Em produção, defina ``APP_SECRET_KEY`` no ambiente.
    """
    path = data_dir / ".secret_key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    data_dir.mkdir(parents=True, exist_ok=True)
    key = secrets.token_urlsafe(48)
    path.write_text(key, encoding="utf-8")
    return key
