"""Tests for the Stage 4c bank heist engine.

The cutscene itself is drawn by the browser, so these tests cover the part that
must never be wrong: the odds, the money, the cooldown and the beat script that
every player in the city receives.
"""

import importlib
import os
import sys
import time

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import game_core  # noqa: E402


class FixedRng:
    """Deterministic stand-in for random.Random."""

    def __init__(self, roll, loot=12000):
        self.roll = roll
        self.loot = loot

    def random(self):
        return self.roll

    def randint(self, low, high):
        return max(low, min(high, self.loot))


@pytest.fixture()
def game(tmp_path, monkeypatch):
    save_path = tmp_path / "scam_jose_paul_save.json"
    monkeypatch.setattr(game_core, "DATA_FILE", str(save_path), raising=False)

    store = importlib.import_module("backend.store")
    monkeypatch.setattr(store, "SECRET_FILE", tmp_path / "secret.key", raising=False)
    monkeypatch.setattr(store, "SQLITE_PATH", tmp_path / "game.db", raising=False)

    heist = importlib.import_module("backend.heist")
    heist.reset_cooldowns()

    api = importlib.import_module("backend.api")
    with TestClient(api.app) as client:
        yield client, heist, store


def signup(client, username):
    response = client.post(
        "/api/register", json={"username": username, "password": "hunter2pass"}
    )
    assert response.status_code in (200, 201), response.text
    payload = response.json()
    return payload.get("token") or payload.get("access_token")


def account(client, token):
    response = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    return response.json()["account"]


def test_success_plays_the_robbery_cutscene(game):
    client, heist, _ = game
    signup(client, "ravi")

    result = heist.run_heist("GLOBAL_HUB", ["ravi"], rng=FixedRng(0.0, loot=12000))
    ids = [beat["id"] for beat in result["beats"]]

    assert result["success"] is True
    assert ids[0] == "arrival"
    # the crew counts the money outside, the leader drops his glasses, the bank blows
    assert ids.index("count") < ids.index("glasses") < ids.index("explode")
    assert ids[-1] == "outro"
    assert result["loot"] == 12000
    assert all(beat["duration"] > 0 for beat in result["beats"])
    assert all(beat["text"] for beat in result["beats"])


def test_failure_plays_the_bust_cutscene(game):
    client, heist, _ = game
    signup(client, "ravi")

    result = heist.run_heist("GLOBAL_HUB", ["ravi"], rng=FixedRng(0.99))
    ids = [beat["id"] for beat in result["beats"]]

    assert result["success"] is False
    for needed in ("alarm", "surround", "cuffed", "bag", "van", "outro"):
        assert needed in ids
    assert result["lockup_seconds"] == heist.LOCKUP_SECONDS
    assert result["fine"] > 0


def test_both_outcomes_open_with_the_same_beat(game):
    """The opening line is identical, so the client can rely on it."""
    client, heist, _ = game
    signup(client, "ravi")

    win = heist.run_heist("GLOBAL_HUB", ["ravi"], rng=FixedRng(0.0))
    heist.reset_cooldowns()
    loss = heist.run_heist("GLOBAL_HUB", ["ravi"], rng=FixedRng(0.99))

    assert win["beats"][0]["text"] == loss["beats"][0]["text"]
    assert win["beats"][0]["text"] == "The crew pulls up outside the bank."


def test_success_pays_every_crew_member(game):
    client, heist, _ = game
    tokens = {name: signup(client, name) for name in ("ravi", "priya")}
    before = {name: account(client, token)["fampay"] for name, token in tokens.items()}

    result = heist.run_heist("GLOBAL_HUB", list(tokens), rng=FixedRng(0.0, loot=9000))

    assert set(result["crew"]) == set(tokens)
    assert result["leader"] == "ravi"
    for name, token in tokens.items():
        assert account(client, token)["fampay"] == before[name] + 9000
        assert result["payouts"][name]["delta"] == 9000


def test_failure_costs_money_and_books_lockup_time(game):
    client, heist, _ = game
    token = signup(client, "ravi")
    before = account(client, token)["fampay"]

    result = heist.run_heist("GLOBAL_HUB", ["ravi"], rng=FixedRng(0.99))
    after = account(client, token)["fampay"]

    assert after < before
    assert result["payouts"]["ravi"]["delta"] == -result["fine"]
    assert result["payouts"]["ravi"]["lockup_until"] > time.time()


def test_cooldown_blocks_a_second_heist(game):
    client, heist, _ = game
    signup(client, "ravi")

    heist.run_heist("GLOBAL_HUB", ["ravi"], rng=FixedRng(0.0))
    assert heist.cooldown_left("GLOBAL_HUB") > 0
    with pytest.raises(heist.HeistError):
        heist.run_heist("GLOBAL_HUB", ["ravi"], rng=FixedRng(0.0))


def test_empty_city_cannot_run_a_heist(game):
    client, heist, _ = game
    with pytest.raises(heist.HeistError):
        heist.run_heist("GLOBAL_HUB", [])


def test_bigger_crews_get_better_odds_within_the_cap(game):
    client, heist, _ = game
    assert heist.success_chance(1) < heist.success_chance(3)
    assert heist.success_chance(40) <= heist.MAX_CHANCE


def test_heist_over_the_socket_broadcasts_the_cutscene(game):
    client, heist, _ = game
    token = signup(client, "ravi")

    with client.websocket_connect(f"/ws/city?token={token}") as socket:
        welcome = socket.receive_json()
        assert welcome["type"] == "welcome"

        socket.send_json({"type": "heist"})

        message = None
        for _ in range(5):
            frame = socket.receive_json()
            if frame.get("type") == "heist":
                message = frame
                break

    assert message is not None, "the room never received the heist cutscene"
    assert message["heist"]["crew"] == ["ravi"]
    assert message["heist"]["beats"][0]["id"] == "arrival"
