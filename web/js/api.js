// Thin fetch wrapper around the FastAPI backend.
const TOKEN_KEY = "sjp.token";

export const getToken = () => localStorage.getItem(TOKEN_KEY) || "";
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

async function request(path, { method = "GET", body, auth = true } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (auth) {
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;
  }

  let response;
  try {
    response = await fetch(path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    const error = new Error("Cannot reach the game server. Check your connection.");
    error.cause = cause;
    throw error;
  }

  let data = null;
  try {
    data = await response.json();
  } catch {
    /* empty or non-JSON body */
  }

  if (!response.ok) {
    const detail = data && (data.detail || data.message);
    const message =
      typeof detail === "string" && detail
        ? detail
        : `Request failed (HTTP ${response.status})`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  return data;
}

export const api = {
  health: () => request("/api/health", { auth: false }),
  register: (username, password) =>
    request("/api/register", { method: "POST", auth: false, body: { username, password } }),
  login: (username, password) =>
    request("/api/login", { method: "POST", auth: false, body: { username, password } }),
  me: () => request("/api/me"),
  characters: () => request("/api/characters", { auth: false }),
  presets: () => request("/api/presets", { auth: false }),
  cities: () => request("/api/cities", { auth: false }),
  createCity: (name, preset, isPublic) =>
    request("/api/cities", {
      method: "POST",
      body: { name, preset, is_public: Boolean(isPublic) },
    }),
  joinCity: (code) => request("/api/cities/join", { method: "POST", body: { code } }),
  selectCharacter: (characterId) =>
    request("/api/character/select", { method: "POST", body: { character_id: characterId } }),
  shop: () => request("/api/shop"),
  buy: (itemId) => request("/api/shop/buy", { method: "POST", body: { item_id: itemId } }),
  inventory: () => request("/api/inventory"),
  house: () => request("/api/house"),
  saveHouse: (house) => request("/api/house", { method: "POST", body: house }),
  jobs: () => request("/api/jobs"),
  acceptJob: (jobId) => request("/api/jobs/accept", { method: "POST", body: { job_id: jobId } }),
  workShift: () => request("/api/jobs/work", { method: "POST" }),
  casino: () => request("/api/casino"),
  playCasino: (game, bet, choice) =>
    request("/api/casino/play", { method: "POST", body: { game, bet, choice } }),
};
