"""Smoke tests for the SCAM JOSE PAUL rules engine (game_core.py).

Why these exist: the 3D client will be built on top of this module, so any
accidental change to game content, password hashing or the save-file contract
should fail loudly here instead of breaking the game for players.

The real save file is never touched. Every test that reads or writes data
points ``game_core.DATA_FILE`` at a temporary file.
"""

import inspect
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import game_core  # noqa: E402

EXPECTED_CITY_PRESETS = {
    "anna_nagar",
    "egmore",
    "perambur",
    "nungambakkam",
    "kilpauk",
}

CASINO_GAMES = [
    "play_baccarat",
    "play_blackjack",
    "play_keno",
    "play_mines",
    "play_plinko",
    "play_rps",
    "play_war",
    "play_wheel",
]


# ---------------------------------------------------------------------------
# Game content
# ---------------------------------------------------------------------------
def test_five_original_city_presets_exist():
    assert set(game_core.CITIES) == EXPECTED_CITY_PRESETS
    for key, city in game_core.CITIES.items():
        assert city["name"], f"{key} has no display name"
        for field in ("mug_chance", "tax_mult", "pay_mult", "death_mult"):
            assert field in city, f"{key} is missing {field}"


def test_content_tables_keep_their_size():
    # Minimums, not exact counts: adding content should not fail the build,
    # but accidentally deleting a chunk of it must.
    assert len(game_core.JOBS) >= 37
    assert len(game_core.SHOP_ITEMS) >= 15
    assert len(game_core.LOOT_ITEMS) >= 114
    assert len(game_core.PET_CATALOG) >= 20


def test_every_job_is_well_formed():
    for job_id, job in game_core.JOBS.items():
        assert job.get("name"), job_id
        assert "pay" in job, job_id
        assert int(job.get("req_level", 0)) >= 0, job_id


def test_every_shop_item_and_loot_item_is_well_formed():
    for item_id, item in game_core.SHOP_ITEMS.items():
        assert item.get("name"), item_id
        assert float(item["price"]) >= 0, item_id
    for loot_id, loot in game_core.LOOT_ITEMS.items():
        assert loot.get("name"), loot_id
        assert float(loot["sell_price"]) >= 0, loot_id


def test_every_pet_is_well_formed():
    for pet_id, pet in game_core.PET_CATALOG.items():
        assert pet.get("name"), pet_id
        assert float(pet["price"]) >= 0, pet_id
        assert pet.get("rarity"), pet_id


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------
def test_password_hash_round_trip():
    stored = game_core.hash_password("correct horse battery")
    assert "$" in stored, "hash must keep the salt$hash format stored in save files"
    assert game_core.verify_password(stored, "correct horse battery") is True
    assert game_core.verify_password(stored, "wrong password") is False


def test_password_hash_is_salted():
    assert game_core.hash_password("same") != game_core.hash_password("same")


def test_existing_stored_hash_format_still_verifies():
    """Backward compatibility: hashes already written to save files must work."""
    legacy = game_core.hash_password("oldpass", salt="deadbeefcafe")
    assert legacy == game_core.hash_password("oldpass", salt="deadbeefcafe")
    assert game_core.verify_password(legacy, "oldpass") is True


def test_malformed_password_hash_is_rejected_not_crashed():
    for bad in ("", "no-separator", "a$b$c", "$", None):
        assert game_core.verify_password(bad, "anything") is False


# ---------------------------------------------------------------------------
# Casino
# ---------------------------------------------------------------------------
def test_all_eight_casino_games_exist():
    for name in CASINO_GAMES:
        func = getattr(game_core, name, None)
        assert callable(func), f"{name} is missing"
        # They all take (all_data, username, bet, ...)
        params = list(inspect.signature(func).parameters)
        assert params[:3] == ["all_data", "username", "bet"], f"{name} signature changed: {params}"


# ---------------------------------------------------------------------------
# Player profile
# ---------------------------------------------------------------------------
def test_default_profile_has_the_core_fields():
    profile = game_core.get_default_room_profile("egmore")
    for field in (
        "preset", "fampay", "bank", "bank_max", "level", "xp",
        "job", "inventory", "pets", "loot", "mailbox",
    ):
        assert field in profile, f"default profile is missing {field}"
    assert profile["preset"] == "egmore"
    assert profile["level"] == 1
    assert profile["xp"] == 0


def test_default_profile_works_for_every_preset():
    for preset in sorted(EXPECTED_CITY_PRESETS):
        assert game_core.get_default_room_profile(preset)["preset"] == preset


# ---------------------------------------------------------------------------
# Save file contract
# ---------------------------------------------------------------------------
def test_load_creates_a_default_world(tmp_path, monkeypatch):
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(game_core, "DATA_FILE", str(save_path))

    data = game_core.load_all_data()

    assert save_path.exists(), "a first run must persist a default world"
    assert isinstance(data["users"], dict)
    assert "GLOBAL_HUB" in data["rooms"], "new worlds need the shared hub city"


def test_save_then_load_round_trip(tmp_path, monkeypatch):
    save_path = tmp_path / "save.json"
    monkeypatch.setattr(game_core, "DATA_FILE", str(save_path))

    data = game_core.load_all_data()
    data["users"]["tester"] = {
        "password": game_core.hash_password("hunter2"),
        "current_room": "GLOBAL_HUB",
    }
    game_core.save_all_data(data)

    reloaded = game_core.load_all_data()
    assert "tester" in reloaded["users"]
    assert game_core.verify_password(reloaded["users"]["tester"]["password"], "hunter2")

    # The file on disk must be readable JSON, not a pickle or a partial write.
    on_disk = json.loads(save_path.read_text(encoding="utf-8"))
    assert "tester" in on_disk["users"]
