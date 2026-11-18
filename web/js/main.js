// Screen flow: login -> city lobby -> character select -> 3D world.
import { api, getToken, setToken, clearToken } from "./api.js";
import { buildCity } from "./city.js";
import { World } from "./world.js";
import { CitySocket } from "./net.js";
import { Phone } from "./phone.js";
import { HeistCutscene } from "./cutscene.js";

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
  net: null,
  online: 1,
  netStatus: "offline",
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
  if (!select.options.length) {
    for (const preset of state.presets) {
      const option = document.createElement("option");
      option.value = preset.id;
      option.textContent = preset.name;
      select.appendChild(option);
    }
  }
  // Make sure a real preset is selected, never an empty value.
  if (!select.value && select.options.length) select.selectedIndex = 0;
}

$("create-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  $("lobby-error").textContent = "";
  const name = $("create-name").value.trim();
  const submit = $("create-form").querySelector('button[type="submit"]');

  // The lobby appears before the city/preset lists finish loading on slow
  // connections. Wait for them so we never submit an empty map preset.
  if (!state.presets.length) {
    await refreshLobby();
  }

  const preset = $("create-preset").value;
  if (!preset) {
    $("lobby-error").textContent =
      "Map presets are still loading — please try again in a moment.";
    return;
  }
  const isPublic = $("create-public").checked;

  submit.disabled = true;
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
  connectMultiplayer(code);
}

function stopWorld() {
  if (hudTimer) {
    clearInterval(hudTimer);
    hudTimer = 0;
  }
  state.net?.close();
  state.net = null;
  state.phone?.hide();
  cutscene?.stop();
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

function requestHeist() {
  if (!state.world) return;
  if (!state.net || !state.net.sendHeist()) {
    addChatLine({ system: true, text: "Not connected - the crew cannot be called." });
    return;
  }
  addChatLine({ system: true, text: "Calling the crew... the bank is on notice." });
}

$("btn-heist").addEventListener("click", requestHeist);

// Pointer lock hides the cursor, so a key works where a button click cannot.
window.addEventListener("keydown", (event) => {
  if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) return;
  const tag = (event.target && event.target.tagName ? event.target.tagName : "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return;
  if (event.key.toLowerCase() !== "h") return;
  if (!$("screen-world").classList.contains("active")) return;
  requestHeist();
});

$("btn-phone").addEventListener("click", () => {
  if (!state.phone || !state.layout || !state.world) return;
  state.phone.toggle(state.layout, state.world.getPlayerPosition());
});

$("btn-leave").addEventListener("click", async () => {
  stopWorld();
  await openLobby();
});

/* ---------------------------------------------------------------- heists */
let cutscene = null;

function initCutscene() {
  if (cutscene) return cutscene;
  cutscene = new HeistCutscene({
    overlay: $("cutscene"),
    canvas: $("cutscene-canvas"),
    subtitle: $("cutscene-subtitle"),
    title: $("cutscene-title"),
    result: $("cutscene-result"),
    flash: $("cutscene-flash"),
    skip: $("cutscene-skip"),
    onFinish: async (heist) => {
      state.world?.controls?.setEnabled(true);
      if (!isTouch) $("lock-overlay")?.classList.add("visible");
      if (heist) {
        addChatLine({
          system: true,
          text: heist.success
            ? `Heist clean - the crew walked out with ${Number(heist.loot).toLocaleString()} each.`
            : `Heist blown - ${Number(heist.fine).toLocaleString()} fine and ${heist.lockup_seconds}s in lockup.`,
        });
      }
      await refreshAccount();
    },
  });
  return cutscene;
}

async function refreshAccount() {
  try {
    const me = await api.me();
    if (me && me.account) {
      state.account = me.account;
      updateHud();
    }
  } catch (error) {
    // A stale HUD beats a broken screen; the next refresh corrects it.
  }
}

function playHeist(heist) {
  if (!heist || !state.world) return;
  const player = initCutscene();
  state.phone?.hide();
  state.world.controls?.setEnabled(false);
  $("lock-overlay")?.classList.remove("visible");
  if (!player.play(heist)) {
    state.world.controls?.setEnabled(true);
    if (!isTouch) $("lock-overlay")?.classList.add("visible");
  }
}

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

  if (state.world && state.net) {
    // Tell the other players in this city where we are.
    const position = state.world.getPlayerPosition();
    state.net.sendMove(position.x, position.y, position.z, state.world.getPlayerYaw());
  }
}

/* ----------------------------------------------------------- multiplayer */
function connectMultiplayer(code) {
  state.net?.close();
  state.online = 1;
  state.netStatus = "connecting";
  updateOnlineHud();
  initChat();

  state.net = new CitySocket({
    onStatus: (status) => {
      state.netStatus = status;
      updateOnlineHud();
    },
    onWelcome: (message) => {
      state.online = message.online || 1;
      state.world?.clearRemotePlayers();
      for (const player of message.players || []) {
        state.world?.addRemotePlayer({
          username: player.username,
          characterId: player.character_id,
        });
        state.world?.updateRemotePlayer(player);
      }
      updateOnlineHud();
    },
    onJoin: (message) => {
      const player = message.player || {};
      state.online = message.online || state.online;
      state.world?.addRemotePlayer({
        username: player.username,
        characterId: player.character_id,
      });
      state.world?.updateRemotePlayer(player);
      updateOnlineHud();
      if (player.username) {
        addChatLine({ system: true, text: `${player.username} joined the city` });
      }
    },
    onLeave: (message) => {
      state.online = message.online || 1;
      state.world?.removeRemotePlayer(message.username);
      updateOnlineHud();
      if (message.username) {
        addChatLine({ system: true, text: `${message.username} left the city` });
      }
    },
    onMove: (message) => {
      state.world?.updateRemotePlayer(message.player || {});
    },
    onHeist: (message) => {
      playHeist(message.heist);
    },
    onHeistError: (message) => {
      addChatLine({
        system: true,
        text: message.message || "The heist could not start.",
      });
    },
    onChat: (message) => {
      addChatLine({ username: message.username, text: message.text });
    },
  });

  state.net.connect(code);
}

function updateOnlineHud() {
  const element = $("hud-net");
  if (!element) return;
  if (state.netStatus === "online") {
    element.textContent = `${state.online} online`;
  } else if (state.netStatus === "connecting") {
    element.textContent = "connecting…";
  } else if (state.netStatus === "reconnecting") {
    element.textContent = "reconnecting…";
  } else if (state.netStatus === "unauthorized") {
    element.textContent = "signed out";
  } else {
    element.textContent = "offline";
  }
}

// Chat text is inserted with textContent, never innerHTML, so a player cannot
// inject HTML into everyone else's screen.
function addChatLine({ username, text, system } = {}) {
  const log = $("chat-log");
  if (!log) return;

  const line = document.createElement("div");
  line.className = system ? "chat-line system" : "chat-line";
  if (system) {
    line.textContent = text;
  } else {
    const who = document.createElement("strong");
    who.textContent = `${username}: `;
    line.append(who, document.createTextNode(text));
  }

  log.appendChild(line);
  while (log.children.length > 6) log.removeChild(log.firstChild);
  log.scrollTop = log.scrollHeight;
}

let chatWired = false;
function initChat() {
  if (chatWired) return;
  chatWired = true;

  $("chat-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = $("chat-input");
    const text = input.value;
    input.value = "";
    input.blur();
    if (!text.trim()) return;
    if (!state.net || !state.net.sendChat(text)) {
      addChatLine({ system: true, text: "Not connected — message not sent." });
    }
  });

  $("chat-input").addEventListener("click", () => document.exitPointerLock?.());
  $("chat-input").addEventListener("keydown", (event) => {
    if (event.code === "Escape") {
      event.stopPropagation();
      $("chat-input").blur();
    }
  });

  // Pressing T opens chat without leaving the 3D world.
  document.addEventListener("keydown", (event) => {
    if (event.code !== "KeyT" || event.ctrlKey || event.metaKey || event.altKey) return;
    if (!$("screen-world").classList.contains("active")) return;
    const input = $("chat-input");
    if (document.activeElement === input) return;
    event.preventDefault();
    document.exitPointerLock?.();
    input.focus();
  });
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

// ---------------------------------------------------------------------------
// Stage 4a: world interaction (E / tap), shop, bag and the starter house
// ---------------------------------------------------------------------------
const TOUCH_DEVICE = window.matchMedia("(pointer: coarse)").matches;

function worldPois() {
  const layout = state.world && state.world.layout ? state.world.layout : null;
  return layout && Array.isArray(layout.pois) ? layout.pois : [];
}

function housePoi() {
  return worldPois().find((poi) => poi.id === "house") || null;
}

function activePanel() {
  return document.querySelector(".panel-overlay.open");
}

function setPrompt(text) {
  const prompt = $("interact-prompt");
  const label = $("interact-label");
  if (!prompt || !label) return;
  if (!text) {
    prompt.classList.remove("visible");
    return;
  }
  label.textContent = text;
  prompt.classList.add("visible");
}

// Returns the POI the player can currently use (or null) so interact() acts on
// the same target the on-screen prompt is describing.
function updateInteractionPrompt() {
  if (!state.world || !state.world.running || activePanel()) {
    state.nearPoi = null;
    setPrompt("");
    return null;
  }
  if (state.world.insideInterior) {
    state.nearPoi = null;
    setPrompt("Leave your house");
    return null;
  }
  const position = state.world.getPlayerPosition();
  let nearest = null;
  let bestSq = Infinity;
  for (const poi of worldPois()) {
    const dx = poi.x - position.x;
    const dz = poi.z - position.z;
    const distanceSq = dx * dx + dz * dz;
    if (distanceSq <= poi.radius * poi.radius && distanceSq < bestSq) {
      nearest = poi;
      bestSq = distanceSq;
    }
  }
  state.nearPoi = nearest;
  setPrompt(nearest ? nearest.label : "");
  return nearest;
}

async function interact() {
  if (!state.world || !state.world.running) return;
  if (state.world.insideInterior) {
    leaveHouse();
    return;
  }
  const poi = updateInteractionPrompt() || state.nearPoi;
  if (!poi) return;
  if (poi.kind === "house") await enterHouse();
  else if (poi.kind === "shop") await openShop();
  else if (poi.kind === "casino") {
    addChatLine({ system: true, text: "The casino tables open in the next stage." });
  }
}

async function enterHouse() {
  try {
    const data = await api.house();
    state.house = data.house;
    if (!state.world.enterInterior(state.house)) {
      addChatLine({ system: true, text: "Could not open your house. Try again in a moment." });
      return;
    }
    addChatLine({ system: true, text: "Home sweet home. Press I to decorate." });
    updateInteractionPrompt();
  } catch (error) {
    addChatLine({ system: true, text: error.message });
  }
}

function leaveHouse() {
  if (!state.world || !state.world.insideInterior) return;
  state.world.exitInterior(housePoi());
  addChatLine({ system: true, text: "Back on the street." });
  updateInteractionPrompt();
}

function openPanel(id) {
  const panel = $(id);
  if (!panel) return;
  panel.classList.add("open");
  document.body.classList.add("panel-open");
  if (state.world && state.world.controls) state.world.controls.setEnabled(false);
  const overlay = $("lock-overlay");
  if (overlay) overlay.classList.remove("visible");
  setPrompt("");
}

function closePanels() {
  document.querySelectorAll(".panel-overlay.open").forEach((panel) => panel.classList.remove("open"));
  document.body.classList.remove("panel-open");
  if (state.world && state.world.controls) state.world.controls.setEnabled(true);
  updateInteractionPrompt();
}

async function openShop() {
  try {
    renderShop(await api.shop());
    openPanel("panel-shop");
  } catch (error) {
    addChatLine({ system: true, text: error.message });
  }
}

function renderShop(data) {
  const list = $("shop-list");
  if (!list) return;
  const balance = $("shop-balance");
  if (balance) balance.textContent = `Cash ₹${Number(data.fampay).toLocaleString("en-IN")}`;
  const errorBox = $("shop-error");
  if (errorBox) errorBox.textContent = "";
  list.innerHTML = "";

  for (const section of data.sections) {
    const title = document.createElement("div");
    title.className = "shop-section-title";
    title.textContent = section.title;
    list.appendChild(title);

    for (const item of section.items) {
      const row = document.createElement("div");
      row.className = "shop-row";

      const name = document.createElement("div");
      name.className = "shop-name";
      name.textContent = item.name;

      const desc = document.createElement("div");
      desc.className = "shop-desc";
      desc.textContent = item.desc || "";

      const meta = document.createElement("div");
      meta.className = "shop-meta";
      const price = document.createElement("span");
      price.textContent = `₹${Number(item.price).toLocaleString("en-IN")}`;
      const owned = document.createElement("span");
      owned.textContent = item.owned > 0 ? `owned ${item.owned}` : item.category;
      meta.append(price, owned);

      const button = document.createElement("button");
      button.type = "button";
      button.className = "pill shop-buy";
      const affordable = item.price <= data.fampay;
      button.textContent = affordable ? "Buy" : "Need cash";
      button.disabled = !affordable;
      button.addEventListener("click", () => buyItem(item.id));

      row.append(name, desc, meta, button);
      list.appendChild(row);
    }
  }
}

async function buyItem(itemId) {
  const errorBox = $("shop-error");
  if (errorBox) errorBox.textContent = "";
  try {
    const result = await api.buy(itemId);
    if (result.account) state.account = result.account;
    updateHud();
    addChatLine({
      system: true,
      text: `Bought ${result.purchase.item.name} for ₹${Number(
        result.purchase.item.price,
      ).toLocaleString("en-IN")}.`,
    });
    renderShop(await api.shop());
    if (state.world && state.world.insideInterior) await refreshHouseInterior();
  } catch (error) {
    if (errorBox) errorBox.textContent = error.message;
  }
}

async function refreshHouseInterior() {
  try {
    const data = await api.house();
    state.house = data.house;
    if (state.world && state.world.insideInterior) state.world.enterInterior(state.house);
  } catch (error) {
    addChatLine({ system: true, text: error.message });
  }
}

async function openInventory() {
  try {
    const [inventory, house] = await Promise.all([api.inventory(), api.house()]);
    state.house = house.house;
    renderInventory(inventory.inventory);
    openPanel("panel-inventory");
  } catch (error) {
    addChatLine({ system: true, text: error.message });
  }
}

function swatchButton(entry, selected, onPick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `swatch${selected ? " selected" : ""}`;
  button.style.background = entry.color;
  button.title = entry.name;
  button.setAttribute("aria-label", entry.name);
  button.addEventListener("click", onPick);
  return button;
}

function renderInventory(data) {
  const house = state.house || { walls: [], floors: [], furniture: [], wall: "", floor: "" };

  const walls = $("house-walls");
  if (walls) {
    walls.innerHTML = "";
    for (const entry of house.walls || []) {
      walls.appendChild(
        swatchButton(entry, entry.id === house.wall, () => applyHouse({ wall: entry.id })),
      );
    }
  }

  const floors = $("house-floors");
  if (floors) {
    floors.innerHTML = "";
    for (const entry of house.floors || []) {
      floors.appendChild(
        swatchButton(entry, entry.id === house.floor, () => applyHouse({ floor: entry.id })),
      );
    }
  }

  const list = $("inventory-list");
  if (!list) return;
  list.innerHTML = "";

  if (!data.items.length) {
    const empty = document.createElement("div");
    empty.className = "panel-empty";
    empty.textContent = "Nothing yet. Visit the shop and buy something.";
    list.appendChild(empty);
    return;
  }

  for (const item of data.items) {
    const row = document.createElement("div");
    row.className = "shop-row";

    const name = document.createElement("div");
    name.className = "shop-name";
    name.textContent = `${item.name} ×${item.count}`;

    const desc = document.createElement("div");
    desc.className = "shop-desc";
    desc.textContent = item.desc || "";

    const meta = document.createElement("div");
    meta.className = "shop-meta";
    const value = document.createElement("span");
    value.textContent = `worth ₹${Number(item.price * item.count).toLocaleString("en-IN")}`;
    meta.appendChild(value);

    row.append(name, desc, meta);

    if (item.kind === "furniture") {
      const placed = (house.furniture || []).includes(item.id);
      const button = document.createElement("button");
      button.type = "button";
      button.className = `pill shop-buy${placed ? " active" : ""}`;
      button.textContent = placed ? "Placed" : "Place";
      button.addEventListener("click", () => toggleFurniture(item.id));
      row.appendChild(button);
    }

    list.appendChild(row);
  }
}

async function toggleFurniture(itemId) {
  const house = state.house;
  if (!house) return;
  const current = house.furniture || [];
  const next = current.includes(itemId)
    ? current.filter((id) => id !== itemId)
    : [...current, itemId];
  await applyHouse({ furniture: next });
}

async function applyHouse(patch) {
  const house = state.house || {};
  const errorBox = $("shop-error");
  if (errorBox) errorBox.textContent = "";
  try {
    const data = await api.saveHouse({
      wall: patch.wall || house.wall,
      floor: patch.floor || house.floor,
      furniture: patch.furniture || house.furniture || [],
    });
    state.house = data.house;
    if (state.world && state.world.insideInterior) state.world.enterInterior(state.house);
    const inventory = await api.inventory();
    renderInventory(inventory.inventory);
  } catch (error) {
    if (errorBox) errorBox.textContent = error.message;
  }
}

const interactPromptEl = $("interact-prompt");
if (interactPromptEl) interactPromptEl.addEventListener("click", interact);

// The "Click to play" card is the only clickable part of the lock overlay, so it
// must actually start mouse look (the overlay itself ignores pointer events).
const lockCard = document.querySelector("#lock-overlay .lock-card");
if (lockCard) {
  lockCard.addEventListener("click", () => {
    if (state.world && state.world.controls) state.world.controls.requestLock();
  });
}
const bagButton = $("btn-bag");
if (bagButton) bagButton.addEventListener("click", openInventory);
const shopClose = $("shop-close");
if (shopClose) shopClose.addEventListener("click", closePanels);
const inventoryClose = $("inventory-close");
if (inventoryClose) inventoryClose.addEventListener("click", closePanels);

document.querySelectorAll(".panel-overlay").forEach((panel) => {
  panel.addEventListener("click", (event) => {
    if (event.target === panel) closePanels();
  });
});

window.addEventListener("keydown", (event) => {
  if (event.repeat || event.metaKey || event.ctrlKey || event.altKey) return;
  const tag = (event.target && event.target.tagName ? event.target.tagName : "").toLowerCase();
  if (tag === "input" || tag === "textarea" || tag === "select") return;
  const worldScreen = $("screen-world");
  if (!worldScreen || !worldScreen.classList.contains("active")) return;

  if (event.code === "KeyE") {
    event.preventDefault();
    interact();
    return;
  }
  if (event.code === "KeyI") {
    event.preventDefault();
    if (activePanel()) closePanels();
    else openInventory();
    return;
  }
  if (event.code === "Escape" && activePanel()) closePanels();
});

setInterval(updateInteractionPrompt, 220);
