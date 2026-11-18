"""Storage and auth helpers for the FastAPI backend (Stage 1).

Design rules this file follows:

* ``game_core.py`` stays the source of truth for rules and password hashing.
* The existing JSON save is read and written exactly as ``app.py`` does, so the
  Streamlit app keeps working and no player data is reset.
* SQLite is written as a best-effort mirror for fast queries in later stages.
  A mirror failure must never break a request or lose a login.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import game_core as core
from db import migrate as migration

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
SECRET_FILE = DATA_DIR / "secret.key"
SQLITE_PATH = DATA_DIR / "game.db"

TOKEN_TTL_SECONDS = 7 * 24 * 3600
GLOBAL_ROOM = "GLOBAL_HUB"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,20}$")
MIN_PASSWORD_LENGTH = 6
MAX_PASSWORD_LENGTH = 128
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
CODE_LENGTH = 6


def now() -> float:
    return time.time()


# --------------------------------------------------------------------------
# Character catalogue (mirrors app.py so both clients show the same roster)
# --------------------------------------------------------------------------
_RAW_CHARACTERS = [
    ("professor", "THE PROFESSOR", "Has 47 unfinished degrees and still asks Google how to boil water.", "+10% pay from WORK shifts."),
    ("heartbreaker", "THE RIZZLER", "Will get the buzz to pull thy huzz.", "+15% coins from BEG."),
    ("uncle_jose", "UNCLE JOSE", "Retired businessman. Wanted in 4 neighbourhood WhatsApp groups.", "Loses 10% fewer coins in failed street encounters."),
    ("sleeping_ceo", "THE NAKED MAFIA LEADER", "Will send tingles down ur wingles.", "+15% coins from successful CRIME runs."),
    ("og", "SAM DA BABY", "4 year old bebeh.", "10% discount on SHOP purchases."),
    ("mystery_man", "THE MYSTERY MAN", "Nobody knows who he is. Not even his own profile picture.", "+5% returns from CASINO games."),
    ("ancient_one", "THE ANCIENT ONE", "His account is older than the City's economy.", "+10% coins when selling LOOT."),
    ("hello_kitty_boss", "HELLO KITTY FINAL BOSS", "Cute appearance. The financial crimes department has opened a file.", "+10% DAILY reward."),
    ("npc", "THE NPC", "Stares into the distance. Somehow owns a mansion.", "+5% bonus on HUNT and FISH rewards."),
    ("cat_whisperer", "THE CAT WHISPERER", "Doesn't trust humans. Has a suspiciously large fish collection.", "+15% rewards from HUNT and FISH."),
    ("confused_citizen", "Paul mogger", "Only mews and eats gum.", "+15% XP from activities."),
    ("security_guard", "THE SECURITY GUARD", "Looks like he knows something. Refuses to elaborate.", "Reduces failed CRIME-run losses by 15%."),
    ("invingoppa", "INVINGOPPA", "The bank clerk has arrived. Your loan application was rejected before you even opened it.", "Banknote upgrades add +6,000 bank space."),
    ("drip_lord", "Chikko chezhiyanin magan", "Anna sowwww.", "+15% DAILY reward."),
]

_ABILITIES = {
    "professor": ("EXAM CRAM", "Gain 120 XP instantly."),
    "heartbreaker": ("RIZZ STORM", "Charm the City into giving you 750-1,500 coins."),
    "uncle_jose": ("OLD CONTACTS", "Call in a favour and receive one Padlock."),
    "sleeping_ceo": ("MAFIA ENVELOPE", "Collect a secret 2,000-4,000 coin bonus."),
    "og": ("TINY CEO SUBSIDY", "Get one free Shield from the tiny treasury."),
    "mystery_man": ("MYSTERY PAYOUT", "Flip a mystery reward: coins or XP."),
    "ancient_one": ("ANTIQUE APPRAISAL", "Sell one random piece of loot automatically; if you have none, receive 1,000 coins."),
    "hello_kitty_boss": ("CUTENESS TAX REFUND", "Claim a 1,250-coin refund from the City."),
    "npc": ("MAIN CHARACTER MOMENT", "Gain one Shield and 40 XP."),
    "cat_whisperer": ("PURRFECT DELIVERY", "A mysterious cat delivers one random loot item."),
    "confused_citizen": ("MEW MODE", "Gain 180 XP through intense gum-powered focus."),
    "security_guard": ("EMERGENCY LOCKDOWN", "Receive one Padlock and one Shield."),
    "invingoppa": ("BANKER'S BLESSING", "Increase your bank capacity by 1,500 coins."),
    "drip_lord": ("ANNA'S BLESSING", "Receive a 2,000-coin anna-approved bonus."),
}

CHARACTERS: List[Dict[str, str]] = [
    {
        "id": char_id,
        "name": name,
        "tagline": tagline,
        "perk": perk,
        "ability": _ABILITIES.get(char_id, ("", ""))[0],
        "ability_description": _ABILITIES.get(char_id, ("", ""))[1],
        "portrait": f"assets/characters/character_{index:02d}.jpg",
    }
    for index, (char_id, name, tagline, perk) in enumerate(_RAW_CHARACTERS, start=1)
]

_CHARACTER_IDS = {character["id"] for character in CHARACTERS}


def character_exists(character_id: str) -> bool:
    return character_id in _CHARACTER_IDS


def character_by_id(character_id: Optional[str]) -> Optional[Dict[str, str]]:
    for character in CHARACTERS:
        if character["id"] == character_id:
            return character
    return None


def presets() -> List[Dict[str, str]]:
    """The five map presets that already exist in game_core."""
    return [
        {"id": preset_id, "name": data.get("name", preset_id), "description": data.get("desc", "")}
        for preset_id, data in sorted(core.CITIES.items())
    ]


def preset_ids() -> List[str]:
    return sorted(core.CITIES)


# --------------------------------------------------------------------------
# Loading and saving (JSON source of truth + SQLite mirror)
# --------------------------------------------------------------------------
def load() -> Dict[str, Any]:
    return core.load_all_data()


def save(data: Dict[str, Any]) -> None:
    core.save_all_data(data)
    _mirror(data)


def _mirror(data: Dict[str, Any]) -> None:
    """Copy the save into SQLite. Never raises: the JSON save is authoritative."""
    try:
        SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
        connection = migration.connect(SQLITE_PATH)
        try:
            migration.apply_schema(connection)
            migration.import_data(connection, data)
        finally:
            connection.close()
    except Exception:  # pragma: no cover - defensive by design
        pass


# --------------------------------------------------------------------------
# Tokens
# --------------------------------------------------------------------------
def _secret() -> bytes:
    env_secret = os.environ.get("APPJET_SECRET")
    if env_secret:
        return env_secret.encode("utf-8")

    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not SECRET_FILE.exists():
        SECRET_FILE.write_bytes(secrets.token_bytes(32))
    return SECRET_FILE.read_bytes()


def issue_token(username: str, ttl: int = TOKEN_TTL_SECONDS) -> str:
    expires = int(now()) + int(ttl)
    payload = f"{username}|{expires}"
    signature = hmac.new(_secret(), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{signature}".encode("utf-8")).decode("ascii")


def verify_token(token: str) -> Optional[str]:
    """Return the username for a valid, unexpired token, else None."""
    if not token:
        return None
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        username, expires, signature = decoded.rsplit("|", 2)
        expected = hmac.new(
            _secret(), f"{username}|{expires}".encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return None
        if int(expires) < int(now()):
            return None
        return username
    except Exception:
        return None


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
def account_for(data: Dict[str, Any], username: str) -> Optional[Dict[str, Any]]:
    users = data.setdefault("users", {})
    account = users.get(username)
    if account is None:
        account = users.get((username or "").strip())
    return account


def create_account(data: Dict[str, Any], username: str, password: str) -> Dict[str, Any]:
    """Create an account using the same record shape as app.py."""
    name = (username or "").strip()
    if not USERNAME_RE.match(name):
        raise ValueError("Username must be 3-20 letters, numbers or underscores.")
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password is too long.")

    users = data.setdefault("users", {})
    if name in users:
        raise ValueError("That username is already taken.")

    account = {
        "password_hash": core.hash_password(password),
        "last_active": now(),
        "current_room": GLOBAL_ROOM,
        "room_profiles": {},
    }
    users[name] = account
    profile_for(account)
    return account


def authenticate(data: Dict[str, Any], username: str, password: str) -> Optional[Dict[str, Any]]:
    account = account_for(data, username)
    if account is None:
        return None
    if not core.verify_password(account.get("password_hash", ""), password or ""):
        return None
    return account


def profile_for(
    account: Dict[str, Any],
    room_code: Optional[str] = None,
    preset: str = "egmore",
) -> Dict[str, Any]:
    """Return the player's profile for a city, creating it if missing."""
    code = room_code or account.get("current_room") or GLOBAL_ROOM
    profiles = account.setdefault("room_profiles", {})
    if not isinstance(profiles, dict):
        profiles = {}
        account["room_profiles"] = profiles
    if code not in profiles or not isinstance(profiles.get(code), dict):
        profiles[code] = core.get_default_room_profile(preset)
    return profiles[code]


def summary(username: str, account: Dict[str, Any], profile: Dict[str, Any]) -> Dict[str, Any]:
    """A compact, client-friendly view of a player."""
    character = character_by_id(profile.get("character_id"))
    return {
        "character_id": profile.get("character_id"),
        "character_name": character["name"] if character else None,
        "has_character": bool(profile.get("character_id")),
        "level": profile.get("level", 1),
        "xp": profile.get("xp", 0),
        "fampay": profile.get("fampay", 0),
        "bank": profile.get("bank", 0),
        "bank_max": profile.get("bank_max", 0),
        "job": profile.get("job"),
        "city": account.get("current_room") or GLOBAL_ROOM,
        "preset": profile.get("preset", "egmore"),
    }


# --------------------------------------------------------------------------
# Cities
# --------------------------------------------------------------------------
def _new_code(data: Dict[str, Any]) -> str:
    rooms = data.setdefault("rooms", {})
    for _ in range(200):
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
        if code not in rooms:
            return code
    raise ValueError("Could not allocate a city code.")


def _city_view(code: str, room: Dict[str, Any]) -> Dict[str, Any]:
    members = [member for member in room.get("members", []) if isinstance(member, str)]
    return {
        "code": code,
        "name": room.get("name", code),
        "preset": room.get("preset", "egmore"),
        "host": room.get("host", "SYSTEM"),
        "is_public": bool(room.get("is_public", False)),
        "member_count": len(members),
        "members": members,
    }


def public_cities(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    cities = []
    for code, room in (data.get("rooms") or {}).items():
        if not isinstance(room, dict):
            continue
        if room.get("is_public") or code == GLOBAL_ROOM:
            cities.append(_city_view(code, room))
    return sorted(cities, key=lambda city: (city["code"] != GLOBAL_ROOM, city["name"].lower()))


def create_city(
    data: Dict[str, Any],
    account: Dict[str, Any],
    name: str,
    preset: str,
    is_public: bool,
    host: str = "player",
) -> Dict[str, Any]:
    rooms = data.setdefault("rooms", {})
    code = _new_code(data)
    room = {
        "host": host,
        "name": name.strip(),
        "preset": preset,
        "is_public": bool(is_public),
        "members": [],
        "heist": {"active": False, "contributions": {}},
        "started": True,
        "character_claims": {},
        "chat_messages": [],
        "created_at": now(),
    }
    rooms[code] = room
    return _city_view(code, room)


def join_city(data: Dict[str, Any], account: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
    rooms = data.setdefault("rooms", {})
    key = (code or "").strip().upper()
    room = rooms.get(key)
    if not isinstance(room, dict):
        return None

    members = room.setdefault("members", [])
    username = None
    for candidate, value in (data.get("users") or {}).items():
        if value is account:
            username = candidate
            break
    if username and username not in members:
        members.append(username)
    account["current_room"] = key
    profile_for(account, key, room.get("preset", "egmore"))
    return _city_view(key, room)


def city_detail(data: Dict[str, Any], code: str) -> Optional[Dict[str, Any]]:
    key = (code or "").strip().upper()
    room = (data.get("rooms") or {}).get(key)
    if not isinstance(room, dict):
        return None
    return _city_view(key, room)


def claim_character(data: Dict[str, Any], account: Dict[str, Any], character_id: str) -> None:
    """Record the first owner of a character inside the current city."""
    room_code = account.get("current_room") or GLOBAL_ROOM
    room = (data.get("rooms") or {}).get(room_code)
    if not isinstance(room, dict):
        return
    claims = room.setdefault("character_claims", {})
    if not isinstance(claims, dict):
        claims = {}
        room["character_claims"] = claims
    claims.setdefault(character_id, _username_of(data, account))


def _username_of(data: Dict[str, Any], account: Dict[str, Any]) -> Optional[str]:
    for name, value in (data.get("users") or {}).items():
        if value is account:
            return name
    return None
