"""Real-time multiplayer for SCAM JOSE PAUL 3D (Stage 3).

One WebSocket room per city. The server keeps the authoritative list of who is
inside each city and relays movement and chat to the other players in that city.

Protocol (JSON text frames)
---------------------------
client -> server
    {"type": "move", "x": 1.2, "y": 1.7, "z": -4.5, "yaw": 0.3}
    {"type": "chat", "text": "hello"}
    {"type": "ping"}

server -> client
    {"type": "welcome", "you": "ravi", "city": "GLOBAL_HUB",
     "players": [...], "online": 2}
    {"type": "join",    "player": {...}, "online": 2}
    {"type": "leave",   "username": "ravi", "online": 1}
    {"type": "move",    "player": {...}}
    {"type": "chat",    "username": "ravi", "text": "hello", "at": 1700000000}
    {"type": "pong"}

Auth
----
A browser cannot set headers on a WebSocket, so the signed token travels in the
query string: ``/ws/city?token=<token>``. It is the same token the /api routes
use, so nothing new has to be stored or trusted. The city is NOT taken from the
query string: the server uses the city saved on the player's account, so a
player can never listen in on a city they have not joined.

This module is intentionally small and in-process (one worker). If the game ever
runs several workers, the room table needs a shared backend such as Redis.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import heist, store

router = APIRouter()

MAX_CHAT_LENGTH = 160
MIN_CHAT_INTERVAL = 0.25  # seconds between chat lines from one player
MAX_FRAME_LENGTH = 1024  # ignore absurdly large frames
MAX_COORDINATE = 500.0
CLOSE_UNAUTHORIZED = 4401


class Room:
    """Everyone currently inside one city."""

    def __init__(self, code: str) -> None:
        self.code = code
        self.players: Dict[str, Dict[str, Any]] = {}
        self.sockets: Dict[str, WebSocket] = {}

    def join(self, player: Dict[str, Any], socket: WebSocket) -> None:
        self.players[player["username"]] = player
        self.sockets[player["username"]] = socket

    def leave(self, username: str) -> None:
        self.players.pop(username, None)
        self.sockets.pop(username, None)

    def others(self, username: str) -> List[Dict[str, Any]]:
        return [p for name, p in self.players.items() if name != username]

    @property
    def online(self) -> int:
        return len(self.players)


class Hub:
    """All live city rooms."""

    def __init__(self) -> None:
        self.rooms: Dict[str, Room] = {}

    def room(self, code: str) -> Room:
        room = self.rooms.get(code)
        if room is None:
            room = Room(code)
            self.rooms[code] = room
        return room

    def online_count(self, code: str) -> int:
        room = self.rooms.get(code)
        return room.online if room else 0

    def drop_if_empty(self, code: str) -> None:
        room = self.rooms.get(code)
        if room is not None and not room.players:
            self.rooms.pop(code, None)


hub = Hub()


async def _send(socket: WebSocket, payload: Dict[str, Any]) -> bool:
    """Send one JSON frame. Returns False when the socket is gone."""
    try:
        await socket.send_text(json.dumps(payload, separators=(",", ":")))
        return True
    except Exception:
        return False


async def _broadcast(room: Room, payload: Dict[str, Any], skip: Optional[str] = None) -> None:
    """Send to everyone in the room, dropping players whose socket died."""
    dead = []
    for username, socket in list(room.sockets.items()):
        if username == skip:
            continue
        if not await _send(socket, payload):
            dead.append(username)
    for username in dead:
        room.leave(username)


def _number(value: Any) -> Optional[float]:
    """Accept only finite numbers, clamped to the world bounds."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return max(-MAX_COORDINATE, min(MAX_COORDINATE, number))


def _player_payload(username: str, character_id: Optional[str]) -> Dict[str, Any]:
    return {
        "username": username,
        "character_id": character_id,
        "x": 0.0,
        "y": 1.7,
        "z": 0.0,
        "yaw": 0.0,
    }


@router.websocket("/ws/city")
async def city_socket(websocket: WebSocket, token: str = "", city: str = "") -> None:
    """Live presence, movement and chat for one city."""
    username = store.verify_token(token)
    if not username:
        # Accept first so the browser gets a close code it can react to
        # (an expired session) instead of an opaque failed handshake.
        await websocket.accept()
        await websocket.close(code=CLOSE_UNAUTHORIZED)
        return

    data = store.load()
    account = store.account_for(data, username)
    if account is None:
        await websocket.accept()
        await websocket.close(code=CLOSE_UNAUTHORIZED)
        return

    # The account is the source of truth for which city you are allowed in.
    code = (account.get("current_room") or store.GLOBAL_ROOM).upper()
    profile = store.profile_for(account, code)
    character_id = profile.get("character_id")

    await websocket.accept()

    room = hub.room(code)
    # A player who reconnects (new tab, refresh) replaces their old session.
    if username in room.sockets:
        room.leave(username)

    player = _player_payload(username, character_id)
    existing = room.others(username)
    room.join(player, websocket)

    await _send(
        websocket,
        {
            "type": "welcome",
            "you": username,
            "city": code,
            "character_id": character_id,
            "players": existing,
            "online": room.online,
        },
    )
    await _broadcast(
        room,
        {"type": "join", "player": player, "online": room.online},
        skip=username,
    )

    last_chat = 0.0
    try:
        while True:
            raw = await websocket.receive_text()
            if len(raw) > MAX_FRAME_LENGTH:
                continue
            try:
                message = json.loads(raw)
            except (TypeError, ValueError):
                continue
            if not isinstance(message, dict):
                continue

            kind = message.get("type")

            if kind == "move":
                x = _number(message.get("x"))
                y = _number(message.get("y"))
                z = _number(message.get("z"))
                yaw = _number(message.get("yaw"))
                if x is None or y is None or z is None or yaw is None:
                    continue
                player.update({"x": x, "y": y, "z": z, "yaw": yaw})
                await _broadcast(room, {"type": "move", "player": dict(player)}, skip=username)

            elif kind == "chat":
                text = message.get("text")
                if not isinstance(text, str):
                    continue
                text = " ".join(text.split())[:MAX_CHAT_LENGTH]
                if not text:
                    continue
                now = time.time()
                if now - last_chat < MIN_CHAT_INTERVAL:
                    continue  # simple flood guard
                last_chat = now
                await _broadcast(
                    room,
                    {
                        "type": "chat",
                        "username": username,
                        "text": text,
                        "at": int(now),
                    },
                )

            elif kind == "heist":
                # The whole room is the crew. The server rolls the outcome and
                # moves the money FIRST, then everyone watches the same cutscene.
                try:
                    result = await asyncio.to_thread(
                        heist.run_heist, code, list(room.players)
                    )
                except heist.HeistError as error:
                    await _send(websocket, {"type": "heist_error", "message": str(error)})
                    continue
                except Exception:
                    await _send(
                        websocket,
                        {"type": "heist_error", "message": "The heist could not start."},
                    )
                    continue
                await _broadcast(room, {"type": "heist", "heist": result})

            elif kind == "ping":
                await _send(websocket, {"type": "pong"})

    except WebSocketDisconnect:
        pass
    except Exception:
        # A broken frame must never take down the room for everyone else.
        pass
    finally:
        room.leave(username)
        hub.drop_if_empty(code)
        await _broadcast(room, {"type": "leave", "username": username, "online": room.online})
