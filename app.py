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

    for line in out:
        add_log(line)
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

    left, right = st.columns([1.65, 1])
    with left:
        st.markdown("### 🎮 Command Console")
        st.markdown("<div class='muted-note'>Enter a command below. Type <b>help</b> to see the command directory.</div>", unsafe_allow_html=True)
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

        st.markdown("### 📟 Command Output")
        log_lines = st.session_state.get("command_log", [])
        with st.container(border=True):
            if log_lines:
                for line in log_lines[-18:]:
                    st.markdown(f"<div style='padding:5px 2px;border-bottom:1px solid rgba(148,163,184,.10)'>{html.escape(str(line))}</div>", unsafe_allow_html=True)
            else:
                st.caption("Your command results will appear here. Start with `help`.")

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
        st.markdown("### 🏙️ City Status")
        st.write(f"**Host:** {room.get('host', 'Unknown')}")
        st.write(f"**Members:** {len(room.get('members', []))}/{MAX_PLAYERS}")
        job_name = core.JOBS.get(profile.get("job"), {}).get("name", profile.get("job", "None"))
        st.write(f"**Career:** {job_name}")
        st.write(f"**Inventory items:** {sum(profile['inventory'].values())}")
        st.write(f"**Collectibles / loot:** {sum(profile['loot'].values())}")
        st.divider()
        st.markdown("### 👥 Players in this City")
        for member in room.get("members", []):
            if member not in data["users"] or data["users"][member].get("current_room") != room_code:
                continue
            last_active = data["users"].get(member, {}).get("last_active", 0)
            status = "🟢 Online" if time.time() - last_active < 120 else "⚪ Offline"
            st.write(f"{status}  **{member}**" + (" · Host" if member == room.get("host") else ""))

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
