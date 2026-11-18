"""Stage 4a tests: shop purchases, inventory and the starter house.

Every test uses throwaway storage, so the real player save and the real SQLite
database are never touched.
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
from backend import shop  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A TestClient wired to throwaway storage."""
    save_path = tmp_path / "scam_jose_paul_save.json"
    monkeypatch.setattr(game_core, "DATA_FILE", str(save_path), raising=False)

    store = importlib.import_module("backend.store")
    monkeypatch.setattr(store, "SECRET_FILE", tmp_path / "secret.key", raising=False)
    monkeypatch.setattr(store, "SQLITE_PATH", tmp_path / "game.db", raising=False)

    api = importlib.import_module("backend.api")
    with TestClient(api.app) as test_client:
        test_client.save_path = save_path
        yield test_client


def register(client, username="shopper", password="hunter2pass"):
    return client.post("/api/register", json={"username": username, "password": password})


def token_for(client, username="shopper"):
    response = register(client, username)
    assert response.status_code == 201
    return response.json()["token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# --------------------------------------------------------------------------
# Catalogue
# --------------------------------------------------------------------------
def test_shop_lists_furniture_and_gear(client):
    token = token_for(client)
    response = client.get("/api/shop", headers=auth(token))
    assert response.status_code == 200

    body = response.json()
    assert body["fampay"] >= 0
    sections = {section["id"]: section for section in body["sections"]}
    assert set(sections) == {"furniture", "gear"}

    furniture_ids = {item["id"] for item in sections["furniture"]["items"]}
    assert {"bed", "sofa", "plant"} <= furniture_ids

    gear_ids = {item["id"] for item in sections["gear"]["items"]}
    assert "shield" in gear_ids

    for item in sections["furniture"]["items"]:
        assert item["price"] > 0
        assert item["name"]
        assert item["kind"] == "furniture"


def test_shop_requires_auth(client):
    assert client.get("/api/shop").status_code == 401
    assert client.post("/api/shop/buy", json={"item_id": "plant"}).status_code == 401


# --------------------------------------------------------------------------
# Buying
# --------------------------------------------------------------------------
def test_buying_furniture_spends_cash_and_adds_to_inventory(client):
    token = token_for(client)
    before = client.get("/api/shop", headers=auth(token)).json()["fampay"]
    price = shop.FURNITURE["plant"]["price"]

    response = client.post("/api/shop/buy", json={"item_id": "plant"}, headers=auth(token))
    assert response.status_code == 200

    purchase = response.json()["purchase"]
    assert purchase["item"]["id"] == "plant"
    assert purchase["owned"] == 1
    assert purchase["fampay"] == before - price

    inventory = client.get("/api/inventory", headers=auth(token)).json()["inventory"]
    counts = {item["id"]: item["count"] for item in inventory["items"]}
    assert counts["plant"] == 1


def test_buying_gear_uses_the_legacy_shop_items(client):
    """Gear comes from game_core.SHOP_ITEMS, so both UIs share one inventory."""
    token = token_for(client)
    catalog = client.get("/api/shop", headers=auth(token)).json()
    gear_section = next(section for section in catalog["sections"] if section["id"] == "gear")
    affordable = [item for item in gear_section["items"] if item["price"] <= catalog["fampay"]]
    assert affordable, "the starting balance should afford at least one gear item"

    cheapest = min(affordable, key=lambda item: item["price"])
    response = client.post("/api/shop/buy", json={"item_id": cheapest["id"]}, headers=auth(token))
    assert response.status_code == 200
    assert response.json()["purchase"]["owned"] == 1


def test_purchase_is_rejected_without_enough_cash(client):
    token = token_for(client)
    response = client.post("/api/shop/buy", json={"item_id": "reviver"}, headers=auth(token))
    assert response.status_code == 400
    assert "cash" in response.json()["detail"].lower()


def test_unknown_item_is_rejected(client):
    token = token_for(client)
    response = client.post("/api/shop/buy", json={"item_id": "rocket"}, headers=auth(token))
    assert response.status_code == 400


def test_cash_is_not_spent_when_the_purchase_fails():
    profile = {"fampay": 100, "furniture": {}}
    with pytest.raises(shop.ShopError):
        shop.buy(profile, "sofa")
    assert profile["fampay"] == 100
    assert profile["furniture"]["sofa"] == 0


# --------------------------------------------------------------------------
# Starter house
# --------------------------------------------------------------------------
def test_house_starts_with_defaults():
    profile = {"fampay": 500}
    house = shop.house_for(profile)
    assert house["wall"] in shop.WALLS
    assert house["floor"] in shop.FLOORS
    assert house["furniture"] == []


def test_house_repaint_and_place_owned_furniture():
    profile = {"fampay": 5000, "furniture": {}}
    shop.buy(profile, "bed")
    view = shop.update_house(
        profile, {"wall": "mint", "floor": "slate", "furniture": ["bed"]}
    )
    assert view["wall"] == "mint"
    assert view["floor"] == "slate"
    assert view["furniture"] == ["bed"]
    assert view["owned"]["bed"] == 1


def test_placing_furniture_you_do_not_own_is_rejected():
    profile = {"fampay": 5000, "furniture": {}}
    with pytest.raises(shop.ShopError):
        shop.update_house(profile, {"furniture": ["sofa"]})


def test_unknown_wall_or_furniture_is_rejected():
    profile = {"fampay": 500, "furniture": {}}
    with pytest.raises(shop.ShopError):
        shop.update_house(profile, {"wall": "neon"})
    with pytest.raises(shop.ShopError):
        shop.update_house(profile, {"furniture": ["jacuzzi"]})


def test_placed_furniture_is_deduplicated():
    profile = {"fampay": 5000, "furniture": {}}
    shop.buy(profile, "plant")
    view = shop.update_house(profile, {"furniture": ["plant", "plant"]})
    assert view["furniture"] == ["plant"]


def test_house_changes_persist_across_requests(client):
    token = token_for(client)
    assert client.post("/api/shop/buy", json={"item_id": "plant"}, headers=auth(token)).status_code == 200

    saved = client.post(
        "/api/house",
        json={"wall": "sky", "furniture": ["plant"]},
        headers=auth(token),
    )
    assert saved.status_code == 200
    assert saved.json()["house"]["wall"] == "sky"

    again = client.get("/api/house", headers=auth(token)).json()["house"]
    assert again["wall"] == "sky"
    assert again["furniture"] == ["plant"]


def test_house_rejects_unowned_furniture_over_http(client):
    token = token_for(client)
    response = client.post("/api/house", json={"furniture": ["sofa"]}, headers=auth(token))
    assert response.status_code == 400
