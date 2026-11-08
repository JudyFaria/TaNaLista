from __future__ import annotations

import pytest

from app.config import Settings


@pytest.fixture
def env(monkeypatch, tmp_path):
    for name in ("FIREBASE_CREDENTIALS", "VERCEL", "APP_REQUIRE_DATABASE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("APP_SECRET_KEY", "x" * 32)
    return monkeypatch


def test_local_uses_json_database(env):
    assert Settings.from_env().storage == "json"


@pytest.mark.parametrize("flag", ["VERCEL", "APP_REQUIRE_DATABASE"])
def test_ephemeral_host_without_firebase_refuses_to_start(env, flag):
    env.setenv(flag, "true")
    with pytest.raises(RuntimeError, match="FIREBASE_CREDENTIALS"):
        Settings.from_env()



def test_ephemeral_host_with_firebase_uses_firestore(env):
    env.setenv("VERCEL", "true")
    env.setenv("FIREBASE_CREDENTIALS", "/etc/secrets/firebase.json")
    settings = Settings.from_env()
    assert settings.firebase_credentials == "/etc/secrets/firebase.json"
    assert settings.storage == "firestore"


def test_ephemeral_host_without_secret_key_refuses_to_start(env):
    env.setenv("VERCEL", "1")
    env.setenv("FIREBASE_CREDENTIALS", "/etc/secrets/firebase.json")
    env.delenv("APP_SECRET_KEY")
    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        Settings.from_env()


def test_local_without_secret_key_generates_one_in_data_dir(env, tmp_path):
    env.delenv("APP_SECRET_KEY")
    settings = Settings.from_env()
    assert settings.secret_key
    assert (tmp_path / ".secret_key").read_text(encoding="utf-8").strip() == settings.secret_key


def test_ephemeral_host_with_inline_json_credentials_uses_firestore(env):
    env.setenv("VERCEL", "1")
    env.setenv("FIREBASE_CREDENTIALS", '{"type": "service_account"}')
    settings = Settings.from_env()
    assert settings.storage == "firestore"
