import contextlib, io, json, os, random, secrets, time
from pathlib import Path
import streamlit as st
import game_core as core

BASE = Path(__file__).parent
DATA_FILE = BASE / 'data' / 'scam_jose_paul_save.json'
core.DATA_FILE = str(DATA_FILE)

st.set_page_config(page_title='SCAM JOSE PAUL', page_icon='🪙', layout='wide')
st.markdown('''<style>
.stApp {background: radial-gradient(circle at 15% 0%, #202b45 0, #10131d 38%, #0b0e14 100%); color:#f4f6fb}
[data-testid="stSidebar"] {background:#111827}
.block-container {padding-top:2rem; max-width:1400px}
div[data-testid="stMetric"] {background:#171e2d; padding:16px; border:1px solid #2b3549; border-radius:14px}
.stButton>button {border-radius:10px; border:1px solid #3b4963}
</style>''', unsafe_allow_html=True)



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

def character_picker(data, profile, room_code, force=False):
    selected = profile.get('character_id')
    if selected and not force:
        return
    st.title('🎭 Choose your City character')
    st.caption('Your choice is saved separately in each City. You can change it later without losing your progress.')
    cols = st.columns(3)
    for i, (key, name, description, speciality) in enumerate(CHARACTERS):
        with cols[i % 3]:
            with st.container(border=True):
                img = BASE / 'assets' / 'characters' / f'character_{i+1:02d}.jpg'
                st.image(str(img), use_container_width=True)
                st.markdown(f'**{name}**')
                st.caption(description)
                st.caption(f'**Speciality:** {speciality}')
                if st.button('Select character', key=f'pick_{room_code}_{key}', use_container_width=True, type='primary' if selected == key else 'secondary'):
                    profile['character_id'] = key
                    profile['character_name'] = name
                    save(data)
                    st.session_state.pop('changing_character', None)
                    st.rerun()
    st.stop()

def load_data():
    data = core.load_all_data()
    data.setdefault('users', {})
    data.setdefault('rooms', {})
    if 'GLOBAL_HUB' not in data['rooms']:
        data['rooms']['GLOBAL_HUB'] = {'host':'SYSTEM','name':'Global Hub Egmore','preset':'egmore','is_public':True,'members':[],'heist':{'active':False,'contributions':{}}}
    # Migrate legacy single-player saves (username -> wallet/bank/etc.) into the hub.
    legacy = [k for k,v in list(data.items()) if isinstance(v,dict) and 'wallet' in v and k not in ('users','rooms')]
    for name in legacy:
        old = data.pop(name)
        if name not in data['users']:
            data['users'][name] = {'password_hash': core.hash_password(secrets.token_urlsafe(18)), 'current_room':'GLOBAL_HUB','room_profiles':{}}
        prof = core.get_default_room_profile('egmore')
        for key,val in old.items():
            if key == 'wallet': prof['fampay'] = val
            elif key in prof: prof[key] = val
        data['users'][name].setdefault('room_profiles',{})['GLOBAL_HUB'] = prof
        data['users'][name].setdefault('current_room','GLOBAL_HUB')
        if name not in data['rooms']['GLOBAL_HUB']['members']: data['rooms']['GLOBAL_HUB']['members'].append(name)
    return data


def save(data):
    DATA_FILE.parent.mkdir(exist_ok=True)
    tmp = str(DATA_FILE) + '.tmp'
    with open(tmp,'w',encoding='utf-8') as f: json.dump(data,f,indent=2)
    os.replace(tmp, DATA_FILE)


def get_session(data, username):
    user = data['users'][username]
    code = user.get('current_room','GLOBAL_HUB')
    if code not in data['rooms']: code='GLOBAL_HUB'; user['current_room']=code
    room = data['rooms'][code]
    profile = core.get_user_room_profile(data, username, code)
    return user, room, profile, code, core.CITIES.get(room.get('preset','egmore'),core.CITIES['egmore'])


def add_log(msg):
    st.session_state.setdefault('log',[]).append(str(msg))
    st.session_state.log = st.session_state.log[-30:]


def login_screen():
    st.title('🪙 SCAM JOSE PAUL')
    st.caption('A city-based economy game. Your progress is separate in each City.')
    with st.container(border=True):
        mode = st.radio('Account', ['Login','Create account'], horizontal=True)
        username = st.text_input('Username', max_chars=24)
        password = st.text_input('Password', type='password')
        if st.button('Continue', type='primary', use_container_width=True):
            if not username.strip() or not password:
                st.error('Enter both a username and password.')
            else:
                data=load_data(); name=username.strip()
                if mode=='Create account':
                    if name in data['users']: st.error('That username is already taken.')
                    else:
                        data['users'][name]={'password_hash':core.hash_password(password),'last_active':time.time(),'current_room':'GLOBAL_HUB','room_profiles':{'GLOBAL_HUB':core.get_default_room_profile('egmore')}}
                        data['rooms']['GLOBAL_HUB'].setdefault('members',[])
                        if name not in data['rooms']['GLOBAL_HUB']['members']: data['rooms']['GLOBAL_HUB']['members'].append(name)
                        save(data); st.session_state.user=name; st.session_state.log=[]; st.rerun()
                else:
                    u=data['users'].get(name)
                    if u and core.verify_password(u.get('password_hash',''),password):
                        st.session_state.user=name; st.session_state.log=[]; u['last_active']=time.time(); save(data); st.rerun()
                    else: st.error('Incorrect username or password.')
    st.info('This is an early web build. Use a unique password; do not reuse an important password.')

if 'user' not in st.session_state:
    login_screen(); st.stop()

username=st.session_state.user
data=load_data()
if username not in data['users']:
    st.session_state.clear(); st.rerun()
user,room,u,room_code,city_cfg=get_session(data,username)
user['last_active']=time.time()

with st.sidebar:
    st.markdown('## 🪙 SCAM JOSE PAUL')
    st.caption(f'Logged in as **{username}**')
    st.markdown(f'**Current City:** {city_cfg["name"]}')
    st.markdown(f'**Party Code:** `{room_code}`')
    chosen = u.get('character_name', 'No character selected')
    st.markdown(f'**Character:** {chosen}')
    if st.button('Change character', use_container_width=True):
        st.session_state.changing_character = True
        st.rerun()
    if st.button('Log out',use_container_width=True):
        save(data); del st.session_state['user']; st.rerun()
    st.divider()
    st.caption('HELP is the command directory. Type `help` in the console to see available commands.')

if not u.get('character_id') or st.session_state.get('changing_character'):
    character_picker(data, u, room_code, force=bool(st.session_state.get('changing_character')))

st.title(f'🏙️ {room.get("name",city_cfg["name"])}')
st.caption(f'{city_cfg["desc"]}  ·  Room: {room_code}')
c1,c2,c3,c4=st.columns(4)
c1.metric('FamApp Balance',f'🪙 {u["fampay"]:,}')
c2.metric('FamApp Account',f'🪙 {u["bank"]:,}')
c3.metric('Level',u['level'])
c4.metric('XP',f'{u["xp"]}/{u["level"]*300}')

left,right=st.columns([1.55,1])
with left:
    st.subheader('🎮 Command Console')
    command=st.text_input('Enter a command',placeholder='Type help to see commands',label_visibility='collapsed',key='command')
    run=st.button('Run command',type='primary')
    if run and command.strip():
        parts=command.strip().split(); cmd=parts[0].lower(); args=parts[1:]; out=[]
        def say(x): out.append(str(x))
        def commit(): save(data)
        if cmd=='help':
            say('COMMAND DIRECTORY')
            say('balance | bag | shop | buy <item> | sell <loot> [qty]')
            say('work | jobs | apply <job_id> | daily | beg | dig | hunt | fish')
            say('deposit <amount> | withdraw <amount> | rob <username>')
            say('room list | room create <city> | room join <code> | terminate_room')
            say('players | heist start | heist contribute <amount> | heist launch')
            say('leaderboard | revive | help | exit')
        elif cmd in ('balance','bal'):
            say(f'FamApp Balance: {u["fampay"]:,} | FamApp Account: {u["bank"]:,} | Bank limit: {u["bank_max"]:,} | Level: {u["level"]} | Job: {core.JOBS.get(u["job"],{}).get("name",u["job"])}')
        elif cmd in ('bag','inv','inventory'):
            items=[f'{core.SHOP_ITEMS[k]["name"]} x{v}' for k,v in u['inventory'].items() if v]
            loot=[f'{core.LOOT_ITEMS[k]["name"]} x{v}' for k,v in u['loot'].items() if v]
            say('Inventory: '+(', '.join(items+loot) if items or loot else 'Empty'))
        elif cmd=='shop':
            say('FRESH 4 TODAY')
            for k,v in core.SHOP_ITEMS.items(): say(f'{k}: {v["name"]} — {v["price"]:,} coins ({v["category"]})')
        elif cmd=='buy' and args:
            key=args[0].lower()
            if key not in core.SHOP_ITEMS: say('Item not found. Type shop.')
            elif u['fampay']<core.SHOP_ITEMS[key]['price']: say('Not enough FamApp Balance.')
            elif key=='sister_fahaana': say('This collectible cannot be purchased in this build.')
            else:
                u['fampay']-=core.SHOP_ITEMS[key]['price']; u['inventory'][key]=u['inventory'].get(key,0)+1; say(f'Purchased {core.SHOP_ITEMS[key]["name"]}.'); commit()
        elif cmd=='sell' and args:
            key=args[0].lower(); qty=int(args[1]) if len(args)>1 and args[1].isdigit() else 1
            if key not in core.LOOT_ITEMS or qty<1 or u['loot'].get(key,0)<qty: say('Invalid loot item or quantity.')
            else:
                earned=core.LOOT_ITEMS[key]['sell_price']*qty; u['loot'][key]-=qty; u['fampay']+=earned; say(f'Sold {qty}x {core.LOOT_ITEMS[key]["name"]} for {earned:,}.'); commit()
        elif cmd in ('deposit','dep','withdraw','with') and args:
            try: amount=int(args[0])
            except: amount=0
            if amount<=0: say('Enter a positive amount.')
            elif cmd in ('deposit','dep'):
                moved=min(amount,u['fampay'],u['bank_max']-u['bank']); u['fampay']-=moved; u['bank']+=moved; say(f'Deposited {moved:,}.'); commit()
            else:
                moved=min(amount,u['bank']); u['bank']-=moved; u['fampay']+=moved; say(f'Withdrew {moved:,}.'); commit()
        elif cmd=='jobs':
            for k,v in core.JOBS.items(): say(f'{k}: {v["name"]} — level {v["req_level"]}+; pay {v["pay"][0]}–{v["pay"][1]}')
        elif cmd=='apply' and args:
            key=args[0].lower(); job=core.JOBS.get(key)
            if not job: say('Job not found. Type jobs.')
            elif u['level']<job['req_level']: say(f'You need level {job["req_level"]}.')
            else: u['job']=key; say(f'You are now a {job["name"]}.'); commit()
        elif cmd=='work':
            if u['dead']: say('You need to revive before working.')
            else:
                job=core.JOBS.get(u['job'],core.JOBS['moderator']); pay=random.randint(*job['pay']); pay=int(pay*city_cfg['pay_mult']); u['fampay']+=pay; core.add_xp(u,50); say(f'Completed your shift as {job["name"]}. Earned {pay:,} coins and 50 XP.'); commit()
        elif cmd=='daily':
            now=time.time()
            if now-u.get('last_daily',0)<86400: say('Daily reward already claimed. Come back after 24 hours.')
            else:
                reward=1000+u.get('daily_streak',0)*100; u['fampay']+=reward; u['last_daily']=now; u['daily_streak']=u.get('daily_streak',0)+1; say(f'Daily reward: {reward:,} coins.'); commit()
        elif cmd=='beg':
            reward=random.randint(50,350)
            if random.random()<.3: say('Nobody gave you anything this time.')
            else: u['fampay']+=reward; core.add_xp(u,20); say(f'Someone helped you out: +{reward:,} coins.'); commit()
        elif cmd in ('dig','hunt','fish'):
            required={'dig':'shovel','hunt':'hunting_rifle','fish':'fishing_rod'}[cmd]
            if u['inventory'].get(required,0)<=0: say(f'You need {core.SHOP_ITEMS[required]["name"]}. Buy it from shop.')
            else:
                if cmd=='hunt': encounter=random.choice(core.HUNT_BOSSES)
                elif cmd=='fish': encounter=random.choice(core.FISH_BOSSES)
                else: encounter=random.choice(core.DIG_ANIMALS)
                drop=encounter['drop']; u['loot'][drop]=u['loot'].get(drop,0)+1; reward=random.randint(250,1200); u['fampay']+=reward; core.add_xp(u,55); say(f'{encounter["name"]}: collected {core.LOOT_ITEMS[drop]["name"]} and earned {reward:,} coins.'); commit()
        elif cmd in ('room','rooms') and args:
            sub=args[0].lower()
            if sub=='list':
                for code,r in data['rooms'].items(): say(f'{code} — {r.get("name",r.get("preset"))} — host {r["host"]} — {len(r["members"])} members')
            elif sub=='create':
                preset=args[1].lower() if len(args)>1 else 'egmore'
                if preset not in core.CITIES: say('Unknown City. Valid: '+', '.join(core.CITIES))
                else:
                    old=data['users'][username].get('current_room','GLOBAL_HUB')
                    if old in data['rooms'] and username in data['rooms'][old]['members']: data['rooms'][old]['members'].remove(username)
                    code=''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=6))
                    while code in data['rooms']: code=''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789',k=6))
                    data['rooms'][code]={'host':username,'name':f'{username}\'s {core.CITIES[preset]["name"]}','preset':preset,'is_public':False,'members':[username],'heist':{'active':False,'contributions':{}}}
                    data['users'][username]['current_room']=code; data['users'][username].setdefault('room_profiles',{})[code]=core.get_default_room_profile(preset); room_code=code; say(f'Created {preset.title()} City. Party Code: {code}.'); commit()
            elif sub=='join' and len(args)>1:
                code=args[1].upper()
                if code not in data['rooms']: say('Room code not found.')
                else:
                    if room_code in data['rooms'] and username in data['rooms'][room_code]['members']: data['rooms'][room_code]['members'].remove(username)
                    if username not in data['rooms'][code]['members']: data['rooms'][code]['members'].append(username)
                    data['users'][username]['current_room']=code; say(f'Joined {code}.'); commit()
            else: say('Use room list, room create <city>, or room join <code>.')
        elif cmd=='terminate_room':
            if room_code=='GLOBAL_HUB' or room['host']!=username: say('Only the host can terminate their private City.')
            else:
                for member in list(room['members']):
                    if member in data['users']: data['users'][member]['current_room']='GLOBAL_HUB'
                data['rooms']['GLOBAL_HUB']['members']=list(set(data['rooms']['GLOBAL_HUB']['members']+room['members']))
                del data['rooms'][room_code]; say('City terminated. All members returned to Global Hub.'); commit()
        elif cmd in ('players','sidebar'):
            for name in room['members']:
                last=data['users'].get(name,{}).get('last_active',0); status='Online' if time.time()-last<120 else 'Offline'; say(f'{name} — {status}')
        elif cmd=='rob' and args:
            target=args[0]
            if target==username or target not in data['users']: say('Player not found.')
            elif data['users'][target].get('current_room')!=room_code: say('You can only interact with players in your current City.')
            else:
                victim=core.get_user_room_profile(data,target,room_code)
                if victim['inventory'].get('padlock',0)>0:
                    victim['inventory']['padlock']-=1; u['fampay']=max(0,u['fampay']-500); say('Padlock blocked the attempt. You paid a 500-coin fine.')
                elif random.random()<.5 and victim['fampay']>0:
                    stolen=min(victim['fampay'],random.randint(100,1500)); victim['fampay']-=stolen; u['fampay']+=stolen; say(f'You won {stolen:,} coins.')
                else:
                    fine=min(u['fampay'],500); u['fampay']-=fine; say(f'Attempt failed. Fine: {fine:,}.')
                commit()
        elif cmd=='heist' and args:
            h=room.setdefault('heist',{'active':False,'contributions':{}}); sub=args[0].lower()
            if sub=='start':
                if h.get('active'): say('A crew heist is already active.')
                else: h['active']=True; h['host']=username; h['contributions']={username:0}; say('Crew heist opened. Teammates can contribute.')
                commit()
            elif sub=='contribute' and len(args)>1:
                try: amount=int(args[1])
                except: amount=0
                if not h.get('active') or amount<=0 or amount>u['fampay']: say('Invalid contribution or no active heist.')
                else: u['fampay']-=amount; h['contributions'][username]=h['contributions'].get(username,0)+amount; say(f'Contributed {amount:,}.'); commit()
            elif sub=='launch':
                if not h.get('active') or h.get('host')!=username: say('Only the heist host can launch an active crew heist.')
                elif len(h.get('contributions',{}))<2: say('At least two contributors are required.')
                else:
                    total=sum(h['contributions'].values()); success=random.random()<.65
                    if success:
                        pool=total*2
                        for member,contribution in h['contributions'].items():
                            if member in data['users']:
                                p=core.get_user_room_profile(data,member,room_code); p['fampay']+=int(pool*contribution/total)
                        say(f'Crew heist succeeded. {pool:,} coins distributed proportionally.')
                    else: say('The crew heist failed. Contributions were lost.')
                    h.update({'active':False,'contributions':{}}); commit()
        elif cmd in ('leaderboard','lb'):
            ranked=[]
            for name,obj in data['users'].items():
                total=sum(p.get('fampay',p.get('wallet',0))+p.get('bank',0) for p in obj.get('room_profiles',{}).values()); ranked.append((total,name))
            for rank,(total,name) in enumerate(sorted(ranked,reverse=True)[:10],1): say(f'{rank}. {name} — {total:,} coins')
        elif cmd=='revive':
            if not u['dead']: say('You are already active.')
            else: u['dead']=False; u['fampay']=max(200,u['fampay']); say('You have been revived.'); commit()
        elif cmd=='exit': say('Use Log out in the sidebar to leave safely.')
        else: say(f'Unknown command: {cmd}. Type help.')
        for line in out: add_log(line)
        save(data)
        st.rerun()
    with st.container(border=True):
        if st.session_state.get('log'):
            for line in st.session_state.log[-15:]: st.write(line)
        else: st.caption('Your command results will appear here.')
with right:
    st.subheader('🎭 Your character')
    chosen_idx = next((i for i, item in enumerate(CHARACTERS) if item[0] == u.get('character_id')), None)
    if chosen_idx is not None:
        st.image(str(BASE / 'assets' / 'characters' / f'character_{chosen_idx+1:02d}.jpg'), width=150)
        st.markdown(f'**{u.get("character_name", CHARACTERS[chosen_idx][1])}**')
        st.caption(CHARACTERS[chosen_idx][2])
    st.divider()
    st.subheader('🏙️ City & account')
    st.write(f'**Host:** {room["host"]}')
    st.write(f'**Members:** {len(room["members"])}')
    st.write(f'**Career:** {core.JOBS.get(u["job"],{}).get("name",u["job"])}')
    st.write(f'**Inventory items:** {sum(u["inventory"].values())}')
    st.write(f'**Collectibles / loot:** {sum(u["loot"].values())}')
    st.divider()
    st.subheader('👥 Players in this City')
    for name in room['members']:
        last=data['users'].get(name,{}).get('last_active',0)
        status='🟢 Online' if time.time()-last<120 else '⚪ Offline'
        st.write(f'{status}  **{name}**')
    st.divider()
    st.subheader('📍 City presets')
    for key,cfg in core.CITIES.items(): st.caption(f'**{cfg["name"]}:** {cfg["desc"]}')

save(data)
st.caption('SCAM JOSE PAUL · Early web edition · Progress is saved locally in the app data file.')
