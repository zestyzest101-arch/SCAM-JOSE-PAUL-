import hashlib
import json
import os
import random
import secrets
import sys
import time

DATA_FILE = "scam_jose_paul_save.json"

# --- City Presets ---
CITIES = {
    "perambur": {
        "name": "Perambur",
        "desc": "Working-class hub with frequent mugging events.",
        "mug_chance": 0.25,
        "tax_mult": 1.0,
        "pay_mult": 1.0,
        "death_mult": 1.1,
    },
    "nungambakkam": {
        "name": "Nungambakkam",
        "desc": "Lavish elite district with lower death probability.",
        "mug_chance": 0.05,
        "tax_mult": 1.0,
        "pay_mult": 1.1,
        "death_mult": 0.8,
    },
    "egmore": {
        "name": "Egmore",
        "desc": "Balanced, normal difficulty urban center.",
        "mug_chance": 0.12,
        "tax_mult": 1.0,
        "pay_mult": 1.0,
        "death_mult": 1.0,
    },
    "anna_nagar": {
        "name": "Anna Nagar",
        "desc": "Upscale area plagued by random high-tax collector events.",
        "mug_chance": 0.08,
        "tax_mult": 1.35,
        "pay_mult": 1.2,
        "death_mult": 1.0,
    },
    "kilpauk": {
        "name": "Kilpauk",
        "desc": "Exclusive medical & financial enclave with extra bonuses.",
        "mug_chance": 0.03,
        "tax_mult": 0.85,
        "pay_mult": 1.3,
        "death_mult": 0.9,
    },
}

# --- Fresh 4 Today Store & Collectible Items ---
SHOP_ITEMS = {
    "shield": {"name": "Shield", "price": 2500, "category": "Defense", "desc": "Automatically shatters to save your life and FamPay Balance from death."},
    "reviver": {"name": "Reviver Token", "price": 1000000, "category": "Defense", "desc": "Ultimate life insurance. Automatically revives you from death."},
    "padlock": {"name": "Padlock", "price": 1500, "category": "Defense", "desc": "Protects your FamPay Balance from street muggers and player robberies."},
    "golden_padlock": {"name": "Golden Padlock", "price": 100000, "category": "Defense", "desc": "Heavy-duty lock that stops advanced robberies."},
    "bank_lock": {"name": "Bank Lock", "price": 50000, "category": "Defense", "desc": "Secures your bank vault from heists and asset losses."},
    "banknote": {"name": "Banknote", "price": 2000, "category": "Upgrade", "desc": "Permanently increases your maximum bank capacity by 5,000."},
    "fishing_rod": {"name": "Fishing Rod", "price": 2500, "category": "Tool", "desc": "Required to catch sea creatures using the `fish` command."},
    "hunting_rifle": {"name": "Hunting Rifle", "price": 3000, "category": "Tool", "desc": "Required to hunt wild beasts using the `hunt` command."},
    "shovel": {"name": "Shovel", "price": 2500, "category": "Tool", "desc": "Required to unearth buried treasure & underground critters using `dig`."},
    "god_box": {"name": "God Box", "price": 500000, "category": "Lootbox", "desc": "Mythical mystery box packed with huge coin and item rewards."},
    "meme_card": {"name": "Rare Meme Card", "price": 25000, "category": "Collectible", "desc": "Limited edition holographic meme card for true flexers."},
    "sister_fahaana": {"name": "Sister Fahaana", "price": 69000, "category": "Collectible", "desc": "A life-size 5'6 pillow of a human. Peak emotional support & net worth flex."},
    "golden_pepe": {"name": "24K Golden Pepe Statue", "price": 150000, "category": "Collectible", "desc": "Solid gold statue stolen from high-security vaults."},
    "cursed_idol": {"name": "Cursed Aztech Idol", "price": 85000, "category": "Collectible", "desc": "Whispers dark financial advice at 3 AM."},
    "diamond_chain": {"name": "Iced-Out Jose Chain", "price": 250000, "category": "Collectible", "desc": "Blinds bank tellers with pure VVS diamonds."},
}

# --- Sellable Hunt, Fish, Dig & Bank Loot Drops ---
LOOT_ITEMS = {
    "dragon_scale": {"name": "Dragon Scale", "sell_price": 4500},
    "kong_fur": {"name": "Gorilla Fur Tuft", "sell_price": 3200},
    "yeti_claw": {"name": "Frozen Yeti Claw", "sell_price": 3800},
    "magma_core": {"name": "Volcanic Magma Core", "sell_price": 7500},
    "wolf_fang": {"name": "Alpha Wolf Fang", "sell_price": 2800},
    "trex_tooth": {"name": "Fossilized T-Rex Tooth", "sell_price": 5000},
    "saber_pelt": {"name": "Saber-Tooth Pelt", "sell_price": 2500},
    "venom_stinger": {"name": "Giant Venom Stinger", "sell_price": 2700},
    "phoenix_feather": {"name": "Glowing Phoenix Feather", "sell_price": 6500},
    "zombie_brain": {"name": "Preserved Zombie Brain", "sell_price": 2000},
    "mammoth_tusk": {"name": "Ivory Mammoth Tusk", "sell_price": 3600},
    "hydra_head": {"name": "Severed Hydra Head", "sell_price": 6000},
    "boar_hide": {"name": "Tough Boar Hide", "sell_price": 2100},
    "vampire_cape": {"name": "Crimson Vampire Cape", "sell_price": 4800},
    "oni_mask": {"name": "Cursed Oni Mask", "sell_price": 8500},
    "griffin_talon": {"name": "Golden Eagle Feather", "sell_price": 6800},
    "wendigo_antler": {"name": "Forest Wolf Pelt", "sell_price": 7200},
    "chupacabra_fang": {"name": "Chupacabra Blood Fang", "sell_price": 4100},
    "basilisk_eye": {"name": "Petrifying Basilisk Eye", "sell_price": 8900},
    "chimera_mane": {"name": "Tri-Beast Chimera Mane", "sell_price": 9400},
    "minotaur_horn": {"name": "Labyrinth Minotaur Horn", "sell_price": 5200},
    "cerberus_collar": {"name": "Spiked Cerberus Collar", "sell_price": 11000},
    "cyclops_monocle": {"name": "Giant Cyclops Monocle", "sell_price": 4700},
    "manticore_tail": {"name": "Venomous Manticore Spike", "sell_price": 5900},
    "behemoth_rib": {"name": "Colossal Behemoth Rib", "sell_price": 12500},
    "monkey_hair": {"name": "Monkey Tail Hair", "sell_price": 800},
    "fox_pelt": {"name": "Red Fox Pelt", "sell_price": 1200},
    "rabbit_foot": {"name": "Lucky Rabbit Foot", "sell_price": 1500},
    "raccoon_mask": {"name": "Dumpster Diver Mask", "sell_price": 950},
    "skunk_gland": {"name": "Toxic Skunk Gland", "sell_price": 1100},
    "bear_claw": {"name": "Grizzly Bear Claw", "sell_price": 2900},
    "leopard_pelt": {"name": "Spotted Leopard Pelt", "sell_price": 3400},
    "croc_scale": {"name": "Crocodile Scale Armor", "sell_price": 3100},
    "owl_feather": {"name": "Midnight Owl Feather", "sell_price": 1800},
    "warthog_tusk": {"name": "Curved Warthog Tusk", "sell_price": 1650},
    "shark_fin": {"name": "Great White Fin", "sell_price": 3000},
    "kraken_ink": {"name": "Cosmic Kraken Ink", "sell_price": 6500},
    "leviathan_pearl": {"name": "Abyssal Leviathan Pearl", "sell_price": 7200},
    "megalodon_jaw": {"name": "Colossal Megalodon Jaw", "sell_price": 5800},
    "siren_tear": {"name": "Crystallized Siren Tear", "sell_price": 4000},
    "crab_shell": {"name": "Reinforced King Crab Shell", "sell_price": 2400},
    "eel_battery": {"name": "Bio-Electric Eel Gland", "sell_price": 3300},
    "gator_leather": {"name": "Ancient Swamp Gator Skin", "sell_price": 3500},
    "squid_tentacle": {"name": "Giant Squid Tentacle", "sell_price": 4900},
    "ancient_shell": {"name": "Prehistoric Turtle Shell", "sell_price": 2200},
    "hammerhead_skull": {"name": "Hammerhead Trophy Skull", "sell_price": 3100},
    "ghost_compass": {"name": "Cursed Phantom Compass", "sell_price": 9500},
    "vortex_shard": {"name": "Deep Sea Vortex Shard", "sell_price": 6200},
    "puffer_toxin": {"name": "Rare Pufferfish Toxin", "sell_price": 2600},
    "water_dragon_orb": {"name": "Jade Water Dragon Orb", "sell_price": 8000},
    "angler_bulb": {"name": "Bioluminescent Angler Bulb", "sell_price": 3900},
    "narwhal_tusk": {"name": "Spiraled Narwhal Horn", "sell_price": 5400},
    "cthulhu_relic": {"name": "Giant Deep-Sea Squid Eye", "sell_price": 15000},
    "manta_wing": {"name": "Shadow Manta Wing", "sell_price": 4200},
    "orca_tooth": {"name": "Apex Orca Tooth", "sell_price": 4600},
    "abyssal_crown": {"name": "Sunken Poseidon Crown", "sell_price": 13500},
    "goblin_shark_nose": {"name": "Goblin Shark Snout", "sell_price": 3700},
    "sea_serpent_scale": {"name": "Iridescent Serpent Scale", "sell_price": 6900},
    "mermaid_harp": {"name": "Enchanted Coral Harp", "sell_price": 8800},
    "triton_trident": {"name": "Broken Triton Trident", "sell_price": 11500},
    "lobster_claw": {"name": "Giant Lobster Claw", "sell_price": 2300},
    "jelly_gel": {"name": "Bioluminescent Jelly Gel", "sell_price": 2750},
    "seal_blubber": {"name": "Thick Seal Blubber", "sell_price": 2100},
    "marlin_bill": {"name": "Sharp Marlin Bill", "sell_price": 3250},
    "pink_pearl": {"name": "Flawless Pink Pearl", "sell_price": 5500},
    "giant_worm": {"name": "Slimy Giant Earthworm", "sell_price": 650},
    "mole_claw": {"name": "Star-Nosed Mole Claw", "sell_price": 1350},
    "armadillo_shell": {"name": "Armored Armadillo Shell", "sell_price": 1900},
    "amber_mosquito": {"name": "Prehistoric Amber Fossil", "sell_price": 4200},
    "tarantula_fang": {"name": "Subterranean Tarantula Fang", "sell_price": 2450},
    "teller_stamp": {"name": "Official Teller Stamp", "sell_price": 3500},
    "cashier_badge": {"name": "Golden Cashier Badge", "sell_price": 5500},
    "vault_keycard": {"name": "Encrypted Vault Keycard", "sell_price": 9000},
    "manager_rolex": {"name": "Manager Karthik's Fake Rolex", "sell_price": 14000},
    "invingoppa_ledger": {"name": "INVINGOPPA's Secret Black Ledger", "sell_price": 35000},
    "intern_coffee": {"name": "Intern Sanjay's Iced Latte", "sell_price": 2500},
    "auditor_glasses": {"name": "Chief Auditor Murugan's Bifocals", "sell_price": 11000},
    "guard_baton": {"name": "Security Chief Balaji's Stun Baton", "sell_price": 8500},
    "it_usb": {"name": "IT Head Venkat's Backdoor USB", "sell_price": 18000},
    "director_cigar": {"name": "Board Director Sundar's Cuban Cigar", "sell_price": 24000},

    # Expanded wildlife drops
    "snow_fox_pelt": {"name": "Snow Fox Pelt", "sell_price": 1750},
    "moon_bear_fur": {"name": "Moon Bear Fur", "sell_price": 3900},
    "golden_jackal_tooth": {"name": "Golden Jackal Tooth", "sell_price": 2600},
    "clouded_leopard_spot": {"name": "Clouded Leopard Mark", "sell_price": 4400},
    "peacock_plume": {"name": "Iridescent Peacock Plume", "sell_price": 2200},
    "silver_otter_whisker": {"name": "Silver Otter Whisker", "sell_price": 1900},
    "tiger_beetle_shell": {"name": "Titan Tiger Beetle Shell", "sell_price": 1650},
    "giant_panda_token": {"name": "Giant Panda Keepsake", "sell_price": 5200},
    "wild_boar_tusk": {"name": "Wild Boar Tusk", "sell_price": 1450},
    "falcon_feather": {"name": "Falcon Feather", "sell_price": 2400},
    "river_dolphin_charm": {"name": "River Dolphin Charm", "sell_price": 3500},
    "blue_whale_song": {"name": "Blue Whale Song Crystal", "sell_price": 7200},
    "swordfish_bill": {"name": "Swordfish Bill", "sell_price": 3100},
    "koi_scale": {"name": "Golden Koi Scale", "sell_price": 2700},
    "sea_turtle_tag": {"name": "Sea Turtle Tag", "sell_price": 1800},
    "flying_fish_fin": {"name": "Flying Fish Fin", "sell_price": 1250},
    "lanternfish_glow": {"name": "Lanternfish Glow Pearl", "sell_price": 2900},
    "stingray_silk": {"name": "Stingray Silk", "sell_price": 3300},
    "river_crab_claw": {"name": "River Crab Claw", "sell_price": 1150},
    "ice_fish_scale": {"name": "Icefish Scale", "sell_price": 2050},
    "fossil_trilobite": {"name": "Trilobite Fossil", "sell_price": 3600},
    "geode_crystal": {"name": "Rainbow Geode Crystal", "sell_price": 4100},
    "ancient_coin": {"name": "Ancient Buried Coin", "sell_price": 5000},
    "glow_worm": {"name": "Glow Worm Jar", "sell_price": 980},
    "cave_salamander": {"name": "Cave Salamander Scale", "sell_price": 1750},
    "crystal_beetle": {"name": "Crystal Beetle Shell", "sell_price": 2300},
    "buried_robot": {"name": "Vintage Buried Robot Part", "sell_price": 5600},
    "mole_crown": {"name": "Mole King's Tiny Crown", "sell_price": 3200},
    "amber_frog": {"name": "Amber Tree Frog Fossil", "sell_price": 2950},
    "clerk_glasses": {"name": "Clerk's Reading Glasses", "sell_price": 1800},
    "clerk_lanyard": {"name": "Senior Clerk Lanyard", "sell_price": 4200},
    "clerk_calculator": {"name": "INVINGOPPA's Calculator", "sell_price": 7600},
    "clerk_stamp": {"name": "Executive Approval Stamp", "sell_price": 9800},
    "clerk_trophy": {"name": "Employee of the Century Trophy", "sell_price": 15000},

}

JOBS = {
    "moderator": {"name": "Meme Moderator", "pay": (150, 400), "req_level": 1, "desc": "Keep the Discord server clean of cringe."},
    "street_magician": {"name": "Street Magician", "pay": (200, 600), "req_level": 1, "desc": "Do card tricks for loose change."},
    "trash_collector": {"name": "Trash Collector", "pay": (300, 750), "req_level": 1, "desc": "Recycle discarded electronics."},
    "stray_feeder": {"name": "Professional Cat Feeder", "pay": (500, 1200), "req_level": 1, "desc": "Feed stray cats behind local diner."},
    "gugan_pe": {"name": "Gugan PE Sir", "pay": (600, 1500), "req_level": 1, "desc": "Make students run 10 laps in scorching heat while blowing a whistle."},
    "streamer": {"name": "Twitch Streamer", "pay": (400, 900), "req_level": 2, "desc": "Play dank games and get donations."},
    "fast_food": {"name": "Fast Food Fry Cook", "pay": (450, 950), "req_level": 2, "desc": "Flip burgers at 3 AM."},
    "delivery_driver": {"name": "Food Delivery Driver", "pay": (600, 1200), "req_level": 2, "desc": "Eat half the fries before delivery."},
    "barista": {"name": "Overpriced Barista", "pay": (800, 1500), "req_level": 2, "desc": "Spell customer names wrong on purpose."},
    "miner": {"name": "Crypto Miner", "pay": (900, 1800), "req_level": 3, "desc": "Mine Dogecoin in your basement rig."},
    "discord_admin": {"name": "Power-Trip Discord Admin", "pay": (1000, 2000), "req_level": 3, "desc": "Ban people who use light mode."},
    "tiktok_influencer": {"name": "TikTok NPC Streamer", "pay": (1200, 2500), "req_level": 3, "desc": "Say 'Ice cream so good' for 6 hours."},
    "street_artist": {"name": "Underground Graffiti Artist", "pay": (1500, 3200), "req_level": 4, "desc": "Paint murals on subway trains."},
    "hacker": {"name": "Dark Web Hacker", "pay": (1800, 3500), "req_level": 4, "desc": "Steal data from corporate mainframes."},
    "ceo": {"name": "Tech CEO", "pay": (3500, 7000), "req_level": 5, "desc": "Run a multi-billion dollar tech enterprise."},
    "stunt_double": {"name": "Hollywood Stunt Double", "pay": (3500, 7000), "req_level": 5, "desc": "Jump off buildings for action flicks."},
    "scam_caller": {"name": "Scam Call Center Agent", "pay": (4000, 8000), "req_level": 6, "desc": "Tell people their computer has virus."},
    "ghost_hunter": {"name": "Paranormal Investigator", "pay": (4000, 8500), "req_level": 6, "desc": "Hunt poltergeists for reality TV."},
    "cryptid_wrangler": {"name": "Cryptid Wrangler", "pay": (5000, 9000), "req_level": 7, "desc": "Catch Bigfoot in the woods."},
    "ponzi_boss": {"name": "Ponzi Scheme Architect", "pay": (7500, 12000), "req_level": 7, "desc": "Convince investors into fake crypto."},
    "bounty_hunter": {"name": "Cyber Bounty Hunter", "pay": (5000, 10000), "req_level": 8, "desc": "Track down digital fugitives."},
    "ai_trainer": {"name": "AI Prompt Engineer", "pay": (6000, 11000), "req_level": 8, "desc": "Tell LLMs to write python code all day."},
    "bodyguard": {"name": "VIP Bodyguard", "pay": (6500, 13000), "req_level": 9, "desc": "Take bullets for rich influencers."},
    "dj_producer": {"name": "EDM Festival DJ", "pay": (8500, 15000), "req_level": 9, "desc": "Press play on pre-recorded mixes."},
    "quantum_physicist": {"name": "Quantum Physicist", "pay": (12000, 20000), "req_level": 10, "desc": "Open portals to parallel economies."},
    "dark_web_arms": {"name": "Dark Web Arms Dealer", "pay": (15000, 25000), "req_level": 12, "desc": "Sell illegal meme templates."},
    "meme_lord": {"name": "Supreme Meme Lord", "pay": (20000, 35000), "req_level": 15, "desc": "Control viral trends worldwide."},
    "casino_pit_boss": {"name": "Casino Pit Boss", "pay": (25000, 45000), "req_level": 16, "desc": "Ensure the house always wins."},
    "galactic_smuggler": {"name": "Galactic Smuggler", "pay": (30000, 50000), "req_level": 18, "desc": "Smuggle rare Pepe files across galaxies."},
    "time_traveller": {"name": "Time Travelling Trader", "pay": (45000, 75000), "req_level": 20, "desc": "Buy stocks yesterday and sell them last week."},
    "matrix_architect": {"name": "Matrix Architect", "pay": (70000, 100000), "req_level": 25, "desc": "Rewrite the simulation parameters."},
}

HUNT_BOSSES = [
    {"name": "🐉 Ancient Ender Dragon", "reward": 15000, "risk": 0.45, "drop": "dragon_scale"},
    {"name": "🦍 King Kong Gorilla", "reward": 12000, "risk": 0.38, "drop": "kong_fur"},
    {"name": "🧊 Abominable Yeti", "reward": 14000, "risk": 0.40, "drop": "yeti_claw"},
    {"name": "🌋 Volcanic Titan", "reward": 25000, "risk": 0.55, "drop": "magma_core"},
    {"name": "🐺 Alpha Werewolf Pack", "reward": 11000, "risk": 0.35, "drop": "wolf_fang"},
    {"name": "🦖 Mutant T-Rex", "reward": 18000, "risk": 0.48, "drop": "trex_tooth"},
    {"name": "🐅 Saber-Toothed Tiger", "reward": 9500, "risk": 0.30, "drop": "saber_pelt"},
    {"name": "🦂 Giant Death Crawler", "reward": 10500, "risk": 0.32, "drop": "venom_stinger"},
    {"name": "🦅 Thunder Phoenix", "reward": 22000, "risk": 0.50, "drop": "phoenix_feather"},
    {"name": "🧟 Undead Zombie Horde", "reward": 8000, "risk": 0.28, "drop": "zombie_brain"},
    {"name": "🦣 Ice Age Mammoth", "reward": 13000, "risk": 0.39, "drop": "mammoth_tusk"},
    {"name": "🐍 Venomous Hydra", "reward": 20000, "risk": 0.52, "drop": "hydra_head"},
    {"name": "🐗 Razorback Boar King", "reward": 8500, "risk": 0.29, "drop": "boar_hide"},
    {"name": "🦇 Vampire Lord Bat", "reward": 16000, "risk": 0.44, "drop": "vampire_cape"},
    {"name": "👹 Mountain Oni Demon", "reward": 28000, "risk": 0.60, "drop": "oni_mask"},
    {"name": "🦅 Majestic Mountain Eagle", "reward": 19500, "risk": 0.47, "drop": "griffin_talon"},
    {"name": "🐺 Feral Forest Wolf", "reward": 21000, "risk": 0.49, "drop": "wendigo_antler"},
    {"name": "🐕 Nocturnal Chupacabra", "reward": 11500, "risk": 0.34, "drop": "chupacabra_fang"},
    {"name": "🐍 King Basilisk", "reward": 26500, "risk": 0.57, "drop": "basilisk_eye"},
    {"name": "🐐 Fire-Breathing Chimera", "reward": 27500, "risk": 0.58, "drop": "chimera_mane"},
    {"name": "🐂 Labyrinth Minotaur", "reward": 15500, "risk": 0.43, "drop": "minotaur_horn"},
    {"name": "🐕‍🦺 Three-Headed Cerberus", "reward": 32000, "risk": 0.63, "drop": "cerberus_collar"},
    {"name": "👁️ One-Eyed Cyclops", "reward": 14500, "risk": 0.41, "drop": "cyclops_monocle"},
    {"name": "🦁 Scorpion Manticore", "reward": 17500, "risk": 0.46, "drop": "manticore_tail"},
    {"name": "🦕 Earth-Shaking Behemoth", "reward": 35000, "risk": 0.66, "drop": "behemoth_rib"},
    {"name": "🐒 Wild Baboon", "reward": 3500, "risk": 0.20, "drop": "monkey_hair"},
    {"name": "🦊 Sneaky Red Fox", "reward": 4200, "risk": 0.22, "drop": "fox_pelt"},
    {"name": "🐇 Aggressive Jackrabbit", "reward": 3000, "risk": 0.18, "drop": "rabbit_foot"},
    {"name": "🦝 Trash-Panda Raccoon", "reward": 3800, "risk": 0.21, "drop": "raccoon_mask"},
    {"name": "🦨 Revengeful Skunk", "reward": 4000, "risk": 0.23, "drop": "skunk_gland"},
    {"name": "🐻 Grizzly Cave Bear", "reward": 7200, "risk": 0.31, "drop": "bear_claw"},
    {"name": "🐆 Shadow Leopard", "reward": 8400, "risk": 0.33, "drop": "leopard_pelt"},
    {"name": "🐊 Nile River Crocodile", "reward": 7800, "risk": 0.32, "drop": "croc_scale"},
    {"name": "🦉 Giant Horned Owl", "reward": 4500, "risk": 0.20, "drop": "owl_feather"},
    {"name": "🐗 Tusked Warthog", "reward": 4900, "risk": 0.24, "drop": "warthog_tusk"},
]

FISH_BOSSES = [
    {"name": "🦈 Great White Shark", "reward": 10000, "risk": 0.35, "drop": "shark_fin"},
    {"name": "🐙 Cosmic Kraken", "reward": 22000, "risk": 0.52, "drop": "kraken_ink"},
    {"name": "🌊 Leviathan Sea Serpent", "reward": 24000, "risk": 0.55, "drop": "leviathan_pearl"},
    {"name": "🐋 Colossal Megalodon", "reward": 19000, "risk": 0.48, "drop": "megalodon_jaw"},
    {"name": "🧜 Abyssal Siren", "reward": 14000, "risk": 0.40, "drop": "siren_tear"},
    {"name": "🦀 Mutant King Crab", "reward": 9000, "risk": 0.30, "drop": "crab_shell"},
    {"name": "⚡ Electric Moray Eel", "reward": 11500, "risk": 0.36, "drop": "eel_battery"},
    {"name": "🐊 Ancient Swamp Alligator", "reward": 12500, "risk": 0.38, "drop": "gator_leather"},
    {"name": "🦑 Colossal Architeuthis", "reward": 17000, "risk": 0.45, "drop": "squid_tentacle"},
    {"name": "🐢 Prehistoric Sea Turtle", "reward": 8500, "risk": 0.28, "drop": "ancient_shell"},
    {"name": "🦈 Hammerhead Beast", "reward": 10500, "risk": 0.33, "drop": "hammerhead_skull"},
    {"name": "👻 Phantom Ghost Shipwreck", "reward": 30000, "risk": 0.65, "drop": "ghost_compass"},
    {"name": "🌀 Deep Sea Whirlpool Vortex", "reward": 21000, "risk": 0.50, "drop": "vortex_shard"},
    {"name": "🐡 Toxic Pufferfish King", "reward": 9500, "risk": 0.31, "drop": "puffer_toxin"},
    {"name": "🐉 Chinese Water Dragon", "reward": 26000, "risk": 0.58, "drop": "water_dragon_orb"},
    {"name": "🔦 Trench Anglerfish", "reward": 11800, "risk": 0.37, "drop": "angler_bulb"},
    {"name": "🦄 Arctic Narwhal", "reward": 16200, "risk": 0.44, "drop": "narwhal_tusk"},
    {"name": "🐙 Giant Deep-Sea Squid", "reward": 40000, "risk": 0.68, "drop": "cthulhu_relic"},
    {"name": "🛸 Abyssal Manta Ray", "reward": 13200, "risk": 0.39, "drop": "manta_wing"},
    {"name": "🐬 Alpha Killer Orca", "reward": 14800, "risk": 0.42, "drop": "orca_tooth"},
    {"name": "👑 Sunken King Poseidon", "reward": 36000, "risk": 0.64, "drop": "abyssal_crown"},
    {"name": "👺 Deep Goblin Shark", "reward": 11200, "risk": 0.35, "drop": "goblin_shark_nose"},
    {"name": "🐍 Rainbow Sea Serpent", "reward": 20500, "risk": 0.51, "drop": "sea_serpent_scale"},
    {"name": "🎶 Siren Choir Matriarch", "reward": 25500, "risk": 0.56, "drop": "mermaid_harp"},
    {"name": "🔱 Royal Guard Triton", "reward": 31000, "risk": 0.61, "drop": "triton_trident"},
    {"name": "🦞 Colossal Red Lobster", "reward": 6200, "risk": 0.24, "drop": "lobster_claw"},
    {"name": "🪼 Neon Box Jellyfish", "reward": 7400, "risk": 0.29, "drop": "jelly_gel"},
    {"name": "🦭 Arctic Leopard Seal", "reward": 5800, "risk": 0.25, "drop": "seal_blubber"},
    {"name": "🐟 Sword-Nosed Marlin", "reward": 8800, "risk": 0.31, "drop": "marlin_bill"},
    {"name": "🦪 Giant Clam Oyster", "reward": 13500, "risk": 0.27, "drop": "pink_pearl"},
]

DIG_ANIMALS = [
    {"name": "🪱 Giant Earthworm", "drop": "giant_worm"},
    {"name": "🦦 Blind Star-Nosed Mole", "drop": "mole_claw"},
    {"name": "🦔 Armored Armadillo", "drop": "armadillo_shell"},
    {"name": "🦟 Trapped Amber Mosquito", "drop": "amber_mosquito"},
    {"name": "🕷️ Subterranean Tarantula", "drop": "tarantula_fang"},
]

BANK_CLERKS = [
    {"tier": "Entry-Level Staff", "name": "☕ Intern Sanjay", "reward": 5500, "risk": 0.22, "drop": "intern_coffee", "weight": 20},
    {"tier": "Mid-Level Clerk", "name": "🧾 Junior Teller Ramesh", "reward": 8000, "risk": 0.30, "drop": "teller_stamp", "weight": 18},
    {"tier": "Mid-Level Clerk", "name": "💳 Senior Cashier Priya", "reward": 14000, "risk": 0.40, "drop": "cashier_badge", "weight": 15},
    {"tier": "Security Division", "name": "👮 Security Chief Balaji", "reward": 19000, "risk": 0.46, "drop": "guard_baton", "weight": 12},
    {"tier": "Mid-Level Clerk", "name": "📑 Loan Officer Suresh", "reward": 22000, "risk": 0.50, "drop": "vault_keycard", "weight": 10},
    {"tier": "Audit Division", "name": "🧐 Chief Auditor Murugan", "reward": 27000, "risk": 0.54, "drop": "auditor_glasses", "weight": 8},
    {"tier": "Management", "name": "🕴️ Branch Manager Karthik", "reward": 32000, "risk": 0.58, "drop": "manager_rolex", "weight": 7},
    {"tier": "Cyber Vault", "name": "💻 IT Head Venkat", "reward": 42000, "risk": 0.62, "drop": "it_usb", "weight": 5},
    {"tier": "Executive Board", "name": "🎩 Board Director Sundar", "reward": 55000, "risk": 0.67, "drop": "director_cigar", "weight": 3},
    {"tier": "FINAL BOSS", "name": "👑 THE BANK CLERK: INVINGOPPA", "reward": 85000, "risk": 0.74, "drop": "invingoppa_ledger", "weight": 2},
]


# Additional non-graphic wildlife encounters for the web edition.
HUNT_BOSSES.extend([
    {"name": "🦊 Arctic Snow Fox", "reward": 4600, "risk": 0.22, "drop": "snow_fox_pelt"},
    {"name": "🐻 Himalayan Moon Bear", "reward": 8200, "risk": 0.34, "drop": "moon_bear_fur"},
    {"name": "🐆 Clouded Leopard", "reward": 9100, "risk": 0.36, "drop": "clouded_leopard_spot"},
    {"name": "🦚 Royal Peacock", "reward": 3900, "risk": 0.16, "drop": "peacock_plume"},
    {"name": "🦦 Silver River Otter", "reward": 4300, "risk": 0.19, "drop": "silver_otter_whisker"},
    {"name": "🪲 Titan Tiger Beetle", "reward": 3500, "risk": 0.14, "drop": "tiger_beetle_shell"},
    {"name": "🐼 Bamboo Forest Panda", "reward": 10500, "risk": 0.10, "drop": "giant_panda_token"},
    {"name": "🐗 Wild Boar Champion", "reward": 5100, "risk": 0.27, "drop": "wild_boar_tusk"},
    {"name": "🦅 Golden Falcon", "reward": 6200, "risk": 0.23, "drop": "falcon_feather"},
    {"name": "🐺 Midnight Jackal", "reward": 5700, "risk": 0.25, "drop": "golden_jackal_tooth"},
    {"name": "🦌 Silver Antler Deer", "reward": 4900, "risk": 0.18, "drop": "silver_otter_whisker"},
    {"name": "🦡 Burrowing Badger", "reward": 3700, "risk": 0.17, "drop": "wild_boar_tusk"},
])
FISH_BOSSES.extend([
    {"name": "🐬 River Dolphin", "reward": 5600, "risk": 0.16, "drop": "river_dolphin_charm"},
    {"name": "🐋 Blue Whale Calf", "reward": 14000, "risk": 0.28, "drop": "blue_whale_song"},
    {"name": "🐟 Swordfish Sprinter", "reward": 6300, "risk": 0.25, "drop": "swordfish_bill"},
    {"name": "🐠 Golden Koi", "reward": 4700, "risk": 0.12, "drop": "koi_scale"},
    {"name": "🐢 Ancient Sea Turtle", "reward": 4100, "risk": 0.10, "drop": "sea_turtle_tag"},
    {"name": "🐟 Flying Fish", "reward": 2900, "risk": 0.11, "drop": "flying_fish_fin"},
    {"name": "🏮 Deep-Sea Lanternfish", "reward": 5900, "risk": 0.21, "drop": "lanternfish_glow"},
    {"name": "🪽 Giant Stingray", "reward": 6800, "risk": 0.27, "drop": "stingray_silk"},
    {"name": "🦀 Moonlit River Crab", "reward": 2500, "risk": 0.12, "drop": "river_crab_claw"},
    {"name": "🧊 Antarctic Icefish", "reward": 4500, "risk": 0.19, "drop": "ice_fish_scale"},
    {"name": "🦑 Glass Squid", "reward": 7900, "risk": 0.29, "drop": "vortex_shard"},
    {"name": "🐡 Spotted Pufferfish", "reward": 3600, "risk": 0.17, "drop": "puffer_toxin"},
])
DIG_ANIMALS.extend([
    {"name": "🪲 Crystal Cave Beetle", "drop": "crystal_beetle"},
    {"name": "🦎 Blind Cave Salamander", "drop": "cave_salamander"},
    {"name": "🪱 Glowing Glow Worm Colony", "drop": "glow_worm"},
    {"name": "🐸 Amber Tree Frog Fossil", "drop": "amber_frog"},
    {"name": "🦫 Buried Beaver Cache", "drop": "ancient_coin"},
    {"name": "🦴 Trilobite Fossil Bed", "drop": "fossil_trilobite"},
    {"name": "💎 Rainbow Geode Cluster", "drop": "geode_crystal"},
    {"name": "🤖 Forgotten Toy Robot", "drop": "buried_robot"},
    {"name": "🐹 Mole King's Hideout", "drop": "mole_crown"},
    {"name": "🦀 Ancient Buried Crab", "drop": "river_crab_claw"},
    {"name": "🪙 Lost Merchant's Coin Purse", "drop": "ancient_coin"},
    {"name": "🦟 Giant Amber Insect", "drop": "amber_mosquito"},
])

# Expanded clerk cast: these are fictional NPC encounters in the in-game bank event.
BANK_CLERKS.extend([
    {"tier": "Front Desk", "name": "📎 Receptionist Meena", "reward": 6200, "risk": 0.24, "drop": "clerk_glasses", "weight": 14},
    {"tier": "Accounts", "name": "🧮 Accounts Clerk Arjun", "reward": 11000, "risk": 0.34, "drop": "clerk_calculator", "weight": 12},
    {"tier": "Compliance", "name": "📋 Compliance Officer Divya", "reward": 18000, "risk": 0.45, "drop": "clerk_stamp", "weight": 9},
    {"tier": "Regional Office", "name": "🗂️ Regional Clerk Prakash", "reward": 23000, "risk": 0.49, "drop": "clerk_lanyard", "weight": 8},
    {"tier": "Executive Floor", "name": "🏅 Executive Clerk Nandhini", "reward": 36000, "risk": 0.57, "drop": "clerk_trophy", "weight": 5},
    {"tier": "INVINGOPPA's Office", "name": "👑 Deputy Chief Clerk Invingoppa Jr.", "reward": 65000, "risk": 0.68, "drop": "clerk_stamp", "weight": 2},
])

DEATH_MESSAGES = [
    "Soothe moodra dunde!",
    "DVD paiya saavu da!",
    "Unakku idhu thevaiya da? Poi saavu!",
    "Jose Paul personally deleted your kneecaps!",
    "INVINGOPPA stamped 'REJECTED' directly onto your forehead.",
    "Your Wi-Fi disconnected mid-heist and your heart stopped.",
    "You got ambushed during a high-stakes job and didn't make it.",
    "Your crypto portfolio hit -99.99% and gave you instant cardiac arrest.",
]

# --- Database & Multiplayer Helpers ---
def load_all_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "rooms": {
                "GLOBAL_HUB": {
                    "host": "SYSTEM",
                    "name": "Global Hub Egmore",
                    "preset": "egmore",
                    "is_public": True,
                    "members": [],
                    "heist": {"active": False, "contributions": {}}
                }
            }
        }
        save_all_data(default_data)
        return default_data
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
            if "users" not in data: data["users"] = {}
            if "rooms" not in data:
                data["rooms"] = {
                    "GLOBAL_HUB": {
                        "host": "SYSTEM", "name": "Global Hub Egmore", "preset": "egmore",
                        "is_public": True, "members": [],
                        "heist": {"active": False, "contributions": {}}
                    }
                }
            return data
    except Exception:
        return {"users": {}, "rooms": {"GLOBAL_HUB": {"host": "SYSTEM", "name": "Global Hub", "preset": "egmore", "is_public": True, "members": [], "heist": {"active": False}}}}


def save_all_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


def hash_password(password, salt=None):
    if not salt: salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}${hashed}"


def verify_password(stored_hash, password):
    try:
        salt, hashed = stored_hash.split("$")
        return hashed == hashlib.sha256((password + salt).encode()).hexdigest()
    except Exception:
        return False


def get_default_room_profile(preset_name):
    return {
        "preset": preset_name,
        "fampay": 500,
        "bank": 0,
        "bank_max": 5000,
        "level": 1,
        "xp": 0,
        "job": "moderator",
        "last_work": time.time(),
        "work_reminder_sent": False,
        "mailbox": [],
        "crypto_units": 0.0,
        "dead": False,
        "prison_end": 0,
        "last_daily": 0,
        "daily_streak": 0,
        "loan_due": 0,
        "loan_amount": 0,
        "inventory": {k: 0 for k in SHOP_ITEMS},
        "loot": {k: 0 for k in LOOT_ITEMS},
    }


def get_user_room_profile(all_data, username, room_code):
    users = all_data["users"]
    if username not in users: return None
    u_obj = users[username]
    if "room_profiles" not in u_obj: u_obj["room_profiles"] = {}
    
    rooms = all_data["rooms"]
    if room_code not in rooms: room_code = "GLOBAL_HUB"

    if room_code not in u_obj["room_profiles"]:
        preset = rooms[room_code].get("preset", "egmore")
        u_obj["room_profiles"][room_code] = get_default_room_profile(preset)
    else:
        def_prof = get_default_room_profile(rooms[room_code].get("preset", "egmore"))
        prof = u_obj["room_profiles"][room_code]
        for k, v in def_prof.items():
            if k not in prof: prof[k] = v
        if "wallet" in prof and "fampay" not in prof:
            prof["fampay"] = prof.pop("wallet")
        for k, v in def_prof["inventory"].items():
            if k not in prof["inventory"]: prof["inventory"][k] = v
        for k, v in def_prof["loot"].items():
            if k not in prof["loot"]: prof["loot"][k] = v
    return u_obj["room_profiles"][room_code]


def get_current_session(all_data, username):
    users = all_data["users"]
    if username not in users: return None, None, None
    u_obj = users[username]
    u_obj["last_active"] = time.time()
    room_code = u_obj.get("current_room", "GLOBAL_HUB")
    if room_code not in all_data["rooms"]: room_code = "GLOBAL_HUB"
    
    preset = all_data["rooms"][room_code].get("preset", "egmore")
    city_cfg = CITIES.get(preset, CITIES["egmore"])
    profile = get_user_room_profile(all_data, username, room_code)
    return profile, room_code, city_cfg


def add_xp(u, amount):
    u["xp"] += amount
    xp_needed = u["level"] * 300
    if u["xp"] >= xp_needed:
        u["level"] += 1
        u["xp"] = 0
        u["bank_max"] += 2500
        bonus = u["level"] * 500
        u["fampay"] += bonus
        print(f"\n🎉 **LEVEL UP!** Reached **Level {u['level']}**! Bonus: 🪙 {bonus:,} Coins & +2,500 Bank Space!")


def handle_death(u, city_cfg):
    if u["inventory"]["shield"] > 0:
        u["inventory"]["shield"] -= 1
        print("\n🛡️ **SHIELD SAVED YOU!** Shield shattered and saved your life!")
        return False
    elif u["inventory"]["reviver"] > 0:
        u["inventory"]["reviver"] -= 1
        print("\n✨ **REVIVER TOKEN ACTIVATED!** Instantly resurrected you!")
        return False
    else:
        u["fampay"] = 0
        u["dead"] = True
        print(f"\n💀 **YOU DIED!** {random.choice(DEATH_MESSAGES)}")
        return True


def check_status(u, city_cfg):
    if u["dead"]:
        print("\n💀 You are **DEAD**! Type `revive` or buy a Reviver Token.")
        return False
    if time.time() < u["prison_end"]:
        rem = int(u["prison_end"] - time.time())
        print(f"\n🚨 In Prison! Wait {rem} seconds.")
        return False
    
    if city_cfg["name"] == "Perambur" and random.random() < city_cfg["mug_chance"]:
        lost = min(u["fampay"], random.randint(200, 1000))
        if lost > 0 and u["inventory"]["padlock"] == 0:
            u["fampay"] -= lost
            print(f"\n🥷 **PERAMBUR MUGGING!** Stole 🪙 {lost:,} coins from your FamPay Balance!")
        elif u["inventory"]["padlock"] > 0:
            u["inventory"]["padlock"] -= 1
            print("\n🔒 **PADLOCK SAVED YOU!** Padlock broke!")
    elif city_cfg["name"] == "Anna Nagar" and random.random() < 0.20:
        tax = min(u["fampay"], random.randint(500, 2500))
        if tax > 0:
            u["fampay"] -= tax
            print(f"\n🧾 **ANNA NAGAR TAX AUDIT!** Seized 🪙 {tax:,} coins from FamPay!")
    return True


def perform_job_check(u, job_name):
    print(f"\n📋 **MANDATORY SHIFT CHECK — {job_name.upper()}**")
    if random.choice(["math", "code"]) == "math":
        a, b = random.randint(12, 49), random.randint(11, 39)
        ans = input(f"🧮 What is {a} + {b}? > ").strip()
        return ans == str(a + b)
    else:
        code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=5))
        ans = input(f"⌨️ Type `{code}` exactly > ").strip()
        return ans == code


# --- DLF COMMANDERS CASINO GAMES ---
def create_deck():
    return [(v, s) for s in ["♠", "♥", "♦", "♣"] for v in ["2","3","4","5","6","7","8","9","10","J","Q","K","A"]]


def format_hand(hand):
    return " ".join([f"[{v}{s}]" for v, s in hand])


def play_blackjack(all_data, username, bet):
    u, _, _ = get_current_session(all_data, username)
    deck = create_deck(); random.shuffle(deck)
    p_hand, d_hand = [deck.pop(), deck.pop()], [deck.pop(), deck.pop()]

    def val(h):
        v, aces = 0, 0
        for card, _ in h:
            if card in ["J", "Q", "K"]: v += 10
            elif card == "A": aces += 1; v += 11
            else: v += int(card)
        while v > 21 and aces > 0: v -= 10; aces -= 1
        return v

    print(f"\n🃏 ======= DLF COMMANDERS CASINO: BLACKJACK =======")
    print(f"Dealer shows: {format_hand([d_hand[0]])} [??]")
    print(f"Your hand:    {format_hand(p_hand)} (Value: {val(p_hand)})")

    while val(p_hand) < 21:
        choice = input("Type `hit` or `stand`: ").strip().lower()
        if choice == "hit":
            p_hand.append(deck.pop())
            print(f"Your hand: {format_hand(p_hand)} (Value: {val(p_hand)})")
        elif choice == "stand": break

    p_val, d_val = val(p_hand), val(d_hand)
    if p_val > 21:
        u["fampay"] -= bet; print(f"💥 **BUST!** Lost 🪙 {bet:,} coins.")
    else:
        while d_val < 17: d_hand.append(deck.pop()); d_val = val(d_hand)
        if d_val > 21 or p_val > d_val:
            u["fampay"] += bet; add_xp(u, 90); print(f"🎉 **YOU WIN!** Won 🪙 {bet:,} coins!")
        elif p_val < d_val:
            u["fampay"] -= bet; print(f"💸 **YOU LOSE!** Lost 🪙 {bet:,} coins.")
        else: print("🤝 **PUSH!** Tie game.")
    save_all_data(all_data)


def play_mines(all_data, username, bet, bombs=3):
    u, _, _ = get_current_session(all_data, username)
    bomb_pos = set(random.sample(range(1, 17), bombs))
    revealed, mult = set(), 1.0
    print(f"\n💣 ======= MINES ({bombs} BOMBS) =======")
    while True:
        for r in range(4):
            print("  " + " ".join([("[💎]" if (r*4+c+1) in revealed else f"[{r*4+c+1:02d}]") for c in range(4)]))
        curr_payout = int(bet * mult)
        print(f"Multiplier: {mult:.2f}x | Potential: 🪙 {curr_payout:,}")
        choice = input("Enter tile (1-16) or `cashout`: ").strip().lower()
        if choice == "cashout":
            if not revealed: print("❌ Reveal at least 1 tile!"); continue
            u["fampay"] += (curr_payout - bet); add_xp(u, 85); save_all_data(all_data)
            print(f"🎉 **CASHED OUT!** Won 🪙 {curr_payout:,} coins!"); return
        try: tile = int(choice)
        except ValueError: continue
        if tile in bomb_pos:
            u["fampay"] -= bet; save_all_data(all_data); print(f"💥 **BOOM!** Lost 🪙 {bet:,}!"); return
        else:
            revealed.add(tile); mult += 0.25 + (bombs * 0.12)
            if len(revealed) == 16 - bombs:
                u["fampay"] += (int(bet * mult) - bet); save_all_data(all_data); print("🏆 **BOARD CLEARED!**"); return


def play_baccarat(all_data, username, bet, side):
    u, _, _ = get_current_session(all_data, username)
    deck = create_deck()
    sc = lambda cards: sum([0 if v in ["10","J","Q","K"] else (1 if v=="A" else int(v)) for v,_ in cards]) % 10
    p, b = [deck.pop(), deck.pop()], [deck.pop(), deck.pop()]
    winner = "player" if sc(p) > sc(b) else ("banker" if sc(b) > sc(p) else "tie")
    if side == winner:
        mult = 8 if winner == "tie" else 2
        u["fampay"] += (bet * mult - bet); print(f"🎉 **BACCARAT WIN!** Won 🪙 {bet * mult:,} coins!")
    else:
        u["fampay"] -= bet; print(f"💸 **BACCARAT LOSS!** Lost 🪙 {bet:,} coins.")
    save_all_data(all_data)


def play_keno(all_data, username, bet):
    u, _, _ = get_current_session(all_data, username)
    picks = [int(x) for x in input("Pick 4 numbers (1-20): ").strip().split()]
    drawn = sorted(random.sample(range(1, 21), 5))
    matches = len(set(picks).intersection(set(drawn)))
    mult = {0:0, 1:0, 2:2, 3:5, 4:15}.get(matches, 0)
    if mult > 0: u["fampay"] += (bet * mult - bet); print(f"🎉 **KENO WIN ({mult}x)!**")
    else: u["fampay"] -= bet; print("💸 **KENO LOSS!**")
    save_all_data(all_data)


def play_wheel(all_data, username, bet):
    u, _, _ = get_current_session(all_data, username)
    label, mult = random.choice([("BUST", 0.0), ("0.5x", 0.5), ("1.5x", 1.5), ("2x", 2.0), ("5x", 5.0), ("10x JACKPOT", 10.0)])
    print(f"🎡 Wheel landed on: **{label}**")
    if mult > 1.0: u["fampay"] += int(bet * mult - bet); print("🎉 Win!")
    else: u["fampay"] -= bet; print("💸 Loss!")
    save_all_data(all_data)


def play_plinko(all_data, username, bet):
    u, _, _ = get_current_session(all_data, username)
    mult = random.choice([0.2, 0.5, 0.5, 1.5, 1.5, 3.0, 8.0])
    payout = int(bet * mult); u["fampay"] += (payout - bet)
    print(f"🎯 Plinko slot: {mult}x | Payout: 🪙 {payout:,}")
    save_all_data(all_data)


def play_rps(all_data, username, bet, choice):
    u, _, _ = get_current_session(all_data, username)
    bot = random.choice(["rock", "paper", "scissors"])
    print(f"You: {choice} | House: {bot}")
    if choice == bot: print("🤝 Tie.")
    elif (choice=="rock" and bot=="scissors") or (choice=="paper" and bot=="rock") or (choice=="scissors" and bot=="paper"):
        u["fampay"] += bet; print("🎉 Win!")
    else: u["fampay"] -= bet; print("💸 Loss!")
    save_all_data(all_data)


def play_war(all_data, username, bet):
    u, _, _ = get_current_session(all_data, username)
    p, d = random.randint(2, 14), random.randint(2, 14)
    if p > d: u["fampay"] += bet; print("🎉 War Win!")
    elif p < d: u["fampay"] -= bet; print("💸 War Loss!")
    else: print("Tie war.")
    save_all_data(all_data)


# --- Help Menu ---
def show_help():
    print("\n================ 🎮 SCAM JOSE PAUL MULTIPLAYER HELP ================")
    print("  bal / balance          - Check FamPay Balance, bank, room stats")
    print("  rooms / room list      - View public and private rooms")
    print("  room create <preset>   - Create a private City room with Party Code")
    print("  room join <code>       - Join another player's private room")
    print("  terminate_room         - Host-only: Dissolve current room")
    print("  players / sidebar      - View real-time online/offline player status")
    print("  rob <player>           - Rob another player in the SAME room")
    print("  heist start / contribute <amt> / launch - Co-op Bank Heists")
    print("  bank_heist             - Solo raid against Bank Clerks & INVINGOPPA")
    print("  bag / inv              - Check inventory & loot drops")
    print("  shop                   - Open 'Fresh 4 Today' store")
    print("  buy <item>             - Purchase defense gear or collectibles from shop")
    print("  sell <item> / pawn     - Sell loot or rare collectibles")
    print("  jobs / apply <id> / work - Career & shift work with anti-bot check")
    print("  daily, beg, dig, scam  - Street hustles & daily claims")
    print("  hunt, fish, dig        - Boss encounters and material drops")
    print("  crypto <amt>           - Meme coin trading")
    print("  loan_shark <amt>       - Borrow dirty cash")
    print("  --- DLF COMMANDERS CASINO (19 GAMES) ---")
    print("  blackjack, mines, baccarat, keno, wheel, plinko, rps, war")
    print("  gamble, coinflip, slots, roulette, dice, crash, highlow, horse_race, lottery, russian_roulette")
    print("  leaderboard / lb       - Global net worth leaderboard")
    print("  exit                   - Save and logout")
    print("=====================================================================")


# --- Authentication Handler ---
def authenticate():
    all_data = load_all_data()
    print("\n================ AUTHENTICATION ================")
    print(" [1] Login\n [2] Register New Account")
    choice = input("Select option (1/2): ").strip()
    username = input("Enter Username: ").strip()
    if not username: return None

    if choice == "2":
        if username in all_data["users"]:
            print("❌ Username already exists!"); return authenticate()
        pwd = input("Enter Password: ").strip()
        all_data["users"][username] = {
            "password_hash": hash_password(pwd),
            "last_active": time.time(),
            "current_room": "GLOBAL_HUB",
            "room_profiles": {"GLOBAL_HUB": get_default_room_profile("egmore")}
        }
        if username not in all_data["rooms"]["GLOBAL_HUB"]["members"]:
            all_data["rooms"]["GLOBAL_HUB"]["members"].append(username)
        save_all_data(all_data)
        print("✅ Account created successfully!"); return username
    else:
        if username not in all_data["users"]:
            print("❌ Username not found."); return authenticate()
        pwd = input("Enter Password: ").strip()
        if verify_password(all_data["users"][username]["password_hash"], pwd):
            all_data["users"][username]["last_active"] = time.time()
            save_all_data(all_data); print("✅ Login successful!"); return username
        else: print("❌ Incorrect password."); return authenticate()


def main():
    print("🎮 Welcome to Scam Jose Paul - Fully Loaded Multiplayer Edition!")
    username = authenticate()
    if not username: return

    all_data = load_all_data()
    u, curr_room, city_cfg = get_current_session(all_data, username)
    save_all_data(all_data)

    print(f"\nWelcome, **{username}**! Room: **{curr_room}** ({city_cfg['name']}). Type `help`.")

    while True:
        try:
            all_data = load_all_data()
            u, curr_room, city_cfg = get_current_session(all_data, username)
            
            command_input = input(f"\n[{username}@{curr_room}] > ").strip().split()
            if not command_input: continue

            cmd = command_input[0].lower()
            args = command_input[1:]

            if cmd == "exit":
                save_all_data(all_data); print("💾 Saved. Goodbye!"); break

            elif cmd == "help": show_help()

            elif cmd in ["rooms", "room"]:
                if args and args[0] == "list":
                    print("\n🏙️ ====== ACTIVE ROOMS ======")
                    for r_code, r_data in all_data["rooms"].items():
                        print(f"  • Room Code: `{r_code}` | Preset: {r_data['preset']} | Host: {r_data['host']} | Members: {len(r_data['members'])}")
                    print("============================")
                elif args and args[0] == "create":
                    preset = args[1].lower() if len(args) > 1 else "egmore"
                    if preset not in CITIES: preset = "egmore"
                    code = "".join(random.choices("ABCDEFGHJKLMNPQRSTUVWXYZ23456789", k=6))
                    all_data["rooms"][code] = {"host": username, "name": f"{username}'s Room", "preset": preset, "is_public": False, "members": [username], "heist": {"active": False}}
                    all_data["users"][username]["current_room"] = code
                    all_data["users"][username]["room_profiles"][code] = get_default_room_profile(preset)
                    save_all_data(all_data); print(f"🎉 Created room! Party Code: **{code}**")
                elif args and args[0] == "join":
                    code = args[1].upper() if len(args) > 1 else ""
                    if code not in all_data["rooms"]: print("❌ Room code not found."); continue
                    old = all_data["users"][username].get("current_room")
                    if old in all_data["rooms"] and username in all_data["rooms"][old]["members"]:
                        all_data["rooms"][old]["members"].remove(username)
                    all_data["users"][username]["current_room"] = code
                    if username not in all_data["rooms"][code]["members"]: all_data["rooms"][code]["members"].append(username)
                    if code not in all_data["users"][username]["room_profiles"]:
                        all_data["users"][username]["room_profiles"][code] = get_default_room_profile(all_data["rooms"][code]["preset"])
                    save_all_data(all_data); print(f"✈️ Joined room **{code}**!")

            elif cmd == "terminate_room":
                rooms = all_data["rooms"]
                if curr_room == "GLOBAL_HUB" or rooms[curr_room]["host"] != username:
                    print("❌ Cannot terminate this room."); continue
                for mem in rooms[curr_room]["members"]:
                    if mem in all_data["users"]:
                        all_data["users"][mem]["current_room"] = "GLOBAL_HUB"
                        if mem not in all_data["rooms"]["GLOBAL_HUB"]["members"]: all_data["rooms"]["GLOBAL_HUB"]["members"].append(mem)
                del rooms[curr_room]; save_all_data(all_data)
                print("🛑 Room terminated. Occupants returned to Global Hub.")

            elif cmd in ["bal", "balance"]:
                inv_v = sum(u["inventory"][k] * SHOP_ITEMS[k]["price"] for k in u["inventory"])
                loot_v = sum(u["loot"][k] * LOOT_ITEMS[k]["sell_price"] for k in u["loot"])
                print(f"\n📊 ====== ROOM PROFILE ({curr_room}) ======")
                print(f"⭐ LEVEL: {u['level']} | XP: {u['xp']}")
                print(f"💳 FAMPAY BALANCE: 🪙 {u['fampay']:,} | 🏦 BANK: 🪙 {u['bank']:,} / {u['bank_max']:,}")
                print(f"💎 ROOM NET WORTH: 🪙 {u['fampay'] + u['bank'] + inv_v + loot_v:,}")
                print("===========================================")

            elif cmd in ["players", "sidebar"]:
                print("\n👥 ====== PLAYER SIDEBAR ======")
                now = time.time()
                for p_name, p_data in all_data["users"].items():
                    status = "🟢 Online" if (now - p_data.get("last_active", 0) < 45) else "⚪ Offline"
                    print(f"  • **{p_name}** [Room: {p_data.get('current_room','GLOBAL_HUB')}] — {status}")
                print("==============================")

            elif cmd == "rob":
                if not check_status(u, city_cfg): continue
                if not args: print("❌ Usage: `rob <player>`"); continue
                target = args[0]
                if target == username or target not in all_data["users"]: print("❌ Invalid target."); continue
                if all_data["users"][target].get("current_room") != curr_room:
                    print(f"❌ Player `{target}` is not in your current room!"); continue
                t_prof = get_user_room_profile(all_data, target, curr_room)
                if t_prof["inventory"]["padlock"] > 0:
                    t_prof["inventory"]["padlock"] -= 1; u["fampay"] = max(0, u["fampay"] - 500)
                    save_all_data(all_data); print("🔒 **PADLOCK BLOCKED ROBBERY!** Fined 500 from FamPay Balance."); continue
                if random.random() < 0.5:
                    stolen = min(t_prof["fampay"], random.randint(1000, 5000))
                    t_prof["fampay"] -= stolen; u["fampay"] += stolen; add_xp(u, 100)
                    save_all_data(all_data); print(f"🥷 Stole 🪙 {stolen:,} coins from {target}'s FamPay Balance!")
                else:
                    u["fampay"] = max(0, u["fampay"] - 1500); save_all_data(all_data)
                    print("🚨 Robbery failed! Fined 1,500 coins from FamPay Balance.")

            elif cmd == "heist":
                if not check_status(u, city_cfg): continue
                if not args: print("❌ Usage: `heist start`, `heist contribute <amt>`, `heist launch`"); continue
                sub = args[0].lower()
                room_obj = all_data["rooms"][curr_room]
                heist = room_obj.setdefault("heist", {"active": False, "contributions": {}})
                if sub == "start":
                    heist["active"] = True; heist["contributions"] = {username: 0}
                    save_all_data(all_data); print("🚨 Heist initiated in room!")
                elif sub == "contribute":
                    amt = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
                    if not heist["active"] or amt <= 0 or u["fampay"] < amt: print("❌ Invalid contribution."); continue
                    u["fampay"] -= amt; heist["contributions"][username] = heist["contributions"].get(username, 0) + amt
                    save_all_data(all_data); print(f"✅ Contributed 🪙 {amt:,} coins from FamPay Balance!")
                elif sub == "launch":
                    if not heist["active"]: print("❌ No active heist."); continue
                    pool = sum(heist["contributions"].values())
                    if random.random() < 0.65:
                        reward = pool * 3
                        print(f"🎉 **HEIST SUCCESS!** Total pool paid out: 🪙 {reward:,}")
                        for mem, c in heist["contributions"].items():
                            if c > 0:
                                share = int((c / pool) * reward)
                                get_user_room_profile(all_data, mem, curr_room)["fampay"] += share
                    else: print("💥 Heist failed!")
                    heist["active"] = False; heist["contributions"] = {}; save_all_data(all_data)

            elif cmd == "bank_heist":
                if not check_status(u, city_cfg): continue
                weights = [clerk["weight"] for clerk in BANK_CLERKS]
                clerk = random.choices(BANK_CLERKS, weights=weights, k=1)[0]
                print(f"\n🚨 **BANK HEIST RAID** — Raiding against **{clerk['tier']}: {clerk['name']}**!")
                if random.random() > clerk["risk"]:
                    u["fampay"] += clerk["reward"]
                    u["loot"][clerk["drop"]] += 1
                    add_xp(u, 250)
                    save_all_data(all_data)
                    print(f"🎉 **SUCCESS!** Overcame {clerk['name']}! Stole 🪙 {clerk['reward']:,} & drop `{clerk['drop']}` to FamPay!")
                else:
                    handle_death(u, city_cfg)
                    save_all_data(all_data)

            elif cmd in ["bag", "inv", "inventory"]:
                print(f"\n🎒 ====== BAG ({curr_room}) ======")
                for k, c in u["inventory"].items():
                    if c > 0: print(f"  - {SHOP_ITEMS[k]['name']}: {c}x")
                for k, c in u["loot"].items():
                    if c > 0: print(f"  - {LOOT_ITEMS[k]['name']}: {c}x")
                print("==============================")

            elif cmd == "shop":
                print("\n🛒 ====== FRESH 4 TODAY STORE ====== 🛒")
                for k, i in SHOP_ITEMS.items():
                    print(f"  [{k}] {i['name']} ({i['category']}) — 🪙 {i['price']:,}\n       ↳ {i['desc']}")
                print("=======================================")

            elif cmd == "buy":
                if not check_status(u, city_cfg): continue
                k = args[0].lower() if args else ""
                if k not in SHOP_ITEMS or u["fampay"] < SHOP_ITEMS[k]["price"]: print("❌ Invalid purchase or insufficient FamPay Balance."); continue
                u["fampay"] -= SHOP_ITEMS[k]["price"]; u["inventory"][k] += 1
                save_all_data(all_data); print(f"✅ Bought 1x {SHOP_ITEMS[k]['name']} using FamPay Balance!")

            elif cmd == "sell":
                if not check_status(u, city_cfg): continue
                k = args[0].lower() if args else ""
                if k == "all":
                    earned = sum([u["loot"][l] * LOOT_ITEMS[l]["sell_price"] for l in u["loot"]])
                    for l in u["loot"]: u["loot"][l] = 0
                    u["fampay"] += earned; save_all_data(all_data)
                    print(f"💰 Sold all loot for 🪙 {earned:,} coins added to FamPay Balance!")
                elif k in LOOT_ITEMS and u["loot"][k] > 0:
                    earned = u["loot"][k] * LOOT_ITEMS[k]["sell_price"]
                    u["fampay"] += earned; u["loot"][k] = 0; save_all_data(all_data)
                    print(f"💰 Sold loot for 🪙 {earned:,} coins added to FamPay Balance!")
                else: print("❌ Invalid drop to sell.")

            elif cmd == "work":
                if not check_status(u, city_cfg): continue
                j = JOBS.get(u.get("job", "moderator"), JOBS["moderator"])
                if not perform_job_check(u, j["name"]):
                    u["job"] = "moderator"; save_all_data(all_data); print("🔥 Fired!"); continue
                pay = int(random.randint(j["pay"][0], j["pay"][1]) * city_cfg["pay_mult"])
                u["fampay"] += pay; add_xp(u, 70); save_all_data(all_data)
                print(f"💼 Worked as {j['name']} for 🪙 {pay:,} coins credited to FamPay Balance!")

            elif cmd == "hunt":
                if not check_status(u, city_cfg): continue
                if u["inventory"]["hunting_rifle"] <= 0: print("❌ Need a Hunting Rifle (`shop`)!"); continue
                boss = random.choice(HUNT_BOSSES)
                if random.random() > (boss["risk"] - 0.15):
                    u["fampay"] += boss["reward"]; u["loot"][boss["drop"]] += 1; add_xp(u, 300)
                    save_all_data(all_data); print(f"🎉 Hunted {boss['name']}! Won 🪙 {boss['reward']:,} + drop to FamPay!")
                else: handle_death(u, city_cfg); save_all_data(all_data)

            elif cmd == "fish":
                if not check_status(u, city_cfg): continue
                if u["inventory"]["fishing_rod"] <= 0: print("❌ Need a Fishing Rod (`shop`)!"); continue
                boss = random.choice(FISH_BOSSES)
                if random.random() > (boss["risk"] - 0.15):
                    u["fampay"] += boss["reward"]; u["loot"][boss["drop"]] += 1; add_xp(u, 300)
                    save_all_data(all_data); print(f"🎉 Caught {boss['name']}! Won 🪙 {boss['reward']:,} + drop to FamPay!")
                else: handle_death(u, city_cfg); save_all_data(all_data)

            elif cmd == "dig":
                if not check_status(u, city_cfg): continue
                if u["inventory"]["shovel"] <= 0: print("❌ Need a Shovel (`shop`)!"); continue
                loot = random.randint(400, 1800); u["fampay"] += loot; add_xp(u, 55)
                if random.random() < 0.65:
                    critter = random.choice(DIG_ANIMALS)
                    u["loot"][critter["drop"]] += 1
                    print(f"⛏️ Dug up 🪙 {loot:,} coins & **{critter['name']}** added to FamPay!")
                else: print(f"⛏️ Dug up 🪙 {loot:,} coins added to FamPay!")
                save_all_data(all_data)

            elif cmd == "beg":
                if not check_status(u, city_cfg): continue
                earned = random.randint(50, 350); u["fampay"] += earned; add_xp(u, 20); save_all_data(all_data)
                print(f"🤲 Begged and earned 🪙 {earned:,} coins on FamPay!")

            elif cmd == "crypto":
                if not check_status(u, city_cfg): continue
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid amount or insufficient FamPay Balance."); continue
                change = random.uniform(-0.85, 1.60)
                if change >= 0:
                    profit = int(amt * change); u["fampay"] += profit; add_xp(u, 65)
                    print(f"📈 Crypto pumped +{int(change*100)}%! Made 🪙 {profit:,} profit on FamPay!")
                else:
                    loss = int(amt * abs(change)); u["fampay"] -= loss
                    print(f"📉 Crypto crashed -{int(abs(change)*100)}%! Lost 🪙 {loss:,} coins from FamPay!")
                save_all_data(all_data)

            # --- CASINO ROUTER ---
            elif cmd in ["blackjack", "bj"]:
                if not check_status(u, city_cfg): continue
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                play_blackjack(all_data, username, amt)

            elif cmd == "mines":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                bombs = int(args[1]) if len(args) > 1 and args[1].isdigit() else 3
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                play_mines(all_data, username, amt, bombs)

            elif cmd == "baccarat":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                side = args[1].lower() if len(args) > 1 else ""
                if amt <= 0 or amt > u["fampay"] or side not in ["player", "banker", "tie"]: print("❌ Usage: `baccarat <amt> <player/banker/tie>`"); continue
                play_baccarat(all_data, username, amt, side)

            elif cmd == "keno":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                play_keno(all_data, username, amt)

            elif cmd == "wheel":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                play_wheel(all_data, username, amt)

            elif cmd == "plinko":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                play_plinko(all_data, username, amt)

            elif cmd == "rps":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                choice = args[1].lower() if len(args) > 1 else ""
                if choice in ["r", "p", "s"]: choice = {"r": "rock", "p": "paper", "s": "scissors"}[choice]
                if amt <= 0 or amt > u["fampay"] or choice not in ["rock", "paper", "scissors"]: print("❌ Usage: `rps <amt> <r/p/s>`"); continue
                play_rps(all_data, username, amt, choice)

            elif cmd == "war":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                play_war(all_data, username, amt)

            elif cmd == "gamble":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                if random.random() < 0.48: u["fampay"] += amt; add_xp(u, 60); print("🎉 Won gamble!")
                else: u["fampay"] -= amt; print("💸 Lost gamble!")
                save_all_data(all_data)

            elif cmd == "coinflip":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                choice = args[1].lower() if len(args) > 1 else ""
                if amt <= 0 or amt > u["fampay"] or choice not in ["heads", "tails", "h", "t"]: print("❌ Usage: `coinflip <amt> <heads/tails>`"); continue
                res = random.choice(["heads", "tails"])
                print(f"🪙 Landed on: **{res.upper()}**")
                if choice.startswith(res[0]): u["fampay"] += amt; add_xp(u, 50); print("🎉 Won coinflip!")
                else: u["fampay"] -= amt; print("💸 Lost coinflip!")
                save_all_data(all_data)

            elif cmd == "slots":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                spin = [random.choice(["🍒", "🍋", "🍊", "⭐", "💎"]) for _ in range(3)]
                print(f"\n🎰 [ {spin[0]} | {spin[1]} | {spin[2]} ]")
                if spin[0] == spin[1] == spin[2]:
                    payout = amt * 5; u["fampay"] += payout; add_xp(u, 100); print(f"🎉 Jackpot! Won 🪙 {payout:,}!")
                elif spin[0] == spin[1] or spin[1] == spin[2]:
                    payout = amt * 2; u["fampay"] += payout; add_xp(u, 40); print(f"🎉 Double match! Won 🪙 {payout:,}!")
                else: u["fampay"] -= amt; print("💸 No match.")
                save_all_data(all_data)

            elif cmd == "roulette":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                choice = args[1].lower() if len(args) > 1 else ""
                if amt <= 0 or amt > u["fampay"] or choice not in ["red", "black", "green"]: print("❌ Usage: `roulette <amt> <red/black/green>`"); continue
                roll = random.random()
                res = "green" if roll < 0.04 else ("red" if roll < 0.52 else "black")
                print(f"🎡 Landed on: **{res.upper()}**")
                if choice == res:
                    mult = 14 if res == "green" else 2
                    payout = amt * mult; u["fampay"] += payout; add_xp(u, 80); print(f"🎉 Won 🪙 {payout:,}!")
                else: u["fampay"] -= amt; print("💸 Loss!")
                save_all_data(all_data)

            elif cmd == "dice":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                p_r, d_r = random.randint(1, 6), random.randint(1, 6)
                print(f"🎲 Your Roll: [{p_r}] vs House: [{d_r}]")
                if p_r > d_r: u["fampay"] += amt; add_xp(u, 50); print("🎉 Win!")
                elif p_r < d_r: u["fampay"] -= amt; print("💸 Loss!")
                else: print("🤝 Tie.")
                save_all_data(all_data)

            elif cmd == "crash":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                pt = round(random.uniform(1.01, 3.50), 2)
                print("🚀 Rocket climbing... Type `c` to cash out!")
                cashed = False
                try:
                    if input("Quick! Type `c`: ").strip().lower() == "c": cashed = True
                except: pass
                if cashed and pt > 1.2:
                    win = int(amt * 1.5); u["fampay"] += win; add_xp(u, 70); print(f"🎉 Cashed out at {pt}x! Won 🪙 {win:,}!")
                else: u["fampay"] -= amt; print(f"💥 Crashed at {pt}x!")
                save_all_data(all_data)

            elif cmd == "highlow":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                secret, base = random.randint(1, 100), random.randint(1, 100)
                print(f"📈 Mystery Number: **{base}**.")
                choice = input("Type `high` or `low`: ").strip().lower()
                if (choice in ["high", "h"] and secret > base) or (choice in ["low", "l"] and secret < base):
                    u["fampay"] += amt; add_xp(u, 40); print(f"🎉 Correct! Secret was {secret}.")
                else: u["fampay"] -= amt; print(f"💸 Wrong! Secret was {secret}.")
                save_all_data(all_data)

            elif cmd == "horse_race":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                h_c = int(args[1]) if len(args) > 1 and args[1].isdigit() else 0
                if amt <= 0 or amt > u["fampay"] or h_c not in [1, 2, 3, 4]: print("❌ Usage: `horse_race <amt> <1-4>`"); continue
                winner = random.randint(1, 4)
                print(f"🐎 Horse #{winner} won the race!")
                if h_c == winner: payout = amt * 3; u["fampay"] += payout; add_xp(u, 90); print(f"🎉 Your horse won 🪙 {payout:,}!")
                else: u["fampay"] -= amt; print("💸 Your horse lost.")
                save_all_data(all_data)

            elif cmd == "lottery":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                if random.random() < 0.10: jackpot = amt * 10; u["fampay"] += jackpot; add_xp(u, 250); print(f"🍀 Jackpot! Won 🪙 {jackpot:,}!")
                else: u["fampay"] -= amt; print("💸 Busted ticket.")
                save_all_data(all_data)

            elif cmd == "russian_roulette":
                amt = int(args[0]) if args and args[0].isdigit() else 0
                if amt <= 0 or amt > u["fampay"]: print("❌ Invalid bet."); continue
                print("🔫 Spinning revolver... *CLICK*")
                if random.randint(1, 6) == 1: print("💥 BANG!"); handle_death(u, city_cfg)
                else: win = amt * 5; u["fampay"] += win; add_xp(u, 250); print(f"😅 Survived! Won 🪙 {win:,}!")
                save_all_data(all_data)

            elif cmd in ["leaderboard", "lb"]:
                all_data = load_all_data()
                print("\n🏆 ====== GLOBAL LEADERBOARD ====== 🏆")
                for p_name, p_data in all_data["users"].items():
                    tot = sum([p["fampay"] + p["bank"] for p in p_data.get("room_profiles", {}).values()])
                    print(f"  • **{p_name}** — 🪙 {tot:,} Total Net Worth")
                print("========================================")

            elif cmd == "revive":
                u["dead"] = False; u["fampay"] = 200; save_all_data(all_data); print("✨ Revived with 200 coins on FamPay!")

            else:
                print(f"❌ Unknown command `{cmd}`. Type `help`.")

        except (KeyboardInterrupt, EOFError):
            save_all_data(all_data); print("\n💾 Saved. Goodbye!"); break


if __name__ == "__main__":
    main()
