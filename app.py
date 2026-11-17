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
    ("professor", "THE PROFESSOR", "Has 47 unfinished degrees and still asks Google how to boil water.", "+10% pay from WORK shifts."),
    ("heartbreaker", "THE RIZZLER", "Will get the buzz to pull thy huzz.", "+15% coins from BEG. The charm is apparently tax-deductible."),
    ("uncle_jose", "UNCLE JOSE", "Retired businessman. Wanted in 4 neighbourhood WhatsApp groups.", "Loses 10% fewer coins in failed street encounters."),
    ("sleeping_ceo", "THE NAKED MAFIA LEADER", "Will send tingles down ur wingles.", "+15% coins from successful CRIME runs. The City fears the vibes."),
    ("og", "SAM DA BABY", "4 year old bebeh.", "10% discount on SHOP purchases. Tiny CEO, enormous savings."),
    ("mystery_man", "THE MYSTERY MAN", "Nobody knows who he is. Not even his own profile picture.", "+5% returns from CASINO games."),
    ("ancient_one", "THE ANCIENT ONE", "His account is older than the City's economy.", "+10% coins when selling LOOT."),
    ("hello_kitty_boss", "HELLO KITTY FINAL BOSS", "Cute appearance. The financial crimes department has opened a file.", "+10% DAILY reward."),
    ("npc", "THE NPC", "Stares into the distance. Somehow owns a mansion.", "+5% bonus on HUNT and FISH rewards."),
    ("cat_whisperer", "THE CAT WHISPERER", "Doesn't trust humans. Has a suspiciously large fish collection.", "+15% rewards from HUNT and FISH."),
    ("confused_citizen", "Paul mogger", "Only mews and eats gum.", "+15% XP from activities. Mewing is apparently productive."),
    ("security_guard", "THE SECURITY GUARD", "Looks like he knows something. Refuses to elaborate.", "Reduces failed CRIME-run losses by 15%."),
    ("invingoppa", "INVINGOPPA", "The bank clerk has arrived. Your loan application was rejected before you even opened it.", "Banknote upgrades add +6,000 bank space instead of +5,000."),
    ("drip_lord", "Chikko chezhiyanin magan", "Anna sowwww.", "+15% DAILY reward. The anna economy is thriving."),
]


def character_id(profile):
    return profile.get("character_id")


def award_xp(profile, amount):
    if character_id(profile) == "confused_citizen":
        amount = int(amount * 1.15)
    if "_pet_bonus" in globals():
        amount = _pet_bonus(profile, "xp", amount)
    core.add_xp(profile, amount)


def character_bonus(profile, activity, amount):
    """Apply the selected character's small, activity-specific passive bonus."""
    cid = character_id(profile)
    multipliers = {
        ("professor", "work"): 1.10,
        ("mystery_man", "casino"): 1.05,
        ("ancient_one", "sell"): 1.10,
        ("hello_kitty_boss", "daily"): 1.10,
        ("npc", "wildlife"): 1.05,
        ("cat_whisperer", "wildlife"): 1.15,
        ("heartbreaker", "beg"): 1.15,
        ("sleeping_ceo", "crime"): 1.15,
        ("drip_lord", "daily"): 1.15,
    }
    adjusted = int(amount * multipliers.get((cid, activity), 1.0))
    return _pet_bonus(profile, activity, adjusted) if "_pet_bonus" in globals() else adjusted


# One active ability per character. All abilities use a one-hour cooldown.
CHARACTER_ABILITIES = {
    "professor": ("EXAM CRAM", "Gain 120 XP instantly."),
    "heartbreaker": ("RIZZ STORM", "Charm the City into giving you 750–1,500 coins."),
    "uncle_jose": ("OLD CONTACTS", "Call in a favour and receive one Padlock."),
    "sleeping_ceo": ("MAFIA ENVELOPE", "Collect a secret 2,000–4,000 coin bonus."),
    "og": ("TINY CEO SUBSIDY", "Get one free Shield from the tiny treasury."),
    "mystery_man": ("MYSTERY PAYOUT", "Flip a mystery reward: coins or XP."),
    "ancient_one": ("ANTIQUE APPRAISAL", "Sell one random piece of loot automatically; if you have none, receive 1,000 coins."),
    "hello_kitty_boss": ("CUTENESS TAX REFUND", "Claim a 1,250-coin refund from the City."),
    "npc": ("MAIN CHARACTER MOMENT", "Gain one Shield and 40 XP."),
    "cat_whisperer": ("PURRFECT DELIVERY", "A mysterious cat delivers one random loot item."),
    "confused_citizen": ("MEW MODE", "Gain 180 XP through intense gum-powered focus."),
    "security_guard": ("EMERGENCY LOCKDOWN", "Receive one Padlock and one Shield."),
    "invingoppa": ("BANKER'S BLESSING", "Increase your bank capacity by 1,500 coins."),
    "drip_lord": ("ANNA'S BLESSING", "Receive a 2,000-coin anna-approved bonus."),
}
ABILITY_COOLDOWN_SECONDS = 3600


GAIN_BANTER = [
    "SAAVU DAAA! THE COINS ARE FLOWING.", "WE ARE SO BACK.",
    "THE ECONOMY HAS CHOSEN YOU TODAY.", "MONEY PRINTER GO BRRR.",
    "BIG W. YOUR WALLET THANKS YOU.", "ABSOLUTE FINANCIAL CINEMA.",
    "STONKS. THE BANKER IS NERVOUS.", "THAT'S A CLEAN PROFIT.",
    "CHA-CHING! THE CITY HEARD THAT.", "ANNA LEVEL FINANCIAL PERFORMANCE.",
    "WALLET GLOW-UP IN PROGRESS.", "THE COIN COUNT GOES CRAZY.",
    "BILLIONAIRE ARC UNLOCKED (IN THIS GAME).", "THAT'S WHAT WE CALL A W.",
]
LOSS_BANTER = [
    "AYYO WHERE DID THE MONEY GO?", "SAAVU DAAA... THE WALLET IS CRYING.",
    "THE ECONOMY HAS BETRAYED YOU.", "FINANCIAL DAMAGE. ABSOLUTELY UNNECESSARY.",
    "YOUR WALLET JUST TOOK A VACATION WITHOUT YOU.", "NOT THE COINS. ANYTHING BUT THE COINS.",
    "THIS IS A PERSONAL ATTACK ON YOUR BANK BALANCE.", "THE BANKER IS NOT PICKING UP.",
    "L. WE LEARN AND WE MOVE.", "THAT PURCHASE HURT MORE THAN EXPECTED.",
    "THE WALLET HAS LEFT THE GROUP CHAT.", "BRO GOT FINANCIALLY JUMPSCARED.",
    "COINS DOWN. CHARACTER DEVELOPMENT UP.", "THE TREASURER IS DISAPPOINTED.",
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
    room.setdefault("created_at", time.time())
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


def create_city(data, username, city_name, preset, is_public=False):
    code = make_room_code(data)
    name = city_name.strip()[:35] or f"{username}'s City"
    data["rooms"][code] = {
        "host": username,
        "name": name,
        "preset": preset if preset in core.CITIES else "egmore",
        "is_public": bool(is_public),
        "created_at": time.time(),
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
                visibility = st.radio("City visibility", ["Private", "Public"],
                                      index=1 if room.get("is_public") else 0, horizontal=True)
                start = st.form_submit_button("🚀 START CITY", type="primary", use_container_width=True)
            if start:
                room["name"] = city_name.strip() or f"{username}'s City"
                room["preset"] = preset
                room["is_public"] = visibility == "Public"
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
                visibility = st.radio("City visibility", ["Private", "Public"], horizontal=True,
                                      help="Public Cities appear in discovery. Private Cities can only be joined with their Party Code.")
                create = st.form_submit_button("CREATE CITY", type="primary", use_container_width=True)
            if create:
                code = create_city(data, username, new_city_name, new_preset, visibility == "Public")
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
    st.subheader("🌐 Public Cities")
    available = [
        (code, room) for code, room in data["rooms"].items()
        if code != GLOBAL_ROOM and room.get("started", True) and room.get("is_public", False)
    ]
    if not available:
        st.caption("No public Cities are listed yet. Private Cities require a Party Code from the host.")
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
# -------------------------- MULTIPLAYER HEIST / PAYMENTS / PETS --------------------------
HEIST_ACTIONS = [
    "Bluff your way through", "Make a dramatic escape", "Attempt the cartoon caper", "Negotiate with the clerk", "Try a ridiculous wildcard",
    "Pretend you're an inspector", "Ask for the manager", "Challenge the clerk to chess", "Tell an elaborate excuse", "Request a timeout",
    "Start an impromptu talent show", "Challenge the apprentice to riddles", "Ask about INVINGOPPA", "Offer a peace treaty", "Try to impress the clerk",
    "Call a team meeting", "Let the NPC decide", "Ask for a clue", "Solve the mystery puzzle", "Use your character ability",
    "Search for a fictional clue", "Choose the mystery answer", "Try a logic challenge", "Ask a teammate for help", "Request a hint",
    "Propose a friendly competition", "Offer a trade", "Challenge the rival leader to trivia", "Request a joint challenge", "Make a ridiculous bet",
    "Ask the visitor for directions", "Pretend everything is normal", "Explain the misunderstanding", "Invite the visitor to join the quiz", "Request a peaceful resolution",
    "Face the final challenge", "Ask for one final chance", "Trust your luck", "Pull a mystery card", "Make an absurd declaration",
    "Summon the Rizzler", "Call Uncle Jose", "Ask Sam da Baby for advice", "Trust the Ancient One", "Ask the Security Guard for a hint",
    "Activate a pet's speciality", "Start a dance-off", "Challenge the bank mascot", "Offer a dramatic apology", "Say absolutely nothing",
    "Request divine intervention", "Tell a terrible joke", "Ask for a group quiz", "Play rock-paper-scissors", "Choose the mystery envelope",
]
HEIST_SCENARIOS = [
    {"title":"The clerk is staring directly at your crew.","type":"Clerk encounter"},
    {"title":"INVINGOPPA'S FIRST APPRENTICE arrives with a clipboard and a very serious expression.","type":"Apprentice encounter"},
    {"title":"INVINGOPPA'S SECOND APPRENTICE challenges the crew to an absurdly difficult logic test.","type":"Elite apprentice"},
    {"title":"The bank mascot has started asking everyone for identification. It is a cardboard cut-out.","type":"Unexpected visitor"},
    {"title":"A mysterious vault puzzle appears on the big screen. Nobody understands the instructions.","type":"Puzzle"},
    {"title":"A rival crew appears and challenges your team to a ridiculous competition.","type":"Rival crew"},
    {"title":"The bank's automated announcement system starts narrating your every move.","type":"Random event"},
    {"title":"A VIP visitor mistakes your crew for the entertainment committee.","type":"Visitor"},
    {"title":"The clerk announces a surprise inspection by the Department of Dramatic Paperwork.","type":"Inspection"},
    {"title":"The elevator opens and INVINGOPPA himself steps out.","type":"INVINGOPPA encounter"},
    {"title":"A giant question mark appears above the vault. The bank insists this is normal.","type":"Mystery vault"},
    {"title":"The bank mascot has challenged everyone to a dance-off.","type":"Wildcard"},
    {"title":"A confused NPC offers the crew a suspiciously helpful riddle.","type":"NPC event"},
    {"title":"The apprentice clerks arrive together for a double challenge.","type":"Double apprentice"},
]
HEIST_OUTCOMES = [
    ("Perfect Success", "The crew clears the challenge with style.", 1.30, "success"),
    ("Lucky Success", "A ridiculous coincidence works in the crew's favour.", 1.18, "success"),
    ("Clean Getaway", "The crew gets out of the encounter with a modest win.", 0.90, "success"),
    ("Unexpected Jackpot", "A mystery bonus is added to the prize pool.", 1.55, "jackpot"),
    ("Clerk Confused", "The clerk is too confused to continue. The crew advances.", 1.05, "success"),
    ("Clerk Laughs", "The clerk laughs so hard that the crew gets another chance.", 1.10, "success"),
    ("Apprentice Impressed", "The apprentice acknowledges the crew's creativity.", 1.25, "success"),
    ("Apprentice Furious", "The apprentice calls for a harder challenge.", 0.75, "complication"),
    ("INVINGOPPA Appears", "INVINGOPPA enters the story and raises the difficulty.", 0.70, "complication"),
    ("INVINGOPPA's Approval", "The crew earns a rare stamp of approval.", 1.45, "jackpot"),
    ("Mystery Vault", "A mystery prize is discovered.", 1.20, "loot"),
    ("Bonus Safe", "A bonus cache adds extra coins.", 1.25, "jackpot"),
    ("Fake Jackpot", "The glittering prize turns out to be a novelty coupon.", 0.65, "complication"),
    ("Puzzle Solved", "The crew solves the puzzle and advances.", 1.12, "success"),
    ("Puzzle Failed", "The puzzle resets and a complication appears.", 0.65, "complication"),
    ("Rival Crew Outplayed", "The rival crew concedes the challenge.", 1.20, "success"),
    ("Rival Crew Wins", "The rival crew takes the spotlight.", 0.60, "complication"),
    ("Unexpected Ally", "A friendly NPC offers a useful bonus.", 1.15, "success"),
    ("NPC Intervention", "The NPC presses a random button. Somehow it helps.", 1.05, "success"),
    ("Character Moment", "A crew member's character speciality creates a bonus.", 1.20, "success"),
    ("Lucky Coin Shower", "A harmless shower of bonus coins rains down.", 1.10, "success"),
    ("Rare Collectible", "The crew discovers a rare collectible.", 1.0, "loot"),
    ("Inspection Delay", "The inspection delays the crew and lowers the payout.", 0.75, "complication"),
    ("Team Disagreement", "The crew cannot agree and loses some momentum.", 0.70, "complication"),
    ("Teamwork Bonus", "The crew's coordination earns bonus XP.", 1.10, "xp"),
    ("Dramatic Reversal", "The situation flips unexpectedly. The crew gets another challenge.", 0.90, "complication"),
    ("Partial Success", "The crew salvages a smaller reward.", 0.65, "partial"),
    ("Heist Abandoned", "The crew decides to call it a day. No payout.", 0.0, "failure"),
    ("Total Defeat", "The crew loses the fictional challenge together.", 0.0, "failure"),
    ("Legendary Ending", "An extremely rare ending unlocks a legendary prize.", 1.85, "jackpot"),
    ("Secret Character Ending", "A character-specific event gives the crew a special prize.", 1.50, "jackpot"),
    ("Double Apprentice Encounter", "Both apprentices team up for an elite challenge.", 0.70, "complication"),
    ("Mysterious Envelope", "A sealed envelope contains random loot or coins.", 1.15, "loot"),
    ("Unexpected Refund", "The bank's fictional system issues a surprise refund.", 1.08, "success"),
    ("The Bank Remembers You", "The bank records the crew's visit and unlocks a future event.", 1.0, "special"),
    ("Mascot's Blessing", "The bank mascot gives the crew a tiny lucky charm.", 1.12, "loot"),
    ("Legendary Clerk Stamp", "The crew earns a collectible clerk stamp.", 1.35, "loot"),
]


def _today_key():
    return time.strftime("%Y-%m-%d", time.localtime())


def _active_city_members(data, room_code):
    room = data["rooms"].get(room_code, {})
    return [m for m in room.get("members", []) if m in data.get("users", {}) and data["users"][m].get("current_room") == room_code]


def _heist_mail(data, room_code, names, subject, body):
    for name in names:
        if name in data.get("users", {}):
            add_mail(get_profile(data, name, room_code), subject, body, "heist")


def _heist_announce(room, message):
    add_chat_message(room, "🏦 BANK HEIST SYSTEM", message, kind="system")


def _heist_begin_round(data, room_code, room, heist):
    scenario = random.choice(HEIST_SCENARIOS)
    heist["round"] = int(heist.get("round", 0)) + 1
    heist["scenario"] = scenario
    # Five choices are drawn from the full 55+ action library, with no duplicates.
    heist["choices"] = random.sample(HEIST_ACTIONS, 5)
    heist["deadline"] = time.time() + 60
    heist["status"] = "decision"
    heist["last_result"] = None
    names = heist.get("participants", [])
    option_text = " | ".join(f"{i+1}. {x}" for i,x in enumerate(heist['choices']))
    message = f"ROUND {heist['round']}: {scenario['title']} Options: {option_text}. Only {heist['leader']} may decide. Crew discussion: 60 seconds."
    _heist_mail(data, room_code, names, f"BANK HEIST — ROUND {heist['round']}", message)
    _heist_announce(room, message)


def _heist_finish(data, room_code, room, heist, outcome):
    names = list(heist.get("participants", []))
    count = len(names)
    # Total prize pool rises with team size; capped at 14 City members.
    base_ranges = {2:(5000,12000),3:(9000,19000),4:(14000,28000),5:(20000,40000)}
    if count <= 5:
        low, high = base_ranges.get(count, (5000,12000))
    else:
        low, high = 20000 + (count-5)*6500, 40000 + (count-5)*10000
    factor = float(outcome[2]) * float(heist.get("pending_factor", 1.0))
    prize_pool = random.randint(low, high) * factor if factor > 0 else 0
    prize_pool = int(prize_pool)
    xp_each = 80 if factor >= 1 else 35 if factor > 0 else 0
    loot_drop = random.choice(["clerk_trophy", "clerk_stamp", "golden_ticket", "mystery_box"]) if outcome[3] in ("loot", "jackpot") else None
    # Rare outcomes may grant loot; only use valid catalogue keys.
    if loot_drop not in core.LOOT_ITEMS:
        loot_drop = random.choice(list(core.LOOT_ITEMS)) if outcome[3] in ("loot", "jackpot") else None
    share = prize_pool // max(1, count)
    for name in names:
        if name not in data["users"]:
            continue
        p = get_profile(data, name, room_code)
        p["fampay"] = int(p.get("fampay", 0)) + share
        if xp_each:
            xp_reward = _pet_bonus(p, "heist_xp", xp_each)
            award_xp(p, xp_reward)
        if loot_drop:
            p.setdefault("loot", {})[loot_drop] = int(p.get("loot", {}).get(loot_drop, 0)) + 1
        if factor > 0 and outcome[3] not in ("failure",):
            p.setdefault("pet_quests", {})["multiplayer_event"] = True
        add_mail(p, "BANK HEIST RESULTS", f"Outcome: {outcome[0]}. {outcome[1]} Team size: {count}. Your share: {share:,} coins. XP: {xp_each}. Loot: {core.LOOT_ITEMS[loot_drop]['name'] if loot_drop else 'None'}.", "heist")
    _heist_announce(room, f"HEIST COMPLETE — {outcome[0]}. Crew: {', '.join(names)}. Total prize pool: {prize_pool:,} coins.")
    heist.clear()
    heist.update({"status":"cooldown_complete", "last_completed":time.time(), "last_outcome":outcome[0], "last_team":names, "last_prize_pool":prize_pool})


def _heist_resolve(data, room_code, room, heist, choice_index=None, timeout=False):
    choices = heist.get("choices", [])
    if timeout or choice_index is None:
        chosen = random.choice(choices) if choices else "The crew freezes and lets fate decide"
    else:
        chosen = choices[choice_index]
    # Team size, encounter tier, and randomness influence the outcome.
    count = len(heist.get("participants", []))
    scenario_type = heist.get("scenario", {}).get("type", "Random event")
    chance = min(0.78, 0.34 + 0.075 * count)
    if "Apprentice" in scenario_type or "INVINGOPPA" in scenario_type:
        chance -= 0.12
    if "Double" in scenario_type:
        chance -= 0.10
    if timeout:
        chance -= 0.08
    for member in heist.get("participants", []):
        member_profile = get_profile(data, member, room_code)
        active_pet = next((p for p in member_profile.get("pets", []) if p.get("id") == member_profile.get("active_pet_id")), None)
        if active_pet and core.PET_CATALOG.get(active_pet.get("species"), {}).get("bonus_activity") == "heist_defense":
            _pet_decay(active_pet)
            if min(active_pet.get("hunger", 0), active_pet.get("happiness", 0), active_pet.get("energy", 0)) >= 30:
                chance += 0.025
                break
    if any("challenge" in chosen.lower() or "puzzle" in chosen.lower() or "quiz" in chosen.lower() for _ in [0]):
        chance += 0.06
    chance = max(0.12, min(0.82, chance))
    roll = random.random()
    if roll < chance * 0.035:
        outcome = random.choice([o for o in HEIST_OUTCOMES if o[3] == "jackpot"])
    elif roll < chance * 0.10:
        outcome = random.choice([o for o in HEIST_OUTCOMES if o[0] in ("Legendary Ending", "Secret Character Ending", "The Bank Remembers You")])
    elif roll < chance * 0.18:
        outcome = random.choice([o for o in HEIST_OUTCOMES if o[3] == "failure"])
    elif roll < chance:
        outcome = random.choice([o for o in HEIST_OUTCOMES if o[3] in ("success", "loot", "xp", "special", "partial")])
    else:
        outcome = random.choice([o for o in HEIST_OUTCOMES if o[3] in ("complication", "partial", "failure")])
    result_text = f"ROUND {heist.get('round',1)} — {chosen}. RESULT: {outcome[0]}. {outcome[1]}"
    heist.setdefault("round_history", []).append({"choice":chosen,"outcome":outcome[0],"timestamp":time.time()})
    heist["last_result"] = result_text
    _heist_announce(room, result_text)
    names = heist.get("participants", [])
    _heist_mail(data, room_code, names, f"BANK HEIST — ROUND {heist.get('round',1)} RESULT", result_text)
    if outcome[3] == "failure" or heist.get("round", 1) >= 3:
        _heist_finish(data, room_code, room, heist, outcome)
    else:
        heist["status"] = "between_rounds"
        heist["next_scenario"] = None
        heist["deadline"] = 0
        heist["pending_factor"] = max(0.25, min(1.75, float(heist.get("pending_factor", 1.0)) * max(0.5, float(outcome[2]))))


def _heist_timeout_if_needed(data, room_code, room):
    heist = room.get("multiplayer_bank_heist", {})
    if heist.get("status") == "decision" and time.time() >= float(heist.get("deadline", 0)):
        _heist_resolve(data, room_code, room, heist, timeout=True)
        save(data)
        return True
    return False


def _pet_decay(pet):
    now = time.time()
    last = float(pet.get("last_update", now))
    elapsed_hours = max(0, (now - last) / 3600)
    steps = int(elapsed_hours)
    if steps:
        pet["hunger"] = max(0, int(pet.get("hunger", 100)) - steps * 8)
        pet["happiness"] = max(0, int(pet.get("happiness", 100)) - steps * 5)
        pet["energy"] = max(0, int(pet.get("energy", 100)) - steps * 6)
        pet["last_update"] = last + steps * 3600


def _pet_bonus(profile, activity, amount):
    active_id = profile.get("active_pet_id")
    pet = next((p for p in profile.get("pets", []) if p.get("id") == active_id), None)
    if not pet:
        return amount
    _pet_decay(pet)
    if min(int(pet.get("hunger", 0)), int(pet.get("happiness", 0)), int(pet.get("energy", 0))) < 30:
        return amount
    spec = core.PET_CATALOG.get(pet.get("species"), {})
    activity_key = spec.get("bonus_activity")
    if activity_key in (activity, "random"):
        level_scale = 1 + max(0, int(pet.get("level", 1)) - 1) * 0.05
        return int(amount * (1 + float(spec.get("bonus", 0)) * level_scale))
    return amount


def _pet_find(profile, pet_id):
    return next((p for p in profile.get("pets", []) if p.get("id") == pet_id), None)


def _pet_adopt(profile, species):
    spec = core.PET_CATALOG[species]
    pet = {"id":secrets.token_hex(5),"species":species,"name":spec["name"],"level":1,"xp":0,"hunger":100,"happiness":100,"energy":100,"last_update":time.time(),"adopted_at":time.time()}
    profile.setdefault("pets", []).append(pet)
    if not profile.get("active_pet_id"):
        profile["active_pet_id"] = pet["id"]
    return pet


def execute_command(data, username, room_code, room, profile, city_cfg, raw_command):
    parts = raw_command.strip().split()
    if not parts:
        return
    cmd = parts[0].lower()
    args = parts[1:]
    out = []

    def say(message):
        message = str(message)
        out.append(message)
        lower = message.lower()
        if "coin" in lower and any(word in lower for word in ("earned", "reward", "won", "bonus", "sold", "purchased", "deposited", "withdrew", "paid", "lost", "fine", "mugged", "cost", "contributed", "consumed", "bought")):
            loss_words = ("lost", "fine", "mugged", "cost", "paid", "contributed", "purchased", "deposited", "consumed", "bought")
            out.append(random.choice(LOSS_BANTER if any(word in lower for word in loss_words) else GAIN_BANTER))

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
        say("ABILITY / SPECIAL — Activate your selected character's unique power (1-hour cooldown)")
        say("DEPOSIT <amount> — Move FamPay into your bank")
        say("WITHDRAW <amount> — Take FamPay out of your bank")
        say("BANK_HEIST — Recruit your City for a multiplayer bank heist")
        say("HEIST_ACCEPT — Join the active City heist")
        say("HEIST_START — Leader starts the heist (minimum 2 players)")
        say("HEIST_ACTION <1-5> — Leader chooses the current encounter action")
        say("HEIST_CANCEL — Leader cancels recruitment before starting")
        say("CLERKS — Meet the bank clerks and view clerk encounters")
        say("PAY <username> <amount> — Send wallet coins to a same-City player (10,000/day)")
        say("PETS / PETSHOP — Browse 20 companions; PET <action> for care/training")
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
        say("HEIST START / CONTRIBUTE / LAUNCH — Legacy contribution-pool mini-event (separate from BANK_HEIST story mode)")
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

    elif cmd in ("ability", "special", "power"):
        cid = character_id(profile)
        ability = CHARACTER_ABILITIES.get(cid)
        if not ability:
            say("Select a character first to unlock a character ability.")
        elif profile.get("dead"):
            say("You need to revive before using your character ability.")
        else:
            ability_name, description = ability
            now = time.time()
            cooldown_until = float(profile.get("ability_cooldown", 0) or 0)
            if now < cooldown_until:
                remaining = int(cooldown_until - now)
                say(f"{ability_name} is recharging. Try again in {remaining // 60}m {remaining % 60}s.")
            else:
                result = ""
                if cid == "professor":
                    award_xp(profile, 120)
                    result = "Your brain cells clocked in. +120 XP."
                elif cid == "heartbreaker":
                    amount = random.randint(750, 1500)
                    profile["fampay"] += amount
                    result = f"The whole City fell for the pitch. +{amount:,} coins."
                elif cid == "uncle_jose":
                    profile.setdefault("inventory", {})["padlock"] = profile["inventory"].get("padlock", 0) + 1
                    result = "One old contact delivered a Padlock. Your wallet has connections."
                elif cid == "sleeping_ceo":
                    amount = random.randint(2000, 4000)
                    profile["fampay"] += amount
                    result = f"A mysterious envelope arrived. +{amount:,} coins. No questions asked."
                elif cid == "og":
                    profile.setdefault("inventory", {})["shield"] = profile["inventory"].get("shield", 0) + 1
                    result = "Tiny CEO approved one free Shield. Small boss, big budget."
                elif cid == "mystery_man":
                    if random.random() < 0.5:
                        amount = random.randint(1000, 2500)
                        profile["fampay"] += amount
                        result = f"The mystery envelope contained +{amount:,} coins. Nobody knows why."
                    else:
                        award_xp(profile, 100)
                        result = "The mystery envelope contained +100 XP. Knowledge? Suspicious."
                elif cid == "ancient_one":
                    loot = profile.setdefault("loot", {})
                    owned = [key for key, quantity in loot.items() if quantity > 0 and key in core.LOOT_ITEMS]
                    if owned:
                        key = random.choice(owned)
                        loot[key] -= 1
                        amount = core.LOOT_ITEMS[key]["sell_price"]
                        amount = character_bonus(profile, "sell", amount)
                        profile["fampay"] += amount
                        result = f"Appraised and sold one {core.LOOT_ITEMS[key]['name']}. +{amount:,} coins."
                    else:
                        profile["fampay"] += 1000
                        result = "No antiques in your bag. The appraiser paid a 1,000-coin consultation fee anyway."
                elif cid == "hello_kitty_boss":
                    profile["fampay"] += 1250
                    result = "The City paid its cuteness tax refund. +1,250 coins."
                elif cid == "npc":
                    profile.setdefault("inventory", {})["shield"] = profile["inventory"].get("shield", 0) + 1
                    award_xp(profile, 40)
                    result = "You stood perfectly still and somehow gained a Shield +40 XP. NPC lore."
                elif cid == "cat_whisperer":
                    loot_keys = list(core.LOOT_ITEMS)
                    if loot_keys:
                        key = random.choice(loot_keys)
                        profile.setdefault("loot", {})[key] = profile["loot"].get(key, 0) + 1
                        result = f"A cat dropped off {core.LOOT_ITEMS[key]['name']}. It refuses to elaborate."
                    else:
                        profile["fampay"] += 1000
                        result = "The cat left 1,000 coins instead. Meow-nificent."
                elif cid == "confused_citizen":
                    award_xp(profile, 180)
                    result = "Mew Mode activated. +180 XP. The gum-powered grind continues."
                elif cid == "security_guard":
                    inv = profile.setdefault("inventory", {})
                    inv["padlock"] = inv.get("padlock", 0) + 1
                    inv["shield"] = inv.get("shield", 0) + 1
                    result = "Emergency lockdown complete. +1 Padlock and +1 Shield."
                elif cid == "invingoppa":
                    profile["bank_max"] = int(profile.get("bank_max", 10000)) + 1500
                    result = f"The banker's stamp is approved. Bank capacity is now {profile['bank_max']:,} coins."
                elif cid == "drip_lord":
                    profile["fampay"] += 2000
                    result = "Anna's blessing has landed. +2,000 coins. ANNA SOWWWW."
                profile["ability_cooldown"] = now + ABILITY_COOLDOWN_SECONDS
                say(f"✨ {ability_name} ACTIVATED! {result}")
                say("Your next character ability is available in 1 hour.")
                commit()

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
        say("Use BUY <item_key> to purchase. Banknotes are consumed instantly; other items appear in your BAG.")

    elif cmd == "buy" and args:
        key = args[0].lower()
        item = core.SHOP_ITEMS.get(key)
        if not item:
            say("Item not found. Type `shop`.")
        else:
            price = int(item["price"] * 0.90) if character_id(profile) == "og" else item["price"]
            if profile["fampay"] < price:
                say("Not enough FamPay Balance.")
            else:
                profile["fampay"] -= price
                discount_note = " (10% Sam da Baby discount)" if character_id(profile) == "og" else ""
                if key == "banknote":
                    increase = 6000 if character_id(profile) == "invingoppa" else 5000
                    profile["bank_max"] = int(profile.get("bank_max", 5000)) + increase
                    say(f"BANKNOTE USED AUTOMATICALLY! Bank capacity increased by {increase:,} to {profile['bank_max']:,} coins. The note was consumed{discount_note}.")
                else:
                    profile["inventory"][key] = profile["inventory"].get(key, 0) + 1
                    say(f"Purchased {item['name']} for {price:,} coins{discount_note}.")
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
            earned = character_bonus(profile, "sell", item["sell_price"] * qty)
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
                pay = character_bonus(profile, "work", int(random.randint(*job["pay"]) * city_cfg.get("pay_mult", 1)))
                profile["fampay"] += pay
                profile["last_work"] = time.time()
                profile["work_reminder_sent"] = False
                award_xp(profile, 50)
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
                    payout = character_bonus(profile, "casino", int(amount * multiplier))
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
            payout = character_bonus(profile, "casino", int(amount * multiplier))
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
            award_xp(profile, 35)
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
                    # Crime payouts are deliberately much smaller to keep the economy balanced.
                    reward = character_bonus(profile, "crime", random.randint(1000, 8000))
                    profile["fampay"] += reward
                    award_xp(profile, 50)
                    say(f"💰 SMALL SCORE! Your fictional crime run paid {reward:,} coins and 50 XP.")
                elif outcome < 0.86:
                    lost = min(profile["fampay"], max(500, int(profile["fampay"] * random.uniform(0.20, 0.60))))
                    if profile["inventory"].get("padlock", 0) > 0:
                        profile["inventory"]["padlock"] -= 1
                        say("🥷 You got mugged on the way out, but your Padlock broke and protected your wallet!")
                    else:
                        if character_id(profile) == "uncle_jose":
                            lost = int(lost * 0.90)
                        elif character_id(profile) == "security_guard":
                            lost = int(lost * 0.85)
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
            award_xp(profile, 45)
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
        say("Use `bank_heist` to recruit your City for the multiplayer heist. The two INVINGOPPA apprentices are elite encounters.")

    elif cmd == "bank_heist":
        _heist_timeout_if_needed(data, room_code, room)
        existing = room.get("multiplayer_bank_heist", {})
        if existing.get("status") in ("recruiting", "decision", "between_rounds"):
            say("A City bank heist is already active. Use `heist_accept` to join if recruitment is open.")
        elif time.time() < float(data["users"].get(username, {}).get("bank_heist_cooldown", 0)):
            remain = int(data["users"].get(username, {}).get("bank_heist_cooldown", 0) - time.time())
            say(f"Your next bank heist is available in {remain//3600}h {(remain%3600)//60}m.")
        else:
            members = _active_city_members(data, room_code)
            if len(members) < 2:
                say("A bank heist needs a crew. Invite at least one other City member; solo heists are disabled.")
            else:
                heist = {"status":"recruiting","leader":username,"participants":[username],"created_at":time.time(),"round":0,"round_history":[],"pending_factor":1.0}
                room["multiplayer_bank_heist"] = heist
                invitees = list(members)
                _heist_mail(data, room_code, invitees, "BANK HEIST INVITATION", f"{username} is recruiting a bank-heist crew in {room.get('name','this City')}. Type `HEIST_ACCEPT` to join. The leader will decide when to start.")
                _heist_announce(room, f"🚨 {username} is recruiting a BANK HEIST crew! Type `HEIST_ACCEPT` to join. Minimum crew: 2. Leader: {username}.")
                say(f"Recruitment opened! Invitations mailed to {len(invitees)} City member(s). Type `HEIST_START` when at least 2 players have joined.")
        commit()

    elif cmd == "heist_accept":
        heist = room.get("multiplayer_bank_heist", {})
        if heist.get("status") != "recruiting":
            say("There is no open bank-heist recruitment in this City.")
        elif username == heist.get("leader") or username in heist.get("participants", []):
            say("You're already part of this crew.")
        elif username not in _active_city_members(data, room_code):
            say("You must be an active member of this City to join.")
        elif time.time() < float(data["users"].get(username, {}).get("bank_heist_cooldown", 0)):
            remain = int(data["users"].get(username, {}).get("bank_heist_cooldown", 0) - time.time())
            say(f"You are on bank-heist cooldown for another {remain//3600}h {(remain%3600)//60}m.")
        elif len(heist.get("participants", [])) >= 14:
            say("This crew is full.")
        else:
            heist.setdefault("participants", []).append(username)
            _heist_announce(room, f"{username} joined {heist.get('leader')}'s bank-heist crew. Crew: {len(heist['participants'])}.")
            _heist_mail(data, room_code, [heist.get("leader")], "NEW HEIST CREW MEMBER", f"{username} joined your crew. Current crew: {len(heist['participants'])}.")
            say(f"You joined the crew! Current participants: {', '.join(heist['participants'])}.")
        commit()

    elif cmd == "heist_cancel":
        heist = room.get("multiplayer_bank_heist", {})
        if heist.get("status") != "recruiting" or heist.get("leader") != username:
            say("Only the leader can cancel an active recruitment, and only before the heist starts.")
        else:
            names = list(heist.get("participants", []))
            _heist_mail(data, room_code, names, "BANK HEIST CANCELLED", f"{username} cancelled the recruitment. No cooldown was applied.")
            _heist_announce(room, f"{username} cancelled the bank-heist recruitment. No cooldown was applied.")
            room.pop("multiplayer_bank_heist", None)
            say("Recruitment cancelled. No participant received a cooldown.")
        commit()

    elif cmd == "heist_start":
        heist = room.get("multiplayer_bank_heist", {})
        if heist.get("status") != "recruiting":
            say("There is no recruiting heist to start.")
        elif heist.get("leader") != username:
            say(f"Only {heist.get('leader')} can start this heist.")
        elif len(heist.get("participants", [])) < 2:
            say("You cannot start alone. At least 2 players must accept.")
        else:
            eligible = []
            for member in heist["participants"]:
                if member in _active_city_members(data, room_code):
                    mp = get_profile(data, member, room_code)
                    if time.time() >= float(data["users"].get(member, {}).get("bank_heist_cooldown", 0)):
                        eligible.append(member)
            heist["participants"] = eligible
            if len(eligible) < 2:
                say("Fewer than 2 eligible players remain. Recruit another City member.")
            else:
                for member in eligible:
                    data["users"].setdefault(member, {})["bank_heist_cooldown"] = time.time() + 12 * 3600
                    get_profile(data, member, room_code)["bank_heist_cooldown"] = time.time() + 12 * 3600
                heist["status"] = "decision"
                heist["round"] = 0
                heist["round_history"] = []
                heist["pending_factor"] = 1.0
                _heist_announce(room, f"🏦 BANK HEIST STARTED! Leader: {username}. Crew: {', '.join(eligible)}.")
                _heist_begin_round(data, room_code, room, heist)
                say(f"Heist started with {len(eligible)} players. Round 1: {heist['scenario']['title']}")
                for i, choice in enumerate(heist["choices"], 1): say(f"{i}. {choice}")
                say("Only the leader may submit `HEIST_ACTION <1-5>`. The crew has 60 seconds to discuss.")
        commit()

    elif cmd == "heist_action":
        _heist_timeout_if_needed(data, room_code, room)
        heist = room.get("multiplayer_bank_heist", {})
        if heist.get("status") != "decision":
            say("There is no active decision round. The leader may use `HEIST_NEXT` after a completed encounter.")
        elif heist.get("leader") != username:
            say("Only the Heist Leader can decide the crew's action. Discuss your ideas in City Chat!")
        elif time.time() >= float(heist.get("deadline", 0)):
            say("The 60-second decision window expired. A random outcome has already been selected.")
        else:
            try: index = int(args[0]) - 1 if args else -1
            except ValueError: index = -1
            if not 0 <= index < 5:
                say("Choose one of the five displayed options: `HEIST_ACTION 1` through `HEIST_ACTION 5`.")
            else:
                chosen = heist.get("choices", [])[index]
                _heist_resolve(data, room_code, room, heist, choice_index=index)
                say(f"Leader chose: {chosen}.")
                if heist.get("status") == "between_rounds":
                    say(heist.get("last_result", "Encounter resolved."))
                    say("The next round is ready. Leader: use `HEIST_NEXT` when the crew is ready.")
                else:
                    say("The heist has concluded. Check your mailbox for your individual result.")
        commit()

    elif cmd == "heist_next":
        heist = room.get("multiplayer_bank_heist", {})
        if heist.get("status") != "between_rounds" or heist.get("leader") != username:
            say("Only the leader can start the next round after an encounter has resolved.")
        else:
            _heist_begin_round(data, room_code, room, heist)
            say(f"ROUND {heist['round']}: {heist['scenario']['title']}")
            for i, choice in enumerate(heist["choices"], 1): say(f"{i}. {choice}")
            say("60 seconds. Only the leader can submit `HEIST_ACTION <1-5>`.")
        commit()

    elif cmd == "pay":
        if len(args) < 2:
            say("Usage: `pay <username> <amount>`. Payments are same-City only and wallet-only.")
        else:
            target = args[0]
            try: amount = int(args[1])
            except ValueError: amount = 0
            daily = data["users"].setdefault(username, {}).setdefault("payment_daily", {"date":"", "sent":0})
            if daily.get("date") != _today_key(): daily.update({"date":_today_key(),"sent":0})
            sent_today = int(daily.get("sent", 0))
            if target == username: say("You cannot pay yourself.")
            elif target not in _active_city_members(data, room_code): say("Payments are only available to players currently in your City.")
            elif amount <= 0: say("Enter a positive whole-number payment.")
            elif amount > int(profile.get("fampay", 0)): say("Insufficient FamPay wallet balance. Bank funds cannot be used.")
            elif sent_today + amount > 10000: say(f"Daily payment cap: 10,000 coins. You have {max(0,10000-sent_today):,} coins left to send today.")
            else:
                recipient = get_profile(data, target, room_code)
                profile["fampay"] -= amount
                recipient["fampay"] = int(recipient.get("fampay", 0)) + amount
                daily["sent"] = sent_today + amount
                ref = secrets.token_hex(4).upper()
                stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
                record = {"reference":ref,"from":username,"to":target,"amount":amount,"timestamp":time.time()}
                profile.setdefault("payment_history", []).append(record)
                recipient.setdefault("payment_history", []).append(record)
                profile["payment_history"] = profile["payment_history"][-50:]
                recipient["payment_history"] = recipient["payment_history"][-50:]
                add_mail(profile, "PAYMENT SENT", f"You sent {amount:,} coins to {target}. Ref: {ref}. Time: {stamp}.", "payment")
                add_mail(recipient, "PAYMENT RECEIVED", f"You received {amount:,} coins from {username}. Ref: {ref}. Time: {stamp}.", "payment")
                say(f"Payment complete: {amount:,} coins sent to {target}. Reference: {ref}. Your daily sent total is {daily['sent']:,}/10,000.")
                _heist_announce(room, f"💸 {username} sent a payment to {target}.")
            commit()

    elif cmd in ("pets", "petshop"):
        say("🐾 PAUL'S PET PARADISE — 20 companions")
        for rarity in ("Common", "Uncommon", "Rare", "Legendary"):
            names = [f"{v['name']} ({v['game']})" for k,v in core.PET_CATALOG.items() if v['rarity']==rarity]
            say(f"{rarity}: " + ", ".join(names))
        say("Use `pet adopt <pet_id>` for available coin/quest pets. `pet supplies` lists care items.")

    elif cmd == "pet":
        sub = args[0].lower() if args else "list"
        pets = profile.setdefault("pets", [])
        if sub == "quest":
            quests = {
                "harvest": ("starter_harvest", "Starter Harvest", "Spend 500 coins on supplies and complete a 60% harvest challenge."),
                "jump": ("jumping_puzzle", "Jumping Puzzle", "Complete a timing puzzle to unlock Mini Mario."),
                "collectible": ("hidden_collectible", "Hidden Collectible", "Find a hidden City collectible to unlock Korok."),
                "resilience": ("resilience", "Resilience Trial", "Pass a resilience challenge to unlock Little Knight."),
                "arcade": ("arcade", "Arcade Challenge", "Win a fictional arcade challenge to unlock Mugman."),
                "multiplayer": ("multiplayer_event", "City Team Event", "Complete a multiplayer bank heist with a successful result to unlock Mini D.Va."),
                "riddle": ("riddle", "Mailbox Riddle", "Solve a secret riddle to unlock Sans."),
                "exploration": ("exploration", "Exploration Trail", "Pass an exploration challenge to unlock Teemo."),
            }
            if len(args) == 1:
                say("PET QUESTS — " + " | ".join(f"{k}: {v[1]}" for k,v in quests.items()))
                say("Use `pet quest <name>` to attempt a quest. City Team Event is unlocked by completing a successful multiplayer heist.")
            elif args[1].lower() not in quests:
                say("Quest not found. Use `pet quest` to see available quests.")
            else:
                qkey, qname, qdesc = quests[args[1].lower()]
                profile.setdefault("pet_quests", {})
                if profile["pet_quests"].get(qkey): say(f"{qname} is already complete.")
                elif qkey == "multiplayer_event": say("Complete a successful multiplayer bank heist to unlock this quest.")
                else:
                    fee = 500
                    if profile.get("fampay",0) < fee: say("You need 500 coins to enter a pet quest.")
                    else:
                        profile["fampay"] -= fee
                        success = random.random() < (0.62 if qkey in ("jumping_puzzle","riddle") else 0.72)
                        if success:
                            profile["pet_quests"][qkey] = True
                            say(f"QUEST COMPLETE: {qname}! You unlocked a new adoption path.")
                        else: say(f"{qname} challenge not completed this time. Try again later; the 500-coin entry fee was used.")
            commit()
        elif sub == "list":
            say(f"🐾 YOUR PET COLLECTION — {len(pets)}/5")
            for pet in pets:
                _pet_decay(pet)
                spec = core.PET_CATALOG.get(pet.get("species"), {})
                active = " · ACTIVE" if pet.get("id") == profile.get("active_pet_id") else ""
                say(f"{pet.get('name',spec.get('name','Pet'))} · Lv.{pet.get('level',1)} · Hunger {pet.get('hunger',0)} · Happiness {pet.get('happiness',0)} · Energy {pet.get('energy',0)}{active}")
            if not pets: say("You haven't adopted a pet yet. Visit `petshop`.")
        elif sub == "supplies":
            say("PET SUPPLIES")
            for key,(label,price) in core.PET_SUPPLIES.items(): say(f"{key} — {label}: {price:,} coins")
        elif sub == "adopt" and len(args) > 1:
            species = args[1].lower()
            spec = core.PET_CATALOG.get(species)
            if not spec: say("Pet not found. Use `petshop` to see the collection.")
            elif len(pets) >= 5: say("Your pet collection is full (5/5). Trade a pet before adopting another.")
            elif any(p.get("species") == species for p in pets): say("You already own this pet. Duplicates must be traded, not adopted twice.")
            elif species == "junimo" and not profile.get("pet_quests", {}).get("starter_harvest"): say("Quest required: complete the starter harvest quest first.")
            elif species == "mini_mario" and not profile.get("pet_quests", {}).get("jumping_puzzle"): say("Quest required: complete the jumping puzzle first.")
            elif species == "korok" and not profile.get("pet_quests", {}).get("hidden_collectible"): say("Quest required: find a hidden City collectible first.")
            elif species == "little_knight" and not profile.get("pet_quests", {}).get("resilience"): say("Quest required: complete the resilience challenge first.")
            elif species == "mini_chamber" and int(profile.get("level",1)) < 5: say("Mini Chamber unlocks at Level 5.")
            elif species == "mugman" and not profile.get("pet_quests", {}).get("arcade"): say("Quest required: complete the special arcade quest first.")
            elif species == "mini_dva" and not profile.get("pet_quests", {}).get("multiplayer_event"): say("Quest required: win a multiplayer City event first.")
            elif species == "sans" and not profile.get("pet_quests", {}).get("riddle"): say("Quest required: solve the secret mailbox riddle first.")
            elif species == "teemo" and not profile.get("pet_quests", {}).get("exploration"): say("Quest required: complete the exploration quest first.")
            elif species == "peely" and not profile.get("pet_quests", {}).get("seasonal") and spec["price"] <= 0: say("Peely is available during a seasonal event.")
            elif int(profile.get("fampay",0)) < int(spec["price"]): say(f"You need {spec['price']:,} coins to adopt {spec['name']}.")
            else:
                profile["fampay"] -= int(spec["price"])
                pet = _pet_adopt(profile, species)
                say(f"Adopted {pet['name']} from {spec['game']}! It is now Level 1. Use `pet activate {pet['id']}` to select it.")
            commit()
        elif sub == "activate" and len(args) > 1:
            pet = _pet_find(profile, args[1])
            if not pet: say("Pet ID not found. Use `pet list`.")
            else:
                profile["active_pet_id"] = pet["id"]
                say(f"{pet['name']} is now your active companion.")
            commit()
        elif sub == "rename" and len(args) > 2:
            pet = _pet_find(profile, args[1])
            new_name = " ".join(args[2:])[:24]
            if not pet: say("Pet ID not found.")
            elif not new_name: say("Enter a name.")
            else: pet["name"] = new_name; say(f"Pet renamed to {new_name}.")
            commit()
        elif sub == "buy" and len(args) > 1:
            key = args[1].lower()
            if key not in core.PET_SUPPLIES: say("Supply not found. Use `pet supplies`.")
            else:
                label, price = core.PET_SUPPLIES[key]
                if profile["fampay"] < price: say(f"You need {price:,} coins.")
                else:
                    profile["fampay"] -= price
                    supplies = profile.setdefault("pet_supplies", {})
                    supplies[key] = int(supplies.get(key,0)) + 1
                    say(f"Bought {label}. You now have {supplies[key]}.")
            commit()
        elif sub in ("feed", "play", "rest", "train") and len(args) > 1:
            pet = _pet_find(profile, args[1])
            if not pet: say("Pet ID not found. Use `pet list`.")
            else:
                _pet_decay(pet)
                if sub == "feed":
                    item = args[2].lower() if len(args)>2 else core.PET_CATALOG.get(pet['species'],{}).get('care_item','snack')
                    supplies = profile.setdefault("pet_supplies", {})
                    if supplies.get(item,0) <= 0: say(f"You need `{item}`. Buy it using `pet buy {item}`. Use `pet supplies` for the list.")
                    else:
                        supplies[item] -= 1; pet["hunger"] = min(100,pet.get("hunger",0)+35); pet["happiness"] = min(100,pet.get("happiness",0)+5); say(f"You fed {pet['name']}. Hunger and happiness improved.")
                elif sub == "play":
                    pet["happiness"] = min(100,pet.get("happiness",0)+25); pet["energy"] = max(0,pet.get("energy",0)-12); say(f"You played with {pet['name']}. Happiness increased; energy dipped a little.")
                elif sub == "rest":
                    pet["energy"] = min(100,pet.get("energy",0)+35); say(f"{pet['name']} rested and regained energy.")
                else:
                    if pet.get("energy",0) < 20: say("Your pet needs more energy before training.")
                    else:
                        pet["energy"] -= 20; pet["xp"] = int(pet.get("xp",0))+50
                        if pet["xp"] >= int(pet.get("level",1))*150 and pet.get("level",1)<5:
                            pet["xp"] -= int(pet.get("level",1))*150; pet["level"] += 1; say(f"{pet['name']} reached Level {pet['level']}!")
                        else: say(f"Training complete! {pet['name']} gained 50 pet XP.")
                pet["last_update"] = time.time()
            commit()
        elif sub == "trade" and len(args) > 2:
            target, pet_id = args[1], args[2]
            pet = _pet_find(profile, pet_id)
            if target == username or target not in _active_city_members(data, room_code): say("Pet trades are only allowed with another player in your City.")
            elif not pet: say("Pet ID not found.")
            elif profile.get("pet_trade_offer"): say("You already have a pending pet trade.")
            else:
                other = get_profile(data,target,room_code)
                if other.get("pet_trade_offer"): say("That player already has a pending pet trade.")
                elif len(other.get("pets",[])) >= 5: say("That player's pet collection is full.")
                else:
                    profile["pet_trade_offer"]={"to":target,"pet_id":pet_id,"from":username,"created_at":time.time()}
                    add_mail(other,"PET TRADE OFFER",f"{username} offers you {pet['name']}. Type `pet accept {username}` to accept or `pet decline {username}` to decline.","pet_trade")
                    say(f"Trade offer sent to {target}. They must accept before the pet moves.")
            commit()
        elif sub == "cancel_trade":
            offer = profile.get("pet_trade_offer")
            if not offer: say("You have no outgoing pet trade offer.")
            else:
                target = offer.get("to")
                profile["pet_trade_offer"] = None
                if target in _active_city_members(data, room_code):
                    add_mail(get_profile(data,target,room_code),"PET TRADE CANCELLED",f"{username} cancelled the pet trade offer.","pet_trade")
                say("Your pet trade offer was cancelled.")
            commit()
        elif sub in ("accept","decline") and len(args)>1:
            sender=args[1]; sender_profile=get_profile(data,sender,room_code) if sender in _active_city_members(data,room_code) else None
            offer=sender_profile.get("pet_trade_offer") if sender_profile else None
            if not offer or offer.get("to")!=username: say("No matching pet trade offer was found.")
            elif sub=="decline":
                sender_profile["pet_trade_offer"]=None; add_mail(sender_profile,"PET TRADE DECLINED",f"{username} declined your pet trade offer.","pet_trade"); say("Trade declined.")
            else:
                pet=_pet_find(sender_profile,offer.get("pet_id"))
                if len(pets)>=5: say("Your collection is full. Make room before accepting.")
                elif not pet: say("The offered pet is no longer available.")
                else:
                    sender_profile["pets"].remove(pet); pets.append(pet)
                    if sender_profile.get("active_pet_id")==pet["id"]: sender_profile["active_pet_id"]=None
                    sender_profile["pet_trade_offer"]=None
                    add_mail(sender_profile,"PET TRADE COMPLETE",f"{username} accepted the trade. {pet['name']} is now in their collection.","pet_trade")
                    add_mail(profile,"PET TRADE COMPLETE",f"You received {pet['name']} from {sender}.","pet_trade")
                    say(f"Trade complete! {pet['name']} is now yours.")
            commit()
        else:
            say("Pet commands: `pet list`, `pet adopt <pet_id>`, `pet activate <id>`, `pet rename <id> <name>`, `pet buy <supply>`, `pet feed/play/rest/train <id>`, `pet trade <username> <id>`, `pet accept/decline <username>`, `pet cancel_trade`.")

    elif cmd == "daily":
        now = time.time()
        if now - profile.get("last_daily", 0) < 86400:
            remaining = int(86400 - (now - profile.get("last_daily", 0)))
            say(f"Daily reward already claimed. Try again in about {remaining // 3600}h {(remaining % 3600) // 60}m.")
        else:
            reward = 1000 + profile.get("daily_streak", 0) * 100
            reward = character_bonus(profile, "daily", reward)
            profile["fampay"] += reward
            daily_xp = _pet_bonus(profile, "daily_xp", 25)
            award_xp(profile, daily_xp)
            profile["last_daily"] = now
            profile["daily_streak"] = profile.get("daily_streak", 0) + 1
            say(f"Daily reward claimed: +{reward:,} coins and +{daily_xp} XP.")
            commit()

    elif cmd == "beg":
        reward = random.randint(50, 350)
        if random.random() < 0.3:
            say("Nobody gave you anything this time.")
        else:
            reward = character_bonus(profile, "beg", reward)
            profile["fampay"] += reward
            award_xp(profile, 20)
            say(f"Someone helped you out: +{reward:,} coins and 20 XP.")
            commit()

    elif cmd in ("dig", "hunt", "fish"):
        required = {"dig": "shovel", "hunt": "hunting_rifle", "fish": "fishing_rod"}[cmd]
        if profile["inventory"].get(required, 0) <= 0:
            say(f"You need {core.SHOP_ITEMS[required]['name']}. Buy it from `shop`.")
        else:
            if cmd == "hunt":
                pool = core.HUNT_COMMON if random.random() < 0.72 else core.HUNT_BOSSES
                encounter = random.choice(pool)
            elif cmd == "fish":
                pool = core.FISH_COMMON if random.random() < 0.72 else core.FISH_BOSSES
                encounter = random.choice(pool)
            else:
                encounter = random.choice(core.DIG_ANIMALS)
            if encounter.get("attack_chance", 0) and random.random() < encounter["attack_chance"]:
                loss = min(profile["fampay"], encounter.get("attack_loss", 150))
                profile["fampay"] -= loss
                say(f"{encounter['name']} fought back! You lost {loss:,} coins and had to retreat.")
            else:
                reward = character_bonus(profile, "wildlife", random.randint(*encounter.get("reward_range", (250, 1200))))
                profile["fampay"] += reward
                drop = encounter.get("drop")
                if drop and drop in core.LOOT_ITEMS:
                    profile["loot"][drop] = profile["loot"].get(drop, 0) + 1
                    drop_text = f" Loot: {core.LOOT_ITEMS[drop]['name']}."
                else:
                    drop_text = " No loot dropped this time."
                award_xp(profile, 55)
                say(f"{encounter['name']}: earned {reward:,} coins + 55 XP.{drop_text}")
            commit()

    elif cmd in ("room", "rooms") and args:
        sub = args[0].lower()
        if sub == "list":
            for code, listed_room in data["rooms"].items():
                if code == GLOBAL_ROOM or listed_room.get("is_public", False) or username in listed_room.get("members", []):
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
            visibility = st.radio("Visibility", ["Private", "Public"], horizontal=True, key="sidebar_city_visibility")
            create = st.form_submit_button("Create City", use_container_width=True)
        if create:
            code = create_city(data, username, city_name, preset, visibility == "Public")
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
        with st.expander("📘 USERS MANUAL — How to play", expanded=False):
            st.markdown("""
**START HERE**
- `help` — compact command list.
- `ability` — activate your selected character's unique power; recharges after 1 hour.
- `bal` — wallet, bank, level, XP and job.
- `bag` — tools, items and collected loot.
- `players` — see who is in this City.

**MONEY & PROGRESSION**
- `daily` — claim one daily reward when its timer resets.
- `beg` — ask the City for a small random reward.
- `work` — complete a shift for your selected job; cooldown and attendance rules apply.
- `jobs` / `apply <job_id>` — browse jobs and apply if your level is high enough.
- `deposit <amount>` / `withdraw <amount>` — move coins between FamPay and your bank.
- `buy <item_key>` — purchase a shop item. Banknotes are consumed instantly and add bank capacity.
- `sell <loot_key> [quantity]` — sell collected loot for coins.
- `shop` — browse items grouped by category.

**ACTIVITIES**
- `hunt` — wildlife encounter; requires a Hunting Rifle. Some animals may attack and some give no loot.
- `fish` — fishing encounter; requires a Fishing Rod. Some catches may fight back or give no loot.
- `dig` — underground discovery; requires a Shovel.
- `crime` — fictional high-risk money event with possible rewards, fines or a game-only character status consequence.
- `casino <game> <amount>` — play a virtual-coin mini-game. `casino list` shows games.
- `crypto` — view the fictional SCAMCOIN market; use its buy/sell subcommands.
- `tax_fraud` — fictional random tax-office event.
- `bank_heist`, `heist_accept`, `heist_start`, `heist_action 1-5`, `heist_next`, `heist_cancel` — City-wide story-based bank heist. Minimum 2 players; leader-only decisions; 60-second rounds; 12-hour participant cooldown.
- `pet quest` — browse adoption quests; `pet quest <name>` — attempt one.
- `pay <username> <amount>` — send wallet-only coins to a same-City player; 10,000 daily cap.
- `petshop` / `pet` — adopt and care for pets, train them, and trade with City members.

**CITY & SOCIAL**
- `rob <username>` — attempt a fictional player-to-player wallet robbery within your City.
- `heist start` / `heist contribute <amount>` / `heist launch` — run a team event with at least two contributors.
- `leaderboard` — rank current City members by wallet + bank balance.
- `mailbox` — read job notices and messages; use `mailbox read <number>` or `mailbox clear`.
- `room list` / `room join <code>` — list/join Cities by Party Code.
- `revive` — return to play if your character is out of action.

**CHARACTER ABILITIES**
- THE PROFESSOR — `EXAM CRAM`: +120 XP.
- THE RIZZLER — `RIZZ STORM`: +750–1,500 coins.
- UNCLE JOSE — `OLD CONTACTS`: +1 Padlock.
- THE NAKED MAFIA LEADER — `MAFIA ENVELOPE`: +2,000–4,000 coins.
- SAM DA BABY — `TINY CEO SUBSIDY`: +1 Shield.
- THE MYSTERY MAN — `MYSTERY PAYOUT`: random coin or XP reward.
- THE ANCIENT ONE — `ANTIQUE APPRAISAL`: sells one random loot item, or pays 1,000 coins if you have no loot.
- HELLO KITTY FINAL BOSS — `CUTENESS TAX REFUND`: +1,250 coins.
- THE NPC — `MAIN CHARACTER MOMENT`: +1 Shield and +40 XP.
- THE CAT WHISPERER — `PURRFECT DELIVERY`: +1 random loot item.
- Paul mogger — `MEW MODE`: +180 XP.
- THE SECURITY GUARD — `EMERGENCY LOCKDOWN`: +1 Padlock and +1 Shield.
- INVINGOPPA — `BANKER'S BLESSING`: +1,500 bank capacity.
- Chikko chezhiyanin magan — `ANNA'S BLESSING`: +2,000 coins.

**IMPORTANT**
- Coins are fictional game currency; no real money is involved.
- Public Cities appear in the lobby. Private Cities stay hidden and need a Party Code.
- Character perks are passive and differ by character. Each character also has one active `ability` with a 1-hour cooldown.
            """)
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
    city_created = float(room.get("created_at", time.time()))
    clock_html = f"""<div style='margin:0 0 16px;padding:12px 16px;border:1px solid rgba(125,155,210,.28);border-radius:14px;background:rgba(12,20,34,.88);color:#dce8fb;font-family:monospace'>
    <div style='font-size:.72rem;letter-spacing:2px;color:#9dbcf0;font-weight:800'>FAHAAN TIMEZONE</div>
    <div id='fahaan-clock' style='font-size:1.3rem;font-weight:800;margin-top:4px'>Loading City clock…</div>
    <div style='font-size:.72rem;color:#9eacc1;margin-top:3px'>Elapsed time since this City was created</div></div>
    <script>
    const start = {city_created * 1000};
    const target = document.getElementById('fahaan-clock');
    function tickFahaan() {{ const seconds = Math.max(0, Math.floor((Date.now()-start)/1000));
      const day = Math.floor(seconds/86400)+1; const within = seconds%86400;
      const hh=String(Math.floor(within/3600)).padStart(2,'0');
      const mm=String(Math.floor((within%3600)/60)).padStart(2,'0');
      const ss=String(within%60).padStart(2,'0');
      target.textContent = `DAY ${{day}} · ${{hh}}:${{mm}}:${{ss}}`; }}
    tickFahaan(); setInterval(tickFahaan,1000);
    </script>"""
    st.components.v1.html(clock_html, height=105)

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("FamPay Balance", f"🪙 {profile['fampay']:,}")
    metric2.metric("FamPay Account", f"🏦 {profile['bank']:,}")
    metric3.metric("Level", profile["level"])
    metric4.metric("XP", f"{profile['xp']}/{profile['level'] * 300}")

    # Resolve expired heist decision windows whenever a member refreshes the app.
    _heist_timeout_if_needed(data, room_code, room)
    active_heist = room.get("multiplayer_bank_heist", {})
    if active_heist.get("status") in ("recruiting", "decision", "between_rounds"):
        with st.container(border=True):
            st.markdown("### 🏦 LIVE CITY BANK HEIST")
            st.write(f"**Leader:** {active_heist.get('leader')} · **Crew:** {', '.join(active_heist.get('participants', []))}")
            if active_heist.get("status") == "recruiting":
                st.info("Recruitment is open. Players can type `HEIST_ACCEPT`. The leader starts with `HEIST_START`.")
            elif active_heist.get("status") == "decision":
                st.warning(f"ROUND {active_heist.get('round', 1)} · {active_heist.get('scenario', {}).get('title', '')}")
                remaining = max(0, int(float(active_heist.get('deadline', 0)) - time.time()))
                st.markdown(f"**Decision window: {remaining} seconds** · Only the leader can decide.")
                timer_html = f"""<div style='font:700 20px monospace;color:#f0c36d'>⏳ <span id='heist-countdown'>{remaining}</span>s remaining</div><script>(function(){{let n={remaining};const el=document.getElementById('heist-countdown');const t=setInterval(()=>{{n=Math.max(0,n-1);if(el)el.textContent=n;if(n<=0){{clearInterval(t);try{{window.parent.location.reload();}}catch(e){{}}}}}},1000);}})();</script>"""
                st.components.v1.html(timer_html, height=42)
                for i, choice in enumerate(active_heist.get("choices", []), 1):
                    st.write(f"{i}. {choice}")
                st.caption("Discuss in City Chat. Leader submits `HEIST_ACTION 1` through `HEIST_ACTION 5`.")
                if st.button("↻ Refresh heist timer", key="refresh_heist_timer"):
                    st.rerun()
            elif active_heist.get("status") == "between_rounds":
                st.info(active_heist.get("last_result", "The encounter is complete."))
                if username == active_heist.get("leader"):
                    if st.button("Start next round", key="heist_next_round"):
                        execute_command(data, username, room_code, room, profile, city_cfg, "heist_next")
                        st.rerun()
    game_tab, chat_tab, people_tab, pets_tab = st.tabs(["🎮 GAME", "💬 CITY CHAT", "👥 PEOPLE & PAYMENTS", "🐾 PETS"])

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
                st.caption(f"Speciality: {CHARACTERS[char_index][3]}")
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

    with people_tab:
        st.markdown("### 👥 City Members & Wallet Payments")
        st.caption("Profiles reveal wallet balance and bag only. Bank balance remains private.")
        city_members = [m for m in _active_city_members(data, room_code) if m != username]
        if not city_members:
            st.info("No other active players are in this City yet.")
        else:
            for member in city_members:
                member_prof = get_profile(data, member, room_code)
                active_pet = next((p for p in member_prof.get("pets", []) if p.get("id") == member_prof.get("active_pet_id")), None)
                active_pet_name = active_pet.get("name") if active_pet else "No active pet"
                if st.button(f"👤 {member} · {active_pet_name} · View profile", key=f"open_profile_{member}", use_container_width=True):
                    st.session_state["profile_view_target"] = member
            selected_player = st.session_state.get("profile_view_target")
            if selected_player not in city_members:
                selected_player = city_members[0]
            target_profile = get_profile(data, selected_player, room_code)
            target_char = next((x for x in CHARACTERS if x[0] == target_profile.get("character_id")), None)
            c1, c2, c3 = st.columns(3)
            c1.metric("Player", selected_player)
            c2.metric("Wallet", f"🪙 {int(target_profile.get('fampay',0)):,}")
            c3.metric("Level", int(target_profile.get("level",1)))
            if target_char: st.caption(f"Character: {target_char[1]}")
            st.markdown("**Bag / inventory**")
            inv = target_profile.get("inventory", {})
            loot = target_profile.get("loot", {})
            bag_items = [(core.SHOP_ITEMS.get(k,{}).get("name",k),v) for k,v in inv.items() if int(v)>0]
            bag_items += [(core.LOOT_ITEMS.get(k,{}).get("name",k),v) for k,v in loot.items() if int(v)>0]
            st.write(" · ".join(f"{name} ×{count}" for name,count in bag_items) if bag_items else "Bag is empty.")
            target_pets = target_profile.get("pets", [])
            if target_pets:
                st.write("**Pets:** " + ", ".join(f"{p.get('name','Pet')} (Lv.{p.get('level',1)})" + (" ★ Active" if p.get("id")==target_profile.get("active_pet_id") else "") for p in target_pets))
            else:
                st.write("**Pets:** None")
            st.divider()
            st.markdown("**Send FamPay**")
            daily = data["users"].setdefault(username, {}).setdefault("payment_daily", {"date":"","sent":0})
            if daily.get("date") != _today_key(): daily.update({"date":_today_key(),"sent":0})
            remaining_limit = max(0,10000-int(daily.get("sent",0)))
            st.caption(f"Wallet: {int(profile.get('fampay',0)):,} · Daily sending allowance remaining: {remaining_limit:,}/10,000 coins")
            with st.form("player_payment_form", clear_on_submit=True):
                pay_amount = st.number_input("Amount to send", min_value=1, max_value=max(1,min(10000,int(profile.get("fampay",0)),remaining_limit)), value=1, step=100)
                pay_submit = st.form_submit_button(f"💸 PAY {selected_player}", type="primary", use_container_width=True)
            if pay_submit:
                execute_command(data, username, room_code, room, profile, city_cfg, f"pay {selected_player} {int(pay_amount)}")
                st.success("Payment command processed. Check your mailbox for the receipt.")
                save(data)
                st.rerun()
            with st.expander("Recent payment history"):
                history = profile.get("payment_history", [])
                if not history: st.caption("No payments yet.")
                for item in reversed(history[-10:]):
                    direction = "Sent" if item.get("from")==username else "Received"
                    st.write(f"{direction} {int(item.get('amount',0)):,} coins · {item.get('from')} → {item.get('to')} · Ref {item.get('reference')}")

    with pets_tab:
        st.markdown("### 🐾 PAUL'S PET PARADISE")
        st.caption("Collect up to five pets. One active companion provides a bonus. Care stats decay gradually; pets never die or disappear.")
        pet_col1, pet_col2 = st.columns([1.2,1])
        with pet_col1:
            st.markdown("#### Your collection")
            pets = profile.setdefault("pets", [])
            for pet in pets:
                _pet_decay(pet)
                spec = core.PET_CATALOG.get(pet.get("species"), {})
                active = pet.get("id") == profile.get("active_pet_id")
                with st.container(border=True):
                    st.markdown(f"**{pet.get('name',spec.get('name','Pet'))}** · {spec.get('game','Game')} · {spec.get('rarity','Common')} {'⭐ ACTIVE' if active else ''}")
                    st.caption(f"Level {pet.get('level',1)} · {spec.get('speciality','Companion')} · {spec.get('description','')}")
                    st.progress(max(0,min(100,int(pet.get('hunger',0))))/100, text=f"Hunger {int(pet.get('hunger',0))}/100")
                    st.progress(max(0,min(100,int(pet.get('happiness',0))))/100, text=f"Happiness {int(pet.get('happiness',0))}/100")
                    st.progress(max(0,min(100,int(pet.get('energy',0))))/100, text=f"Energy {int(pet.get('energy',0))}/100")
                    b1,b2,b3,b4 = st.columns(4)
                    if b1.button("Feed",key=f"pet_feed_{pet['id']}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet feed {pet['id']}"); save(data); st.rerun()
                    if b2.button("Play",key=f"pet_play_{pet['id']}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet play {pet['id']}"); save(data); st.rerun()
                    if b3.button("Rest",key=f"pet_rest_{pet['id']}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet rest {pet['id']}"); save(data); st.rerun()
                    if b4.button("Train",key=f"pet_train_{pet['id']}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet train {pet['id']}"); save(data); st.rerun()
                    if not active and st.button("Set active",key=f"pet_activate_{pet['id']}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet activate {pet['id']}"); save(data); st.rerun()
            if not pets: st.info("No pets yet. Adopt your first companion from the catalogue.")
        with pet_col2:
            st.markdown("#### Adoption catalogue")
            for rarity in ("Common","Uncommon","Rare","Legendary"):
                with st.expander(f"{rarity} pets", expanded=(rarity=="Common")):
                    for species,spec in core.PET_CATALOG.items():
                        if spec["rarity"] != rarity: continue
                        st.markdown(f"**{spec['name']}** · {spec['game']}")
                        st.caption(f"{spec['speciality']} · +{int(spec['bonus']*100)}% {spec['bonus_activity']} · {spec['adoption']}")
                        st.caption(spec["description"])
                        owned = any(p.get("species")==species for p in pets)
                        if st.button(f"Adopt · {spec['price']:,} coins",key=f"adopt_{species}",disabled=owned or len(pets)>=5 or profile.get('fampay',0)<spec['price']):
                            execute_command(data,username,room_code,room,profile,city_cfg,f"pet adopt {species}"); save(data); st.rerun()
            with st.expander("Pet supplies"):
                for key,(label,price) in core.PET_SUPPLIES.items():
                    if st.button(f"Buy {label} · {price:,}",key=f"supply_{key}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet buy {key}"); save(data); st.rerun()
                st.caption("Your supplies: " + (", ".join(f"{core.PET_SUPPLIES.get(k,(k,0))[0]} ×{v}" for k,v in profile.get('pet_supplies',{}).items() if v) or "none"))
            with st.expander("Trade a pet"):
                if pets:
                    trade_target = st.selectbox("Trade with", city_members, key="pet_trade_target") if city_members else None
                    trade_pet = st.selectbox("Your pet", [p['id'] for p in pets], format_func=lambda pid: next((p['name'] for p in pets if p['id']==pid),pid), key="pet_trade_pet")
                    if trade_target and st.button("Send trade offer",key="send_pet_trade"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet trade {trade_target} {trade_pet}"); save(data); st.rerun()
                else: st.caption("Adopt a pet before trading.")
                incoming=[]
                for sender in city_members:
                    offer=get_profile(data,sender,room_code).get("pet_trade_offer")
                    if offer and offer.get("to")==username: incoming.append((sender,offer))
                for sender,offer in incoming:
                    pet=_pet_find(get_profile(data,sender,room_code),offer.get("pet_id"))
                    st.write(f"Offer from **{sender}**: {pet.get('name') if pet else 'Pet unavailable'}")
                    ca,cd=st.columns(2)
                    if ca.button("Accept",key=f"accept_trade_{sender}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet accept {sender}"); save(data); st.rerun()
                    if cd.button("Decline",key=f"decline_trade_{sender}"):
                        execute_command(data,username,room_code,room,profile,city_cfg,f"pet decline {sender}"); save(data); st.rerun()

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
