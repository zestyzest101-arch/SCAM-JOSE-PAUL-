"""Bank heists (Stage 4c).

A heist is a cooperative event for everyone currently inside one city. The
server is the authority:

* it decides whether the crew gets away,
* it moves the money (and the lockup time) on the real player accounts,
* it broadcasts a scripted list of *cutscene beats* so every player in the city
  watches the same film at the same moment.

The browser only draws those beats. Editing the client cannot create money,
because the payout is already written server-side before the cutscene starts.

Protocol
--------
client -> server:  {"type": "heist"}
server -> room:    {"type": "heist", "heist": {...}}
server -> caller:  {"type": "heist_error", "message": "..."}
"""

from __future__ import annotations

import random
import time
import uuid
from typing import Any, Dict, List, Optional

from . import store

MIN_CREW = 1
MAX_CREW = 6
COOLDOWN_SECONDS = 90.0
BASE_CHANCE = 0.40
CHANCE_PER_EXTRA_CREW = 0.12
MAX_CHANCE = 0.86
LOOT_MIN = 6000
LOOT_MAX = 18000
FINE_SHARE = 0.15
FINE_CAP = 6000
LOCKUP_SECONDS = 45

# city code -> unix time of the last heist, used for the cooldown
_last_heist: Dict[str, float] = {}


class HeistError(Exception):
    """A heist the server refuses to start. The message is safe to show."""


def success_chance(crew_size: int) -> float:
    """Bigger crews have better odds, but it is never a sure thing."""
    extra = max(0, int(crew_size) - 1)
    return min(MAX_CHANCE, BASE_CHANCE + CHANCE_PER_EXTRA_CREW * extra)


def cooldown_left(city: str, now: Optional[float] = None) -> float:
    stamp = _last_heist.get(city)
    if not stamp:
        return 0.0
    return max(0.0, COOLDOWN_SECONDS - ((now or time.time()) - stamp))


def reset_cooldowns() -> None:
    """Test helper: forget every cooldown."""
    _last_heist.clear()


def _beats_success(loot: int) -> List[Dict[str, Any]]:
    return [
        {
            "id": "arrival",
            "text": "The crew pulls up outside the bank.",
            "duration": 3.5,
        },
        {"id": "vault", "text": "The vault door swings open. Fill the bags.", "duration": 3.5},
        {"id": "bags", "text": "Four bags. Nobody says a word.", "duration": 3.0},
        {"id": "exit", "text": "Walk out slow. Count it on the way.", "duration": 4.0},
        {"id": "count", "text": "The crew fans the cash out in daylight.", "duration": 4.5},
        {"id": "glasses", "text": "The leader takes off his glasses.", "duration": 3.5},
        {"id": "explode", "text": "Then the bank goes up behind them.", "duration": 5.0},
        {"id": "outro", "text": f"Clean getaway. \u20b9{loot:,} each.", "duration": 4.5},
    ]


def _beats_failure(fine: int) -> List[Dict[str, Any]]:
    return [
        {
            "id": "arrival",
            "text": "The crew pulls up outside the bank.",
            "duration": 3.5,
        },
        {"id": "alarm", "text": "The silent alarm was never silent.", "duration": 3.0},
        {"id": "surround", "text": "Armed police seal the street.", "duration": 3.5},
        {"id": "cuffed", "text": "The crew is dragged out in cuffs.", "duration": 4.0},
        {"id": "bag", "text": "The leader's bag drops in the gutter. Empty.", "duration": 3.5},
        {"id": "van", "text": "The van doors slam.", "duration": 4.0},
        {
            "id": "outro",
            "text": f"Fine \u20b9{fine:,} each \u00b7 {LOCKUP_SECONDS}s in lockup.",
            "duration": 4.5,
        },
    ]


def _clean_crew(usernames: List[str]) -> List[str]:
    crew: List[str] = []
    for name in usernames or []:
        if isinstance(name, str) and name and name not in crew:
            crew.append(name)
    return crew[:MAX_CREW]


def run_heist(
    city: str,
    usernames: List[str],
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Roll a heist, apply the outcome to every account, return the event.

    Raises ``HeistError`` (with a player-facing message) when the heist cannot
    start. All money changes happen here, before the cutscene is sent.
    """
    roller = rng or random.Random()
    code = (city or store.GLOBAL_ROOM).upper()

    left = cooldown_left(code)
    if left > 0:
        raise HeistError(f"The bank is still hot. Try again in {int(left) + 1}s.")

    crew = _clean_crew(usernames)
    if len(crew) < MIN_CREW:
        raise HeistError("Nobody is in the city to run the heist.")

    data = store.load()
    accounts: Dict[str, Dict[str, Any]] = {}
    for name in crew:
        account = store.account_for(data, name)
        if account is not None:
            accounts[name] = account
    if not accounts:
        raise HeistError("The crew's accounts could not be found.")

    names = list(accounts)
    chance = success_chance(len(names))
    success = roller.random() < chance
    loot = roller.randint(LOOT_MIN, LOOT_MAX)
    now = time.time()

    payouts: Dict[str, Dict[str, Any]] = {}
    fines: List[int] = []

    for name, account in accounts.items():
        profile = store.profile_for(account, code)
        fampay = int(profile.get("fampay") or 0)
        if success:
            profile["fampay"] = fampay + loot
            profile["xp"] = int(profile.get("xp") or 0) + 25
            payouts[name] = {"delta": loot, "fampay": profile["fampay"], "lockup_until": None}
        else:
            fine = min(int(fampay * FINE_SHARE), FINE_CAP)
            fines.append(fine)
            profile["fampay"] = max(0, fampay - fine)
            profile["prison_end"] = max(
                float(profile.get("prison_end") or 0), now + LOCKUP_SECONDS
            )
            payouts[name] = {
                "delta": -fine,
                "fampay": profile["fampay"],
                "lockup_until": profile["prison_end"],
            }

    store.save(data)
    _last_heist[code] = now

    top_fine = max(fines) if fines else 0

    return {
        "id": uuid.uuid4().hex,
        "city": code,
        "success": success,
        "leader": names[0],
        "crew": names,
        "chance": round(chance, 3),
        "loot": loot if success else 0,
        "fine": 0 if success else top_fine,
        "lockup_seconds": 0 if success else LOCKUP_SECONDS,
        "payouts": payouts,
        "beats": _beats_success(loot) if success else _beats_failure(top_fine),
        "started_at": now,
    }
