"""WebSocket multiplayer tests (Stage 3).

These drive the real WebSocket endpoint through Starlette's test client, so a
regression in presence, movement relay, chat or the auth check fails here.
"""

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import game_core  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient wired to throwaway storage and a clean room table."""
    save_path = tmp_path / "scam_jose_paul_save.json"
    monkeypatch.setattr(game_core, "DATA_FILE", str(save_path), raising=False)

    store = importlib.import_module("backend.store")
    monkeypatch.setattr(store, "SECRET_FILE", tmp_path / "secret.key", raising=False)
    monkeypatch.setattr(store, "SQLITE_PATH", tmp_path / "game.db", raising=False)

    realtime = importlib.import_module("backend.realtime")
    realtime.hub.rooms.clear()

    api = importlib.import_module("backend.api")
    with TestClient(api.app) as test_client:
        yield test_client
    realtime.hub.rooms.clear()


def token_for(client, username):
    response = client.post(
        "/api/register", json={"username": username, "password": "testpass123"}
    )
    assert response.status_code == 201, response.text
    return response.json()["token"]


def connect(client, token):
    return client.websocket_connect(f"/ws/city?token={token}")


# --------------------------------------------------------------------------
# Presence
# --------------------------------------------------------------------------
def test_welcome_reports_city_and_online_count(client):
    token = token_for(client, "ravi")
    with connect(client, token) as socket:
        welcome = socket.receive_json()
        assert welcome["type"] == "welcome"
        assert welcome["you"] == "ravi"
        assert welcome["city"] == "GLOBAL_HUB"
        assert welcome["online"] == 1
        assert welcome["players"] == []


def test_two_players_in_the_same_city_see_each_other(client):
    token_a = token_for(client, "ravi")
    token_b = token_for(client, "priya")

    with connect(client, token_a) as first:
        first.receive_json()  # welcome
        with connect(client, token_b) as second:
            welcome = second.receive_json()
            assert welcome["online"] == 2
            assert [player["username"] for player in welcome["players"]] == ["ravi"]

            joined = first.receive_json()
            assert joined["type"] == "join"
            assert joined["player"]["username"] == "priya"
            assert joined["online"] == 2


def test_disconnect_notifies_the_remaining_player(client):
    token_a = token_for(client, "ravi")
    token_b = token_for(client, "priya")

    with connect(client, token_a) as first:
        first.receive_json()
        second = connect(client, token_b)
        second.__enter__()
        second.receive_json()  # welcome
        first.receive_json()  # join
        second.__exit__(None, None, None)

        left = first.receive_json()
        assert left["type"] == "leave"
        assert left["username"] == "priya"
        assert left["online"] == 1


def test_the_city_comes_from_the_account_not_the_query_string(client):
    """A player cannot listen in on a city they never joined."""
    token = token_for(client, "ravi")
    with client.websocket_connect(f"/ws/city?token={token}&city=OTHER1") as socket:
        welcome = socket.receive_json()
        assert welcome["city"] == "GLOBAL_HUB"


# --------------------------------------------------------------------------
# Movement
# --------------------------------------------------------------------------
def test_movement_is_relayed_to_the_other_player(client):
    token_a = token_for(client, "ravi")
    token_b = token_for(client, "priya")

    with connect(client, token_a) as first:
        first.receive_json()
        with connect(client, token_b) as second:
            second.receive_json()
            first.receive_json()  # join

            second.send_json({"type": "move", "x": 12.5, "y": 1.7, "z": -8.0, "yaw": 0.75})
            moved = first.receive_json()
            assert moved["type"] == "move"
            player = moved["player"]
            assert player["username"] == "priya"
            assert player["x"] == 12.5
            assert player["y"] == 1.7
            assert player["z"] == -8.0
            assert player["yaw"] == 0.75


def test_bad_movement_values_are_ignored_and_the_room_stays_usable(client):
    token_a = token_for(client, "ravi")
    token_b = token_for(client, "priya")

    with connect(client, token_a) as first:
        first.receive_json()
        with connect(client, token_b) as second:
            second.receive_json()
            first.receive_json()  # join

            second.send_text("this is not json")
            second.send_json({"type": "move", "x": "far", "y": None, "z": 0, "yaw": 0})
            second.send_json({"type": "move", "x": 3, "y": 1.7, "z": 4, "yaw": 0})

            moved = first.receive_json()
            assert moved["type"] == "move"
            assert moved["player"]["x"] == 3.0
            assert moved["player"]["z"] == 4.0


def test_character_choice_is_visible_to_other_players(client):
    token_a = token_for(client, "ravi")
    token_b = token_for(client, "priya")
    chosen = client.post(
        "/api/character/select",
        json={"character_id": "invingoppa"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert chosen.status_code == 200

    with connect(client, token_a) as first:
        first.receive_json()
        with connect(client, token_b) as second:
            second.receive_json()
            joined = first.receive_json()
            assert joined["player"]["character_id"] == "invingoppa"


# --------------------------------------------------------------------------
# Chat
# --------------------------------------------------------------------------
def test_chat_reaches_everyone_including_the_sender(client):
    token_a = token_for(client, "ravi")
    token_b = token_for(client, "priya")

    with connect(client, token_a) as first:
        first.receive_json()
        with connect(client, token_b) as second:
            second.receive_json()
            first.receive_json()  # join

            second.send_json({"type": "chat", "text": "  hello   city  "})

            heard = first.receive_json()
            assert heard["type"] == "chat"
            assert heard["username"] == "priya"
            assert heard["text"] == "hello city"

            own = second.receive_json()
            assert own["type"] == "chat"
            assert own["username"] == "priya"


def test_long_chat_is_truncated(client):
    token_a = token_for(client, "ravi")
    token_b = token_for(client, "priya")

    with connect(client, token_a) as first:
        first.receive_json()
        with connect(client, token_b) as second:
            second.receive_json()
            first.receive_json()  # join

            second.send_json({"type": "chat", "text": "x" * 500})
            heard = first.receive_json()
            assert heard["type"] == "chat"
            assert len(heard["text"]) == 160


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
def test_an_invalid_token_is_rejected_with_4401(client):
    with client.websocket_connect("/ws/city?token=not-a-real-token") as socket:
        with pytest.raises(WebSocketDisconnect) as failure:
            socket.receive_json()
    assert failure.value.code == 4401


def test_lobby_reports_live_online_counts(client):
    token = token_for(client, "ravi")
    before = client.get("/api/cities").json()["cities"]
    hub = next(city for city in before if city["code"] == "GLOBAL_HUB")
    assert hub["online"] == 0

    with connect(client, token) as socket:
        socket.receive_json()
        during = client.get("/api/cities").json()["cities"]
        hub = next(city for city in during if city["code"] == "GLOBAL_HUB")
        assert hub["online"] == 1
