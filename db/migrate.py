"""Non-destructive import of the existing JSON save file into SQLite.

Project rules this file obeys:

  * never delete player data
  * never reset existing cities or player progress
  * migrations must stay backward compatible

How it stays safe
-----------------
The JSON save is only ever READ. Before importing, a timestamped copy is made
in ``data/backups/``. All inserts use ``INSERT OR IGNORE``, so re-running the
migration (or running it against a database that already has newer data)
never overwrites a row that is already there.

Usage
-----
    python3 -m db.migrate
    python3 -m db.migrate --json data/scam_jose_paul_save.json --db data/game.db
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = Path("data/game.db")

# Locations the existing app may have written the save file to, in priority order.
JSON_CANDIDATES: tuple[Path, ...] = (
    Path("data/scam_jose_paul_save.json"),
    Path("scam_jose_paul_save.json"),
)


def find_json_save(explicit: Optional[str] = None) -> Optional[Path]:
    """Return the JSON save file to import, or None when there isn't one yet."""
    if explicit is not None:
        path = Path(explicit)
        return path if path.exists() else None
    for candidate in JSON_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def connect(db_path: Any) -> sqlite3.Connection:
    """Open (creating if needed) the SQLite database with sane defaults."""
    db_path = Path(db_path)
    if db_path.parent and str(db_path.parent) not in ("", "."):
        db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def apply_schema(conn: sqlite3.Connection) -> None:
    """Create any missing tables. Safe to run repeatedly."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        (SCHEMA_VERSION, time.time()),
    )
    conn.commit()


def backup_json(json_path: Any, backup_dir: Any = None) -> Path:
    """Copy the save file aside before touching anything. Returns the copy path."""
    json_path = Path(json_path)
    target_dir = Path(backup_dir) if backup_dir is not None else json_path.parent / "backups"
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    target = target_dir / f"{json_path.stem}-{stamp}.json"
    shutil.copy2(json_path, target)
    return target


def _as_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _iter_members(room: Dict[str, Any]) -> Iterable[str]:
    members = room.get("members")
    if isinstance(members, dict):  # tolerate dict-shaped member maps
        members = list(members.keys())
    if not members:
        return []
    return [m for m in members if isinstance(m, str)]


def import_data(conn: sqlite3.Connection, data: Dict[str, Any]) -> Dict[str, int]:
    """Import a parsed JSON save. Never overwrites existing rows."""
    users = data.get("users") or {}
    rooms = data.get("rooms") or {}
    now = time.time()
    user_count = 0
    city_count = 0

    for username, account in users.items():
        if not isinstance(account, dict):
            continue
        password_hash = account.get("password") or account.get("password_hash") or ""
        conn.execute(
            """INSERT OR IGNORE INTO users(username, password_hash, created_at, last_active)
               VALUES (?, ?, ?, ?)""",
            (
                username,
                password_hash,
                account.get("created_at", now),
                account.get("last_active"),
            ),
        )
        conn.execute(
            """INSERT OR IGNORE INTO player_state
                   (username, current_city, character_id, level, xp, job, profile_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                username,
                account.get("current_room"),
                account.get("character"),
                int(account.get("level") or 1),
                int(account.get("xp") or 0),
                account.get("job"),
                _as_json(account),
            ),
        )
        user_count += 1

    for code, room in rooms.items():
        if not isinstance(room, dict):
            continue
        conn.execute(
            """INSERT OR IGNORE INTO cities
                   (code, name, host, preset, is_public, created_at, heist_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                code,
                room.get("name") or code,
                room.get("host"),
                room.get("preset"),
                1 if room.get("is_public") else 0,
                room.get("created_at", now),
                _as_json(room.get("heist") or {}),
            ),
        )
        for member in _iter_members(room):
            conn.execute(
                """INSERT OR IGNORE INTO city_members(city_code, username, joined_at)
                   VALUES (?, ?, ?)""",
                (code, member, now),
            )
        city_count += 1

    conn.commit()
    return {"users": user_count, "cities": city_count}


def migrate(
    json_path: Optional[str] = None,
    db_path: Any = DEFAULT_DB_PATH,
    backup_dir: Any = None,
) -> Dict[str, Any]:
    """Create the schema and import the JSON save (if present) into SQLite."""
    resolved_json = find_json_save(json_path)
    stats: Dict[str, Any] = {
        "users": 0,
        "cities": 0,
        "json_found": resolved_json is not None,
        "backup": None,
        "db": str(db_path),
    }
    conn = connect(db_path)
    try:
        apply_schema(conn)
        if resolved_json is None:
            return stats
        stats["backup"] = str(backup_json(resolved_json, backup_dir))
        data = json.loads(Path(resolved_json).read_text(encoding="utf-8"))
        stats.update(import_data(conn, data))
        return stats
    finally:
        conn.close()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import the existing JSON save into SQLite without deleting it."
    )
    parser.add_argument("--json", dest="json_path", default=None, help="path to the JSON save")
    parser.add_argument("--db", dest="db_path", default=str(DEFAULT_DB_PATH), help="SQLite file")
    parser.add_argument("--backup-dir", default=None, help="where to store the JSON backup")
    args = parser.parse_args(argv)

    stats = migrate(args.json_path, args.db_path, args.backup_dir)

    if not stats["json_found"]:
        print("No JSON save found. SQLite schema created and ready for new players.")
    else:
        print(
            f"Imported {stats['users']} player(s) and {stats['cities']} city/cities "
            f"into {stats['db']}"
        )
        print(f"Backup of the original save: {stats['backup']}")
    print("The original JSON save file was NOT modified or deleted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
