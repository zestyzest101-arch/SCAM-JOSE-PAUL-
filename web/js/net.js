// Live multiplayer connection: one WebSocket per city room.
//
// The server relays movement and chat between everyone inside the same city.
// If the connection drops (phone sleeping, wifi blip) it reconnects on its own
// and re-sends the latest position, so the other players see you again.
import { getToken } from "./api.js";

const MOVE_INTERVAL_MS = 90; // ~11 position updates per second
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000];

export class CitySocket {
  constructor(handlers = {}) {
    this.handlers = handlers;
    this.socket = null;
    this.city = "GLOBAL_HUB";
    this.closed = false;
    this._attempt = 0;
    this._lastMoveAt = 0;
    this._pending = null;
    this._timer = 0;
  }

  connect(city) {
    this.city = city || "GLOBAL_HUB";
    this.closed = false;
    this._attempt = 0;
    this._open();
  }

  get connected() {
    return !!this.socket && this.socket.readyState === WebSocket.OPEN;
  }

  _url() {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const token = encodeURIComponent(getToken() || "");
    const city = encodeURIComponent(this.city);
    return `${scheme}://${window.location.host}/ws/city?token=${token}&city=${city}`;
  }

  _open() {
    if (this.closed) return;
    this.handlers.onStatus?.("connecting");

    let socket;
    try {
      socket = new WebSocket(this._url());
    } catch (error) {
      this._scheduleReconnect();
      return;
    }
    this.socket = socket;

    socket.addEventListener("open", () => {
      this._attempt = 0;
      this.handlers.onStatus?.("online");
      // Tell everyone where we are straight away after a reconnect.
      if (this._pending) this._send(this._pending);
    });

    socket.addEventListener("message", (event) => {
      let message;
      try {
        message = JSON.parse(event.data);
      } catch (error) {
        return;
      }
      this._dispatch(message);
    });

    socket.addEventListener("close", (event) => {
      this.socket = null;
      if (event.code === 4401) {
        // The saved login expired; reconnecting would just fail again.
        this.closed = true;
        this.handlers.onStatus?.("unauthorized");
        return;
      }
      if (this.closed) {
        this.handlers.onStatus?.("offline");
        return;
      }
      this._scheduleReconnect();
    });

    socket.addEventListener("error", () => {
      // The close handler runs next and decides whether to reconnect.
    });
  }

  _dispatch(message) {
    if (!message || typeof message !== "object" || typeof message.type !== "string") return;
    const name = `on${message.type.charAt(0).toUpperCase()}${message.type.slice(1)}`;
    const handler = this.handlers[name];
    if (typeof handler === "function") handler(message);
  }

  _scheduleReconnect() {
    if (this.closed) return;
    const delay = RECONNECT_DELAYS[Math.min(this._attempt, RECONNECT_DELAYS.length - 1)];
    this._attempt += 1;
    this.handlers.onStatus?.("reconnecting");
    if (this._timer) clearTimeout(this._timer);
    this._timer = setTimeout(() => {
      this._timer = 0;
      this._open();
    }, delay);
  }

  _send(payload) {
    if (!this.connected) return false;
    try {
      this.socket.send(JSON.stringify(payload));
      return true;
    } catch (error) {
      return false;
    }
  }

  /** Position updates are throttled so we never flood the server. */
  sendMove(x, y, z, yaw) {
    const now = performance.now();
    if (now - this._lastMoveAt < MOVE_INTERVAL_MS) return false;
    this._lastMoveAt = now;
    this._pending = { type: "move", x, y, z, yaw };
    return this._send(this._pending);
  }

  /** Ask the server to run a heist for everyone in this city. */
  sendHeist() {
    return this._send({ type: "heist" });
  }

  sendChat(text) {
    const trimmed = (text || "").trim().slice(0, 160);
    if (!trimmed) return false;
    return this._send({ type: "chat", text: trimmed });
  }

  close() {
    this.closed = true;
    if (this._timer) clearTimeout(this._timer);
    this._timer = 0;
    if (this.socket) {
      try {
        this.socket.close();
      } catch (error) {
        // Already gone; nothing to clean up.
      }
      this.socket = null;
    }
    this.handlers.onStatus?.("offline");
  }
}
