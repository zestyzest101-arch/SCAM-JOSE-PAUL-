"""FastAPI backend for SCAM JOSE PAUL (Stage 1).

This is the API the 3D client (Stage 2) will talk to. It reuses ``game_core.py``
for rules and password hashing and the existing JSON save as the source of
truth, so the Streamlit app in ``app.py`` keeps working unchanged.

Run it with:
    uvicorn backend.api:app --host 0.0.0.0 --port 8000

Auth model: POST /api/login returns a signed token. Send it back as
``Authorization: Bearer <token>``.
"""

from __future__ import annotations

from typing import List, Optional

from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import casino, jobs, realtime, shop, store

app = FastAPI(title="SCAM JOSE PAUL API", version="1.0.0")

# The 3D client is served from a different origin during development, so the
# browser needs explicit permission to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------
class Credentials(BaseModel):
    username: str = Field(..., max_length=40)
    password: str = Field(..., max_length=128)


class CharacterChoice(BaseModel):
    character_id: str = Field(..., max_length=40)


class CityCreate(BaseModel):
    name: str = Field(..., max_length=40)
    preset: str = Field("egmore", max_length=40)
    is_public: bool = False


class CityJoin(BaseModel):
    code: str = Field(..., max_length=12)


# --------------------------------------------------------------------------
# Auth dependency
# --------------------------------------------------------------------------
def current_user(authorization: Optional[str] = Header(default=None)) -> str:
    """Resolve the bearer token to a username, or fail with 401."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token.")
    username = store.verify_token(authorization.split(" ", 1)[1].strip())
    if not username:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")
    return username


# --------------------------------------------------------------------------
# Health / catalogue
# --------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root():
    """Serve the 3D client, or describe the API if it is not installed."""
    index = WEB_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return {"service": "SCAM JOSE PAUL API", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "characters": len(store.CHARACTERS), "presets": store.presets()}


@app.get("/api/characters")
def characters() -> dict:
    """The 14 selectable characters, their perks and their one-hour abilities."""
    return {"characters": store.CHARACTERS}


@app.get("/api/presets")
def presets_endpoint() -> dict:
    return {"presets": store.presets()}


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------
@app.post("/api/register", status_code=201)
def register(body: Credentials) -> dict:
    data = store.load()
    try:
        account = store.create_account(data, body.username, body.password)
    except ValueError as error:
        message = str(error)
        status = 409 if "taken" in message else 400
        raise HTTPException(status_code=status, detail=message) from error

    profile = store.profile_for(account)
    store.save(data)
    return {
        "token": store.issue_token(body.username.strip()),
        "username": body.username.strip(),
        "account": store.summary(body.username.strip(), account, profile),
    }


@app.post("/api/login")
def login(body: Credentials) -> dict:
    data = store.load()
    account = store.authenticate(data, body.username, body.password)
    if account is None:
        raise HTTPException(status_code=401, detail="Incorrect username or password.")

    username = body.username.strip()
    profile = store.profile_for(account)
    account["last_active"] = store.now()
    store.save(data)
    return {
        "token": store.issue_token(username),
        "username": username,
        "account": store.summary(username, account, profile),
    }


@app.get("/api/me")
def me(username: str = Depends(current_user)) -> dict:
    data = store.load()
    account = store.account_for(data, username)
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    profile = store.profile_for(account)
    return {"username": username, "account": store.summary(username, account, profile)}


# --------------------------------------------------------------------------
# Character selection — saved to the account so it is never asked twice
# --------------------------------------------------------------------------
@app.post("/api/character/select")
def select_character(body: CharacterChoice, username: str = Depends(current_user)) -> dict:
    if not store.character_exists(body.character_id):
        raise HTTPException(status_code=404, detail="Unknown character.")

    data = store.load()
    account = store.account_for(data, username)
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")

    profile = store.profile_for(account)
    profile["character_id"] = body.character_id
    store.claim_character(data, account, body.character_id)
    store.save(data)
    return {"username": username, "account": store.summary(username, account, profile)}


# --------------------------------------------------------------------------
# Cities
# --------------------------------------------------------------------------
@app.get("/api/cities")
def list_cities() -> dict:
    data = store.load()
    cities = store.public_cities(data)
    for city in cities:
        # Live players currently inside the city, from the WebSocket rooms.
        city["online"] = realtime.hub.online_count(city["code"])
    return {"cities": cities}


@app.post("/api/cities", status_code=201)
def create_city(body: CityCreate, username: str = Depends(current_user)) -> dict:
    if body.preset not in store.preset_ids():
        raise HTTPException(status_code=400, detail="Unknown city preset.")
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="City name is required.")

    data = store.load()
    account = store.account_for(data, username)
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")

    city = store.create_city(data, account, body.name, body.preset, body.is_public)
    store.save(data)
    return {"username": username, "city": city}


@app.post("/api/cities/join")
def join_city(body: CityJoin, username: str = Depends(current_user)) -> dict:
    data = store.load()
    account = store.account_for(data, username)
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")

    city = store.join_city(data, account, body.code)
    if city is None:
        raise HTTPException(status_code=404, detail="No city with that code.")
    store.save(data)
    return {"username": username, "city": city}


@app.get("/api/cities/{code}")
def city_detail(code: str) -> dict:
    data = store.load()
    city = store.city_detail(data, code)
    if city is None:
        raise HTTPException(status_code=404, detail="No city with that code.")
    return {"city": city}


# --------------------------------------------------------------------------
# Multiplayer WebSocket rooms
#
# Registered before the static mount below, for the same reason the /api
# routes are: a mount on "/" would otherwise swallow /ws/city.
# --------------------------------------------------------------------------
# --------------------------------------------------------------------------
# Stage 4a: shop, bag and the starter house
# --------------------------------------------------------------------------
class ShopBuy(BaseModel):
    """Body for POST /api/shop/buy - one purchase."""

    item_id: str = Field(..., min_length=1, max_length=40)


class HouseUpdate(BaseModel):
    """Body for POST /api/house - repaint and/or re-place furniture."""

    wall: Optional[str] = Field(default=None, max_length=30)
    floor: Optional[str] = Field(default=None, max_length=30)
    furniture: Optional[List[str]] = Field(default=None)


def _player(username: str):
    """Signed-in player's save data, account row and room profile, or 401."""
    data = store.load()
    account = store.account_for(data, username)
    if account is None:
        raise HTTPException(status_code=401, detail="Account no longer exists.")
    return data, account, store.profile_for(account)


@app.get("/api/shop")
def shop_catalog(username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    return shop.catalog(profile)


@app.post("/api/shop/buy")
def shop_buy(body: ShopBuy, username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    try:
        purchase = shop.buy(profile, body.item_id)
    except shop.ShopError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    store.save(data)
    return {
        "username": username,
        "purchase": purchase,
        "account": store.summary(username, account, profile),
    }


@app.get("/api/inventory")
def inventory(username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    return {"username": username, "inventory": shop.inventory_view(profile)}


@app.get("/api/house")
def house(username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    return {"username": username, "house": shop.house_view(profile)}


@app.post("/api/house")
def house_update(body: HouseUpdate, username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    payload = {
        "wall": body.wall,
        "floor": body.floor,
        "furniture": body.furniture,
    }
    try:
        view = shop.update_house(profile, payload)
    except shop.ShopError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    store.save(data)
    return {"username": username, "house": view}


# ---------------------------------------------------------------------------
# Stage 4b: jobs and the casino
# ---------------------------------------------------------------------------
class JobChoice(BaseModel):
    """Body for POST /api/jobs/accept - the career to take."""

    job_id: str = Field(..., min_length=1, max_length=40)


class CasinoBet(BaseModel):
    """Body for POST /api/casino/play - one round at the tables."""

    game: str = Field(..., min_length=1, max_length=20)
    bet: int = Field(..., ge=1)
    choice: Optional[str] = Field(default=None, max_length=20)


@app.get("/api/jobs")
def jobs_board(username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    return {"username": username, "jobs": jobs.catalog(profile)}


@app.post("/api/jobs/accept")
def jobs_accept(body: JobChoice, username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    try:
        view = jobs.accept(profile, body.job_id)
    except jobs.JobError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    store.save(data)
    return {
        "username": username,
        "jobs": view,
        "account": store.summary(username, account, profile),
    }


@app.post("/api/jobs/work")
def jobs_work(username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    try:
        shift = jobs.work(profile)
    except jobs.JobError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    store.save(data)
    return {
        "username": username,
        "shift": shift,
        "account": store.summary(username, account, profile),
    }


@app.get("/api/casino")
def casino_table(username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    return {"username": username, "table": casino.table(profile)}


@app.post("/api/casino/play")
def casino_play(body: CasinoBet, username: str = Depends(current_user)) -> dict:
    data, account, profile = _player(username)
    try:
        round_view = casino.play(profile, body.game, body.bet, body.choice)
    except casino.CasinoError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    store.save(data)
    return {
        "username": username,
        "round": round_view,
        "account": store.summary(username, account, profile),
    }


app.include_router(realtime.router)


# --------------------------------------------------------------------------
# 3D client (web/) and character art (assets/)
#
# Mounted last on purpose: every /api route above is matched first, so the
# client can never shadow the API. Both mounts are optional so the API still
# starts if it is deployed without the static files.
# --------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "web"
ASSETS_DIR = REPO_ROOT / "assets"

if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

if WEB_DIR.is_dir():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="client")
