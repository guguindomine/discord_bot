"""
Paradox Bot - Helper Functions
Swear filter, message formatting, config management, and utilities.
"""

import json
import re
import os
from datetime import datetime
from bot_database import db

# ──────────────────────────────────────────────
#  CONFIG MANAGEMENT
# ──────────────────────────────────────────────

async def save_config_sync(cfg: dict):
    """
    Save the current configuration to both the local JSON file and the MongoDB database.
    This ensures that settings persist even after bot restarts or redeployments.
    """
    save_config(cfg)
    if db.db is not None:
        try:
            await db.update_config(cfg)
        except Exception as e:
            print(f"  [ERROR] Failed to sync config to DB: {e}")


# ──────────────────────────────────────────────
#  CONFIG MANAGEMENT
# ──────────────────────────────────────────────

CONFIG_FILE = "config.json"
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def load_config():
    """Load configuration from JSON or Environment Variables (for Railway)."""
    config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error loading config file: {e}")

    # Prioritize Environment Variables (Higher priority for Railway/hosting)
    if os.environ.get("DISCORD_TOKEN"):
        config["TOKEN"] = os.environ.get("DISCORD_TOKEN")
    if os.environ.get("PREFIX"):
        config["PREFIX"] = os.environ.get("PREFIX")
        
    return config


def save_config(config: dict) -> None:
    """Save configuration back to config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get_config_value(key: str, default=None):
    """Get a single value from config."""
    config = load_config()
    return config.get(key, default)


def set_config_value(key: str, value) -> None:
    """Set a single value in config and save."""
    config = load_config()
    config[key] = value
    save_config(config)


# ──────────────────────────────────────────────
#  SWEAR WORD FILTER
# ──────────────────────────────────────────────

def build_swear_pattern(word: str) -> re.Pattern:
    """Builds a regex pattern that matches repeated characters and leetspeak."""
    # Common leetspeak substitutions
    leet_map = {
        'a': r'[a@4λ∆α]',
        'b': r'[b8ßвь]',
        'e': r'[e3€єe]',
        'g': r'[g69qɢ]',
        'h': r'[hнћ]',
        'i': r'[i1!l|ι¡ï]',
        'o': r'[o0øθо]',
        's': r'[s\$5z§]',
        't': r'[t7\+†]',
        'u': r'[uυμµv]',
        'w': r'[wωvv]',
        'l': r'[l1i!|]',
        'n': r'[nиηñ]',
        'r': r'[rя®]',
    }
    
    regex_body = ""
    for char in word.lower():
        if char in leet_map:
            regex_body += f"{leet_map[char]}+"
        else:
            regex_body += f"{re.escape(char)}+"
            
    # Removed \b for more aggressive matching (catches words inside other words)
    return re.compile(regex_body, re.IGNORECASE)


def contains_swear(message_content: str, swear_list: list[str]) -> bool:
    """
    Check if a message contains any swear words from the list.
    Automatically handles repeated characters and leetspeak evasions.
    """
    for word in swear_list:
        pattern = build_swear_pattern(word)
        if pattern.search(message_content):
            return True
    return False


def find_swear_word(message_content: str, swear_list: list[str]) -> str:
    """Find and return the first swear word found in the message."""
    for word in swear_list:
        pattern = build_swear_pattern(word)
        match = pattern.search(message_content)
        if match:
            return match.group()
    return "Unknown"


def censor_message(message_content: str, swear_list: list[str]) -> str:
    """
    Replace swear words with asterisks, preserving first letter.
    Works with our advanced leetspeak patterns.
    """
    result = message_content
    for word in swear_list:
        pattern = build_swear_pattern(word)
        def replacer(match):
            w = match.group()
            if len(w) <= 1:
                return '*'
            return w[0] + '*' * (len(w) - 1)
        result = pattern.sub(replacer, result)
    return result


# ──────────────────────────────────────────────
#  MESSAGE FORMATTING
# ──────────────────────────────────────────────

def format_welcome_message(member, template: str) -> str:
    """Format a welcome embed description for a new member."""
    return template.format(
        member=member.name,
        mention=member.mention,
        count=member.guild.member_count
    )


def format_goodbye_message(member, template: str) -> str:
    """Format a goodbye message for a departing member."""
    return template.format(
        member=member.name,
        mention=member.mention,
        count=member.guild.member_count
    )


def format_timestamp() -> str:
    """Get a nicely formatted timestamp."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ──────────────────────────────────────────────
#  UTILITIES
# ──────────────────────────────────────────────

def truncate(text: str, max_len: int = 2000) -> str:
    """Truncate text to Discord's message limit."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + "..."


def parse_role_name(guild, role_name: str):
    """Find a role in a guild by name (case-insensitive)."""
    for role in guild.roles:
        if role.name.lower() == role_name.lower():
            return role
    return None


def parse_duration(duration_str: str) -> int:
    """Convert 1h, 2d, 30m etc to seconds. If just numbers, treated as seconds."""
    if duration_str.isdigit():
        return int(duration_str)
    
    match = re.match(r"(\d+)([smhdw])", duration_str.lower())
    if not match:
        return 60  # Default to 60s
    
    amount, unit = match.groups()
    amount = int(amount)
    
    units = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }
    
    return amount * units.get(unit, 1)


def format_duration(seconds: int) -> str:
    """Convert seconds to human readable string (e.g. 1h 30m)."""
    if seconds < 60:
        return f"{seconds}s"
    
    intervals = (
        ('weeks', 604800),
        ('days', 86400),
        ('hours', 3600),
        ('minutes', 60),
        ('seconds', 1),
    )
    
    result = []
    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append(f"{value} {name}")
            
    return ", ".join(result[:2]) or "0s"


# ──────────────────────────────────────────────
#  HUMANIZING HELPERS
# ──────────────────────────────────────────────

def get_random_response(responses: list[str]) -> str:
    """Pick a random response to make the bot feel more varied."""
    import random
    return random.choice(responses)

from bot_economy_data import LEVEL_ROLES

async def handle_level_up(member, level: int, channel = None):
    """Assign roles and notify the user on level up."""
    import discord
    role_info = None
    
    # Find highest role reward for this level
    for req_level in sorted(LEVEL_ROLES.keys(), reverse=True):
        if level >= req_level:
            role_info = LEVEL_ROLES[req_level]
            break
            
    role_to_give = None
    if role_info:
        role_name = f"Level {req_level}+ | {role_info['name']}"
        role_to_give = discord.utils.get(member.guild.roles, name=role_name)
        
        if not role_to_give:
            try:
                role_to_give = await member.guild.create_role(
                    name=role_name,
                    color=discord.Color(role_info["color"]),
                    hoist=True,
                    reason=f"Level {level} Kingdom Reward"
                )
            except: pass
        
        if role_to_give:
            try:
                to_remove = [r for r in member.roles if r.name.startswith("Level ") and " | " in r.name and r.id != role_to_give.id]
                if to_remove: await member.remove_roles(*to_remove)
                await member.add_roles(role_to_give)
            except: pass

    embed = discord.Embed(
        title="🎊 LEVEL UP! 🎊",
        description=f"Congratulations {member.mention}!\nYou've reached **Level {level}**!",
        color=role_info["color"] if role_info else 0x9B59B6,
        timestamp=discord.utils.utcnow()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    if role_to_give: embed.add_field(name="New Rank", value=f"🛡️ **{role_to_give.name}**")
    embed.set_footer(text="Paradox Kingdom 💜")
    
    cfg = load_config()
    lvl_channel_id = cfg.get("LEVEL_CHANNEL_ID")
    target_channel = member.guild.get_channel(int(lvl_channel_id)) if lvl_channel_id else (channel or member.guild.system_channel)
    
    if target_channel:
        try: await target_channel.send(content=member.mention, embed=embed)
        except: pass

def get_greeting() -> str:
    """Return a time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning! ☀️"
    elif hour < 18:
        return "Good afternoon! 🌤️"
    else:
        return "Good evening! 🌙"

def get_xp_for_level(level: int) -> int:
    """Calculate the XP needed to reach the NEXT level from the current one."""
    if level < 0: return 0
    return 5 * (level ** 2) + 50 * level + 100

def get_total_xp_for_level(level: int) -> int:
    """Calculate the cumulative XP needed to reach a specific level starting from zero."""
    total = 0
    for i in range(level):
        total += get_xp_for_level(i)
    return total

def get_level_from_xp(total_xp: int) -> int:
    """Calculate the current level based on total XP accumulated."""
    level = 0
    while True:
        next_xp = get_xp_for_level(level)
        if total_xp >= next_xp:
            total_xp -= next_xp
            level += 1
        else:
            break
    return level

def get_xp_progress(total_xp: int) -> tuple[int, int, int]:
    """Returns (current_level, xp_into_level, xp_needed_for_next)."""
    level = 0
    remaining_xp = total_xp
    while remaining_xp >= get_xp_for_level(level):
        remaining_xp -= get_xp_for_level(level)
        level += 1
    return level, remaining_xp, get_xp_for_level(level)

def evaluate_poker_hand(hole_cards: list[str], community_cards: list[str]) -> tuple[int, str]:
    """Evaluate poker hand and return (rank, description)."""
    all_cards = hole_cards + community_cards
    ranks = []
    suits = []
    for card in all_cards:
        rank = card[:-1]
        suit = card[-1]
        if rank == 'A': ranks.append(14)
        elif rank == 'K': ranks.append(13)
        elif rank == 'Q': ranks.append(12)
        elif rank == 'J': ranks.append(11)
        else: ranks.append(int(rank))
        suits.append(suit)
    
    # Count frequencies
    rank_counts = {}
    suit_counts = {}
    for r, s in zip(ranks, suits):
        rank_counts[r] = rank_counts.get(r, 0) + 1
        suit_counts[s] = suit_counts.get(s, 0) + 1
    
    # Check for flush
    flush = any(count >= 5 for count in suit_counts.values())
    flush_suit = next((s for s, c in suit_counts.items() if c >= 5), None) if flush else None
    
    # Check for straight
    sorted_ranks = sorted(set(ranks), reverse=True)
    straight = False
    straight_high = 0
    for i in range(len(sorted_ranks) - 4):
        if sorted_ranks[i] - sorted_ranks[i+4] == 4:
            straight = True
            straight_high = sorted_ranks[i]
            break
    # Ace low straight
    if set([14, 2, 3, 4, 5]).issubset(set(ranks)):
        straight = True
        straight_high = 5
    
    # Royal flush
    if flush and straight and straight_high == 14 and all(r in ranks for r in [10,11,12,13,14]) and all(suits[i] == flush_suit for i, r in enumerate(ranks) if r in [10,11,12,13,14]):
        return (10, "Royal Flush 👑")
    
    # Straight flush
    if flush and straight:
        return (9, f"Straight Flush {straight_high} 🔥")
    
    # Four of a kind
    if 4 in rank_counts.values():
        quad = next(r for r, c in rank_counts.items() if c == 4)
        return (8, f"Four of a Kind 🔷")
    
    # Full house
    if 3 in rank_counts.values() and 2 in rank_counts.values():
        trips = next(r for r, c in rank_counts.items() if c == 3)
        pair = next(r for r, c in rank_counts.items() if c == 2)
        return (7, f"Full House 🏠")
    
    # Flush
    if flush:
        return (6, f"Flush 💧")
    
    # Straight
    if straight:
        return (5, f"Straight 〰️")
    
    # Three of a kind
    if 3 in rank_counts.values():
        trips = next(r for r, c in rank_counts.items() if c == 3)
        return (4, f"Three of a Kind 🎲")
    
    # Two pair
    pairs = [r for r, c in rank_counts.items() if c == 2]
    if len(pairs) >= 2:
        pairs.sort(reverse=True)
        return (3, f"Two Pair 👥")
    
    # One pair
    if 2 in rank_counts.values():
        pair = next(r for r, c in rank_counts.items() if c == 2)
        return (2, f"Pair 2️⃣")
    
    # High card
    high = max(ranks)
    return (1, f"High Card 🃏")