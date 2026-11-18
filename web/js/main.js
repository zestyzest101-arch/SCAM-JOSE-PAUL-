// Screen flow: login -> city lobby -> character select -> 3D world.
import { api, getToken, setToken, clearToken } from "./api.js";
import { buildCity } from "./city.js";
import { World } from "./world.js";
import { Phone } from "./phone.js";

const $ = (id) => document.getElementById(id);
const isTouch =
  window.matchMedia("(pointer: coarse)").matches || "ontouchstart" in window;

const state = {
  username: "",
  account: null,
  cities: [],
  presets: [],
  characters: [],
  layout: null,
  world: null,
  phone: null,
  waypoint: null,
  authMode: "login",
};

let hudTimer = 0;

function showScreen(name) {
  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.toggle("active", screen.id === `screen-${name}`);
  });
}

/* ------------------------------------------------------------------ auth */
function setAuthMode(mode) {
  state.authMode = mode;
  $("tab-login").classList.toggle("active", mode === "login");
  $("tab-register").classList.toggle("active", mode === "register");
  $("auth-submit").textContent = mode === "login" ? "Log in" : "Create account";
  $("auth-password").autocomplete = mode === "login" ? "current-password" : "new-password";
  $("auth-error").textContent = "";
}

$("tab-login").addEventListener("click", () => setAuthMode("login"));
$("tab-register").addEventListener("click", () => setAuthMode("register"));

$("auth-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("auth-error").textContent = "";
  $("auth-submit").disabled = true;
  const username = $("auth-username").value.trim();
  const password = $("auth-password").value;

  try {
    const result =
      state.authMode === "register"
        ? await api.register(username, password)
        : await api.login(username, password);
    setToken(result.token);
    state.username = result.username;
    state.account = result.account;
    $("auth-password").value = "";
    await openLobby();
  } catch (error) {
    $("auth-error").textContent = error.message;
  } finally {
    $("auth-submit").disabled = false;
  }
});

$("logout").addEventListener("click", () => {
  clearToken();
  window.location.reload();
});

/* ----------------------------------------------------------------- lobby */
async function openLobby() {
  showScreen("lobby");
  $("lobby-username").textContent = state.username;
  await refreshLobby();
}

async function refreshLobby() {
  $("lobby-error").textContent = "";
  try {
    const [cities, presets] = await Promise.all([api.cities(), api.presets()]);
    state.cities = cities.cities || [];
    state.presets = presets.presets || [];
    renderCityList();
    renderPresetOptions();
    updateCityHeader();
  } catch (error) {
    $("lobby-error").textContent = error.message;
  }
}

function currentCity() {
  const code = state.account?.city;
  return state.cities.find((city) => city.code === code) || null;
}

function updateCityHeader() {
  const city = currentCity();
  const preset = state.presets.find((item) => item.id === state.account?.preset);
  const label = city?.name || preset?.name || "GLOBAL HUB";
  $("lobby-city-name").textContent = `${label} (${state.account?.city || "GLOBAL_HUB"})`;
  $("enter-city").textContent = state.account?.has_character ? "Enter city" : "Choose character";
}

function renderCityList() {
  const list = $("city-list");
  list.innerHTML = "";
  if (!state.cities.length) {
    list.innerHTML = '<p class="muted">No public cities yet — create the first one.</p>';
    return;
  }
  for (const city of state.cities) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "city-card";
    if (city.code === state.account?.city) button.classList.add("current");
    const preset = state.presets.find((item) => item.id === city.preset);
    button.innerHTML = `
      <span class="city-name">${city.name}</span>
      <span class="city-meta">${city.code} · ${preset ? preset.name : city.preset} · ${
      city.member_count
    } player${city.member_count === 1 ? "" : "s"}</span>`;
    button.addEventListener("click", () => joinCity(city.code));
    list.appendChild(button);
  }
}

function renderPresetOptions() {
  const select = $("create-preset");
  if (select.options.length) return;
  for (const preset of state.presets) {
    const option = document.createElement("option");
    option.value = preset.id;
    option.textContent = preset.name;
    select.appendChild(option);
  }
}

$("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("lobby-error").textContent = "";
  const name = $("create-name").value.trim();
  const preset = $("create-preset").value;
  const isPublic = $("create-public").checked;

  try {
    const result = await api.createCity(name, preset, isPublic);
    state.account.city = result.city.code;
    state.account.preset = result.city.preset;
    $("create-name").value = "";
    await refreshLobby();
    await enterCity();
  } catch (error) {
    $("lobby-error").textContent = error.message;
  }
});

$("join-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("lobby-error").textContent = "";
  const code = $("join-code").value.trim();
  try {
    await joinCity(code);
    $("join-code").value = "";
  } catch (error) {
    $("lobby-error").textContent = error.message;
  }
});

async function joinCity(code) {
  const result = await api.joinCity(code);
  state.account.city = result.city.code;
  state.account.preset = result.city.preset;
  await refreshLobby();
  await enterCity();
}

$("enter-city").addEventListener("click", () => enterCity());
$("change-character").addEventListener("click", () => openCharacterSelect());
$("character-back").addEventListener("click", () => openLobby());

/* ------------------------------------------------------------ characters */
async function enterCity() {
  if (!state.account) return;
  if (!state.account.has_character) {
    await openCharacterSelect();
    return;
  }
  startWorld();
}

async function openCharacterSelect() {
  showScreen("character");
  $("character-error").textContent = "";

  if (!state.characters.length) {
    try {
      const data = await api.characters();
      state.characters = data.characters || [];
    } catch (error) {
      $("character-error").textContent = error.message;
      return;
    }
  }
  renderCharacters();
}

function renderCharacters() {
  const grid = $("character-grid");
  grid.innerHTML = "";

  for (const character of state.characters) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "character-card";
    if (character.id === state.account?.character_id) card.classList.add("selected");
    card.innerHTML = `
      <img src="/${character.portrait}" alt="${character.name}" loading="lazy" />
      <span class="character-body">
        <span class="character-name">${character.name}</span>
        <span class="character-tagline">${character.tagline}</span>
        <span class="character-perk">${character.perk}</span>
        <span class="character-ability">${character.ability}</span>
      </span>`;
    card.addEventListener("click", () => selectCharacter(character.id));
    grid.appendChild(card);
  }
}

async function selectCharacter(characterId) {
  $("character-error").textContent = "";
  try {
    const result = await api.selectCharacter(characterId);
    state.account = result.account;
    startWorld();
  } catch (error) {
    $("character-error").textContent = error.message;
  }
}

/* ----------------------------------------------------------------- world */
function startWorld() {
  const preset = state.account?.preset || "egmore";
  const code = state.account?.city || "GLOBAL_HUB";
  const city = currentCity();
  const presetMeta = state.presets.find((item) => item.id === preset);
  const name = city?.name || presetMeta?.name || "City";

  state.layout = buildCity({ preset, code, name });
  state.waypoint = null;

  showScreen("world");
  updateHud();

  state.world = new World($("game"), {
    onLockChange: (locked) => {
      if (!isTouch) $("lock-overlay").classList.toggle("visible", !locked);
    },
    onError: (message) => {
      $("hint").textContent = message;
    },
  });

  const started = state.world.start(state.layout);
  if (!started) return;

  if (!state.phone) initPhone();
  state.phone.hide();
  $("lock-overlay").classList.toggle("visible", !isTouch);
  startHudLoop();
}

function stopWorld() {
  if (hudTimer) {
    clearInterval(hudTimer);
    hudTimer = 0;
  }
  state.phone?.hide();
  state.world?.stop();
  state.world = null;
}

function initPhone() {
  state.phone = new Phone({
    root: $("phone"),
    canvas: $("phone-map"),
    cityEl: $("phone-city"),
    closeButton: $("phone-close"),
    navigateButton: $("phone-navigate"),
    onNavigate: (waypoint) => {
      state.waypoint = waypoint;
    },
  });
}

$("btn-phone").addEventListener("click", () => {
  if (!state.phone || !state.layout || !state.world) return;
  state.phone.toggle(state.layout, state.world.getPlayerPosition());
});

$("btn-leave").addEventListener("click", async () => {
  stopWorld();
  await openLobby();
});

function startHudLoop() {
  if (hudTimer) clearInterval(hudTimer);
  hudTimer = setInterval(updateHud, 200);
}

function updateHud() {
  const account = state.account || {};
  $("hud-name").textContent = account.character_name || state.username.toUpperCase();
  $("hud-city").textContent = state.layout?.name || "City";
  $("hud-code").textContent = account.city || "GLOBAL_HUB";
  $("hud-level").textContent = account.level ?? 1;
  $("hud-money").textContent = Number(account.fampay ?? 0).toLocaleString();
  $("hud-bank").textContent = Number(account.bank ?? 0).toLocaleString();

  if (state.world && state.phone) {
    const position = state.world.getPlayerPosition();
    state.phone.update(position);
    updateWaypoint(position);
  }
}

function updateWaypoint(position) {
  const marker = $("waypoint");
  if (!state.waypoint) {
    marker.classList.remove("visible");
    return;
  }

  const dx = state.waypoint.x - position.x;
  const dz = state.waypoint.z - position.z;
  const yaw = state.world.getPlayerYaw();

  // Project the target into camera space so the arrow points on screen.
  const localX = dx * Math.cos(yaw) - dz * Math.sin(yaw);
  const localZ = -dx * Math.sin(yaw) - dz * Math.cos(yaw);
  const angle = Math.atan2(localX, localZ);

  $("waypoint-arrow").style.transform = `rotate(${angle}rad)`;
  $("waypoint-distance").textContent = `${Math.round(Math.hypot(dx, dz))} m`;
  marker.classList.add("visible");
}

/* ---------------------------------------------------------- touch input */
function initTouch() {
  if (!isTouch) return;
  document.body.classList.add("touch");

  const joystick = $("joystick");
  const knob = $("joystick-knob");
  const radius = 52;
  let activeId = null;
  let origin = { x: 0, y: 0 };

  const moveKnob = (clientX, clientY) => {
    const dx = clientX - origin.x;
    const dy = clientY - origin.y;
    const distance = Math.hypot(dx, dy) || 1;
    const clamped = Math.min(distance, radius);
    const nx = (dx / distance) * clamped;
    const ny = (dy / distance) * clamped;
    knob.style.transform = `translate(calc(-50% + ${nx}px), calc(-50% + ${ny}px))`;
    state.world?.controls?.setMove(nx / radius, ny / radius);
  };

  joystick.addEventListener("pointerdown", (event) => {
    activeId = event.pointerId;
    joystick.setPointerCapture(event.pointerId);
    const rect = joystick.getBoundingClientRect();
    origin = { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
    moveKnob(event.clientX, event.clientY);
  });

  joystick.addEventListener("pointermove", (event) => {
    if (activeId !== event.pointerId) return;
    moveKnob(event.clientX, event.clientY);
  });

  const endJoystick = (event) => {
    if (activeId !== event.pointerId) return;
    activeId = null;
    knob.style.transform = "translate(-50%, -50%)";
    state.world?.controls?.setMove(0, 0);
  };
  joystick.addEventListener("pointerup", endJoystick);
  joystick.addEventListener("pointercancel", endJoystick);

  // Drag on the right side of the world to look around.
  const host = $("game");
  let lookId = null;
  let last = { x: 0, y: 0 };

  host.addEventListener("pointerdown", (event) => {
    if (event.clientX < window.innerWidth * 0.4) return;
    lookId = event.pointerId;
    last = { x: event.clientX, y: event.clientY };
  });

  host.addEventListener("pointermove", (event) => {
    if (lookId !== event.pointerId) return;
    state.world?.controls?.addLook(event.clientX - last.x, event.clientY - last.y);
    last = { x: event.clientX, y: event.clientY };
  });

  const endLook = (event) => {
    if (lookId === event.pointerId) lookId = null;
  };
  host.addEventListener("pointerup", endLook);
  host.addEventListener("pointercancel", endLook);

  $("btn-jump").addEventListener("click", () => state.world?.controls?.jump());
}

/* ------------------------------------------------------------------ boot */
async function boot() {
  initTouch();
  setAuthMode("login");

  if (!getToken()) {
    showScreen("auth");
    return;
  }

  try {
    const me = await api.me();
    state.username = me.username;
    state.account = me.account;
    await openLobby();
  } catch {
    clearToken();
    showScreen("auth");
  }
}

boot();
