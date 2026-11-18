"""Stage 4b tests: the free-play casino mini-games.

The games take an injectable RNG, so every outcome here is deterministic.
"""

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import game_core  # noqa: E402
from backend import casino  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    save_path = tmp_path / "scam_jose_paul_save.json"
    monkeypatch.setattr(game_core, "DATA_FILE", str(save_path), raising=False)

    store = importlib.import_module("backend.store")
    monkeypatch.setattr(store, "SECRET_FILE", tmp_path / "secret.key", raising=False)
    monkeypatch.setattr(store, "SQLITE_PATH", tmp_path / "game.db", raising=False)

    api = importlib.import_module("backend.api")
    with TestClient(api.app) as test_client:
        yield test_client


def token_for(client, username="gambler"):
    response = client.post("/api/register", json={"username": username, "password": "hunter2pass"})
    assert response.status_code == 201
    return response.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def profile(fampay=1000):
    return {"fampay": fampay}


class StubRng:
    """Deterministic stand-in for the ``random`` module."""

    def __init__(self, choices=None, ints=None):
        self.choices = list(choices or [])
        self.ints = list(ints or [])

    def choice(self, sequence):
        return self.choices.pop(0) if self.choices else sequence[0]

    def randint(self, low, high):
        return self.ints.pop(0) if self.ints else low


# --------------------------------------------------------------------------
# Table and limits
# --------------------------------------------------------------------------
def test_table_lists_the_three_games_and_the_limits():
    view = casino.table(profile())
    ids = {game["id"] for game in view["games"]}
    assert ids == {"coinflip", "dice", "slots"}
    assert view["min_bet"] == casino.MIN_BET
    assert view["max_bet"] == casino.MAX_BET
    assert view["fampay"] == 1000
    assert view["stats"]["played"] == 0


def test_bets_outside_the_limits_are_rejected():
    for bad in (casino.MIN_BET - 1, casino.MAX_BET + 1, "lots", None):
        with pytest.raises(casino.CasinoError):
            casino.play(profile(), "coinflip", bad, "heads")


def test_betting_more_than_the_balance_is_rejected():
    with pytest.raises(casino.CasinoError):
        casino.play(profile(fampay=100), "coinflip", 500, "heads")


def test_unknown_game_and_missing_choice_are_rejected():
    with pytest.raises(casino.CasinoError):
        casino.play(profile(), "roulette", 100)
    with pytest.raises(casino.CasinoError):
        casino.play(profile(), "coinflip", 100)


def test_a_rejected_bet_never_costs_anything():
    player = profile(fampay=1000)
    with pytest.raises(casino.CasinoError):
        casino.play(player, "coinflip", 200)  # no choice given
    assert player == {"fampay": 1000}


# --------------------------------------------------------------------------
# Coin flip
# --------------------------------------------------------------------------
def test_coinflip_win_and_loss_move_the_balance_by_the_stake():
    player = profile(fampay=1000)
    win = casino.play(player, "coinflip", 100, "heads", rng=StubRng(choices=["heads"]))
    assert win["won"] is True
    assert win["net"] == 100
    assert player["fampay"] == 1100

    loss = casino.play(player, "coinflip", 100, "tails", rng=StubRng(choices=["heads"]))
    assert loss["won"] is False
    assert loss["net"] == -100
    assert player["fampay"] == 1000


# --------------------------------------------------------------------------
# Dice
# --------------------------------------------------------------------------
def test_dice_over_and_under_pay_but_exactly_seven_loses():
    player = profile(fampay=1000)

    over = casino.play(player, "dice", 100, "over", rng=StubRng(ints=[6, 6]))
    assert over["total"] == 12
    assert over["won"] is True
    assert player["fampay"] == 1100

    under = casino.play(player, "dice", 100, "under", rng=StubRng(ints=[1, 2]))
    assert under["total"] == 3
    assert under["won"] is True

    seven = casino.play(player, "dice", 100, "over", rng=StubRng(ints=[3, 4]))
    assert seven["total"] == 7
    assert seven["won"] is False


# --------------------------------------------------------------------------
# Slots
# --------------------------------------------------------------------------
def test_three_of_a_kind_pays_its_multiplier():
    player = profile(fampay=1000)
    result = casino.play(player, "slots", 100, rng=StubRng(choices=["diamond"] * 3))
    assert result["won"] is True
    assert result["multiplier"] == 10
    assert result["net"] == 1000
    assert player["fampay"] == 2000


def test_two_of_a_kind_pays_even_and_a_miss_loses_the_stake():
    player = profile(fampay=1000)
    pair = casino.play(player, "slots", 100, rng=StubRng(choices=["cherry", "cherry", "bell"]))
    assert pair["won"] is True
    assert pair["net"] == 100

    miss = casino.play(player, "slots", 100, rng=StubRng(choices=["cherry", "bell", "lemon"]))
    assert miss["won"] is False
    assert miss["net"] == -100


# --------------------------------------------------------------------------
# Record keeping
# --------------------------------------------------------------------------
def test_the_casino_keeps_a_lifetime_record():
    player = profile(fampay=1000)
    casino.play(player, "coinflip", 100, "heads", rng=StubRng(choices=["heads"]))
    casino.play(player, "coinflip", 100, "heads", rng=StubRng(choices=["tails"]))

    stats = player["casino"]
    assert stats["played"] == 2
    assert stats["won"] == 1
    assert stats["net"] == 0
    assert stats["biggest_win"] == 100


# --------------------------------------------------------------------------
# Over HTTP
# --------------------------------------------------------------------------
def test_casino_endpoints_require_auth(client):
    assert client.get("/api/casino").status_code == 401
    assert client.post("/api/casino/play", json={"game": "coinflip", "bet": 100, "choice": "heads"}).status_code == 401


def test_playing_over_http_persists_the_result(client):
    token = token_for(client)
    table = client.get("/api/casino", headers=auth(token)).json()["table"]
    assert {game["id"] for game in table["games"]} == {"coinflip", "dice", "slots"}

    round_response = client.post(
        "/api/casino/play",
        json={"game": "coinflip", "bet": table["min_bet"], "choice": "heads"},
        headers=auth(token),
    )
    assert round_response.status_code == 200

    played = round_response.json()["round"]
    assert played["bet"] == table["min_bet"]
    assert played["net"] in (table["min_bet"], -table["min_bet"])
    assert played["fampay"] == table["fampay"] + played["net"]

    # The result is stored, not just returned.
    after = client.get("/api/casino", headers=auth(token)).json()["table"]
    assert after["stats"]["played"] == 1
    assert after["fampay"] == played["fampay"]


def test_an_over_limit_bet_returns_400(client):
    token = token_for(client)
    response = client.post(
        "/api/casino/play",
        json={"game": "slots", "bet": casino.MAX_BET + 1},
        headers=auth(token),
    )
    assert response.status_code == 400
    assert "limit" in response.json()["detail"].lower()
