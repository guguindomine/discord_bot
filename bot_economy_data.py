# ── ECONOMY SETTINGS ──
CURRENCY_NAME = "paradoxy"

SHOP_ITEMS = {
    "Lucky Coin": {
        "price": 1500000,
        "desc": "Boosts luck by 5% in casino and chance games.",
        "buff": 1.05
    },
    "Golden Clover": {
        "price": 4500000,
        "desc": "Boosts luck by 15% in casino and chance games.",
        "buff": 1.15
    },
    "Thief Kit": {
        "price": 8500000,
        "desc": "Increase steal success rate by 12%.",
        "buff": 0.12
    },
    "Crime Mask": {
        "price": 5500000,
        "desc": "Reduces crime fines by 35% and increases success by 15%.",
        "buff_fine": 0.65,
        "buff_success": 0.15
    },
    "Shield": {
        "price": 3500000,
        "desc": "40% chance to block being robbed.",
        "buff": 0.40
    },
    "VIP Pass": {
        "price": 35000000,
        "desc": "75% bonus to daily rewards and 25% bonus to work.",
        "buff_daily": 1.75,
        "buff_work": 1.25
    }
}

HEIST_TARGETS = {
    "jewelry": {
        "name": "Jewelry Store",
        "easy": (30000, 50000),
        "normal": (70000, 100000),
        "hard": (150000, 200000),
        "minigames": ["lockpick", "circuit"]
    },
    "bank": {
        "name": "Main Bank",
        "easy": (40000, 60000),
        "normal": (100000, 150000),
        "hard": (250000, 400000),
        "minigames": ["safe", "hacking", "circuit"]
    },
    "truck": {
        "name": "Armored Truck",
        "easy": (25000, 40000),
        "normal": (60000, 90000),
        "hard": (120000, 180000),
        "minigames": ["lockpick", "vault"]
    }
}

SCAM_LINKS = [
    "discord.gift/", "steamcommunity.com/gift", "nitro-", "free-nitro", 
    "steam-promo", "dicsord", "dlscord", "giveaway-nitro"
]

COMMAND_COOLDOWNS = {
    "daily": 86400,
    "work": 300,
    "crime": 60,
    "heist": 300,
    "steal": 300,
}

# ── SECURITY CONSTANTS ──
MAX_EVERYONE_MENTIONS = 1
QUARANTINE_ROLE_NAME = "Quarantined"
QUARANTINE_CHANNEL_NAME = "⚖️-contest-punishment"

class RiggedOdds:
    BASE_WIN_RATES = {
        "cf": 0.48,           # 48% base
        "slots_normal": 0.35, # 35% for any win
        "bj": 0.42,           # Blackjack base
        "roulette_red": 0.47, # Red/Black base
        "roulette_green": 0.02 # Green base
    }

    @staticmethod
    async def calculate_win_chance(game_type, inventory):
        chance = RiggedOdds.BASE_WIN_RATES.get(game_type, 0.45)
        
        # Apply Luck Buffs
        luck_buff = 0
        if "Lucky Coin" in inventory: luck_buff += 0.05
        if "Golden Clover" in inventory: luck_buff += 0.15
        
        # Cap max luck buff at 20%
        final_chance = chance + min(luck_buff, 0.20)
        return final_chance

# ── LEVELING SETTINGS ──
LEVEL_ROLES = {
    0: {"name": "Peasant", "color": 0x808080},
    5: {"name": "Squire", "color": 0x556B2F},
    10: {"name": "Knight", "color": 0x4682B4},
    15: {"name": "Baron", "color": 0x8A2BE2},
    20: {"name": "Viscount", "color": 0x9932CC},
    25: {"name": "Count", "color": 0xBA55D3},
    30: {"name": "Marquis", "color": 0xDA70D6},
    35: {"name": "Duke", "color": 0xC71585},
    40: {"name": "Grand Duke", "color": 0xFF1493},
    45: {"name": "Prince", "color": 0xFF69B4},
    50: {"name": "Archduke", "color": 0xFFD700},
    55: {"name": "Viceroy", "color": 0xFFA500},
    60: {"name": "Governor", "color": 0xFF8C00},
    65: {"name": "High Lord", "color": 0xFF4500},
    70: {"name": "Chancellor", "color": 0xFF0000},
    75: {"name": "Grand Chancellor", "color": 0xB22222},
    80: {"name": "High Chancellor", "color": 0x8B0000},
    85: {"name": "King", "color": 0xFFD700},
    90: {"name": "High King", "color": 0xDAA520},
    95: {"name": "Emperor", "color": 0xB8860B},
    100: {"name": "God Emperor", "color": 0xFFFFFF}
}
