
import contextlib
import io
import json
import os
import random
import secrets
import time
from pathlib import Path

import streamlit as st
import game_core as core


# ============================================================
# CONFIGURATION
# ============================================================

BASE = Path(__file__).parent
DATA_FILE = BASE / "data" / "scam_jose_paul_save.json"
core.DATA_FILE = str(DATA_FILE)

MAX_PLAYERS = 14

st.set_page_config(
    page_title="SCAM JOSE PAUL",
    page_icon="🪙",
    layout="wide"
)

st.markdown("""
<style>
.stApp {
    background: radial-gradient(
        circle at 15% 0%,
        #202b45 0,
        #10131d 38%,
        #0b0e14 100%
    );
    color: #f4f6fb;
}
[data-testid="stSidebar"] {
    background: #111827;
}
.block-container {
    padding-top: 1.5rem;
    max-width: 1400px;
}
div[data-testid="stMetric"] {
    background: #171e2d;
    padding: 16px;
    border: 1px solid #2b3549;
    border-radius: 14px;
}
.stButton > button {
    border-radius: 10px;
    border: 1px solid #3b4963;
    min-height: 42px;
}
.stTextInput input {
    background: #171e2d;
    border: 1px solid #3b4963;
    border-radius: 10px;
}
div[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px;
}
.command-output {
    background: #111827;
    border: 1px solid #303c53;
    border-radius: 12px;
    padding: 15px;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# CHARACTERS
# ============================================================

CHARACTERS = [
    ("professor", "THE PROFESSOR",
     "Has 47 unfinished degrees and still asks Google how to boil water.",
     "Looking suspiciously intelligent."),

    ("heartbreaker", "THE HEARTBREAKER",
     "Joined the City to make money. Left with three friendship requests.",
     "Emotional damage."),

    ("uncle_jose", "UNCLE JOSE",
     "Retired businessman. Wanted in 4 neighbourhood WhatsApp groups.",
     "Unsolicited life advice."),

    ("sleeping_ceo", "THE SLEEPING CEO",
     "Runs a multinational corporation entirely from his bed.",
     "Maximum productivity, minimum movement."),

    ("og", "THE OG",
     "Been here since the tutorial. Still hasn't figured out the tutorial.",
     "Veteran confidence."),

    ("mystery_man", "THE MYSTERY MAN",
     "Nobody knows who he is. Not even his own profile picture.",
     "Classified information."),

    ("ancient_one", "THE ANCIENT ONE",
     "His account is older than the City's economy.",
     "Historical knowledge (questionable)."),

    ("hello_kitty_boss", "HELLO KITTY FINAL BOSS",
     "Cute appearance. The financial crimes department has opened a file.",
     "Unexpected chaos."),

    ("npc", "THE NPC",
     "Stares into the distance. Somehow owns a mansion.",
     "Random encounters."),

    ("cat_whisperer", "THE CAT WHISPERER",
     "Doesn't trust humans. Has a suspiciously large fish collection.",
     "Animal connections."),

    ("confused_citizen", "THE CONFUSED CITIZEN",
     "Entered Perambur looking for the supermarket. Has been missing for 3 days.",
     "Getting lost."),

    ("security_guard", "THE SECURITY GUARD",
     "Looks like he knows something. Refuses to elaborate.",
     "Intimidating presence."),

    ("invingoppa", "INVINGOPPA",
     "The bank clerk has arrived. Your loan application was rejected before you even opened it.",
     "Financial intimidation."),

    ("drip_lord", "THE DRIP LORD",
     "Spends 90% of his salary on accessories. 10% on rent.",
     "Fashion over finances.")
]


# ============================================================
# DATA MANAGEMENT
# ============================================================

def load_data():
    data = core.load_all_data()

    data.setdefault("users", {})
    data.setdefault("rooms", {})

    if "GLOBAL_HUB" not in data["rooms"]:
        data["rooms"]["GLOBAL_HUB"] = {
            "host": "SYSTEM",
            "name": "Global Hub",
            "preset": "egmore",
            "is_public": True,
            "members": [],
            "started": True,
            "heist": {
                "active": False,
                "contributions": {}
            }
        }

    # Older rooms remain accessible.
    for code, room in data["rooms"].items():
        room.setdefault("members", [])
        room.setdefault("heist", {
            "active": False,
            "contributions": {}
        })

        # Existing rooms are considered already started.
        room.setdefault("started", True)

    # Migrate old single-player saves.
    legacy = [
        k for k, v in list(data.items())
        if isinstance(v, dict)
        and "wallet" in v
        and k not in ("users", "rooms")
    ]

    for name in legacy:
        old = data.pop(name)

        if name not in data["users"]:
            data["users"][name] = {
                "password_hash": core.hash_password(
                    secrets.token_urlsafe(18)
                ),
                "current_room": "GLOBAL_HUB",
                "room_profiles": {}
            }

        prof = core.get_default_room_profile("egmore")

        for key, val in old.items():
            if key == "wallet":
                prof["fampay"] = val
            elif key in prof:
                prof[key] = val

        data["users"][name].setdefault(
            "room_profiles", {}
        )["GLOBAL_HUB"] = prof

        data["users"][name].setdefault(
            "current_room", "GLOBAL_HUB"
        )

        if name not in data["rooms"]["GLOBAL_HUB"]["members"]:
            data["rooms"]["GLOBAL_HUB"]["members"].append(name)

    return data


def save(data):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    temporary = str(DATA_FILE) + ".tmp"

    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    os.replace(temporary, DATA_FILE)


def get_session(data, username):
    user = data["users"][username]

    code = user.get("current_room")

    if not code or code not in data["rooms"]:
        return None, None, None, None, None

    room = data["rooms"][code]

    profile = core.get_user_room_profile(
        data, username, code
    )

    city_cfg = core.CITIES.get(
        room.get("preset", "egmore"),
        core.CITIES["egmore"]
    )

    return user, room, profile, code, city_cfg


def remove_from_old_room(data, username, new_code):
    user = data["users"][username]
    old_code = user.get("current_room")

    if old_code in data["rooms"] and old_code != new_code:
        old_room = data["rooms"][old_code]

        if username in old_room.get("members", []):
            old_room["members"].remove(username)


def generate_room_code(data):
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"

    while True:
        code = "".join(
            random.choices(alphabet, k=6)
        )

        if code not in data["rooms"]:
            return code


# ============================================================
# LOGIN
# ============================================================

def login_screen():
    st.title("🪙 SCAM JOSE PAUL")
    st.caption(
        "A city-based economy game. "
        "Your progress is separate in each City."
    )

    with st.container(border=True):
        mode = st.radio(
            "Account",
            ["Login", "Create account"],
            horizontal=True
        )

        username = st.text_input(
            "Username",
            max_chars=24
        )

        password = st.text_input(
            "Password",
            type="password"
        )

        if st.button(
            "Continue",
            type="primary",
            use_container_width=True
        ):
            if not username.strip() or not password:
                st.error("Enter both a username and password.")
                return

            data = load_data()
            name = username.strip()

            if mode == "Create account":
                if name in data["users"]:
                    st.error("That username is already taken.")
                    return

                data["users"][name] = {
                    "password_hash": core.hash_password(password),
                    "last_active": time.time(),
                    "current_room": None,
                    "room_profiles": {}
                }

                save(data)

                st.session_state.user = name
                st.session_state.log = []
                st.session_state.entered_room_code = None

                st.rerun()

            else:
                user = data["users"].get(name)

                if user and core.verify_password(
                    user.get("password_hash", ""),
                    password
                ):
                    st.session_state.user = name
                    st.session_state.log = []
                    st.session_state.entered_room_code = None

                    user["last_active"] = time.time()
                    save(data)

                    st.rerun()

                else:
                    st.error("Incorrect username or password.")

    st.info(
        "This is an early web build. "
        "Use a unique password; do not reuse an important password."
    )


# ============================================================
# CITY LOBBY
# ============================================================

def lobby_screen(data, username):

    user = data["users"][username]

    st.title("🏙️ City Lobby")
    st.caption("Create a City or join an existing one.")

    current_code = user.get("current_room")

    current_room = (
        data["rooms"].get(current_code)
        if current_code else None
    )

    # --------------------------------------------------------
    # CURRENT ROOM
    # --------------------------------------------------------

    if current_room:
        st.subheader("Your current City")

        st.write(
            f"**City:** {core.CITIES.get(current_room.get('preset', 'egmore'), core.CITIES['egmore'])['name']}"
        )

        st.write(
            f"**Party Code:** `{current_code}`"
        )

        st.write(
            f"**Players:** {len(current_room['members'])}/{MAX_PLAYERS}"
        )

        if not current_room.get("started", False):

            if current_room.get("host") == username:

                st.divider()
                st.subheader("Host controls")

                city_names = {
                    key: cfg["name"]
                    for key, cfg in core.CITIES.items()
                }

                presets = list(city_names.keys())

                current_preset = current_room.get(
                    "preset", "egmore"
                )

                if current_preset not in presets:
                    current_preset = presets[0]

                selected_city = st.selectbox(
                    "Choose your City",
                    presets,
                    index=presets.index(current_preset),
                    format_func=lambda x: city_names[x]
                )

                if st.button(
                    "START CITY",
                    type="primary",
                    use_container_width=True
                ):
                    current_room["preset"] = selected_city
                    current_room["name"] = (
                        f"{username}'s {city_names[selected_city]}"
                    )
                    current_room["started"] = True

                    # Create profiles for everyone already in the room.
                    for member in current_room["members"]:
                        core.get_user_room_profile(
                            data, member, current_code
                        )

                    save(data)
                    st.success("Your City has started!")
                    st.rerun()

            else:
                st.info(
                    "Waiting for the host to choose a City and start."
                )

        else:
            st.success("This City has started.")

            if st.button(
                "ENTER CITY",
                type="primary",
                use_container_width=True
            ):
                st.session_state.entered_room_code = None
                st.session_state.log = []
                st.rerun()

        st.write("**Players in this City**")

        for member in current_room["members"]:
            last = data["users"].get(
                member, {}
            ).get("last_active", 0)

            status = (
                "🟢 Online"
                if time.time() - last < 120
                else "⚪ Offline"
            )

            st.write(f"{status} {member}")

        if st.button(
            "Leave this City",
            use_container_width=True
        ):
            if current_code != "GLOBAL_HUB":
                remove_from_old_room(
                    data, username, None
                )

                user["current_room"] = None
                user["room_profiles"] = user.get(
                    "room_profiles", {}
                )

                st.session_state.entered_room_code = None

                save(data)
                st.rerun()
            else:
                st.warning(
                    "You cannot leave the system Global Hub."
                )

        st.divider()

    # --------------------------------------------------------
    # CREATE CITY
    # --------------------------------------------------------

    st.subheader("➕ Create a City")

    if st.button(
        "CREATE NEW CITY",
        type="primary",
        use_container_width=True
    ):
        if current_room and current_code == "GLOBAL_HUB":
            remove_from_old_room(
                data, username, None
            )

        code = generate_room_code(data)

        data["rooms"][code] = {
            "host": username,
            "name": f"{username}'s City",
            "preset": "egmore",
            "is_public": False,
            "started": False,
            "members": [username],
            "heist": {
                "active": False,
                "contributions": {}
            }
        }

        user["current_room"] = code

        user.setdefault(
            "room_profiles", {}
        )[code] = core.get_default_room_profile("egmore")

        st.session_state.entered_room_code = None

        save(data)
        st.rerun()

    # --------------------------------------------------------
    # JOIN CITY
    # --------------------------------------------------------

    st.subheader("🔑 Join a City")

    party_code = st.text_input(
        "Enter Party Code",
        max_chars=6
    ).strip().upper()

    if st.button(
        "JOIN CITY",
        use_container_width=True
    ):
        if not party_code:
            st.error("Enter a Party Code.")
        elif party_code not in data["rooms"]:
            st.error("City not found.")
        else:
            target = data["rooms"][party_code]

            if username in target["members"]:
                user["current_room"] = party_code
                st.session_state.entered_room_code = None
                save(data)
                st.rerun()

            elif len(target["members"]) >= MAX_PLAYERS:
                st.error("This City is full (14/14 players).")

            else:
                remove_from_old_room(
                    data, username, party_code
                )

                target["members"].append(username)
                user["current_room"] = party_code

                core.get_user_room_profile(
                    data, username, party_code
                )

                st.session_state.entered_room_code = None
                st.session_state.log = []

                save(data)
                st.success("Successfully joined the City!")
                st.rerun()

    # --------------------------------------------------------
    # LOGOUT
    # --------------------------------------------------------

    st.divider()

    if st.button("LOG OUT"):
        save(data)

        for key in [
            "user",
            "log",
            "entered_room_code",
            "changing_character",
            "pending_character"
        ]:
            st.session_state.pop(key, None)

        st.rerun()


# ============================================================
# CHARACTER LOCK
# ============================================================

def character_picker(data, profile, room_code):

    st.title("🎭 Choose your character")
    st.caption(
        "Select your character and lock it before entering the City."
    )

    selected = profile.get("character_id")

    character_names = {
        item[0]: item[1]
        for item in CHARACTERS
    }

    keys = list(character_names.keys())

    if selected not in keys:
        selected = keys[0]

    chosen = st.selectbox(
        "Select your character",
        keys,
        index=keys.index(selected),
        format_func=lambda x: character_names[x]
    )

    index = next(
        i for i, item in enumerate(CHARACTERS)
        if item[0] == chosen
    )

    key, name, description, speciality = CHARACTERS[index]

    with st.container(border=True):
        image_path = (
            BASE / "assets" / "characters"
            / f"character_{index + 1:02d}.jpg"
        )

        if image_path.exists():
            st.image(
                str(image_path),
                width=240
            )
        else:
            st.warning(
                f"Character image missing: character_{index + 1:02d}.jpg"
            )

        st.subheader(name)
        st.write(description)
        st.caption(f"Speciality: {speciality}")

    if st.button(
        "🔒 LOCK CHARACTER & ENTER CITY",
        type="primary",
        use_container_width=True
    ):
        profile["character_id"] = key
        profile["character_name"] = name
        profile["character_locked"] = True

        st.session_state.entered_room_code = room_code
        st.session_state.pop("changing_character", None)

        save(data)
        st.rerun()


# ============================================================
# LOGGING
# ============================================================

def add_log(msg):
    st.session_state.setdefault("log", []).append(str(msg))
    st.session_state.log = st.session_state.log[-30:]


# ============================================================
# LOGIN GATE
# ============================================================

if "user" not in st.session_state:
    login_screen()
    st.stop()


username = st.session_state.user
data = load_data()

if username not in data["users"]:
    st.session_state.clear()
    st.rerun()

user = data["users"][username]
user["last_active"] = time.time()

# Every account starts at the lobby.
current_code = user.get("current_room")

if (
    not current_code
    or current_code not in data["rooms"]
    or username not in data["rooms"][current_code]["members"]
):
    user["current_room"] = None

    lobby_screen(data, username)
    save(data)
    st.stop()

room = data["rooms"][current_code]
room_code = current_code

# ------------------------------------------------------------
# CITY WAITING ROOM / LOBBY
# ------------------------------------------------------------

if not room.get("started", False):
    lobby_screen(data, username)
    save(data)
    st.stop()

# ------------------------------------------------------------
# CHARACTER LOCK GATE
# ------------------------------------------------------------

u = core.get_user_room_profile(
    data, username, room_code
)

if st.session_state.get("changing_character"):
    u["character_locked"] = False
    st.session_state.entered_room_code = None

if (
    not u.get("character_locked", False)
    or st.session_state.get("entered_room_code") != room_code
):
    character_picker(data, u, room_code)
    st.stop()

city_cfg = core.CITIES.get(
    room.get("preset", "egmore"),
    core.CITIES["egmore"]
)


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown("## 🪙 SCAM JOSE PAUL")
    st.caption(f"Logged in as **{username}**")

    st.markdown(
        f"**Current City:** {city_cfg['name']}"
    )

    st.markdown(
        f"**Party Code:** `{room_code}`"
    )

    st.markdown(
        f"**Character:** {u.get('character_name', 'Unknown')}"
    )

    if st.button(
        "Change character",
        use_container_width=True
    ):
        st.session_state.changing_character = True
        st.rerun()

    if st.button(
        "Return to lobby",
        use_container_width=True
    ):
        st.session_state.entered_room_code = None
        st.rerun()

    if st.button(
        "Log out",
        use_container_width=True
    ):
        save(data)

        for key in [
            "user",
            "log",
            "entered_room_code",
            "changing_character",
            "pending_character"
        ]:
            st.session_state.pop(key, None)

        st.rerun()

    st.divider()

    st.caption(
        "HELP is the command directory. "
        "Type `help` in the console to see available commands."
    )


# ============================================================
# MAIN GAME SCREEN
# ============================================================

st.title(
    f"🏙️ {room.get('name', city_cfg['name'])}"
)

st.caption(
    f"Party Code: {room_code}"
)

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "FamApp Balance",
    f"🪙 {u['fampay']:,}"
)

c2.metric(
    "FamApp Account",
    f"🪙 {u['bank']:,}"
)

c3.metric(
    "Level",
    u["level"]
)

c4.metric(
    "XP",
    f"{u['xp']}/{u['level'] * 300}"
)


# ============================================================
# COMMAND CONSOLE
# ============================================================

left, right = st.columns([1.55, 1])

with left:

    st.subheader("🎮 Command Console")

    with st.form(
        "command_form",
        clear_on_submit=True
    ):

        command = st.text_input(
            "Command",
            placeholder="Type help to see commands...",
            label_visibility="collapsed"
        )

        run = st.form_submit_button(
            "SEND COMMAND",
            type="primary",
            use_container_width=True
        )

    if run and command.strip():

        parts = command.strip().split()
        cmd = parts[0].lower()
        args = parts[1:]
        out = []

        def say(x):
            out.append(str(x))

        def commit():
            save(data)

        # ----------------------------------------------------
        # HELP
        # ----------------------------------------------------

        if cmd == "help":

            say("COMMAND DIRECTORY")
            say("balance | bag | shop | buy <item> | sell <loot> [qty]")
            say("work | jobs | apply <job_id> | daily | beg | dig | hunt | fish")
            say("deposit <amount> | withdraw <amount> | rob <username>")
            say("players | heist start | heist contribute <amount> | heist launch")
            say("leaderboard | revive | help | exit")
            say("Use the lobby to create or join Cities.")

        # ----------------------------------------------------
        # BALANCE
        # ----------------------------------------------------

        elif cmd in ("balance", "bal"):

            say(
                f"FamApp Balance: {u['fampay']:,} | "
                f"FamApp Account: {u['bank']:,} | "
                f"Bank limit: {u['bank_max']:,} | "
                f"Level: {u['level']} | "
                f"Job: {core.JOBS.get(u['job'], {}).get('name', u['job'])}"
            )

        # ----------------------------------------------------
        # INVENTORY
        # ----------------------------------------------------

        elif cmd in ("bag", "inv", "inventory"):

            items = [
                f"{core.SHOP_ITEMS[k]['name']} x{v}"
                for k, v in u["inventory"].items()
                if v and k in core.SHOP_ITEMS
            ]

            loot = [
                f"{core.LOOT_ITEMS[k]['name']} x{v}"
                for k, v in u["loot"].items()
                if v and k in core.LOOT_ITEMS
            ]

            say(
                "Inventory: "
                + (
                    ", ".join(items + loot)
                    if items or loot
                    else "Empty"
                )
            )

        # ----------------------------------------------------
        # SHOP
        # ----------------------------------------------------

        elif cmd == "shop":

            say("FRESH 4 TODAY")

            for k, v in core.SHOP_ITEMS.items():
                say(
                    f"{k}: {v['name']} — "
                    f"{v['price']:,} coins ({v['category']})"
                )

        # ----------------------------------------------------
        # BUY
        # ----------------------------------------------------

        elif cmd == "buy" and args:

            key = args[0].lower()

            if key not in core.SHOP_ITEMS:
                say("Item not found. Type shop.")

            elif u["fampay"] < core.SHOP_ITEMS[key]["price"]:
                say("Not enough FamApp Balance.")

            elif key == "sister_fahaana":
                say("This collectible cannot be purchased in this build.")

            else:
                u["fampay"] -= core.SHOP_ITEMS[key]["price"]

                u["inventory"][key] = (
                    u["inventory"].get(key, 0) + 1
                )

                say(
                    f"Purchased {core.SHOP_ITEMS[key]['name']}."
                )

                commit()

        # ----------------------------------------------------
        # SELL
        # ----------------------------------------------------

        elif cmd == "sell" and args:

            key = args[0].lower()

            try:
                qty = int(args[1]) if len(args) > 1 else 1
            except ValueError:
                qty = 0

            if (
                key not in core.LOOT_ITEMS
                or qty < 1
                or u["loot"].get(key, 0) < qty
            ):
                say("Invalid loot item or quantity.")

            else:
                earned = (
                    core.LOOT_ITEMS[key]["sell_price"] * qty
                )

                u["loot"][key] -= qty
                u["fampay"] += earned

                say(
                    f"Sold {qty}x "
                    f"{core.LOOT_ITEMS[key]['name']} "
                    f"for {earned:,}."
                )

                commit()

        # ----------------------------------------------------
        # BANK
        # ----------------------------------------------------

        elif cmd in (
            "deposit", "dep", "withdraw", "with"
        ) and args:

            try:
                amount = int(args[0])
            except ValueError:
                amount = 0

            if amount <= 0:
                say("Enter a positive amount.")

            elif cmd in ("deposit", "dep"):

                moved = min(
                    amount,
                    u["fampay"],
                    max(0, u["bank_max"] - u["bank"])
                )

                u["fampay"] -= moved
                u["bank"] += moved

                say(f"Deposited {moved:,}.")
                commit()

            else:

                moved = min(amount, u["bank"])

                u["bank"] -= moved
                u["fampay"] += moved

                say(f"Withdrew {moved:,}.")
                commit()

        # ----------------------------------------------------
        # JOBS
        # ----------------------------------------------------

        elif cmd == "jobs":

            for k, v in core.JOBS.items():
                say(
                    f"{k}: {v['name']} — "
                    f"level {v['req_level']}+; "
                    f"pay {v['pay'][0]}–{v['pay'][1]}"
                )

        elif cmd == "apply" and args:

            key = args[0].lower()
            job = core.JOBS.get(key)

            if not job:
                say("Job not found. Type jobs.")

            elif u["level"] < job["req_level"]:
                say(f"You need level {job['req_level']}.")

            else:
                u["job"] = key
                say(f"You are now a {job['name']}.")
                commit()

        elif cmd == "work":

            if u["dead"]:
                say("You need to revive before working.")

            else:
                job = core.JOBS.get(
                    u["job"],
                    core.JOBS["moderator"]
                )

                pay = random.randint(*job["pay"])
                pay = int(pay * city_cfg["pay_mult"])

                u["fampay"] += pay
                core.add_xp(u, 50)

                say(
                    f"Completed your shift as {job['name']}. "
                    f"Earned {pay:,} coins and 50 XP."
                )

                commit()

        # ----------------------------------------------------
        # DAILY
        # ----------------------------------------------------

        elif cmd == "daily":

            now = time.time()

            if now - u.get("last_daily", 0) < 86400:
                say(
                    "Daily reward already claimed. "
                    "Come back after 24 hours."
                )

            else:
                reward = (
                    1000
                    + u.get("daily_streak", 0) * 100
                )

                u["fampay"] += reward
                u["last_daily"] = now

                u["daily_streak"] = (
                    u.get("daily_streak", 0) + 1
                )

                say(
                    f"Daily reward: {reward:,} coins."
                )

                commit()

        # ----------------------------------------------------
        # BEG
        # ----------------------------------------------------

        elif cmd == "beg":

            reward = random.randint(50, 350)

            if random.random() < 0.3:
                say("Nobody gave you anything this time.")

            else:
                u["fampay"] += reward
                core.add_xp(u, 20)

                say(
                    f"Someone helped you out: "
                    f"+{reward:,} coins."
                )

                commit()

        # ----------------------------------------------------
        # DIG / HUNT / FISH
        # ----------------------------------------------------

        elif cmd in ("dig", "hunt", "fish"):

            required = {
                "dig": "shovel",
                "hunt": "hunting_rifle",
                "fish": "fishing_rod"
            }[cmd]

            if u["inventory"].get(required, 0) <= 0:

                say(
                    f"You need "
                    f"{core.SHOP_ITEMS[required]['name']}. "
                    "Buy it from shop."
                )

            else:

                if cmd == "hunt":
                    encounter = random.choice(
                        core.HUNT_BOSSES
                    )

                elif cmd == "fish":
                    encounter = random.choice(
                        core.FISH_BOSSES
                    )

                else:
                    encounter = random.choice(
                        core.DIG_ANIMALS
                    )

                drop = encounter["drop"]

                u["loot"][drop] = (
                    u["loot"].get(drop, 0) + 1
                )

                reward = random.randint(250, 1200)

                u["fampay"] += reward
                core.add_xp(u, 55)

                say(
                    f"{encounter['name']}: "
                    f"collected {core.LOOT_ITEMS[drop]['name']} "
                    f"and earned {reward:,} coins."
                )

                commit()

        # ----------------------------------------------------
        # ROOM COMMANDS
        # ----------------------------------------------------

        elif cmd in ("room", "rooms"):

            say(
                "City creation and joining are handled "
                "through the City Lobby."
            )

        elif cmd == "terminate_room":

            if (
                room_code == "GLOBAL_HUB"
                or room["host"] != username
            ):

                say(
                    "Only the host can terminate their private City."
                )

            else:

                for member in list(room["members"]):

                    if member in data["users"]:
                        data["users"][member]["current_room"] = None

                del data["rooms"][room_code]

                st.session_state.entered_room_code = None

                say(
                    "City terminated. All members returned to the lobby."
                )

                commit()

        # ----------------------------------------------------
        # PLAYERS
        # ----------------------------------------------------

        elif cmd in ("players", "sidebar"):

            for name in room["members"]:

                last = data["users"].get(
                    name, {}
                ).get("last_active", 0)

                status = (
                    "Online"
                    if time.time() - last < 120
                    else "Offline"
                )

                say(f"{name} — {status}")

        # ----------------------------------------------------
        # ROB
        # ----------------------------------------------------

        elif cmd == "rob" and args:

            target = args[0]

            if (
                target == username
                or target not in data["users"]
            ):

                say("Player not found.")

            elif (
                data["users"][target].get("current_room")
                != room_code
            ):

                say(
                    "You can only interact with players "
                    "in your current City."
                )

            else:

                victim = core.get_user_room_profile(
                    data, target, room_code
                )

                if victim["inventory"].get("padlock", 0) > 0:

                    victim["inventory"]["padlock"] -= 1

                    u["fampay"] = max(
                        0, u["fampay"] - 500
                    )

                    say(
                        "Padlock blocked the attempt. "
                        "You paid a 500-coin fine."
                    )

                elif (
                    random.random() < 0.5
                    and victim["fampay"] > 0
                ):

                    stolen = min(
                        victim["fampay"],
                        random.randint(100, 1500)
                    )

                    victim["fampay"] -= stolen
                    u["fampay"] += stolen

                    say(f"You won {stolen:,} coins.")

                else:

                    fine = min(u["fampay"], 500)
                    u["fampay"] -= fine

                    say(
                        f"Attempt failed. Fine: {fine:,}."
                    )

                commit()

        # ----------------------------------------------------
        # CREW HEIST
        # ----------------------------------------------------

        elif cmd == "heist" and args:

            h = room.setdefault(
                "heist",
                {
                    "active": False,
                    "contributions": {}
                }
            )

            sub = args[0].lower()

            if sub == "start":

                if h.get("active"):

                    say("A crew heist is already active.")

                else:

                    h["active"] = True
                    h["host"] = username
                    h["contributions"] = {
                        username: 0
                    }

                    say(
                        "Crew heist opened. "
                        "Teammates can contribute."
                    )

                commit()

            elif sub == "contribute" and len(args) > 1:

                try:
                    amount = int(args[1])
                except ValueError:
                    amount = 0

                if (
                    not h.get("active")
                    or amount <= 0
                    or amount > u["fampay"]
                ):

                    say(
                        "Invalid contribution or no active heist."
                    )

                else:

                    u["fampay"] -= amount

                    h["contributions"][username] = (
                        h["contributions"].get(username, 0)
                        + amount
                    )

                    say(f"Contributed {amount:,}.")
                    commit()

            elif sub == "launch":

                if (
                    not h.get("active")
                    or h.get("host") != username
                ):

                    say(
                        "Only the heist host can launch "
                        "an active crew heist."
                    )

                elif len(h.get("contributions", {})) < 2:

                    say(
                        "At least two contributors are required."
                    )

                else:

                    total = sum(
                        h["contributions"].values()
                    )

                    success = random.random() < 0.65

                    if success:

                        pool = total * 2

                        for member, contribution in (
                            h["contributions"].items()
                        ):

                            if member in data["users"]:

                                profile = (
                                    core.get_user_room_profile(
                                        data,
                                        member,
                                        room_code
                                    )
                                )

                                profile["fampay"] += int(
                                    pool * contribution / total
                                )

                        say(
                            f"Crew heist succeeded. "
                            f"{pool:,} coins distributed proportionally."
                        )

                    else:

                        say(
                            "The crew heist failed. "
                            "Contributions were lost."
                        )

                    h.update({
                        "active": False,
                        "contributions": {}
                    })

                    commit()

        # ----------------------------------------------------
        # LEADERBOARD
        # ----------------------------------------------------

        elif cmd in ("leaderboard", "lb"):

            ranked = []

            for name, obj in data["users"].items():

                total = sum(
                    p.get("fampay", p.get("wallet", 0))
                    + p.get("bank", 0)
                    for p in obj.get(
                        "room_profiles", {}
                    ).values()
                )

                ranked.append((total, name))

            for rank, (total, name) in enumerate(
                sorted(ranked, reverse=True)[:10],
                1
            ):

                say(
                    f"{rank}. {name} — {total:,} coins"
                )

        # ----------------------------------------------------
        # REVIVE
        # ----------------------------------------------------

        elif cmd == "revive":

            if not u["dead"]:

                say("You are already active.")

            else:

                u["dead"] = False
                u["fampay"] = max(200, u["fampay"])

                say("You have been revived.")
                commit()

        # ----------------------------------------------------
        # EXIT / UNKNOWN
        # ----------------------------------------------------

        elif cmd == "exit":

            say(
                "Use Return to lobby or Log out "
                "in the sidebar."
            )

        else:

            say(
                f"Unknown command: {cmd}. Type help."
            )

        for line in out:
            add_log(line)

        save(data)
        st.rerun()

    # --------------------------------------------------------
    # OUTPUT AREA
    # --------------------------------------------------------

    st.subheader("📨 Command Messages")

    with st.container(
        border=True,
        height=350
    ):

        if st.session_state.get("log"):

            for line in st.session_state.log[-15:]:
                st.write(line)

        else:

            st.caption(
                "Your command results will appear here."
            )


# ============================================================
# RIGHT PANEL
# ============================================================

with right:

    st.subheader("🎭 Your character")

    chosen_idx = next(
        (
            i for i, item in enumerate(CHARACTERS)
            if item[0] == u.get("character_id")
        ),
        None
    )

    if chosen_idx is not None:

        image_path = (
            BASE / "assets" / "characters"
            / f"character_{chosen_idx + 1:02d}.jpg"
        )

        if image_path.exists():
            st.image(
                str(image_path),
                width=150
            )

        st.markdown(
            f"**{u.get('character_name', CHARACTERS[chosen_idx][1])}**"
        )

        st.caption(
            CHARACTERS[chosen_idx][2]
        )

    st.divider()

    st.subheader("👥 Players in this City")

    st.write(
        f"**Host:** {room['host']}"
    )

    st.write(
        f"**Members:** {len(room['members'])}/{MAX_PLAYERS}"
    )

    for name in room["members"]:

        last = data["users"].get(
            name, {}
        ).get("last_active", 0)

        status = (
            "🟢 Online"
            if time.time() - last < 120
            else "⚪ Offline"
        )

        st.write(
            f"{status} **{name}**"
        )

    st.divider()

    st.subheader("📊 Account information")

    st.write(
        f"**Career:** "
        f"{core.JOBS.get(u['job'], {}).get('name', u['job'])}"
    )

    st.write(
        f"**Inventory items:** "
        f"{sum(u['inventory'].values())}"
    )

    st.write(
        f"**Collectibles / loot:** "
        f"{sum(u['loot'].values())}"
    )


# ============================================================
# FINAL SAVE
# ============================================================

save(data)

st.caption(
    "SCAM JOSE PAUL · Early web edition"
)
