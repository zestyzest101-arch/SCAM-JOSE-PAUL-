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

from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import store

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
@app.get("/")
def root() -> dict:
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
    return {"cities": store.public_cities(data)}


@app.post("/api/cities", status_code=201)
def create_city(body: CityCreate, username: str = Depends(current_user)) -> dict:
    if body.preset not in store.presets():
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
