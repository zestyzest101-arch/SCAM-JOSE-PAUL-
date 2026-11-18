"""API tests for the Stage 1 FastAPI backend.

Every test runs against a temporary save file, so the real player save and the
real SQLite database are never touched.
"""

import importlib
import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import game_core  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient wired to throwaway storage."""
    save_path = tmp_path / "scam_jose_paul_save.json"
    monkeypatch.setattr(game_core, "DATA_FILE", str(save_path), raising=False)

    store = importlib.import_module("backend.store")
    monkeypatch.setattr(store, "SECRET_FILE", tmp_path / "secret.key", raising=False)
    monkeypatch.setattr(store, "SQLITE_PATH", tmp_path / "game.db", raising=False)

    api = importlib.import_module("backend.api")
    with TestClient(api.app) as test_client:
        test_client.save_path = save_path
        yield test_client


def register(client, username="ravi", password="hunter2pass"):
    return client.post("/api/register", json={"username": username, "password": password})


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# Health and catalogue
# --------------------------------------------------------------------------
def test_health_reports_engine_content(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["characters"] == 14
    assert len(body["presets"]) == 5


def test_character_catalogue_matches_game_roster(client):
    body = client.get("/api/characters").json()
    characters = body["characters"]
    assert len(characters) == 14
    ids = {character["id"] for character in characters}
    assert "invingoppa" in ids
    assert "drip_lord" in ids
    for character in characters:
        assert character["name"]
        assert character["perk"]
        assert character["ability"]


def test_presets_are_the_five_original_maps(client):
    presets = client.get("/api/presets").json()["presets"]
    names = {preset["name"] for preset in presets}
    assert names == {"Anna Nagar", "Egmore", "Perambur", "Nungambakkam", "Kilpauk"}


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
def test_register_returns_token_and_profile(client):
    response = register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "ravi"
    assert body["token"]
    assert body["account"]["has_character"] is False
    assert body["account"]["city"] == "GLOBAL_HUB"


def test_register_rejects_duplicate_and_weak_input(client):
    assert register(client).status_code == 201
    assert register(client).status_code == 409
    assert client.post("/api/register", json={"username": "x", "password": "longenough"}).status_code == 400
    assert client.post("/api/register", json={"username": "valid_name", "password": "123"}).status_code == 400


def test_login_accepts_correct_password_and_rejects_wrong_one(client):
    register(client)
    assert client.post("/api/login", json={"username": "ravi", "password": "wrongpass"}).status_code == 401
    assert client.post("/api/login", json={"username": "ghost", "password": "whatever"}).status_code == 401
    good = client.post("/api/login", json={"username": "ravi", "password": "hunter2pass"})
    assert good.status_code == 200
    assert good.json()["token"]


def test_me_requires_a_valid_token(client):
    token = register(client).json()["token"]
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/me", headers=auth("garbage")).status_code == 401

    response = client.get("/api/me", headers=auth(token))
    assert response.status_code == 200
    assert response.json()["username"] == "ravi"


def test_password_is_hashed_not_stored_in_plain_text(client):
    register(client)
    saved = json.loads(client.save_path.read_text(encoding="utf-8"))
    stored = saved["users"]["ravi"]["password_hash"]
    assert "hunter2pass" not in stored
    assert "$" in stored


# --------------------------------------------------------------------------
# Character selection persists across logins (the key requirement)
# --------------------------------------------------------------------------
def test_character_choice_is_saved_and_survives_relogin(client):
    token = register(client).json()["token"]

    chosen = client.post(
        "/api/character/select", json={"character_id": "invingoppa"}, headers=auth(token)
    )
    assert chosen.status_code == 200
    account = chosen.json()["account"]
    assert account["character_id"] == "invingoppa"
    assert account["character_name"] == "INVINGOPPA"
    assert account["has_character"] is True

    # Logging in again must NOT ask the player to pick a character again.
    relogin = client.post("/api/login", json={"username": "ravi", "password": "hunter2pass"})
    assert relogin.json()["account"]["character_id"] == "invingoppa"
    assert relogin.json()["account"]["has_character"] is True


def test_unknown_character_is_rejected(client):
    token = register(client).json()["token"]
    response = client.post(
        "/api/character/select", json={"character_id": "not_a_character"}, headers=auth(token)
    )
    assert response.status_code == 404


def test_character_selection_requires_login(client):
    assert client.post("/api/character/select", json={"character_id": "og"}).status_code == 401


# --------------------------------------------------------------------------
# Cities
# --------------------------------------------------------------------------
def test_create_city_returns_a_unique_code_and_makes_creator_a_member(client):
    token = register(client).json()["token"]
    response = client.post(
        "/api/cities",
        json={"name": "Anna Nagar Boys", "preset": "anna_nagar", "is_public": True},
        headers=auth(token),
    )
    assert response.status_code == 201
    city = response.json()["city"]
    assert len(city["code"]) == 6
    assert city["preset"] == "anna_nagar"
    assert city["is_public"] is True


def test_create_city_rejects_unknown_preset(client):
    token = register(client).json()["token"]
    response = client.post(
        "/api/cities", json={"name": "Nowhere", "preset": "atlantis"}, headers=auth(token)
    )
    assert response.status_code == 400


def test_join_city_by_code_and_read_it_back(client):
    host_token = register(client, "host_user").json()["token"]
    code = client.post(
        "/api/cities",
        json={"name": "Kilpauk Kings", "preset": "kilpauk", "is_public": True},
        headers=auth(host_token),
    ).json()["city"]["code"]

    guest_token = register(client, "guest_user").json()["token"]
    joined = client.post("/api/cities/join", json={"code": code.lower()}, headers=auth(guest_token))
    assert joined.status_code == 200
    assert "guest_user" in joined.json()["city"]["members"]

    detail = client.get(f"/api/cities/{code}")
    assert detail.status_code == 200
    assert detail.json()["city"]["member_count"] == 2


def test_join_unknown_city_is_404(client):
    token = register(client).json()["token"]
    assert client.post("/api/cities/join", json={"code": "ZZZZZZ"}, headers=auth(token)).status_code == 404
    assert client.get("/api/cities/ZZZZZZ").status_code == 404


def test_public_city_list_includes_the_global_hub(client):
    cities = client.get("/api/cities").json()["cities"]
    codes = {city["code"] for city in cities}
    assert "GLOBAL_HUB" in codes


def test_existing_save_data_is_preserved_by_api_writes(client):
    """A pre-existing player must still be there after new API activity."""
    saved = json.loads(client.save_path.read_text(encoding="utf-8"))
    saved["users"]["legacy_player"] = {
        "password_hash": game_core.hash_password("oldpassword"),
        "last_active": 0,
        "current_room": "GLOBAL_HUB",
        "room_profiles": {},
    }
    client.save_path.write_text(json.dumps(saved), encoding="utf-8")

    token = register(client, "new_user").json()["token"]
    client.post("/api/cities", json={"name": "New City", "preset": "egmore"}, headers=auth(token))

    after = json.loads(client.save_path.read_text(encoding="utf-8"))
    assert "legacy_player" in after["users"]
    assert game_core.verify_password(after["users"]["legacy_player"]["password_hash"], "oldpassword")
