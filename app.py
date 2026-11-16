import contextlib
import io
import html
import json
import os
import random
import secrets
import time
from pathlib import Path

import streamlit as st
import game_core as core

# ============================================================
# SCAM JOSE PAUL — STREAMLIT WEB APP
# Replace the existing app.py with this file.
# Keep game_core.py and assets/characters/ unchanged.
# ============================================================

BASE = Path(__file__).parent
DATA_DIR = BASE / "data"
DATA_FILE = DATA_DIR / "scam_jose_paul_save.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)
core.DATA_FILE = str(DATA_FILE)

MAX_PLAYERS = 14
GLOBAL_ROOM = "GLOBAL_HUB"
CITY_PRESETS = list(core.CITIES.keys())

st.set_page_config(
    page_title="SCAM JOSE PAUL",
    page_icon="🪙",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&display=swap');

    :root { color-scheme: dark; }
    .stApp {
        background:
            radial-gradient(circle at 12% 0%, rgba(57,91,150,.30), transparent 32%),
            radial-gradient(circle at 90% 12%, rgba(113,63,153,.18), transparent 27%),
            linear-gradient(145deg, #0a0d14 0%, #101827 48%, #0b101a 100%);
        color: #f4f6fb;
        font-family: 'DM Sans', sans-serif;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111a2a 0%, #0c111b 100%);
        border-right: 1px solid rgba(148,163,184,.13);
    }
    .block-container { padding-top: 1.55rem; padding-bottom: 3rem; max-width: 1500px; }
    h1, h2, h3 { font-family: 'Space Grotesk', sans-serif !important; letter-spacing: -.4px; }
    h1 { font-weight: 700 !important; }
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, rgba(28,40,61,.96), rgba(18,27,43,.96));
        border: 1px solid rgba(148,163,184,.17);
        padding: 18px 18px 14px;
        border-radius: 17px;
        min-height: 112px;
        box-shadow: 0 8px 26px rgba(0,0,0,.13);
    }
    [data-testid="stMetricLabel"] { color: #aebbd0 !important; font-weight: 600; }
    [data-testid="stMetricValue"] { color: #ffffff !important; font-family: 'Space Grotesk', sans-serif; }
    .stButton > button, .stFormSubmitButton > button {
        min-height: 45px;
        border-radius: 12px;
        border: 1px solid rgba(148,163,184,.22);
        font-weight: 700;
        transition: .15s ease;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        border-color: #8aa9e8;
        transform: translateY(-1px);
    }
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        min-height: 48px;
        border-radius: 11px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: rgba(148,163,184,.19) !important;
        border-radius: 16px !important;
        background: rgba(19,29,46,.58);
    }
    .hero-card {
        padding: 22px 24px;
        border: 1px solid rgba(125,155,210,.24);
        border-radius: 19px;
        background: linear-gradient(120deg, rgba(36,55,86,.82), rgba(24,31,51,.78));
        margin-bottom: 18px;
    }
    .hero-kicker { color:#a9bddf; font-size: .78rem; font-weight:800; letter-spacing:2px; }
    .hero-title { font-family:'Space Grotesk',sans-serif; font-size: clamp(1.8rem,4vw,2.7rem); font-weight:800; line-height:1.08; margin-top:5px; }
    .hero-sub { color:#b6c2d5; margin-top:8px; }
    .command-shell {
        padding: 19px;
        border: 1px solid rgba(125,155,210,.24);
        border-radius: 18px;
        background: linear-gradient(145deg, rgba(22,34,54,.96), rgba(14,22,36,.96));
        box-shadow: 0 12px 35px rgba(0,0,0,.16);
    }
    .command-output {
        padding: 15px 17px;
        border-radius: 13px;
        background: rgba(5,10,18,.72);
        border: 1px solid rgba(148,163,184,.16);
        color: #e5edf9;
        line-height: 1.75;
        min-height: 145px;
        overflow-wrap: anywhere;
    }
    .muted-note { color:#9eacc1; font-size:.88rem; }
    .character-name { font-family:'Space Grotesk',sans-serif; font-weight:800; font-size:1.04rem; }
    .st-key-command_form label, .st-key-command_form input { font-size: .88rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------- CHARACTERS --------------------------
# INVINGOPPA remains character 13 (character_13.jpg).
CHARACTERS = [
    ("professor", "THE PROFESSOR", "Has 47 unfinished degrees and still asks Google how to boil water.", "Looking suspiciously intelligent."),
    ("heartbreaker", "THE HEARTBREAKER", "Joined the City to make money. Left with three friendship requests.", "Emotional damage."),
    ("uncle_jose", "UNCLE JOSE", "Retired businessman. Wanted in 4 neighbourhood WhatsApp groups.", "Unsolicited life advice."),
    ("sleeping_ceo", "THE SLEEPING CEO", "Runs a multinational corporation entirely from his bed.", "Maximum productivity, minimum movement."),
    ("og", "THE OG", "Been here since the tutorial. Still hasn't figured out the tutorial.", "Veteran confidence."),
    ("mystery_man", "THE MYSTERY MAN", "Nobody knows who he is. Not even his own profile picture.", "Classified information."),
    ("ancient_one", "THE ANCIENT ONE", "His account is older than the City's economy.", "Historical knowledge (questionable)."),
    ("hello_kitty_boss", "HELLO KITTY FINAL BOSS", "Cute appearance. The financial crimes department has opened a file.", "Unexpected chaos."),
    ("npc", "THE NPC", "Stares into the distance. Somehow owns a mansion.", "Random encounters."),
    ("cat_whisperer", "THE CAT WHISPERER", "Doesn't trust humans. Has a suspiciously large fish collection.", "Animal connections."),
    ("confused_citizen", "THE CONFUSED CITIZEN", "Entered Perambur looking for the supermarket. Has been missing for 3 days.", "Getting lost."),
    ("security_guard", "THE SECURITY GUARD", "Looks like he knows something. Refuses to elaborate.", "Intimidating presence."),
    ("invingoppa", "INVINGOPPA", "The bank clerk has arrived. Your loan application was rejected before you even opened it.", "Financial intimidation."),
    ("drip_lord", "THE DRIP LORD", "Spends 90% of his salary on accessories. 10% on rent.", "Fashion over finances."),
]


# -------------------------- DATA / SAVE --------------------------
def save(data):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = str(DATA_FILE) + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
    os.replace(temp_path, DATA_FILE)


def room_defaults(room):
    room.setdefault("host", "SYSTEM")
    room.setdefault("name", "Global Hub Egmore")
    room.setdefault("preset", "egmore")
    room.setdefault("is_public", False)
    room.setdefault("members", [])
    room.setdefault("heist", {"active": False, "contributions": {}})
    room.setdefault("started", True)
    room.setdefault("character_claims", {})
    room.setdefault("chat_messages", [])
    # Keep the first recorded owner of a character. Claims are deliberately
    # not removed when a member leaves the City.
    if not isinstance(room["character_claims"], dict):
        room["character_claims"] = {}
    return room


def load_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    data = core.load_all_data()
    data.setdefault("users", {})
    data.setdefault("rooms", {})

    if GLOBAL_ROOM not in data["rooms"]:
        data["rooms"][GLOBAL_ROOM] = {
            "host": "SYSTEM",
            "name": "Global Hub Egmore",
            "preset": "egmore",
            "is_public": True,
            "members": [],
            "heist": {"active": False, "contributions": {}},
            "started": True,
            "character_claims": {},
        }

    for code, room in list(data["rooms"].items()):
        room_defaults(room)
        if room.get("preset") not in core.CITIES:
            room["preset"] = "egmore"

    # Migrate older single-player saves into the Global Hub.
    legacy_names = [
        key for key, value in list(data.items())
        if isinstance(value, dict) and "wallet" in value and key not in ("users", "rooms")
    ]
    for name in legacy_names:
        old = data.pop(name)
        if name not in data["users"]:
            data["users"][name] = {
                "password_hash": core.hash_password(secrets.token_urlsafe(18)),
                "current_room": GLOBAL_ROOM,
                "room_profiles": {},
                "last_active": 0,
            }
        profile = core.get_default_room_profile("egmore")
        for key, value in old.items():
            if key == "wallet":
                profile["fampay"] = value
            elif key in profile:
                profile[key] = value
        data["users"][name].setdefault("room_profiles", {})[GLOBAL_ROOM] = profile
        data["users"][name]["current_room"] = GLOBAL_ROOM
        if name not in data["rooms"][GLOBAL_ROOM]["members"]:
            data["rooms"][GLOBAL_ROOM]["members"].append(name)

    # Give old accounts a safe default room pointer and ensure profile maps exist.
    for name, account in data["users"].items():
        account.setdefault("room_profiles", {})
        account.setdefault("last_active", 0)
        if "current_room" not in account:
            account["current_room"] = GLOBAL_ROOM
        code = account.get("current_room")
        if code and code not in data["rooms"]:
            account["current_room"] = None

    # Migrate existing character choices into permanent room claims.
    for code, room in data["rooms"].items():
        claims = room["character_claims"]
        for member in room["members"]:
            account = data["users"].get(member, {})
            profile = account.get("room_profiles", {}).get(code, {})
            char_id = profile.get("character_id")
            if char_id in {item[0] for item in CHARACTERS} and char_id not in claims:
                claims[char_id] = member
                profile["character_locked"] = True

    return data


def get_profile(data, username, room_code):
    return core.get_user_room_profile(data, username, room_code)


def get_current(data, username):
    account = data["users"][username]
    code = account.get("current_room")
    if not code or code not in data["rooms"]:
        return None, None, None, None, None
    room = data["rooms"][code]
    profile = get_profile(data, username, code)
    city_cfg = core.CITIES.get(room.get("preset", "egmore"), core.CITIES["egmore"])
    return account, room, profile, code, city_cfg


def add_log(message):
    """Keep compatibility with any older plain-text command log entries."""
    st.session_state.setdefault("command_log", [])
    st.session_state.command_log.append(str(message))


def add_command_result(command, lines, profile=None):
    """Store one complete interactive-console command/result block."""
    st.session_state.setdefault("command_log", [])
    entry = {"command": str(command), "lines": [str(line) for line in lines], "kind": "normal"}
    if command.strip().lower().split()[:1] in (["bal"], ["balance"]):
        entry["kind"] = "balance"
        if profile is not None:
            job_name = core.JOBS.get(profile.get("job"), {}).get("name", profile.get("job", "None"))
            entry["balance"] = {
                "wallet": profile.get("fampay", 0),
                "bank": profile.get("bank", 0),
                "bank_max": profile.get("bank_max", 0),
                "level": profile.get("level", 0),
                "xp": profile.get("xp", 0),
                "xp_next": profile.get("level", 0) * 300,
                "job": job_name,
            }
    st.session_state.command_log.append(entry)


def add_chat_message(room, username, message, kind="user"):
    """Append a persistent City chat message to the room save data."""
    room.setdefault("chat_messages", []).append({
        "user": str(username),
        "message": str(message)[:1000],
        "kind": kind,
        "timestamp": time.time(),
    })


def make_room_code(data):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    code = "".join(random.choices(alphabet, k=6))
    while code in data["rooms"]:
        code = "".join(random.choices(alphabet, k=6))
    return code


def remove_member(data, username, room_code):
    room = data["rooms"].get(room_code)
    if room and username in room.get("members", []):
        room["members"].remove(username)
        # Permanent character claims intentionally remain in room data.
        if room.get("host") == username and room.get("members"):
            room["host"] = room["members"][0]


def move_user(data, username, destination_code):
    account = data["users"][username]
    old_code = account.get("current_room")
    if old_code and old_code in data["rooms"] and old_code != destination_code:
        remove_member(data, username, old_code)
    account["current_room"] = destination_code
    if destination_code:
        room = data["rooms"][destination_code]
        if username not in room["members"]:
            room["members"].append(username)
        get_profile(data, username, destination_code)


def create_city(data, username, city_name, preset):
    code = make_room_code(data)
    name = city_name.strip()[:35] or f"{username}'s City"
    data["rooms"][code] = {
        "host": username,
        "name": name,
        "preset": preset if preset in core.CITIES else "egmore",
        "is_public": False,
        "members": [],
        "heist": {"active": False, "contributions": {}},
        "started": False,
        "character_claims": {},
    }
    move_user(data, username, code)
    save(data)
    return code


def join_city(data, username, code):
    code = code.strip().upper()
    room = data["rooms"].get(code)
    if not room:
        return False, "That City code was not found."
    if username not in room["members"] and len(room["members"]) >= MAX_PLAYERS:
        return False, f"That City is full ({MAX_PLAYERS}/{MAX_PLAYERS})."
    move_user(data, username, code)
    save(data)
    return True, f"Joined {room.get('name', 'the City')} ({code})."


def character_picker(data, username, room_code, profile):
    room = data["rooms"][room_code]
    claims = room.setdefault("character_claims", {})
    current_id = profile.get("character_id")
    owner = claims.get(current_id) if current_id else None

    # If an old duplicate choice conflicts with a previously recorded claim,
    # require this account to choose a genuinely available character.
    if current_id and owner not in (None, username):
        profile.pop("character_id", None)
        profile.pop("character_name", None)
        profile["character_locked"] = False
        current_id = None

    # Restore a valid existing choice as a permanent claim.
    if current_id and owner in (None, username):
        claims[current_id] = username
        profile["character_locked"] = True
        save(data)
        return True

    # If this account already owns a permanent claim in this City, restore it
    # rather than allowing the account to claim a second character.
    previous_claim = next((key for key, owner_name in claims.items() if owner_name == username), None)
    if previous_claim:
        previous_character = next((item for item in CHARACTERS if item[0] == previous_claim), None)
        if previous_character:
            profile["character_id"] = previous_character[0]
            profile["character_name"] = previous_character[1]
            profile["character_locked"] = True
            save(data)
            return True

    st.markdown("## 🎭 Choose your character")
    st.caption("Choose carefully. A character is reserved permanently in this City, even if its player leaves.")
    st.caption(f"{len(claims)} of {len(CHARACTERS)} characters have already been claimed in this City.")
    cols = st.columns(3)
    for index, (key, name, description, speciality) in enumerate(CHARACTERS):
        claim_owner = claims.get(key)
        available = claim_owner is None or claim_owner == username
        with cols[index % 3]:
            with st.container(border=True):
                image_path = BASE / "assets" / "characters" / f"character_{index + 1:02d}.jpg"
                if image_path.exists():
                    st.image(str(image_path), use_container_width=True)
                st.markdown(f"**{name}**")
                st.caption(description)
                st.caption(f"Speciality: {speciality}")
                if not available:
                    st.button(
                        f"🔒 Taken by {claim_owner}",
                        key=f"taken_{room_code}_{key}",
                        disabled=True,
                        use_container_width=True,
                    )
                else:
                    if st.button(
                        "Select character",
                        key=f"pick_{room_code}_{key}",
                        type="primary",
                        use_container_width=True,
                    ):
                        # Recheck immediately before writing the claim.
                        latest_owner = room.setdefault("character_claims", {}).get(key)
                        if latest_owner not in (None, username):
                            st.error("Someone just claimed that character. Choose another one.")
                            st.rerun()
                        claims[key] = username
                        profile["character_id"] = key
                        profile["character_name"] = name
                        profile["character_locked"] = True
                        save(data)
                        st.rerun()
    return False


# -------------------------- ACCOUNT SCREENS --------------------------
def login_screen():
    st.markdown(
        "<div class='hero-card'><div class='hero-kicker'>WELCOME TO THE CITY</div>"
        "<div class='hero-title'>🪙 SCAM JOSE PAUL</div>"
        "<div class='hero-sub'>Build your balance. Find your people. Run your City.</div></div>",
        unsafe_allow_html=True,
    )
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        with st.container(border=True):
            mode = st.radio("ACCOUNT", ["Login", "Create account"], horizontal=True)
            username = st.text_input("Username", max_chars=24, placeholder="Choose a username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            if st.button("Continue", type="primary", use_container_width=True):
                if not username.strip() or not password:
                    st.error("Enter both a username and password.")
                else:
                    data = load_data()
                    name = username.strip()
                    if mode == "Create account":
                        if name in data["users"]:
                            st.error("That username is already taken.")
                        else:
                            data["users"][name] = {
                                "password_hash": core.hash_password(password),
                                "last_active": time.time(),
                                "current_room": None,
                                "room_profiles": {},
                            }
                            save(data)
                            st.session_state.user = name
                            st.session_state.command_log = []
                            st.rerun()
                    else:
                        account = data["users"].get(name)
                        if account and core.verify_password(account.get("password_hash", ""), password):
                            account["last_active"] = time.time()
                            save(data)
                            st.session_state.user = name
                            st.session_state.command_log = []
                            st.rerun()
                        else:
                            st.error("Incorrect username or password.")
    st.caption("Use a unique password. This is a game account, not a secure password manager.")


def lobby_screen(data, username, account, room_code=None):
    st.markdown(
        "<div class='hero-card'><div class='hero-kicker'>CITY NETWORK</div>"
        "<div class='hero-title'>🏙️ City Lobby</div>"
        "<div class='hero-sub'>Create a new City or join one with a Party Code.</div></div>",
        unsafe_allow_html=True,
    )

    if room_code and room_code in data["rooms"]:
        room = data["rooms"][room_code]
        room_defaults(room)
        st.subheader(f"🏙️ {room.get('name', 'Your City')}")
        st.write(f"**Party Code:** `{room_code}`")
        st.write(f"**Host:** {room.get('host', 'Unknown')}  ·  **Players:** {len(room['members'])}/{MAX_PLAYERS}")
        st.divider()
        if username == room.get("host"):
            st.markdown("### Host controls")
            with st.form(f"host_setup_{room_code}"):
                city_name = st.text_input(
                    "NAME YOUR CITY",
                    value=room.get("name", ""),
                    max_chars=35,
                    placeholder="Enter your City name...",
                )
                preset_keys = list(core.CITIES.keys())
                current_preset = room.get("preset", "egmore")
                default_index = preset_keys.index(current_preset) if current_preset in preset_keys else 0
                preset = st.selectbox(
                    "Choose the City's location preset",
                    options=preset_keys,
                    index=default_index,
                    format_func=lambda key: core.CITIES[key]["name"],
                )
                start = st.form_submit_button("🚀 START CITY", type="primary", use_container_width=True)
            if start:
                room["name"] = city_name.strip() or f"{username}'s City"
                room["preset"] = preset
                room["started"] = True
                save(data)
                st.success("Your City is live!")
                st.rerun()
            st.caption("Players can join while the City is running, until it reaches the 14-player limit.")
        else:
            st.info(f"Waiting for **{room.get('host', 'the host')}** to start this City.")
            if st.button("Leave this lobby", use_container_width=True):
                remove_member(data, username, room_code)
                account["current_room"] = None
                save(data)
                st.rerun()

        st.markdown("### 👥 Players in this lobby")
        for member in room["members"]:
            st.write(f"• {member}" + ("  ·  Host" if member == room.get("host") else ""))
        return

    create_col, join_col = st.columns(2)
    with create_col:
        with st.container(border=True):
            st.subheader("✨ Create a City")
            with st.form("create_city_form"):
                new_city_name = st.text_input("City name", max_chars=35, placeholder="e.g. The Jose Empire")
                new_preset = st.selectbox(
                    "Location preset",
                    options=list(core.CITIES.keys()),
                    format_func=lambda key: core.CITIES[key]["name"],
                )
                create = st.form_submit_button("CREATE CITY", type="primary", use_container_width=True)
            if create:
                code = create_city(data, username, new_city_name, new_preset)
                st.session_state.last_created_code = code
                st.rerun()
    with join_col:
        with st.container(border=True):
            st.subheader("🔑 Join a City")
            with st.form("join_city_form"):
                party_code = st.text_input("Party Code", max_chars=6, placeholder="Enter 6-character code").strip().upper()
                join = st.form_submit_button("JOIN CITY", type="primary", use_container_width=True)
            if join:
                ok, message = join_city(data, username, party_code)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    if st.session_state.get("last_created_code"):
        st.success(f"Your City was created. Party Code: {st.session_state.last_created_code}")

    st.divider()
    st.subheader("🌐 Available Cities")
    available = [
        (code, room) for code, room in data["rooms"].items()
        if code != GLOBAL_ROOM and room.get("started", True)
    ]
    if not available:
        st.caption("No public City listings yet. Join using a Party Code from the host.")
    else:
        for code, room in available:
            c1, c2, c3 = st.columns([2.4, 1, 1])
            c1.write(f"**{room.get('name', 'Unnamed City')}**")
            c2.caption(f"{len(room.get('members', []))}/{MAX_PLAYERS} players")
            if c3.button("Join", key=f"quick_join_{code}", disabled=len(room.get("members", [])) >= MAX_PLAYERS):
                ok, message = join_city(data, username, code)
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)


# -------------------------- JOB / MAIL / MINI-GAME HELPERS --------------------------
JOB_GRACE_SECONDS = 24 * 60 * 60
JOB_REMINDER_SECONDS = 20 * 60 * 60
WORK_COOLDOWN_SECONDS = 60 * 60
CRYPTO_START_PRICE = 125


def add_mail(profile, subject, body, mail_type="notice"):
    mailbox = profile.setdefault("mailbox", [])
    mailbox.append({"subject": str(subject), "body": str(body), "type": mail_type,
                    "timestamp": time.time(), "read": False})
    profile["mailbox"] = mailbox[-50:]


def refresh_job_status(profile):
    """Issue an inbox reminder at 20h and fire an inactive employee at 24h."""
    changed = False
    job_key = profile.get("job")
    if not job_key or job_key == "unemployed":
        return changed
    now = time.time()
    last_work = profile.get("last_work")
    if not last_work:
        profile["last_work"] = now
        profile["work_reminder_sent"] = False
        return True
    elapsed = now - float(last_work)
    if elapsed >= JOB_GRACE_SECONDS:
        old_job = core.JOBS.get(job_key, {}).get("name", job_key)
        add_mail(profile, "EMPLOYMENT TERMINATED", f"You were fired from {old_job} because you missed the 24-hour work deadline. Apply for a new job to get back on the payroll.", "fired")
        profile["job"] = "unemployed"
        profile["last_work"] = 0
        profile["work_reminder_sent"] = False
        changed = True
    elif elapsed >= JOB_REMINDER_SECONDS and not profile.get("work_reminder_sent", False):
        job_name = core.JOBS.get(job_key, {}).get("name", job_key)
        remaining = max(0, int(JOB_GRACE_SECONDS - elapsed))
        add_mail(profile, "SHIFT REMINDER", f"Reminder: complete `work` within {remaining // 3600}h {(remaining % 3600) // 60}m or you will be fired from {job_name}.", "reminder")
        profile["work_reminder_sent"] = True
        changed = True
    return changed


CASINO_GAMES = {
    "coinflip": "Coinflip — call heads or tails (automatic random call)",
    "dice": "Dice — roll a six; high multiplier, low odds",
    "slots": "Slots — match symbols for a payout",
    "roulette": "Roulette — land on the lucky number",
    "blackjack": "Blackjack — simplified draw against the dealer",
    "highlow": "High-Low — guess whether the next card is higher",
    "wheel": "Prize Wheel — spin for a multiplier",
    "scratch": "Scratch Card — reveal a prize tier",
    "rps": "Rock-Paper-Scissors — play against the house",
    "horse": "Horse Race — pick the winning racer automatically",
    "cups": "Shell Cups — find the hidden token",
    "plinko": "Plinko — drop a token through the board",
    "lottery": "Lucky Draw — rare jackpot chance",
    "mines": "Crystal Grid — find the safe crystal",
    "baccarat": "Baccarat — simplified player/banker draw",
}


def casino_result(game):
    """Return (multiplier, explanation). Multiplier is gross return, not profit."""
    if game == "coinflip":
        win = random.choice([True, False])
        return (1.9 if win else 0), ("The coin landed on your side." if win else "The coin landed the other way.")
    if game == "dice":
        roll = random.randint(1, 6)
        return (5 if roll == 6 else 0), f"You rolled {roll}."
    if game == "slots":
        symbols = [random.choice(["🍒", "🍋", "🔔", "💎", "7️⃣"]) for _ in range(3)]
        if len(set(symbols)) == 1:
            return (12 if symbols[0] == "7️⃣" else 7), "Slot result: " + " | ".join(symbols) + " — triple match!"
        if len(set(symbols)) == 2:
            return 1.8, "Slot result: " + " | ".join(symbols) + " — pair match!"
        return 0, "Slot result: " + " | ".join(symbols) + " — no match."
    if game == "roulette":
        number = random.randint(0, 17)
        return (14 if number == 7 else 0), f"Roulette landed on {number}. Lucky number: 7."
    if game == "blackjack":
        player, dealer = random.randint(15, 22), random.randint(15, 22)
        won = player <= 21 and (dealer > 21 or player > dealer)
        push = player == dealer or (player > 21 and dealer > 21)
        return (2 if won else 1 if push else 0), f"Your total: {player} · Dealer: {dealer}."
    if game == "highlow":
        first, second = random.randint(1, 13), random.randint(1, 13)
        return (1.9 if second > first else 0), f"Card values: {first} → {second} (higher wins)."
    if game == "wheel":
        mult = random.choices([0, 1, 1.5, 2, 3, 5], weights=[25, 25, 20, 15, 10, 5])[0]
        return mult, f"The prize wheel stopped at {mult}x."
    if game == "scratch":
        mult = random.choices([0, 1, 2, 4, 8], weights=[55, 15, 18, 9, 3])[0]
        return mult, f"Your scratch card revealed a {mult}x prize."
    if game == "rps":
        return random.choice([(0, "The house won rock-paper-scissors."), (0, "The house won rock-paper-scissors."), (2, "You beat the house!")])
    if game == "horse":
        winner = random.randint(1, 5)
        return (4 if winner == 1 else 0), f"Horse #{winner} crossed the finish line first. Your lucky horse was #1."
    if game == "cups":
        cup = random.randint(1, 3)
        return (2.5 if cup == 1 else 0), f"The token was under cup #{cup}."
    if game == "plinko":
        mult = random.choices([0, 0.5, 1, 2, 4, 8], weights=[20, 20, 25, 20, 12, 3])[0]
        return mult, f"Your Plinko chip landed in the {mult}x slot."
    if game == "lottery":
        ticket = random.randint(1, 100)
        return (30 if ticket == 1 else 0), f"Lucky Draw ticket #{ticket:02d}. Jackpot number: 01."
    if game == "mines":
        safe = random.random() < 0.25
        return (4 if safe else 0), ("You found the hidden crystal!" if safe else "That tile was empty.")
    if game == "baccarat":
        player, banker = random.randint(0, 9), random.randint(0, 9)
        return (2 if player > banker else 1 if player == banker else 0), f"Player score: {player} · Banker score: {banker}."
    return 0, "Unknown game."


# -------------------------- COMMAND HANDLER --------------------------
def execute_command(data, username, room_code, room, profile, city_cfg, raw_command):
    parts = raw_command.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()
    args = parts[1:]
    out = []

    def say(message):
        out.append(str(message))

    def commit():
        save(data)

    if refresh_job_status(profile):
        save(data)

    if cmd == "help":
        say("╔══════════════════════════════════════════════════════╗")
        say("                 SCAM JOSE PAUL — HELP")
        say("╚══════════════════════════════════════════════════════╝")
        say("")
        say("💰 MONEY & BANKING")
        say("BAL / BALANCE — View wallet, bank, level, XP and job")
        say("DEPOSIT <amount> — Move FamPay into your bank")
        say("WITHDRAW <amount> — Take FamPay out of your bank")
        say("BANK_HEIST — Enter a fictional bank encounter")
        say("CLERKS — Meet the bank clerks and view clerk encounters")
        say("")
        say("🎰 CASINO — 15 VIRTUAL-COIN GAMES")
        say("Use: CASINO <game> <amount>  |  CASINO LIST")
        say("COINFLIP — Call the coin toss")
        say("DICE — Roll for a high-value result")
        say("SLOTS — Match the slot symbols")
        say("ROULETTE — Try your luck on the number wheel")
        say("BLACKJACK — Play a simplified hand against the dealer")
        say("HIGHLOW — Guess whether the next card is higher")
        say("WHEEL — Spin the prize wheel")
        say("SCRATCH — Reveal a scratch-card prize")
        say("RPS — Rock, Paper, Scissors against the house")
        say("HORSE — Pick a racer in the horse race")
        say("CUPS — Find the hidden token")
        say("PLINKO — Drop a chip through the board")
        say("LOTTERY — Try for the jackpot")
        say("MINES — Search the crystal grid")
        say("BACCARAT — Compare player and banker scores")
        say("All casino games use fictional FamPay only; no real-money deposits or cash-outs.")
        say("")
        say("📈 SIDE HUSTLES & CITY ACTIVITIES")
        say("SCAM_CALL — Play a fictional comedy call encounter")
        say("CRYPTO — Check the fictional market; CRYPTO BUY <units> / CRYPTO SELL <units>")
        say("TAX_FRAUD — Play the fictional tax-office risk challenge")
        say("CRIME — High-risk fictional crime run: big payout, mugging, or character death")
        say("ROB <username> — Attempt a City robbery")
        say("HEIST START — Start a group heist")
        say("HEIST CONTRIBUTE <amount> — Add to the heist pool")
        say("HEIST LAUNCH — Launch the group heist")
        say("")
        say("💼 JOBS & MAILBOX")
        say("JOBS — Browse available jobs")
        say("APPLY <job_id> — Apply for a job")
        say("WORK — Complete your shift and earn your pay")
        say("MAILBOX — Read job reminders and other notices")
        say("MAILBOX READ <number> — Mark a message as read")
        say("MAILBOX CLEAR — Clear read messages")
        say("Work before your deadline: missing the required work window means you are fired.")
        say("")
        say("🧭 EXPLORATION & COLLECTING")
        say("HUNT — Encounter wildlife and collect hunt drops")
        say("FISH — Catch fish and discover rare aquatic finds")
        say("DIG — Search underground for creatures and collectibles")
        say("DAILY — Claim your daily reward")
        say("BEG — Ask around for a small random reward")
        say("")
        say("🎒 ITEMS & INVENTORY")
        say("BAG / INV / INVENTORY — View items, loot and collectibles")
        say("SHOP — Browse the categorized store: Defense, Tools, Upgrades, Lootboxes, Collectibles")
        say("BUY <item> — Purchase an item")
        say("SELL <loot> [quantity] — Sell collected loot")
        say("")
        say("🏙️ CITY & PLAYER INFO")
        say("PLAYERS — View members in your current City")
        say("LEADERBOARD / LB — View the current City's leaderboard")
        say("REVIVE — Use an available revive option")
        say("EXIT — Leave the current session")
        say("")
        say("💡 Tip: HELP is the in-game feature directory. Explore a category to discover what your City has to offer!")

    elif cmd in ("balance", "bal"):
        job_name = core.JOBS.get(profile.get("job"), {}).get("name", profile.get("job", "None"))
        say(f"FamPay Balance: 🪙 {profile['fampay']:,}")
        say(f"FamPay Account: 🏦 {profile['bank']:,} / {profile['bank_max']:,}")
        say(f"Level: {profile['level']}  ·  XP: {profile['xp']}/{profile['level'] * 300}  ·  Job: {job_name}")

    elif cmd in ("bag", "inv", "inventory"):
        items = [f"{core.SHOP_ITEMS[key]['name']} x{qty}" for key, qty in profile["inventory"].items() if qty and key in core.SHOP_ITEMS]
        loot = [f"{core.LOOT_ITEMS[key]['name']} x{qty}" for key, qty in profile["loot"].items() if qty and key in core.LOOT_ITEMS]
        say("🎒 INVENTORY")
        say(", ".join(items + loot) if items or loot else "Your inventory is empty.")

    elif cmd == "shop":
        say("╔══════════════════════════════════════════════════════╗")
        say("                 🛒 FRESH 4 TODAY — SHOP")
        say("╚══════════════════════════════════════════════════════╝")
        grouped_items = {}
        for item_key, shop_item in core.SHOP_ITEMS.items():
            grouped_items.setdefault(shop_item.get("category", "Miscellaneous"), []).append((item_key, shop_item))
        category_order = ["Defense", "Tool", "Upgrade", "Lootbox", "Collectible"]
        for category in category_order + [c for c in grouped_items if c not in category_order]:
            entries = grouped_items.get(category, [])
            if not entries:
                continue
            say("")
            say(f"━━━ {category.upper()} ━━━")
            for item_key, shop_item in entries:
                say(f"▸ {shop_item['name']}  —  {shop_item['price']:,} coins")
                say(f"  BUY KEY: {item_key}")
                if shop_item.get("desc"):
                    say(f"  {shop_item['desc']}")
        say("")
        say("Use BUY <item_key> to purchase. Your BAG shows what you own.")

    elif cmd == "buy" and args:
        key = args[0].lower()
        item = core.SHOP_ITEMS.get(key)
        if not item:
            say("Item not found. Type `shop`.")
        elif key == "sister_fahaana":
            say("This collectible cannot be purchased in this build.")
        elif profile["fampay"] < item["price"]:
            say("Not enough FamPay Balance.")
        else:
            profile["fampay"] -= item["price"]
            profile["inventory"][key] = profile["inventory"].get(key, 0) + 1
            say(f"Purchased {item['name']} for {item['price']:,} coins.")
            commit()

    elif cmd == "sell" and args:
        key = args[0].lower()
        try:
            qty = int(args[1]) if len(args) > 1 else 1
        except ValueError:
            qty = 0
        item = core.LOOT_ITEMS.get(key)
        if not item or qty < 1 or profile["loot"].get(key, 0) < qty:
            say("Invalid loot item or quantity.")
        else:
            earned = item["sell_price"] * qty
            profile["loot"][key] -= qty
            profile["fampay"] += earned
            say(f"Sold {qty}x {item['name']} for {earned:,} coins.")
            commit()

    elif cmd in ("deposit", "dep", "withdraw", "with") and args:
        try:
            amount = int(args[0])
        except ValueError:
            amount = 0
        if amount <= 0:
            say("Enter a positive amount.")
        elif cmd in ("deposit", "dep"):
            moved = min(amount, profile["fampay"], max(0, profile["bank_max"] - profile["bank"]))
            profile["fampay"] -= moved
            profile["bank"] += moved
            say(f"Deposited {moved:,} coins.")
            commit()
        else:
            moved = min(amount, profile["bank"])
            profile["bank"] -= moved
            profile["fampay"] += moved
            say(f"Withdrew {moved:,} coins.")
            commit()

    elif cmd == "jobs":
        say("💼 AVAILABLE JOBS")
        for key, job in core.JOBS.items():
            say(f"{key} — {job['name']} · Level {job['req_level']}+ · Pay {job['pay'][0]:,}–{job['pay'][1]:,}")
        say("Rule: complete at least one shift every 24 hours or you are automatically fired.")

    elif cmd == "apply" and args:
        key = args[0].lower()
        job = core.JOBS.get(key)
        if not job:
            say("Job not found. Type `jobs`.")
        elif profile["level"] < job["req_level"]:
            say(f"You need to reach level {job['req_level']} for this job.")
        else:
            profile["job"] = key
            profile["last_work"] = time.time()
            profile["work_reminder_sent"] = False
            add_mail(profile, "WELCOME TO THE TEAM", f"You have been hired as {job['name']}. Complete `work` at least once every 24 hours to keep this job.", "hiring")
            say(f"You are now a {job['name']}. Your 24-hour work timer has started.")
            commit()

    elif cmd == "work":
        if profile.get("dead"):
            say("You need to revive before working.")
        elif profile.get("job") in (None, "unemployed"):
            say("You are unemployed. Type `jobs`, then `apply <job_id>` to get hired.")
        else:
            last_work = float(profile.get("last_work", 0) or 0)
            remaining = WORK_COOLDOWN_SECONDS - (time.time() - last_work)
            if remaining > 0:
                say(f"You have already completed a shift recently. Next shift available in {int(remaining // 60)}m {int(remaining % 60)}s. Your job deadline is still 24 hours from your last completed shift.")
            else:
                job = core.JOBS.get(profile.get("job"), core.JOBS.get("moderator"))
                pay = int(random.randint(*job["pay"]) * city_cfg.get("pay_mult", 1))
                profile["fampay"] += pay
                profile["last_work"] = time.time()
                profile["work_reminder_sent"] = False
                core.add_xp(profile, 50)
                add_mail(profile, "SHIFT COMPLETED", f"Your shift as {job['name']} is complete. You earned {pay:,} coins and 50 XP. Your next work deadline is in 24 hours.", "payroll")
                say(f"Completed your shift as {job['name']}. Earned {pay:,} coins and 50 XP. Your 24-hour job timer has reset.")
                commit()

    elif cmd == "mailbox":
        mailbox = profile.setdefault("mailbox", [])
        sub = args[0].lower() if args else "list"
        if sub == "clear":
            before = len(mailbox)
            profile["mailbox"] = [mail for mail in mailbox if not mail.get("read")]
            say(f"Cleared {before - len(profile['mailbox'])} read message(s). Unread messages were kept.")
            commit()
        elif sub == "read" and len(args) > 1:
            try:
                index = int(args[1]) - 1
            except ValueError:
                index = -1
            if 0 <= index < len(mailbox):
                mail = mailbox[index]
                mail["read"] = True
                say(f"📨 {mail.get('subject', 'Message')} — {mail.get('body', '')}")
                commit()
            else:
                say("Message number not found. Use `mailbox` to view your inbox.")
        else:
            unread = sum(not mail.get("read") for mail in mailbox)
            say(f"📬 MAILBOX — {unread} unread / {len(mailbox)} total")
            if not mailbox:
                say("Your mailbox is empty.")
            for index, mail in enumerate(reversed(mailbox), 1):
                status = "UNREAD" if not mail.get("read") else "READ"
                say(f"{index}. [{status}] {mail.get('subject', 'Message')} — {mail.get('body', '')}")
            say("Use `mailbox read <number>` to mark a message read, or `mailbox clear` to clear read messages.")

    elif cmd == "casino":
        if not args or args[0].lower() == "list":
            say("🎰 VIRTUAL ARCADE — 15 MINI-GAMES")
            for game_name, description in CASINO_GAMES.items():
                say(f"{game_name} — {description}")
            say("Play with fictional FamPay only: `casino <game> <amount>`. No real-money deposits or cash-outs.")
        else:
            game_name = args[0].lower()
            if game_name not in CASINO_GAMES:
                say("Game not found. Use `casino list`.")
            else:
                try:
                    amount = int(args[1]) if len(args) > 1 else 0
                except ValueError:
                    amount = 0
                if amount <= 0 or amount > profile["fampay"]:
                    say("Enter a valid virtual-coin amount within your FamPay balance.")
                else:
                    profile["fampay"] -= amount
                    multiplier, detail = casino_result(game_name)
                    payout = int(amount * multiplier)
                    profile["fampay"] += payout
                    net = payout - amount
                    say(f"🎮 {game_name.upper()} — {detail}")
                    say(f"Entry: {amount:,} coins · Return: {payout:,} coins · Net: {net:+,} coins.")
                    commit()

    elif cmd in CASINO_GAMES:
        # Short aliases are accepted, but the HELP directory remains the source of truth.
        try:
            amount = int(args[0]) if args else 0
        except ValueError:
            amount = 0
        if amount <= 0 or amount > profile["fampay"]:
            say("Usage: " + cmd + " <virtual_coin_amount>")
        else:
            profile["fampay"] -= amount
            multiplier, detail = casino_result(cmd)
            payout = int(amount * multiplier)
            profile["fampay"] += payout
            say(f"🎮 {cmd.upper()} — {detail}")
            say(f"Entry: {amount:,} coins · Return: {payout:,} coins · Net: {payout - amount:+,} coins.")
            commit()

    elif cmd in ("scam_call", "scamcall"):
        # Fictional comedy encounter only; no real-world scripts or tactics.
        callers = ["Mr. Ramasamy", "The Confused Uncle", "A Very Suspicious NPC", "INVINGOPPA's Reception Desk"]
        target = random.choice(callers)
        if random.random() < 0.55:
            reward = random.randint(700, 2600)
            profile["fampay"] += reward
            core.add_xp(profile, 35)
            say(f"📞 SCAM CALL SIMULATION — {target} spotted the obvious joke and tipped your comedy hotline {reward:,} coins. +35 XP.")
        else:
            fine = min(profile["fampay"], random.randint(250, 900))
            profile["fampay"] -= fine
            say(f"📞 SCAM CALL SIMULATION — {target} reported the ridiculous call. City fine: {fine:,} coins.")
        commit()

    elif cmd == "crypto":
        market = room.setdefault("crypto_market", {"price": CRYPTO_START_PRICE, "updated": time.time()})
        now = time.time()
        if now - float(market.get("updated", 0)) >= 900:
            market["price"] = max(10, int(float(market.get("price", CRYPTO_START_PRICE)) * random.uniform(0.82, 1.20)))
            market["updated"] = now
        price = int(market.get("price", CRYPTO_START_PRICE))
        sub = args[0].lower() if args else "market"
        if sub == "buy" and len(args) > 1:
            try:
                units = float(args[1])
            except ValueError:
                units = 0
            cost = int(units * price)
            if units <= 0 or cost <= 0 or cost > profile["fampay"]:
                say("Usage: `crypto buy <units>` — enter a positive quantity you can afford.")
            else:
                profile["fampay"] -= cost
                profile["crypto_units"] = round(float(profile.get("crypto_units", 0)) + units, 4)
                say(f"Bought {units:g} SCAMCOIN for {cost:,} FamPay. Market price: {price:,} per coin.")
                commit()
        elif sub == "sell" and len(args) > 1:
            try:
                units = float(args[1])
            except ValueError:
                units = 0
            held = float(profile.get("crypto_units", 0))
            if units <= 0 or units > held:
                say(f"You hold {held:g} SCAMCOIN. Enter a valid quantity to sell.")
            else:
                proceeds = int(units * price)
                profile["crypto_units"] = round(held - units, 4)
                profile["fampay"] += proceeds
                say(f"Sold {units:g} SCAMCOIN for {proceeds:,} FamPay at {price:,} each.")
                commit()
        else:
            value = int(float(profile.get("crypto_units", 0)) * price)
            say("🪙 SCAMCOIN MARKET — fictional in-game market")
            say(f"Current price: {price:,} FamPay per SCAMCOIN")
            say(f"Your holdings: {float(profile.get('crypto_units', 0)):g} SCAMCOIN · Estimated value: {value:,} FamPay")
            say("Use `crypto buy <units>` or `crypto sell <units>`. Market prices fluctuate every 15 minutes.")

    elif cmd == "crime":
        if profile.get("dead"):
            say("You are currently out of action. Use `revive` first.")
        else:
            now = time.time()
            cooldown = max(0, int(profile.get("crime_cooldown", 0) - now))
            if cooldown:
                say(f"The City is watching you. Try another fictional crime run in {cooldown}s.")
            else:
                profile["crime_cooldown"] = now + 45
                outcome = random.random()
                if outcome < 0.58:
                    reward = random.randint(8000, 65000)
                    profile["fampay"] += reward
                    core.add_xp(profile, 90)
                    say(f"💰 BIG SCORE! Your fictional crime run paid {reward:,} coins and 90 XP.")
                elif outcome < 0.86:
                    lost = min(profile["fampay"], max(500, int(profile["fampay"] * random.uniform(0.20, 0.60))))
                    if profile["inventory"].get("padlock", 0) > 0:
                        profile["inventory"]["padlock"] -= 1
                        say("🥷 You got mugged on the way out, but your Padlock broke and protected your wallet!")
                    else:
                        profile["fampay"] -= lost
                        say(f"🥷 YOU GOT MUGGED! You lost {lost:,} coins. The run went very badly.")
                else:
                    if profile["inventory"].get("shield", 0) > 0:
                        profile["inventory"]["shield"] -= 1
                        say("🛡️ Your Shield shattered and saved you from the worst outcome. You escaped with no reward.")
                    elif profile["inventory"].get("reviver", 0) > 0:
                        profile["inventory"]["reviver"] -= 1
                        say("✨ Your Reviver Token activated. You were revived immediately, but the crime run failed.")
                    else:
                        profile["dead"] = True
                        profile["fampay"] = 0
                        say("💀 YOUR CHARACTER DIED! Your wallet was lost. Type `revive` to return to the game.")
                commit()

    elif cmd == "tax_fraud":
        # Purely fictional random event; deliberately contains no real tax-evasion advice.
        say("🧾 TAX_FRAUD — fictional cartoon tax-office challenge")
        if random.random() < 0.35:
            bonus = random.randint(1800, 5200)
            profile["fampay"] += bonus
            core.add_xp(profile, 45)
            say(f"The pixel auditor approved your imaginary paperwork. Bonus: {bonus:,} coins +45 XP.")
        else:
            fine = min(profile["fampay"], random.randint(900, 3000))
            profile["fampay"] -= fine
            say(f"INVINGOPPA's audit bot flagged the cartoon form. Fine: {fine:,} coins.")
        commit()

    elif cmd == "clerks":
        say("🏦 BANK CLERK ROSTER")
        for clerk in core.BANK_CLERKS:
            say(f"[{clerk['tier']}] {clerk['name']} · Reward {clerk['reward']:,} · Encounter risk {int(clerk['risk'] * 100)}%")
        say("Use `bank_heist` for a random fictional clerk encounter.")

    elif cmd == "bank_heist":
        clerk = random.choices(core.BANK_CLERKS, weights=[c["weight"] for c in core.BANK_CLERKS], k=1)[0]
        say(f"🏦 BANK HEIST EVENT — {clerk['name']} ({clerk['tier']})")
        if random.random() > clerk["risk"]:
            reward = clerk["reward"]
            drop = clerk["drop"]
            profile["fampay"] += reward
            profile["loot"][drop] = profile["loot"].get(drop, 0) + 1
            core.add_xp(profile, 100)
            say(f"The encounter was cleared! +{reward:,} coins, +100 XP, and {core.LOOT_ITEMS[drop]['name']}.")
        else:
            fine = min(profile["fampay"], max(500, clerk["reward"] // 5))
            profile["fampay"] -= fine
            say(f"The clerk caught the attempt. You paid a {fine:,}-coin game fine. No real-world instructions are involved.")
        commit()

    elif cmd == "daily":
        now = time.time()
        if now - profile.get("last_daily", 0) < 86400:
            remaining = int(86400 - (now - profile.get("last_daily", 0)))
            say(f"Daily reward already claimed. Try again in about {remaining // 3600}h {(remaining % 3600) // 60}m.")
        else:
            reward = 1000 + profile.get("daily_streak", 0) * 100
            profile["fampay"] += reward
            profile["last_daily"] = now
            profile["daily_streak"] = profile.get("daily_streak", 0) + 1
            say(f"Daily reward claimed: +{reward:,} coins.")
            commit()

    elif cmd == "beg":
        reward = random.randint(50, 350)
        if random.random() < 0.3:
            say("Nobody gave you anything this time.")
        else:
            profile["fampay"] += reward
            core.add_xp(profile, 20)
            say(f"Someone helped you out: +{reward:,} coins and 20 XP.")
            commit()

    elif cmd in ("dig", "hunt", "fish"):
        required = {"dig": "shovel", "hunt": "hunting_rifle", "fish": "fishing_rod"}[cmd]
        if profile["inventory"].get(required, 0) <= 0:
            say(f"You need {core.SHOP_ITEMS[required]['name']}. Buy it from `shop`.")
        else:
            if cmd == "hunt":
                encounter = random.choice(core.HUNT_BOSSES)
            elif cmd == "fish":
                encounter = random.choice(core.FISH_BOSSES)
            else:
                encounter = random.choice(core.DIG_ANIMALS)
            drop = encounter["drop"]
            profile["loot"][drop] = profile["loot"].get(drop, 0) + 1
            reward = random.randint(250, 1200)
            profile["fampay"] += reward
            core.add_xp(profile, 55)
            say(f"{encounter['name']}: collected {core.LOOT_ITEMS[drop]['name']} and earned {reward:,} coins + 55 XP.")
            commit()

    elif cmd in ("room", "rooms") and args:
        sub = args[0].lower()
        if sub == "list":
            for code, listed_room in data["rooms"].items():
                say(f"{code} — {listed_room.get('name', 'Unnamed City')} — host {listed_room.get('host', 'Unknown')} — {len(listed_room.get('members', []))}/{MAX_PLAYERS} players")
        elif sub == "create":
            preset = args[1].lower() if len(args) > 1 else "egmore"
            if preset not in core.CITIES:
                say("Unknown preset. Available: " + ", ".join(core.CITIES.keys()))
            else:
                new_code = create_city(data, username, f"{username}'s City", preset)
                say(f"Created a City lobby. Party Code: {new_code}. Name it and start it from the lobby screen.")
        elif sub == "join" and len(args) > 1:
            ok, message = join_city(data, username, args[1])
            say(message)
        else:
            say("Use: `room list`, `room create <preset>`, or `room join <code>`. ")

    elif cmd == "terminate_room":
        if room_code == GLOBAL_ROOM or room.get("host") != username:
            say("Only the host can terminate a private City.")
        else:
            for member in list(room.get("members", [])):
                if member in data["users"]:
                    data["users"][member]["current_room"] = None
            del data["rooms"][room_code]
            say("City terminated. All members returned to the City Lobby.")
            commit()

    elif cmd in ("players", "sidebar"):
        say("👥 PLAYERS IN THIS CITY")
        for member in room.get("members", []):
            last_active = data["users"].get(member, {}).get("last_active", 0)
            status = "Online" if time.time() - last_active < 120 else "Offline"
            say(f"{member} — {status}")

    elif cmd == "rob" and args:
        target = args[0]
        if target == username or target not in data["users"]:
            say("Player not found.")
        elif data["users"][target].get("current_room") != room_code:
            say("You can only interact with players in your current City.")
        else:
            victim = get_profile(data, target, room_code)
            if victim["inventory"].get("padlock", 0) > 0:
                victim["inventory"]["padlock"] -= 1
                profile["fampay"] = max(0, profile["fampay"] - 500)
                say("Padlock blocked the attempt. You paid a 500-coin fine.")
            elif random.random() < 0.5 and victim["fampay"] > 0:
                stolen = min(victim["fampay"], random.randint(100, 1500))
                victim["fampay"] -= stolen
                profile["fampay"] += stolen
                say(f"You won {stolen:,} coins.")
            else:
                fine = min(profile["fampay"], 500)
                profile["fampay"] -= fine
                say(f"Attempt failed. Fine: {fine:,} coins.")
            commit()

    elif cmd == "heist" and args:
        heist = room.setdefault("heist", {"active": False, "contributions": {}})
        sub = args[0].lower()
        if sub == "start":
            if heist.get("active"):
                say("A crew heist is already active.")
            else:
                heist["active"] = True
                heist["host"] = username
                heist["contributions"] = {username: 0}
                say("Crew heist opened. Teammates can contribute.")
            commit()
        elif sub == "contribute" and len(args) > 1:
            try:
                amount = int(args[1])
            except ValueError:
                amount = 0
            if not heist.get("active") or amount <= 0 or amount > profile["fampay"]:
                say("Invalid contribution or no active heist.")
            else:
                profile["fampay"] -= amount
                heist.setdefault("contributions", {})[username] = heist["contributions"].get(username, 0) + amount
                say(f"Contributed {amount:,} coins.")
                commit()
        elif sub == "launch":
            if not heist.get("active") or heist.get("host") != username:
                say("Only the heist host can launch an active crew heist.")
            elif len(heist.get("contributions", {})) < 2:
                say("At least two contributors are required.")
            else:
                total = sum(heist["contributions"].values())
                success = random.random() < 0.65
                if success:
                    pool = total * 2
                    for member, contribution in heist["contributions"].items():
                        if member in data["users"]:
                            member_profile = get_profile(data, member, room_code)
                            if total:
                                member_profile["fampay"] += int(pool * contribution / total)
                    say(f"Crew heist succeeded. {pool:,} coins distributed proportionally.")
                else:
                    say("The crew heist failed. Contributions were lost.")
                heist.update({"active": False, "contributions": {}})
                commit()
        else:
            say("Use `heist start`, `heist contribute <amount>`, or `heist launch`.")

    elif cmd in ("leaderboard", "lb"):
        ranked = []
        # IMPORTANT: only current members of this City are ranked.
        for member in room.get("members", []):
            if member not in data["users"]:
                continue
            if data["users"][member].get("current_room") != room_code:
                continue
            member_profile = get_profile(data, member, room_code)
            total = member_profile.get("fampay", 0) + member_profile.get("bank", 0)
            ranked.append((total, member))
        ranked.sort(key=lambda item: (item[0], item[1].lower()), reverse=True)
        say(f"🏆 {room.get('name', 'CITY')} LEADERBOARD")
        for rank, (total, member) in enumerate(ranked[:14], 1):
            say(f"{rank}. {member} — {total:,} coins")
        if not ranked:
            say("No players to rank yet.")

    elif cmd == "revive":
        if not profile.get("dead"):
            say("You are already active.")
        else:
            profile["dead"] = False
            profile["fampay"] = max(200, profile["fampay"])
            say("You have been revived.")
            commit()

    elif cmd == "exit":
        say("Use the Log out button in the sidebar to leave safely.")

    else:
        say(f"Unknown command: {cmd}. Type `help`.")

    add_command_result(raw_command, out, profile)
    # Robbery and heist activity is also announced in the City's persistent chat.
    if cmd in ("rob", "heist") and out:
        add_chat_message(room, "CITY SYSTEM", f"{username}: {' '.join(out)}", kind="system")
    save(data)


# -------------------------- SIDEBAR / GAME SCREEN --------------------------
def city_tools(data, username):
    with st.expander("🏙️ Create or join another City"):
        with st.form("sidebar_create_city"):
            city_name = st.text_input("New City name", max_chars=35, placeholder="Enter a City name")
            preset = st.selectbox(
                "Location preset",
                options=list(core.CITIES.keys()),
                format_func=lambda key: core.CITIES[key]["name"],
                key="sidebar_city_preset",
            )
            create = st.form_submit_button("Create City", use_container_width=True)
        if create:
            code = create_city(data, username, city_name, preset)
            st.session_state.last_created_code = code
            st.rerun()
        with st.form("sidebar_join_city"):
            code_to_join = st.text_input("Party Code", max_chars=6, placeholder="ABC123").strip().upper()
            join = st.form_submit_button("Join City", use_container_width=True)
        if join:
            ok, message = join_city(data, username, code_to_join)
            if ok:
                st.success(message)
                st.rerun()
            else:
                st.error(message)


def game_screen(data, username, account, room, profile, room_code, city_cfg):
    account["last_active"] = time.time()
    room_defaults(room)
    if refresh_job_status(profile):
        save(data)

    # No character can be changed after selection. A missing character means
    # this account has not yet claimed one in this City.
    if not profile.get("character_locked") or not profile.get("character_id"):
        character_picker(data, username, room_code, profile)
        st.stop()

    with st.sidebar:
        st.markdown("## 🪙 SCAM JOSE PAUL")
        st.caption(f"Logged in as **{username}**")
        st.markdown(f"**Current City:** {room.get('name', 'Unnamed City')}")
        st.markdown(f"**Party Code:** `{room_code}`")
        st.markdown(f"**Character:** {profile.get('character_name', 'Selected')}")
        if st.button("Leave City", use_container_width=True):
            if room.get("host") == username and room_code != GLOBAL_ROOM and len(room.get("members", [])) > 1:
                remove_member(data, username, room_code)
                account["current_room"] = None
            else:
                remove_member(data, username, room_code)
                account["current_room"] = None
            save(data)
            st.rerun()
        if st.button("Log out", use_container_width=True):
            save(data)
            st.session_state.pop("user", None)
            st.session_state.pop("command_log", None)
            st.rerun()
        st.divider()
        st.caption("HELP is the command directory. Type `help` in the console to see commands.")
        city_tools(data, username)
        if room_code != GLOBAL_ROOM and room.get("host") == username:
            st.divider()
            if st.button("Terminate City", type="secondary", use_container_width=True):
                st.session_state.confirm_terminate = room_code
        if st.session_state.get("confirm_terminate") == room_code:
            st.warning("This permanently closes the City and returns every member to the lobby.")
            confirm_col, cancel_col = st.columns(2)
            if confirm_col.button("Confirm", type="primary", key="confirm_terminate_yes"):
                for member in list(room.get("members", [])):
                    if member in data["users"]:
                        data["users"][member]["current_room"] = None
                data["rooms"].pop(room_code, None)
                st.session_state.pop("confirm_terminate", None)
                save(data)
                st.rerun()
            if cancel_col.button("Cancel", key="confirm_terminate_no"):
                st.session_state.pop("confirm_terminate", None)
                st.rerun()

    st.markdown(
        f"<div class='hero-card'><div class='hero-kicker'>WELCOME TO YOUR CITY</div>"
        f"<div class='hero-title'>🏙️ {html.escape(str(room.get('name', city_cfg.get('name', 'Your City'))))}</div>"
        f"<div class='hero-sub'>Party Code: <b>{html.escape(str(room_code))}</b> &nbsp; · &nbsp; Host: <b>{html.escape(str(room.get('host', 'Unknown')))}</b></div></div>",
        unsafe_allow_html=True,
    )

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("FamPay Balance", f"🪙 {profile['fampay']:,}")
    metric2.metric("FamPay Account", f"🏦 {profile['bank']:,}")
    metric3.metric("Level", profile["level"])
    metric4.metric("XP", f"{profile['xp']}/{profile['level'] * 300}")

    game_tab, chat_tab = st.tabs(["🎮 GAME", "💬 CITY CHAT"])

    with game_tab:
        left, right = st.columns([1.65, 1])
        with left:
            st.markdown("### 🎮 Command Console")
            st.markdown("<div class='muted-note'>Your command history stays above the input. Type <b>help</b> to see the command directory.</div>", unsafe_allow_html=True)

            # Larger scrollable Python-style console. Each command is grouped
            # with its own prompt and formatted result instead of loose lines.
            log_lines = st.session_state.get("command_log", [])
            with st.container(height=540, border=True):
                if log_lines:
                    for item in log_lines:
                        if isinstance(item, dict):
                            command_text = html.escape(str(item.get("command", "")))
                            st.markdown(
                                f"<div style='font-family:ui-monospace,monospace;font-size:.82rem;color:#8fb7ff;padding:8px 10px 3px'>&gt;&gt;&gt; {command_text}</div>",
                                unsafe_allow_html=True,
                            )
                            if item.get("kind") == "balance" and item.get("balance"):
                                b = item["balance"]
                                rows = [
                                    ("FamPay Balance", f"🪙 {b['wallet']:,}"),
                                    ("FamPay Account", f"🏦 {b['bank']:,} / {b['bank_max']:,}"),
                                    ("Level", str(b["level"])),
                                    ("XP", f"{b['xp']:,} / {b['xp_next']:,}"),
                                    ("Career", str(b["job"])),
                                ]
                                cells = "".join(
                                    f"<div style='display:flex;justify-content:space-between;gap:12px;padding:5px 0;border-bottom:1px solid rgba(148,163,184,.12)'><span style='color:#aab8ce'>{html.escape(label)}</span><b style='color:#f4f7ff;text-align:right'>{html.escape(value)}</b></div>"
                                    for label, value in rows
                                )
                                st.markdown(
                                    f"<div style='margin:5px 8px 13px;padding:12px 15px;border:1px solid rgba(113,151,218,.30);border-radius:12px;background:linear-gradient(145deg,rgba(24,39,62,.92),rgba(10,17,29,.96));font-size:.80rem'><div style='font-weight:800;letter-spacing:1.2px;color:#9dbcf0;font-size:.72rem;margin-bottom:7px'>ACCOUNT SUMMARY</div>{cells}</div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                # Every command gets the same polished result-card treatment
                                # as BAL: a clear heading, framed panel, and neatly spaced rows.
                                output_lines = item.get("lines", [])
                                rendered = "".join(
                                    f"<div style='padding:5px 0;border-bottom:1px solid rgba(148,163,184,.10)'>{html.escape(str(line))}</div>"
                                    for line in output_lines
                                )
                                if not rendered:
                                    rendered = "<div style='padding:5px 0;color:#93a2b8'>No output.</div>"
                                st.markdown(
                                    f"<div style='margin:5px 8px 13px;padding:12px 15px;border:1px solid rgba(113,151,218,.30);border-radius:12px;background:linear-gradient(145deg,rgba(24,39,62,.92),rgba(10,17,29,.96));font-family:ui-monospace,monospace;font-size:.78rem;line-height:1.58;color:#e5edf9'><div style='font-family:DM Sans,sans-serif;font-weight:800;letter-spacing:1.2px;color:#9dbcf0;font-size:.72rem;margin-bottom:7px'>COMMAND OUTPUT</div>{rendered}</div>",
                                    unsafe_allow_html=True,
                                )
                        else:
                            st.markdown(
                                f"<div style='padding:4px 10px;font-family:ui-monospace,monospace;font-size:.78rem;color:#dce6f5'>{html.escape(str(item))}</div>",
                                unsafe_allow_html=True,
                            )
                else:
                    st.caption("Your command results will appear here. Start with `help`.")

            command_key = f"command_entry_{st.session_state.get('command_nonce', 0)}"
            with st.container(border=True):
                with st.form("command_form", clear_on_submit=True):
                    command = st.text_input(
                        "Command",
                        placeholder="Enter a command...",
                        label_visibility="collapsed",
                        key=command_key,
                    )
                    submitted = st.form_submit_button("⚡ RUN COMMAND", type="primary", use_container_width=True)
            if submitted and command.strip():
                execute_command(data, username, room_code, room, profile, city_cfg, command)
                st.session_state.command_nonce = st.session_state.get("command_nonce", 0) + 1
                st.rerun()

        with right:
            st.markdown("### 🎭 Your Character")
            char_index = next((i for i, item in enumerate(CHARACTERS) if item[0] == profile.get("character_id")), None)
            if char_index is not None:
                image_path = BASE / "assets" / "characters" / f"character_{char_index + 1:02d}.jpg"
                if image_path.exists():
                    st.image(str(image_path), width=190)
                st.markdown(f"<div class='character-name'>{CHARACTERS[char_index][1]}</div>", unsafe_allow_html=True)
                st.caption(CHARACTERS[char_index][2])
            st.divider()
            unread_mail = sum(not mail.get("read") for mail in profile.get("mailbox", []))
            st.markdown(f"### 📬 Mailbox · {unread_mail} unread")
            if unread_mail:
                for mail in [m for m in reversed(profile.get("mailbox", [])) if not m.get("read")][:3]:
                    st.warning(f"**{mail.get('subject', 'Message')}**\n\n{mail.get('body', '')}")
                st.caption("Type `mailbox` in the console to view all messages.")
            else:
                st.caption("No unread messages. Type `mailbox` to open your inbox.")
            st.divider()
            st.markdown("### 🏙️ City Status")
            st.write(f"**Host:** {room.get('host', 'Unknown')}")
            st.write(f"**Members:** {len(room.get('members', []))}/{MAX_PLAYERS}")
            job_name = core.JOBS.get(profile.get("job"), {}).get("name", profile.get("job", "None"))
            st.write(f"**Career:** {job_name}")
            st.write(f"**Inventory items:** {sum(profile['inventory'].values())}")
            st.write(f"**Collectibles / loot:** {sum(profile['loot'].values())}")
            st.divider()
            st.markdown("### 👥 People in this City")
            for member in room.get("members", []):
                if member not in data["users"] or data["users"][member].get("current_room") != room_code:
                    continue
                member_profile = get_profile(data, member, room_code)
                member_char_id = member_profile.get("character_id")
                char_index = next((i for i, item in enumerate(CHARACTERS) if item[0] == member_char_id), None)
                char_label = CHARACTERS[char_index][1] if char_index is not None else "Character pending"
                last_active = data["users"].get(member, {}).get("last_active", 0)
                is_online = time.time() - last_active < 120
                avatar_col, details_col = st.columns([0.75, 2.5], vertical_alignment="center")
                with avatar_col:
                    if char_index is not None:
                        avatar_path = BASE / "assets" / "characters" / f"character_{char_index + 1:02d}.jpg"
                        if avatar_path.exists():
                            st.image(str(avatar_path), width=62)
                        else:
                            st.markdown("<div style='width:62px;height:62px;border-radius:12px;background:#24344d'></div>", unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='width:62px;height:62px;border-radius:12px;background:#24344d'></div>", unsafe_allow_html=True)
                with details_col:
                    st.markdown(f"<div style='font-size:.91rem;font-weight:750;line-height:1.25'>{html.escape(str(member))}{' <span style="color:#e7bd72;font-size:.68rem">HOST</span>' if member == room.get('host') else ''}</div><div style='font-size:.70rem;color:#9eacc1;margin-top:3px'>{html.escape(char_label)}</div><div style='font-size:.68rem;color:{'#69d69b' if is_online else '#a0a9b8'};margin-top:3px'>{'● Online' if is_online else '● Offline'}</div>", unsafe_allow_html=True)
                st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)

    with chat_tab:
        st.markdown("### 💬 City Chat")
        st.caption("Messages are saved with this City and remain available when players leave and return.")
        refresh_col, info_col = st.columns([1, 3])
        with refresh_col:
            if st.button("↻ Refresh chat", use_container_width=True, key="refresh_city_chat"):
                st.rerun()
        with info_col:
            st.caption("Chat is shared only with members of this City. Robbery and heist events appear here automatically.")

        messages = room.setdefault("chat_messages", [])
        with st.container(height=480, border=True):
            if not messages:
                st.caption("No messages yet. Start the conversation!")
            for msg in messages:
                author = str(msg.get("user", "Unknown"))
                body = str(msg.get("message", ""))
                stamp = msg.get("timestamp", 0)
                time_label = time.strftime("%H:%M", time.localtime(stamp)) if stamp else ""
                if msg.get("kind") == "system":
                    st.info(f"**{author}** · {time_label}\n\n{body}")
                else:
                    with st.chat_message("user" if author == username else "assistant", avatar=None):
                        st.markdown(f"**{html.escape(author)}** · {time_label}")
                        st.write(body)

        with st.form("city_chat_form", clear_on_submit=True):
            chat_text = st.text_input("Message", placeholder="Message your City...", max_chars=1000)
            send_chat = st.form_submit_button("➤ SEND MESSAGE", type="primary", use_container_width=True)
        if send_chat and chat_text.strip():
            add_chat_message(room, username, chat_text.strip())
            save(data)
            st.rerun()

    save(data)
    st.caption("SCAM JOSE PAUL · Web edition · City progress is saved separately for each player and City.")


# -------------------------- MAIN ROUTER --------------------------
if "user" not in st.session_state:
    login_screen()
    st.stop()

username = st.session_state.user
data = load_data()
if username not in data["users"]:
    st.session_state.clear()
    st.rerun()

account = data["users"][username]
account["last_active"] = time.time()
room_code = account.get("current_room")

if not room_code or room_code not in data["rooms"]:
    account["current_room"] = None
    save(data)
    with st.sidebar:
        st.markdown("## 🪙 SCAM JOSE PAUL")
        st.caption(f"Logged in as **{username}**")
        if st.button("Log out", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()
    lobby_screen(data, username, account)
    st.stop()

room = data["rooms"][room_code]
room_defaults(room)
if username not in room["members"]:
    if len(room["members"]) >= MAX_PLAYERS:
        account["current_room"] = None
        save(data)
        st.error("This City is full. Choose another City or create your own.")
        lobby_screen(data, username, account)
        st.stop()
    room["members"].append(username)

if not room.get("started", True):
    with st.sidebar:
        st.markdown("## 🪙 SCAM JOSE PAUL")
        st.caption(f"Logged in as **{username}**")
        if st.button("Log out", use_container_width=True):
            save(data)
            st.session_state.pop("user", None)
            st.rerun()
    lobby_screen(data, username, account, room_code)
    st.stop()

profile = get_profile(data, username, room_code)
city_cfg = core.CITIES.get(room.get("preset", "egmore"), core.CITIES["egmore"])
save(data)
game_screen(data, username, account, room, profile, room_code, city_cfg)
