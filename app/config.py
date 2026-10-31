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
    # Chave da conta de serviço do Firebase (JSON ou caminho do arquivo).
    # Vazio = banco JSON local em ``data_dir`` (desenvolvimento).
    firebase_credentials: str | None = None

    @property
    def database_path(self) -> Path:
        return self.data_dir / "db.json"

    @property
    def storage(self) -> str:
        return "firestore" if self.firebase_credentials else "json"

    @classmethod
    def from_env(cls) -> Settings:
        data_dir = Path(os.getenv("APP_DATA_DIR", PROJECT_ROOT / "data"))
        firebase_credentials = os.getenv("FIREBASE_CREDENTIALS") or None
        if not firebase_credentials and _has_ephemeral_disk():
            raise RuntimeError(
                "Banco de dados não configurado. Neste servidor o disco é apagado a cada "
                "reinício, então listas e itens seriam perdidos. Defina FIREBASE_CREDENTIALS "
                "com a chave da conta de serviço do Firebase."
            )
        return cls(
            data_dir=data_dir,
            secret_key=os.getenv("APP_SECRET_KEY") or _local_secret(data_dir),
            token_ttl=timedelta(days=int(os.getenv("APP_TOKEN_TTL_DAYS", "30"))),
            firebase_credentials=firebase_credentials,
        )


def _has_ephemeral_disk() -> bool:
    """Hospedagens cujo disco não sobrevive a reinícios/deploys (Render define ``RENDER``).

    ``APP_REQUIRE_DATABASE=1`` força a mesma verificação em outros provedores.
    """
    return bool(os.getenv("RENDER") or os.getenv("APP_REQUIRE_DATABASE"))


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
