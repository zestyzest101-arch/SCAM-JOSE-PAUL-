"""Jobs: pick a career, work a shift, get paid (Stage 4b).

The catalogue is the legacy ``game_core.JOBS`` table, so the Streamlit app and
the 3D client always offer the same careers at the same pay.

Everything here is a pure function over one room profile dict, which keeps the
FastAPI layer thin and lets the tests run without a server.

Profile keys used (all already existed, nothing is renamed):

* ``profile["job"]``        the job id the player currently holds
* ``profile["last_work"]``  unix timestamp of the last finished shift
* ``profile["fampay"]``     cash on hand
* ``profile["level"]`` / ``profile["xp"]`` / ``profile["bank_max"]``

A shift pays a random amount inside the job's pay range, plus a small seniority
bonus for every level above the job requirement, and grants XP that can level
the player up exactly like ``game_core.add_xp`` does.
"""

from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional

import game_core as core

#: Seconds between finished shifts. Long enough to matter, short enough that a
#: new player can try a second job while they are still exploring.
WORK_COOLDOWN_SECONDS = 60

#: XP for a shift, on top of the job requirement.
BASE_SHIFT_XP = 25

DEFAULT_JOB = "moderator"


class JobError(ValueError):
    """A career move the player cannot make right now."""


# --------------------------------------------------------------------------
# Lookup helpers
# --------------------------------------------------------------------------
def _level(profile: Dict[str, Any]) -> int:
    try:
        return max(1, int(profile.get("level") or 1))
    except (TypeError, ValueError):
        return 1


def _job_id(profile: Dict[str, Any]) -> str:
    job_id = profile.get("job")
    return job_id if job_id in core.JOBS else DEFAULT_JOB


def _pay_range(raw: Dict[str, Any]) -> tuple[int, int]:
    pay = raw.get("pay") or (100, 200)
    try:
        low, high = int(pay[0]), int(pay[1])
    except (TypeError, ValueError, IndexError):
        low, high = 100, 200
    if high < low:
        low, high = high, low
    return low, high


def cooldown_remaining(profile: Dict[str, Any], now: Optional[float] = None) -> float:
    """Seconds until the player can work again (0 when a shift is available)."""
    now = time.time() if now is None else now
    try:
        last = float(profile.get("last_work") or 0)
    except (TypeError, ValueError):
        last = 0.0
    return max(0.0, WORK_COOLDOWN_SECONDS - (now - last))


def _add_xp(profile: Dict[str, Any], amount: int) -> bool:
    """Grant XP and apply level-ups. Mirrors ``game_core.add_xp`` without prints."""
    profile["xp"] = int(profile.get("xp") or 0) + int(amount)
    profile["level"] = _level(profile)
    leveled_up = False
    while profile["xp"] >= profile["level"] * 300:
        profile["xp"] -= profile["level"] * 300
        profile["level"] += 1
        profile["bank_max"] = int(profile.get("bank_max") or 0) + 2500
        profile["fampay"] = int(profile.get("fampay") or 0) + profile["level"] * 500
        leveled_up = True
    return leveled_up


# --------------------------------------------------------------------------
# Job board
# --------------------------------------------------------------------------
def catalog(profile: Dict[str, Any], now: Optional[float] = None) -> Dict[str, Any]:
    """Every career, with lock state, the active one and the shift cooldown."""
    now = time.time() if now is None else now
    level = _level(profile)
    current = _job_id(profile)

    jobs: List[Dict[str, Any]] = []
    for job_id, raw in core.JOBS.items():
        low, high = _pay_range(raw)
        required = int(raw.get("req_level") or 1)
        jobs.append(
            {
                "id": job_id,
                "name": raw.get("name", job_id),
                "desc": raw.get("desc", ""),
                "pay_min": low,
                "pay_max": high,
                "req_level": required,
                "locked": level < required,
                "active": job_id == current,
            }
        )
    # Cheapest first, so a new player reads the list from the top.
    jobs.sort(key=lambda job: (job["req_level"], job["pay_min"], job["name"]))

    remaining = cooldown_remaining(profile, now)
    active = next((job for job in jobs if job["id"] == current), None)
    return {
        "job": current,
        "job_name": active["name"] if active else current,
        "level": level,
        "xp": int(profile.get("xp") or 0),
        "fampay": int(profile.get("fampay") or 0),
        "jobs": jobs,
        "cooldown_seconds": WORK_COOLDOWN_SECONDS,
        "cooldown_remaining": round(remaining, 1),
        "can_work": remaining <= 0,
    }


def accept(profile: Dict[str, Any], job_id: str, now: Optional[float] = None) -> Dict[str, Any]:
    """Take a job. Locked jobs are refused with a readable reason."""
    job_id = (job_id or "").strip()
    if job_id not in core.JOBS:
        raise JobError("Unknown job.")

    required = int(core.JOBS[job_id].get("req_level") or 1)
    if _level(profile) < required:
        raise JobError(
            f"{core.JOBS[job_id].get('name', job_id)} needs level {required}."
        )

    profile["job"] = job_id
    return catalog(profile, now)


def work(
    profile: Dict[str, Any],
    now: Optional[float] = None,
    rng: Optional[random.Random] = None,
) -> Dict[str, Any]:
    """Work one shift: pay, XP, level-ups and a fresh cooldown."""
    now = time.time() if now is None else now
    rng = rng or random

    job_id = _job_id(profile)
    raw = core.JOBS[job_id]

    remaining = cooldown_remaining(profile, now)
    if remaining > 0:
        raise JobError(f"Your shift just ended - {int(remaining) + 1}s until the next one.")

    low, high = _pay_range(raw)
    base = rng.randint(low, high)
    required = int(raw.get("req_level") or 1)
    seniority = max(0, _level(profile) - required) * 50
    payout = base + seniority

    profile["fampay"] = int(profile.get("fampay") or 0) + payout
    profile["last_work"] = now
    leveled_up = _add_xp(profile, BASE_SHIFT_XP + required * 5)

    return {
        "job": job_id,
        "job_name": raw.get("name", job_id),
        "payout": payout,
        "base_pay": base,
        "seniority_bonus": seniority,
        "fampay": int(profile.get("fampay") or 0),
        "level": _level(profile),
        "xp": int(profile.get("xp") or 0),
        "bank_max": int(profile.get("bank_max") or 0),
        "leveled_up": leveled_up,
        "cooldown_remaining": WORK_COOLDOWN_SECONDS,
    }
