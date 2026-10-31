from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.application.auth_service import AuthService
from app.application.dto import Notification
from app.application.group_service import GroupService
from app.application.item_service import ItemService
from app.config import Settings
from app.factory import create_app
from app.container import build_repositories
from app.infrastructure.security import JwtTokenService, ScryptPasswordHasher
from tests.fake_firestore import FakeFirestore

TEST_SECRET = "test-secret-key-with-at-least-32-bytes"


class RecordingPublisher:
    """Publicador falso: guarda as notificações para os testes conferirem."""

    def __init__(self) -> None:
        self.sent: list[tuple[set[str], Notification]] = []

    def publish(self, user_ids, notification: Notification) -> None:
        self.sent.append((set(user_ids), notification))

    def of_type(self, type_: str) -> list[tuple[set[str], Notification]]:
        return [entry for entry in self.sent if entry[1].type == type_]


class Services:
    def __init__(self, settings: Settings) -> None:
        users, groups, items = build_repositories(settings)
        self.events = RecordingPublisher()
        self.auth = AuthService(
            users, ScryptPasswordHasher(n=2**10), JwtTokenService(TEST_SECRET, timedelta(hours=1))
        )
        self.groups = GroupService(groups, users, items, self.events)
        self.items = ItemService(groups, items, users, self.events)

    def user(self, username: str, name: str | None = None) -> str:
        return self.auth.register(username, name or username.title(), "senha-segura").user.id


def make_settings(tmp_path: Path, backend: str) -> Settings:
    return Settings(
        data_dir=tmp_path,
        secret_key=TEST_SECRET,
        token_ttl=timedelta(hours=1),
        firebase_credentials="fake" if backend == "firestore" else None,
    )


# Os mesmos testes rodam contra o banco JSON e o Firestore (falso, em memória):
# os adaptadores precisam se comportar igual.
@pytest.fixture(params=["json", "firestore"])
def backend(request, monkeypatch) -> str:
    if request.param == "firestore":
        fake = FakeFirestore()  # um "projeto" por teste, compartilhado entre reinícios
        monkeypatch.setattr("app.container.create_firestore_client", lambda _credentials: fake)
    return request.param


@pytest.fixture
def settings(tmp_path: Path, backend: str) -> Settings:
    return make_settings(tmp_path, backend)


@pytest.fixture
def services(settings: Settings) -> Services:
    return Services(settings)


@pytest.fixture
def client(settings: Settings) -> TestClient:
    with TestClient(create_app(settings)) as test_client:
        yield test_client
