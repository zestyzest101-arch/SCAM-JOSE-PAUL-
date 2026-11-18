"""Tests for the JSON -> SQLite migration (db/migrate.py).

The migration must be safe by contract:
  * it never modifies or deletes the original JSON save
  * it takes a backup before importing
  * it is idempotent, so re-running never duplicates or overwrites rows
"""

import json
import os
import sqlite3
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from db import migrate  # noqa: E402

SAMPLE_SAVE = {
    "users": {
        "alice": {
            "password": "abc123$deadbeef",
            "current_room": "CITY-ALICE",
            "character": "char_01",
        },
        "bob": {"password": "xyz789$cafebabe", "current_room": "GLOBAL_HUB"},
    },
    "rooms": {
        "GLOBAL_HUB": {
            "name": "Global Hub",
            "host": None,
            "preset": "anna_nagar",
            "is_public": True,
            "members": ["bob"],
            "heist": {"active": False, "contributions": {}},
        },
        "CITY-ALICE": {
            "name": "Alice City",
            "host": "alice",
            "preset": "egmore",
            "is_public": False,
            "members": ["alice"],
            "heist": {"active": True, "contributions": {"alice": 500}},
        },
    },
}


def _write_save(tmp_path):
    json_path = tmp_path / "scam_jose_paul_save.json"
    json_path.write_text(json.dumps(SAMPLE_SAVE), encoding="utf-8")
    return json_path


def test_schema_is_created_when_no_save_exists(tmp_path):
    db_path = tmp_path / "game.db"
    stats = migrate.migrate(json_path=None, db_path=db_path, backup_dir=tmp_path / "backups")

    # No save file in this directory, so nothing to import...
    assert stats["json_found"] is False
    assert stats["users"] == 0
    # ...but the database and its tables must exist and be usable.
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    finally:
        conn.close()
    for expected in ("users", "player_state", "cities", "city_members", "schema_migrations"):
        assert expected in tables


def test_import_creates_rows_and_keeps_the_json_untouched(tmp_path):
    json_path = _write_save(tmp_path)
    db_path = tmp_path / "game.db"

    stats = migrate.migrate(
        json_path=str(json_path), db_path=db_path, backup_dir=tmp_path / "backups"
    )

    assert stats["json_found"] is True
    assert stats["users"] == 2
    assert stats["cities"] == 2

    # The original save must be byte-for-byte unchanged.
    assert json.loads(json_path.read_text(encoding="utf-8")) == SAMPLE_SAVE

    # A backup must have been taken before importing.
    backups = list((tmp_path / "backups").glob("*.json"))
    assert backups, "expected a backup copy of the JSON save"
    assert json.loads(backups[0].read_text(encoding="utf-8")) == SAMPLE_SAVE

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM city_members").fetchone()[0] == 2

        alice = conn.execute(
            "SELECT current_city, character_id FROM player_state WHERE username='alice'"
        ).fetchone()
        assert alice == ("CITY-ALICE", "char_01")

        # The full legacy profile is preserved verbatim for later stages.
        profile_json = conn.execute(
            "SELECT profile_json FROM player_state WHERE username='bob'"
        ).fetchone()[0]
        assert json.loads(profile_json)["password"] == "xyz789$cafebabe"
    finally:
        conn.close()


def test_rerunning_the_migration_is_idempotent(tmp_path):
    json_path = _write_save(tmp_path)
    db_path = tmp_path / "game.db"

    migrate.migrate(json_path=str(json_path), db_path=db_path, backup_dir=tmp_path / "backups")
    migrate.migrate(json_path=str(json_path), db_path=db_path, backup_dir=tmp_path / "backups")

    conn = sqlite3.connect(db_path)
    try:
        assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM cities").fetchone()[0] == 2
        assert conn.execute("SELECT COUNT(*) FROM city_members").fetchone()[0] == 2
    finally:
        conn.close()


def test_migration_never_overwrites_newer_player_progress(tmp_path):
    """A second import must not roll back progress made inside SQLite."""
    json_path = _write_save(tmp_path)
    db_path = tmp_path / "game.db"

    migrate.migrate(json_path=str(json_path), db_path=db_path, backup_dir=tmp_path / "backups")

    conn = sqlite3.connect(db_path)
    try:
        conn.execute("UPDATE users SET last_active = 12345.0 WHERE username='alice'")
        conn.execute("UPDATE player_state SET level = 42 WHERE username='alice'")
        conn.commit()
    finally:
        conn.close()

    migrate.migrate(json_path=str(json_path), db_path=db_path, backup_dir=tmp_path / "backups")

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT last_active FROM users WHERE username='alice'"
        ).fetchone()
        level = conn.execute(
            "SELECT level FROM player_state WHERE username='alice'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert row[0] == 12345.0
    assert level == 42
