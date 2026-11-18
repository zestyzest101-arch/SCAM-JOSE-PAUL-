"""Stage 4b tests: the job board, paid shifts and their cooldown.

Throwaway storage only - the real player save and SQLite database are untouched.
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
from backend import jobs  # noqa: E402


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


def token_for(client, username="worker"):
    response = client.post("/api/register", json={"username": username, "password": "hunter2pass"})
    assert response.status_code == 201
    return response.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def fresh_profile(**overrides):
    profile = {
        "fampay": 500,
        "level": 1,
        "xp": 0,
        "bank_max": 5000,
        "job": "moderator",
        "job_last_shift": 0,
        "last_work": 0,
    }
    profile.update(overrides)
    return profile


class StubRng:
    """Deterministic stand-in for the ``random`` module."""

    def __init__(self, ints=None):
        self.ints = list(ints or [])

    def randint(self, low, high):
        if self.ints:
            return self.ints.pop(0)
        return low


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------
def test_catalogue_uses_the_legacy_job_table():
    view = jobs.catalog(fresh_profile())
    ids = {job["id"] for job in view["jobs"]}

    # The Streamlit game and the 3D client must offer the same careers.
    assert set(game_core.JOBS) == ids
    assert view["job"] == "moderator"
    assert view["job_name"] == game_core.JOBS["moderator"]["name"]
    assert view["can_work"] is True


def test_jobs_are_sorted_cheapest_first_and_locked_by_level():
    view = jobs.catalog(fresh_profile(level=1))
    requirements = [job["req_level"] for job in view["jobs"]]
    assert requirements == sorted(requirements)

    low = {job["id"]: job for job in view["jobs"] if job["req_level"] <= 1}
    high = {job["id"]: job for job in view["jobs"] if job["req_level"] > 1}
    assert low and all(not job["locked"] for job in low.values())
    assert high and all(job["locked"] for job in high.values())


def test_cooldown_blocks_a_second_shift():
    profile = fresh_profile(job_last_shift=1000.0)
    view = jobs.catalog(profile, now=1010.0)
    assert view["can_work"] is False
    assert 0 < view["cooldown_remaining"] <= jobs.WORK_COOLDOWN_SECONDS

    with pytest.raises(jobs.JobError):
        jobs.work(profile, now=1010.0)


# --------------------------------------------------------------------------
# Taking a job
# --------------------------------------------------------------------------
def test_accepting_an_unlocked_job_updates_the_profile():
    profile = fresh_profile()
    view = jobs.accept(profile, "street_magician")
    assert profile["job"] == "street_magician"
    assert view["job"] == "street_magician"
    assert next(job for job in view["jobs"] if job["id"] == "street_magician")["active"] is True


def test_locked_and_unknown_jobs_are_rejected():
    profile = fresh_profile(level=1)
    with pytest.raises(jobs.JobError):
        jobs.accept(profile, "matrix_architect")  # needs level 25
    with pytest.raises(jobs.JobError):
        jobs.accept(profile, "astronaut")
    # A refused move must not change the player's career.
    assert profile["job"] == "moderator"


# --------------------------------------------------------------------------
# Working
# --------------------------------------------------------------------------
def test_a_shift_pays_inside_the_job_range_and_starts_the_cooldown():
    profile = fresh_profile(fampay=500)
    low, high = game_core.JOBS["moderator"]["pay"]

    shift = jobs.work(profile, now=5000.0, rng=StubRng([high]))

    assert low <= shift["payout"] <= high
    assert shift["base_pay"] == high
    assert shift["fampay"] == 500 + shift["payout"]
    assert profile["job_last_shift"] == 5000.0
    assert shift["cooldown_remaining"] == jobs.WORK_COOLDOWN_SECONDS


def test_seniority_adds_a_bonus_above_the_job_requirement():
    profile = fresh_profile(level=4)
    shift = jobs.work(profile, now=10_000.0, rng=StubRng([300]))
    # Moderator requires level 1, so three extra levels pay 3 x 50.
    assert shift["seniority_bonus"] == 150
    assert shift["payout"] == 450


def test_shifts_grant_xp_and_can_level_the_player_up():
    profile = fresh_profile(xp=0)
    shift = jobs.work(profile, now=10_000.0, rng=StubRng([300]))
    assert shift["xp"] > 0 or shift["leveled_up"] is True

    # Enough XP to cross the level-1 threshold (1 * 300).
    profile = fresh_profile(xp=295, fampay=0, bank_max=5000)
    shift = jobs.work(profile, now=10_000.0, rng=StubRng([300]))
    assert shift["leveled_up"] is True
    assert profile["level"] == 2
    assert profile["bank_max"] == 7500
    # The level-up bonus lands in cash along with the shift pay.
    assert profile["fampay"] == shift["payout"] + 2 * 500


# --------------------------------------------------------------------------
# Over HTTP
# --------------------------------------------------------------------------
def test_job_endpoints_require_auth(client):
    assert client.get("/api/jobs").status_code == 401
    assert client.post("/api/jobs/work").status_code == 401
    assert client.post("/api/jobs/accept", json={"job_id": "moderator"}).status_code == 401


def test_working_over_http_persists_cash_and_enforces_the_cooldown(client):
    token = token_for(client)
    board = client.get("/api/jobs", headers=auth(token)).json()["jobs"]
    assert board["can_work"] is True

    shift = client.post("/api/jobs/work", headers=auth(token))
    assert shift.status_code == 200
    payout = shift.json()["shift"]["payout"]
    assert payout > 0

    again = client.get("/api/jobs", headers=auth(token)).json()["jobs"]
    assert again["can_work"] is False
    assert again["fampay"] == shift.json()["account"]["fampay"]

    # A second immediate shift is refused, and the cash is unchanged.
    blocked = client.post("/api/jobs/work", headers=auth(token))
    assert blocked.status_code == 400
    assert "shift" in blocked.json()["detail"].lower()


def test_accepting_a_locked_job_over_http_returns_400(client):
    token = token_for(client)
    response = client.post("/api/jobs/accept", json={"job_id": "matrix_architect"}, headers=auth(token))
    assert response.status_code == 400
    assert "level" in response.json()["detail"].lower()
