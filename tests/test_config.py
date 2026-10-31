from __future__ import annotations

import pytest

from app.config import Settings


@pytest.fixture
def env(monkeypatch, tmp_path):
    for name in ("FIREBASE_CREDENTIALS", "RENDER", "APP_REQUIRE_DATABASE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_SECRET_KEY", "x" * 32)
    return monkeypatch


def test_local_uses_json_database(env):
    assert Settings.from_env().storage == "json"


@pytest.mark.parametrize("flag", ["RENDER", "APP_REQUIRE_DATABASE"])
def test_ephemeral_host_without_firebase_refuses_to_start(env, flag):
    env.setenv(flag, "true")
    with pytest.raises(RuntimeError, match="FIREBASE_CREDENTIALS"):
        Settings.from_env()



def test_ephemeral_host_with_firebase_uses_firestore(env):
    env.setenv("RENDER", "true")
    env.setenv("FIREBASE_CREDENTIALS", "/etc/secrets/firebase.json")
    settings = Settings.from_env()
    assert settings.firebase_credentials == "/etc/secrets/firebase.json"
    assert settings.storage == "firestore"
