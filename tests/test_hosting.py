"""Comportamento em hospedagem serverless: cliente do banco único e frontend com CSP."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.factory import create_app
from tests.conftest import make_settings
from tests.fake_firestore import FakeFirestore


def test_firestore_client_is_created_once_per_instance(tmp_path, monkeypatch):
    fake = FakeFirestore()
    calls: list[str] = []

    def counting_client(credentials: str) -> FakeFirestore:
        calls.append(credentials)
        return fake

    monkeypatch.setattr("app.container.create_firestore_client", counting_client)
    settings = make_settings(tmp_path, "firestore")

    with TestClient(create_app(settings)) as client:
        assert client.get("/api/health").json()["storage"] == "firestore"
        body = {"username": "judy", "display_name": "Judy", "password": "senha-segura"}
        assert client.post("/api/auth/register", json=body).status_code == 201
        login = client.post("/api/auth/login", json={"username": "judy", "password": "senha-segura"})
        assert login.status_code == 200
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        for _ in range(3):
            assert client.get("/api/groups", headers=headers).status_code == 200

    assert len(calls) == 1


def test_frontend_and_service_worker_carry_csp(client):
    for path in ("/", "/sw.js"):
        response = client.get(path)
        assert response.status_code == 200, path
        assert "default-src 'self'" in response.headers["content-security-policy"], path
    assert "javascript" in client.get("/sw.js").headers["content-type"]
