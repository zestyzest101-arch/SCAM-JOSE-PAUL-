"""The DLF Commanders casino: free-play mini-games (Stage 4b).

"Free play" means the casino never asks for real money - you bet the in-game
cash you already earned. Three games, each a single round so it works the same
on a phone and on a PC:

* ``coinflip``  pick heads or tails, win double your stake.
* ``dice``      two dice, bet over 7 or under 7; exactly 7 goes to the house.
* ``slots``     three reels; three of a kind pays big, two of a kind pays even.

``play`` is a pure function over the profile dict with an injectable ``rng``, so
tests are deterministic and no server is needed.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

MIN_BET = 50
MAX_BET = 5000

SLOT_SYMBOLS = ("cherry", "bell", "seven", "diamond", "lemon")
#: Net multiplier for three of a kind, by symbol.
TRIPLE_MULTIPLIERS = {
    "diamond": 10,
    "seven": 8,
    "bell": 5,
    "cherry": 5,
    "lemon": 5,
}

GAMES: Dict[str, Dict[str, Any]] = {
    "coinflip": {
        "name": "Coin flip",
        "desc": "Call it in the air. Heads or tails pays double.",
        "choices": ["heads", "tails"],
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
    },
    "dice": {
        "name": "Over / under seven",
        "desc": "Two dice. Over 7 or under 7 wins; exactly 7 belongs to the house.",
        "choices": ["over", "under"],
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
    },
    "slots": {
        "name": "Three reels",
        "desc": "Three of a kind pays 5x to 10x. Two of a kind pays even.",
        "choices": [],
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
    },
}


class CasinoError(ValueError):
    """A bet the house will not take."""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _stats(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Lifetime casino record, created lazily on the first bet."""
    stats = profile.get("casino")
    if not isinstance(stats, dict):
        stats = {}
        profile["casino"] = stats
    for key in ("played", "won", "net", "biggest_win"):
        value = stats.get(key)
        if not isinstance(value, (int, float)) or value < 0 and key != "net":
            stats[key] = 0
    return stats


def _balance(profile: Dict[str, Any]) -> int:
    try:
        return max(0, int(profile.get("fampay") or 0))
    except (TypeError, ValueError):
        return 0


def _clean_bet(bet: Any) -> int:
    try:
        amount = int(bet)
    except (TypeError, ValueError):
        raise CasinoError("Enter a whole-number bet.") from None
    if amount < MIN_BET:
        raise CasinoError(f"The minimum bet is ₹{MIN_BET:,}.")
    if amount > MAX_BET:
        raise CasinoError(f"The table limit is ₹{MAX_BET:,}.")
    return amount


# --------------------------------------------------------------------------
# Table
# --------------------------------------------------------------------------
def table(profile: Dict[str, Any]) -> Dict[str, Any]:
    """The games on offer, the stake limits and the player's record."""
    stats = _stats(profile)
    return {
        "fampay": _balance(profile),
        "min_bet": MIN_BET,
        "max_bet": MAX_BET,
        "games": [
            {"id": game_id, **game} for game_id, game in GAMES.items()
        ],
        "stats": {
            "played": int(stats["played"]),
            "won": int(stats["won"]),
            "net": int(stats["net"]),
            "biggest_win": int(stats["biggest_win"]),
        },
    }


# --------------------------------------------------------------------------
# One round
# --------------------------------------------------------------------------
def _coinflip(choice: str, rng: Any) -> Dict[str, Any]:
    if choice not in GAMES["coinflip"]["choices"]:
        raise CasinoError("Call heads or tails.")
    landed = rng.choice(["heads", "tails"])
    won = landed == choice
    return {
        "won": won,
        "net": None,  # filled in by play()
        "roll": landed,
        "message": f"The coin landed on {landed}.",
    }


def _dice(choice: str, rng: Any) -> Dict[str, Any]:
    if choice not in GAMES["dice"]["choices"]:
        raise CasinoError("Bet on over 7 or under 7.")
    first = rng.randint(1, 6)
    second = rng.randint(1, 6)
    total = first + second
    if total == 7:
        won = False
    elif choice == "over":
        won = total > 7
    else:
        won = total < 7
    return {
        "won": won,
        "net": None,
        "roll": [first, second],
        "total": total,
        "message": f"The dice came up {first} and {second} ({total}).",
    }


def _slots(choice: str, rng: Any) -> Dict[str, Any]:
    reels: List[str] = [rng.choice(SLOT_SYMBOLS) for _ in range(3)]
    if reels[0] == reels[1] == reels[2]:
        multiplier = TRIPLE_MULTIPLIERS.get(reels[0], 5)
        return {
            "won": True,
            "multiplier": multiplier,
            "net": None,
            "reels": reels,
            "message": f"Three {reels[0]}s! Pays {multiplier}x.",
        }
    if len(set(reels)) == 2:
        return {
            "won": True,
            "multiplier": 1,
            "net": None,
            "reels": reels,
            "message": "Two of a kind - your stake comes back doubled.",
        }
    return {
        "won": False,
        "multiplier": 0,
        "net": None,
        "reels": reels,
        "message": "Nothing on the reels this time.",
    }


_ROUNDS = {"coinflip": _coinflip, "dice": _dice, "slots": _slots}


def play(
    profile: Dict[str, Any],
    game: str,
    bet: Any,
    choice: Optional[str] = None,
    rng: Any = None,
) -> Dict[str, Any]:
    """Play one round. The stake is always taken; winnings are added back."""
    rng = rng or random
    game = (game or "").strip()
    if game not in GAMES:
        raise CasinoError("Unknown game.")

    amount = _clean_bet(bet)
    balance = _balance(profile)
    if amount > balance:
        raise CasinoError(
            f"Not enough cash - you need ₹{amount - balance:,} more."
        )

    choice = (choice or "").strip().lower()
    if GAMES[game]["choices"] and choice not in GAMES[game]["choices"]:
        raise CasinoError("Pick one of the table options first.")

    # Run the round before touching the balance, so a rejected bet never costs
    # the player anything.
    outcome = _ROUNDS[game](choice, rng)

    if game == "slots" and outcome["won"]:
        net = amount * int(outcome.get("multiplier", 1))
    else:
        net = amount if outcome["won"] else -amount

    profile["fampay"] = balance + net

    stats = _stats(profile)
    stats["played"] = int(stats["played"]) + 1
    stats["net"] = int(stats["net"]) + net
    if net > 0:
        stats["won"] = int(stats["won"]) + 1
        stats["biggest_win"] = max(int(stats["biggest_win"]), net)

    outcome["net"] = net
    outcome["game"] = game
    outcome["game_name"] = GAMES[game]["name"]
    outcome["bet"] = amount
    outcome["choice"] = choice or None
    outcome["fampay"] = int(profile["fampay"])
    outcome["stats"] = {
        "played": int(stats["played"]),
        "won": int(stats["won"]),
        "net": int(stats["net"]),
        "biggest_win": int(stats["biggest_win"]),
    }
    return outcome
