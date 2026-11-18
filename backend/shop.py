"""Shop, inventory and starter-house interiors (Stage 4a).

Everything here is a pure function over one room profile dict, so the FastAPI
layer stays thin and the legacy Streamlit app (``app.py``/``game_core.py``)
keeps its own text shop untouched.

Data layout, all backward compatible with existing saves:

* ``profile["fampay"]``      cash on hand (already existed)
* ``profile["inventory"]``   the 15 items from ``game_core.SHOP_ITEMS`` (already existed)
* ``profile["furniture"]``   ``{item_id: count}`` — added here, created lazily
* ``profile["house"]``       ``{"wall", "floor", "furniture": [ids]}`` — created lazily

Nothing is deleted or rewritten: missing keys are filled in on first use, so an
old save simply gains the new sections.
"""

from __future__ import annotations

from typing import Any, Dict, List

import game_core as core

MAX_PLACED_FURNITURE = 12
BANKNOTE_BANK_BONUS = 5000

# Wall and floor palettes are free: they are paint, not furniture.
WALLS: Dict[str, Dict[str, str]] = {
    "cream": {"name": "Warm cream", "color": "#f3e7d3"},
    "mint": {"name": "Mint", "color": "#cfe8d8"},
    "peach": {"name": "Peach", "color": "#f6d3bd"},
    "sky": {"name": "Sky blue", "color": "#cfe0f2"},
    "charcoal": {"name": "Charcoal", "color": "#4a4a55"},
}

FLOORS: Dict[str, Dict[str, str]] = {
    "oak": {"name": "Oak boards", "color": "#b98b5e"},
    "tile": {"name": "Marble tile", "color": "#e6e3dc"},
    "slate": {"name": "Slate", "color": "#6b6f76"},
    "terracotta": {"name": "Terracotta", "color": "#b5654a"},
}

# ``kind`` tells the 3D client which model to build in the interior.
FURNITURE: Dict[str, Dict[str, Any]] = {
    "plant": {
        "name": "Potted plant",
        "price": 300,
        "kind": "plant",
        "desc": "A plastic fern that has never needed water.",
    },
    "lamp": {
        "name": "Floor lamp",
        "price": 450,
        "kind": "lamp",
        "desc": "Warm light for the corner of any room.",
    },
    "rug": {
        "name": "Patterned rug",
        "price": 600,
        "kind": "rug",
        "desc": "Ties the whole questionable interior together.",
    },
    "table": {
        "name": "Dining table",
        "price": 800,
        "kind": "table",
        "desc": "Four legs, one top, endless bad decisions.",
    },
    "desk": {
        "name": "Work desk",
        "price": 900,
        "kind": "desk",
        "desc": "Where the scams get planned.",
    },
    "shelf": {
        "name": "Bookshelf",
        "price": 1100,
        "kind": "shelf",
        "desc": "Holds books nobody has opened.",
    },
    "bed": {
        "name": "Double bed",
        "price": 1200,
        "kind": "bed",
        "desc": "The most important furniture in the game.",
    },
    "sofa": {
        "name": "Three-seater sofa",
        "price": 1500,
        "kind": "sofa",
        "desc": "For the crew to sit on while counting money.",
    },
    "fridge": {
        "name": "Fridge",
        "price": 2500,
        "kind": "fridge",
        "desc": "Keeps the cold drinks cold.",
    },
    "tv": {
        "name": "Big screen TV",
        "price": 4000,
        "kind": "tv",
        "desc": "Wall-mounted, permanently on the news.",
    },
}

DEFAULT_HOUSE: Dict[str, Any] = {"wall": "cream", "floor": "oak", "furniture": []}


class ShopError(ValueError):
    """A purchase or house edit the player cannot do right now."""


# --------------------------------------------------------------------------
# Lookup helpers
# --------------------------------------------------------------------------
def _furniture_inventory(profile: Dict[str, Any]) -> Dict[str, int]:
    """Return the furniture counts, creating/repairing the map if needed."""
    inventory = profile.get("furniture")
    if not isinstance(inventory, dict):
        inventory = {}
        profile["furniture"] = inventory
    for item_id in FURNITURE:
        if not isinstance(inventory.get(item_id), int) or inventory.get(item_id) < 0:
            inventory[item_id] = 0
    return inventory


def _gear_inventory(profile: Dict[str, Any]) -> Dict[str, int]:
    inventory = profile.get("inventory")
    if not isinstance(inventory, dict):
        inventory = {}
        profile["inventory"] = inventory
    return inventory


def _item(item_id: str):
    """Look one item up across both catalogues, or return None."""
    if item_id in core.SHOP_ITEMS:
        raw = core.SHOP_ITEMS[item_id]
        return {
            "id": item_id,
            "name": raw.get("name", item_id),
            "price": int(raw.get("price", 0)),
            "category": raw.get("category", "Misc"),
            "desc": raw.get("desc", ""),
            "kind": "gear",
        }
    if item_id in FURNITURE:
        raw = FURNITURE[item_id]
        return {
            "id": item_id,
            "name": raw["name"],
            "price": int(raw["price"]),
            "category": "Furniture",
            "desc": raw.get("desc", ""),
            "kind": "furniture",
            "model": raw.get("kind", "table"),
        }
    return None


# --------------------------------------------------------------------------
# Shop
# --------------------------------------------------------------------------
def catalog(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Everything for sale, grouped into sections, with what you already own."""
    furniture_items = []
    furniture_owned = _furniture_inventory(profile)
    for item_id in FURNITURE:
        view = _item(item_id)
        view["owned"] = int(furniture_owned.get(item_id, 0))
        furniture_items.append(view)

    gear_items = []
    gear_owned = _gear_inventory(profile)
    for item_id in core.SHOP_ITEMS:
        view = _item(item_id)
        view["owned"] = int(gear_owned.get(item_id, 0))
        gear_items.append(view)

    return {
        "fampay": int(profile.get("fampay", 0)),
        "sections": [
            {"id": "furniture", "title": "House furniture", "items": furniture_items},
            {"id": "gear", "title": "Tools & gear", "items": gear_items},
        ],
    }


def buy(profile: Dict[str, Any], item_id: str) -> Dict[str, Any]:
    """Buy one item with cash. Raises ShopError when that is not possible."""
    item = _item((item_id or "").strip())
    if item is None:
        raise ShopError("Unknown item.")

    price = item["price"]
    balance = int(profile.get("fampay", 0))
    if balance < price:
        raise ShopError(
            f"Not enough cash - you need {price - balance:,} more."
        )

    profile["fampay"] = balance - price

    if item["kind"] == "furniture":
        owned_map = _furniture_inventory(profile)
        owned_map[item_id] = int(owned_map.get(item_id, 0)) + 1
    else:
        owned_map = _gear_inventory(profile)
        owned_map[item_id] = int(owned_map.get(item_id, 0)) + 1
        if item_id == "banknote":
            profile["bank_max"] = int(profile.get("bank_max", 0)) + BANKNOTE_BANK_BONUS

    return {
        "item": item,
        "owned": int(owned_map[item_id]),
        "fampay": int(profile["fampay"]),
        "bank_max": int(profile.get("bank_max", 0)),
    }


def inventory_view(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Only what the player actually owns, plus its resale-ish valuation."""
    items: List[Dict[str, Any]] = []
    total = 0

    gear_owned = _gear_inventory(profile)
    for item_id in core.SHOP_ITEMS:
        count = int(gear_owned.get(item_id, 0))
        if count <= 0:
            continue
        view = _item(item_id)
        view["count"] = count
        total += view["price"] * count
        items.append(view)

    furniture_owned = _furniture_inventory(profile)
    for item_id in FURNITURE:
        count = int(furniture_owned.get(item_id, 0))
        if count <= 0:
            continue
        view = _item(item_id)
        view["count"] = count
        total += view["price"] * count
        items.append(view)

    return {
        "items": items,
        "total_value": total,
        "fampay": int(profile.get("fampay", 0)),
    }


# --------------------------------------------------------------------------
# Starter house
# --------------------------------------------------------------------------
def house_for(profile: Dict[str, Any]) -> Dict[str, Any]:
    """Return the player's house, creating or repairing it in place."""
    house = profile.get("house")
    if not isinstance(house, dict):
        house = {}
        profile["house"] = house

    if house.get("wall") not in WALLS:
        house["wall"] = DEFAULT_HOUSE["wall"]
    if house.get("floor") not in FLOORS:
        house["floor"] = DEFAULT_HOUSE["floor"]

    placed = house.get("furniture")
    if not isinstance(placed, list):
        placed = []
    # Drop anything unknown or duplicated so the renderer can trust the list.
    cleaned: List[str] = []
    for item_id in placed:
        if item_id in FURNITURE and item_id not in cleaned:
            cleaned.append(item_id)
    house["furniture"] = cleaned[:MAX_PLACED_FURNITURE]
    return house


def house_view(profile: Dict[str, Any]) -> Dict[str, Any]:
    house = house_for(profile)
    owned = {
        item_id: count
        for item_id, count in _furniture_inventory(profile).items()
        if count > 0
    }
    return {
        "wall": house["wall"],
        "floor": house["floor"],
        "furniture": list(house["furniture"]),
        "walls": [
            {"id": key, "name": value["name"], "color": value["color"]}
            for key, value in WALLS.items()
        ],
        "floors": [
            {"id": key, "name": value["name"], "color": value["color"]}
            for key, value in FLOORS.items()
        ],
        "owned": owned,
        "max_placed": MAX_PLACED_FURNITURE,
        "catalog": [_item(item_id) for item_id in FURNITURE],
    }


def update_house(profile: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Repaint the house and/or re-place owned furniture."""
    house = house_for(profile)

    wall = payload.get("wall") or house["wall"]
    floor = payload.get("floor") or house["floor"]
    if wall not in WALLS:
        raise ShopError("Unknown wall style.")
    if floor not in FLOORS:
        raise ShopError("Unknown floor style.")

    furniture = payload.get("furniture")
    if furniture is None:
        furniture = house["furniture"]
    if not isinstance(furniture, (list, tuple)):
        raise ShopError("Furniture must be a list of item ids.")

    owned = _furniture_inventory(profile)
    placed: List[str] = []
    for raw_id in furniture:
        item_id = str(raw_id)
        if item_id not in FURNITURE:
            raise ShopError(f"Unknown furniture: {item_id}")
        if int(owned.get(item_id, 0)) < 1:
            raise ShopError(f"You do not own {FURNITURE[item_id]['name']}.")
        if item_id not in placed:
            placed.append(item_id)

    if len(placed) > MAX_PLACED_FURNITURE:
        raise ShopError(
            f"Your house holds {MAX_PLACED_FURNITURE} pieces of furniture at most."
        )

    house["wall"] = wall
    house["floor"] = floor
    house["furniture"] = placed
    return house_view(profile)
