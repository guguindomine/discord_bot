"""
╔═══════════════════════════════════════════════════════════╗
║                    PARADOX BOT                            ║
║          Discord Bot by Paradox · Python                  ║
║                                                           ║
║  Features:                                                ║
║   • Auto-role on join                                     ║
║   • Welcome & goodbye messages                            ║
║   • !hello / !goodbye custom commands                     ║
║   • Swear word auto-filter                                ║
║   • Moderation utilities                                  ║
╚═══════════════════════════════════════════════════════════╝
"""

import discord
from discord.ext import commands
from datetime import datetime, timedelta
from bot_functions import (
    load_config,
    save_config,
    contains_swear,
    censor_message,
    find_swear_word,
    format_welcome_message,
    format_goodbye_message,
    format_timestamp,
    parse_role_name,
)

# ──────────────────────────────────────────────
#  LOAD CONFIG
# ──────────────────────────────────────────────
import os
import re

# ── SECURITY CONSTANTS ──
SCAM_LINKS = [
    "discord.gift/", "steamcommunity.com/gift", "nitro-", "free-nitro", 
    "steam-promo", "dicsord", "dlscord", "giveaway-nitro"
]
MAX_EVERYONE_MENTIONS = 1
QUARANTINE_ROLE_NAME = "Quarantined"
QUARANTINE_CHANNEL_NAME = "⚖️-contest-punishment"

config = load_config()

# Load token from environment variable (Railway)
TOKEN = os.environ.get("DISCORD_TOKEN")
PREFIX = os.environ.get("PREFIX") or config.get("PREFIX", "!")

# ──────────────────────────────────────────────
#  BOT SETUP
# ──────────────────────────────────────────────
intents = discord.Intents.default()
intents.members = True          # Needed for on_member_join / on_member_remove
intents.message_content = True  # Needed to read message content

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)


# ══════════════════════════════════════════════
#  TICKET SYSTEM UI
# ══════════════════════════════════════════════

class TicketControlView(discord.ui.View):
    """View inside a created ticket for closing it."""
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🚨 **Closing ticket thread in 5 seconds...**")
        await discord.utils.sleep_until(datetime.fromtimestamp(interaction.created_at.timestamp() + 5))
        try:
            # Check if it's a thread and delete it
            if isinstance(interaction.channel, discord.Thread):
                await interaction.channel.delete()
            else:
                # Fallback for old channel tickets
                await interaction.channel.delete()
        except Exception as e:
            print(f"Failed to delete ticket: {e}")

class BoostRoleView(discord.ui.View):
    """Dropdown for boosters to pick a role."""
    def __init__(self, roles: list):
        super().__init__(timeout=180)
        self.add_item(BoostRoleSelect(roles))

class BoostRoleSelect(discord.ui.Select):
    def __init__(self, roles: list):
        options = [discord.SelectOption(label=r.name, value=str(r.id)) for r in roles[:25]]
        super().__init__(placeholder="💎 Pick your booster role...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        if role:
            try:
                # Remove other selectable boost roles first (optional, but cleaner)
                cfg = load_config()
                selectable_names = cfg.get("SELECTABLE_BOOST_ROLES", [])
                for r_name in selectable_names:
                    r_old = discord.utils.get(interaction.user.roles, name=r_name)
                    if r_old and r_old.id != role.id:
                        await interaction.user.remove_roles(r_old)
                
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ You've been given the **{role.name}** role! Enjoy! ✨", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("❌ I don't have permission to give you that role!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Role not found.", ephemeral=True)

class SupportTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Support Ticket", style=discord.ButtonStyle.primary, custom_id="create_support_ticket", emoji="🎟️")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        
        channel_name = f"support-{member.name}"
        
        # Check if channel already exists
        existing_channel = discord.utils.get(guild.channels, name=channel_name.lower())
        if existing_channel:
            await interaction.response.send_message(f"⚠️ You already have an open support ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        # Create channel in the SAME CATEGORY as the button
        category = interaction.channel.category
        
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            reason=f"Support ticket for {member.name}"
        )
        
        embed = discord.Embed(
            title="🎟️ Support Ticket Created",
            description=f"Hello {member.mention}! Staff will be with you shortly.\nThis is your private support channel.",
            color=0x3498DB
        )
        await channel.send(content=f"{member.mention} | Staff", embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ Created! Check {channel.mention}", ephemeral=True)

class HelpView(discord.ui.View):
    """View for the interactive help command."""
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Setup & Config", description="Greetings, Roles, Logs & Channels", emoji="⚙️", value="setup"),
            discord.SelectOption(label="Tickets & Apps", description="Support, Macros & Application setup", emoji="🎟️", value="tickets"),
            discord.SelectOption(label="Server Boost", description="Rewards, Logs & Special Roles", emoji="💎", value="boost"),
            discord.SelectOption(label="Moderation", description="Kick, Ban, Mute & Cleanup", emoji="🔨", value="mod"),
            discord.SelectOption(label="Security & Filter", description="Anti-Scam, Quarantine & Swear Filter", emoji="🛡️", value="security"),
            discord.SelectOption(label="General & Stats", description="Polls, Info & Server data", emoji="📊", value="general")
        ]
        super().__init__(placeholder="Select a category to view commands...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        prefix = load_config().get("PREFIX", "!")
        
        embed = discord.Embed(color=0x9B59B6, timestamp=discord.utils.utcnow())
        
        if cat == "setup":
            embed.title = "⚙️ Setup & Configuration"
            embed.description = (
                f"`{prefix}setrole <role>` - Set the auto-join role\n"
                f"`{prefix}setwelcomechannel <#ch>` - Set where greetings go\n"
                f"`{prefix}setlogchannel <#ch>` - Set where logs go\n"
                f"`{prefix}setwelcome <msg>` - Set the join message\n"
                f"`{prefix}setgoodbye <msg>` - Set the leave message\n"
                f"`{prefix}setimg <welcome/goodbye> <url>` - Set banners\n"
                f"`{prefix}setcolor <hex>` - Set embed colors\n"
                f"`{prefix}togglewelcome` - Enable/Disable greetings\n"
                f"`{prefix}testjoin` / `{prefix}testleave` - Test greeting embeds"
            )
        elif cat == "tickets":
            embed.title = "🎟️ Tickets & Helper Applications"
            embed.description = (
                f"`{prefix}setupticket <support/macro/helper>` - Setup buttons\n"
                f"`{prefix}setticketcategory <id>` - Set category for new tickets\n"
                f"`{prefix}sethelpertext <id> <questions>` - Config app forms\n"
                f"**IDs:** `ALS`, `AV`, `ASTD`, `UTD`, `AG`, `AC`, `BL`, `SP`, `ARX`, `AOL`"
            )
        elif cat == "boost":
            embed.title = "💎 Server Boosting System"
            embed.description = (
                f"`{prefix}setboostchannel <#ch>` - Set the boost log\n"
                f"`{prefix}setboostrole <role>` - Set the auto-given role\n"
                f"`{prefix}setboostmessage <msg>` - Set the boost message\n"
                f"`{prefix}addboostselectrole <role>` - Add role to selector\n"
                f"`{prefix}removeboostselectrole <role>` - Remove from selector\n"
                f"`{prefix}testboost` - Simulate a boost event"
            )
        elif cat == "mod":
            embed.title = "🔨 Advanced Moderation"
            embed.description = (
                f"`{prefix}purge <num>` - Delete bulk messages (1-100)\n"
                f"`{prefix}mute <@user> <min>` - Timeout a member\n"
                f"`{prefix}softban <@user>` - Kick & clear messages\n"
                f"`{prefix}kick <@user> [reason]` - Kick a member\n"
                f"`{prefix}ban <@user> [reason]` - Ban a member\n"
                f"`{prefix}quarantine <@user>` - Send to quarantine manually\n"
                f"`{prefix}goodbye` - Send a final manual farewell"
            )
        elif cat == "security":
            embed.title = "🛡️ Security & Filter System"
            embed.description = (
                f"`{prefix}togglefilter` - Toggle swear detection\n"
                f"`{prefix}setthreshold <sys> <key> <val>` - Config punishment levels\n"
                f"`{prefix}addscam <link>` - Add to phishing blacklist\n"
                f"`{prefix}clearscamlog <@user>` - Reset scam strikes\n"
                f"`{prefix}addswear <word>` - Add word to filter\n"
                f"`{prefix}removeswear <word>` - Remove word from filter\n"
                f"`{prefix}whitelist <add/remove/list>` - Swear filter bypass\n"
                f"`{prefix}logwhitelist <add/remove/list>` - Invisible from logs\n"
                f"`{prefix}unquarantine <@user>` - Release user from prison"
            )
        elif cat == "general":
            embed.title = "📊 General & Stats"
            embed.description = (
                f"`{prefix}poll \"Question\" <time>` - Create interactive poll\n"
                f"`{prefix}swearlog [@user]` - View infraction history/top\n"
                f"`{prefix}botinfo` - See bot stats & features\n"
                f"`{prefix}serverinfo` - See detailed server stats\n"
                f"`{prefix}help paradox` - Open this menu"
            )

        embed.set_footer(text=f"Paradox Bot 💜 | {cat.capitalize()} Menu")
        await interaction.response.edit_message(embed=embed)

class HelperTicketView(discord.ui.View):
    """View for the Helper/Carry application dropdown."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(HelperTicketSelect())

class HelperTicketSelect(discord.ui.Select):
    def __init__(self):
        cfg = load_config()
        # Fallback game list if not in config
        games = cfg.get("HELPER_GAMES", {
            "ALS": {"name": "Anime Last Stand (ALS)", "emoji": "⚔️"},
            "AG": {"name": "Anime Guardians (AG)", "emoji": "👻"},
            "AC": {"name": "Anime Crusaders (AC)", "emoji": "🗡️"},
            "UTD": {"name": "Universal Tower Defense (UTD)", "emoji": "🌍"},
            "AV": {"name": "Anime Vanguards (AV)", "emoji": "🛡️"},
            "BL": {"name": "Bizarre Lineage (BL)", "emoji": "💫"},
            "SP": {"name": "Sailor Piece (SP)", "emoji": "⛵"},
            "ARX": {"name": "Anime Rangers X (ARX)", "emoji": "🔥"},
            "ASTD": {"name": "All Star Tower Defense (ASTD)", "emoji": "⭐"},
            "AOL": {"name": "Anime Overlord (AOL)", "emoji": "👑"}
        })
        
        options = [
            discord.SelectOption(label=data["name"], value=code, emoji=data["emoji"])
            for code, data in games.items()
        ]
        super().__init__(placeholder="Select a game to start your ticket!", min_values=1, max_values=1, options=options, custom_id="helper_ticket_select")

    async def callback(self, interaction: discord.Interaction):
        game_code = self.values[0]
        guild = interaction.guild
        member = interaction.user
        cfg = load_config()
        
        game_data = cfg.get("HELPER_GAMES", {}).get(game_code, {})
        game_name = game_data.get("name", game_code)
        
        channel_name = f"carry-{game_code.lower()}-{member.name}"
        
        # Check for existing
        existing = discord.utils.get(guild.channels, name=channel_name.lower())
        if existing:
            await interaction.response.send_message(f"⚠️ You already have an open ticket for this game: {existing.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=interaction.channel.category,
            reason=f"Carry request for {game_name}"
        )

        questions = game_data.get("questions", "1. Timezone?\n2. Roblox Level?\n3. Image of units?")
        
        embed = discord.Embed(
            title=f"🎮 {game_name} | Helper Application",
            description=f"Hello {member.mention}! Please answer the questions below to apply for the **Helper/Booster** role for this game.\n\n**Application Form:**\n```\n{questions}\n```",
            color=0xF1C40F
        )
        embed.set_footer(text="Paradox Bot 💜 Helper System")
        
        await channel.send(content=f"{member.mention} | Staff", embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ Created! Check {channel.mention}", ephemeral=True)

class MacroTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Macro Ticket", style=discord.ButtonStyle.success, custom_id="create_macro_ticket", emoji="⌨️")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = interaction.user
        
        channel_name = f"macro-{member.name}"
        
        # Check if channel already exists
        existing_channel = discord.utils.get(guild.channels, name=channel_name.lower())
        if existing_channel:
            await interaction.response.send_message(f"⚠️ You already have an open macro ticket: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True, embed_links=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, manage_channels=True)
        }

        category = interaction.channel.category
        
        channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites,
            category=category,
            reason=f"Macro ticket for {member.name}"
        )
        
        embed = discord.Embed(
            title="⌨️ Macro Ticket Created",
            description=f"Hello {member.mention}! This is your direct channel for Macro support.\nStaff will assist you shortly.",
            color=0x2ECC71
        )
        await channel.send(content=f"{member.mention} | Staff", embed=embed, view=TicketControlView())
        await interaction.response.send_message(f"✅ Created! Check {channel.mention}", ephemeral=True)


# ══════════════════════════════════════════════
#  EVENTS
# ══════════════════════════════════════════════

@bot.event
async def on_ready():
    """Fires when the bot is connected and ready."""
    # Register persistent views
    bot.add_view(SupportTicketView())
    bot.add_view(MacroTicketView())
    bot.add_view(HelperTicketView())
    bot.add_view(TicketControlView())

    print("═" * 50)
    print(f"  ✅  Paradox Bot is ONLINE!")
    print(f"  🤖  Logged in as: {bot.user} (ID: {bot.user.id})")
    print(f"  🌐  Servers: {len(bot.guilds)}")
    print(f"  ⏰  {format_timestamp()}")
    print("═" * 50)

    # Set a custom status
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{PREFIX}help | Paradox Bot 💜"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)


# ── AUTO-ROLE + WELCOME MESSAGE ──────────────

@bot.event
async def on_member_join(member: discord.Member):
    """Auto-assign role and send a welcome message when someone joins."""
    cfg = load_config()  # Reload in case it changed

    # ── Auto-role ──
    role_name = cfg.get("AUTO_ROLE_NAME", "Member")
    role = parse_role_name(member.guild, role_name)
    if role:
        try:
            await member.add_roles(role)
            print(f"  [AUTO-ROLE] Gave '{role.name}' to {member.name}")
        except discord.Forbidden:
            print(f"  [ERROR] Missing permissions to assign role '{role_name}'")
        except Exception as e:
            print(f"  [ERROR] Auto-role failed: {e}")
    else:
        print(f"  [WARN] Role '{role_name}' not found in {member.guild.name}. Create it first!")

    # ── Welcome message in channel ──
    channel_id = cfg.get("WELCOME_CHANNEL_ID")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            welcome_tpl = cfg.get("JOIN_MESSAGE", "Welcome {mention}!")
            color_hex = cfg.get("WELCOME_COLOR", "#9B59B6")
            try:
                color_val = int(color_hex.lstrip('#'), 16)
            except:
                color_val = 0x9B59B6

            embed = discord.Embed(
                title="👋 Welcome!",
                description=format_welcome_message(member, welcome_tpl),
                color=color_val,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            img_url = cfg.get("WELCOME_IMAGE_URL")
            if img_url:
                embed.set_image(url=img_url)
                
            embed.set_footer(text="Paradox Bot 💜")
            await channel.send(content=f"🎉 Welcome {member.mention}! 🎉", embed=embed)

    # ── Optional DM ──
    if cfg.get("WELCOME_DM", False):
        try:
            dm_embed = discord.Embed(
                title=f"Welcome to {member.guild.name}! 🎉",
                description=(
                    f"Hey **{member.name}**, thanks for joining **{member.guild.name}**!\n\n"
                    f"Make sure to check out the rules and enjoy your stay! 💜"
                ),
                color=0x9B59B6,
            )
            await member.send(embed=dm_embed)
        except discord.Forbidden:
            print(f"  [WARN] Can't DM {member.name} (DMs disabled)")


# ── GOODBYE MESSAGE ──────────────────────────

@bot.event
async def on_member_remove(member: discord.Member):
    """Send a goodbye message when someone leaves."""
    cfg = load_config()

    channel_id = cfg.get("GOODBYE_CHANNEL_ID") or cfg.get("WELCOME_CHANNEL_ID")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            leave_tpl = cfg.get("LEAVE_MESSAGE", "{member} has left.")
            color_hex = cfg.get("WELCOME_COLOR", "#E74C3C")
            try:
                color_val = int(color_hex.lstrip('#'), 16)
            except:
                color_val = 0xE74C3C

            embed = discord.Embed(
                title="😢 Goodbye!",
                description=format_goodbye_message(member, leave_tpl),
                color=color_val,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            img_url = cfg.get("GOODBYE_IMAGE_URL")
            if img_url:
                embed.set_image(url=img_url)

            embed.set_footer(text="Paradox Bot 💜")
            await channel.send(embed=embed)


# ── SWEAR WORD FILTER ────────────────────────

@bot.event
async def on_message(message: discord.Message):
    """Filter swear words from messages."""
    # Don't respond to ourselves
    if message.author == bot.user:
        return
    # Ignore DMs
    if not message.guild:
        await bot.process_commands(message)
        return

    cfg = load_config()

    # ── Boost Detection (System Message) ──
    if message.type in (
        discord.MessageType.premium_guild_subscription,
        discord.MessageType.premium_guild_tier_1,
        discord.MessageType.premium_guild_tier_2,
        discord.MessageType.premium_guild_tier_3,
    ):
        boost_channel_id = cfg.get("BOOST_CHANNEL_ID")
        channel = bot.get_channel(int(boost_channel_id)) if boost_channel_id else message.channel
        
        if channel:
            boost_tpl = cfg.get("BOOST_MESSAGE", "Thank you for boosting the server, {mention}! 💖")
            
            embed = discord.Embed(
                title="✨ Server Boosted! ✨",
                description=boost_tpl.replace("{mention}", message.author.mention).replace("{member}", message.author.name).replace("{server}", message.guild.name),
                color=0xF47FFF,
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_footer(text="Paradox Bot 💜")
            
            # Interactive Role Selector for Boosters
            selectable_names = cfg.get("SELECTABLE_BOOST_ROLES", [])
            if selectable_names:
                roles = []
                for name in selectable_names:
                    r = parse_role_name(message.guild, name)
                    if r: roles.append(r)
                
                if roles:
                    selector_view = BoostRoleView(roles)
                    await channel.send(content=f"🎁 {message.author.mention}, you can pick one special booster role below!", view=selector_view)
            else:
                await channel.send(embed=embed)
            
        # Add boost role
        role_id_or_name = cfg.get("BOOST_ROLE_NAME", "Server Booster")
        role = parse_role_name(message.guild, role_id_or_name)
        
        if not role:
            try:
                # Create the role if it doesn't exist
                role = await message.guild.create_role(
                    name=role_id_or_name,
                    color=0xF47FFF, # Premium Pink/Purple
                    hoist=True,
                    reason="Auto-created boost role for boosters"
                )
                print(f"  [BOOST] Created missing role: {role_id_or_name}")
            except discord.Forbidden:
                print(f"  [ERROR] Lacking permissions to create Boost role '{role_id_or_name}'.")

        if role:
            try:
                await message.author.add_roles(role)
                print(f"  [BOOST] Assigned role '{role.name}' to {message.author.name}")
            except discord.Forbidden:
                print(f"  [ERROR] Lacking permissions to give Boost role '{role.name}'.")
        return

    # ── LOG EVERY MESSAGE ────────────────────────
    whitelisted_users = cfg.get("WHITELISTED_USERS", [])
    log_whitelisted = cfg.get("LOG_WHITELISTED_USERS", [])
    log_channel_id = cfg.get("LOG_CHANNEL_ID")
    
    # Check if user is in log whitelist
    if log_channel_id and not message.author.bot and message.channel.id != int(log_channel_id) and message.author.id not in log_whitelisted:
        try:
            log_channel = bot.get_channel(int(log_channel_id)) or await bot.fetch_channel(int(log_channel_id))
            if log_channel:
                log_embed = discord.Embed(
                    title="💬 Message Sent",
                    color=0x2ECC71, # Green
                    timestamp=discord.utils.utcnow()
                )
                log_embed.add_field(name="Author", value=message.author.mention, inline=True)
                log_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                log_embed.add_field(name="Content", value=message.content or "*No text content*", inline=False)
                log_embed.set_footer(text=f"User ID: {message.author.id}")
                await log_channel.send(embed=log_embed)
        except Exception as e:
            print(f"  [ERROR] Failed to log message: {e}")

    # Skip moderation for whitelisted users, commands or bot messages
    if (message.author.id in whitelisted_users or message.content.startswith(PREFIX)):
        await bot.process_commands(message)
        return

    # ── SECURITY & MODERATION SYSTEM ──
    swear_filter_on = cfg.get("SWEAR_FILTER_ENABLED", True)
    swear_list = cfg.get("SWEAR_WORDS", [])
    user_id = str(message.author.id)

    # 1. PHISHING & SCAM DETECTION
    content_lower = message.content.lower()
    is_scam = any(link in content_lower for link in SCAM_LINKS)
    
    if is_scam or (message.mention_everyone and not message.author.guild_permissions.mention_everyone):
        try:
            await message.delete()
            scam_infractions = cfg.get("SCAM_INFRACTIONS", {})
            scam_count = scam_infractions.get(user_id, 0) + 1
            scam_infractions[user_id] = scam_count
            cfg["SCAM_INFRACTIONS"] = scam_infractions
            save_config(cfg)

            scam_cfg = cfg.get("SCAM_THRESHOLDS", {"warn": 1, "mute1": 2, "mute2": 3, "quarantine": 4, "ban": 5})
            
            if scam_count == scam_cfg.get("warn"):
                await message.channel.send(f"⚠️ {message.author.mention}, links de phishing são proibidos! (Aviso 1)", delete_after=15)
            elif scam_count == scam_cfg.get("mute1"):
                await message.author.timeout(timedelta(hours=1), reason="Scam Strike 2")
                await message.channel.send(f"🔇 {message.author.mention} silenciado por 1h (Scam Strike 2)", delete_after=15)
            elif scam_count == scam_cfg.get("mute2"):
                await message.author.timeout(timedelta(days=1), reason="Scam Strike 3")
                await message.channel.send(f"🔇 {message.author.mention} silenciado por 1 dia (Scam Strike 3)", delete_after=15)
            elif scam_count == scam_cfg.get("quarantine"):
                await apply_quarantine(message.author, "Scam Strikes")
                await message.channel.send(f"⚖️ {message.author.mention} enviado para Quarentena (Scam Strike 4)", delete_after=15)
            elif scam_count >= scam_cfg.get("ban"):
                await message.author.ban(reason="Scam Strikes Limit")
                await message.channel.send(f"🚫 {message.author.name} banido por links de phishing.")
            return 
        except Exception as e:
            print(f"  [ERROR] Scam detection failed: {e}")

    # 2. SWEAR FILTER
    if swear_filter_on and swear_list and contains_swear(message.content, swear_list):
        infractions = cfg.get("INFRACTIONS", {})
        if user_id not in infractions:
            infractions[user_id] = []
        
        # Cooldown/Reset Check
        if infractions[user_id]:
            last_inf = infractions[user_id][-1]
            last_time = datetime.strptime(last_inf["time"], "%Y-%m-%d %H:%M:%S")
            time_diff = datetime.now() - last_time
            count_before = len(infractions[user_id])
            
            reset_needed = False
            if count_before <= 3 and time_diff > timedelta(minutes=30): reset_needed = True
            elif count_before == 4 and time_diff > timedelta(hours=1): reset_needed = True
            elif count_before >= 5 and time_diff > timedelta(days=1): reset_needed = True
            
            if reset_needed:
                infractions[user_id] = []

        # Log new infraction
        word_found = find_swear_word(message.content, swear_list)
        infractions[user_id].append({
            "word": word_found,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "channel": message.channel.name
        })
        cfg["INFRACTIONS"] = infractions
        save_config(cfg)
        
        count = len(infractions[user_id])
        swear_cfg = cfg.get("SWEAR_THRESHOLDS", {"silent": 1, "warn1": 2, "warn2": 3, "mute": 4, "quarantine": 8})
        
        # 1. Action: Silent delete
        if count <= swear_cfg.get("silent", 1):
            try: await message.delete()
            except: pass
            print(f"  [FILTER] Silent strike {count} for {message.author.name}")
            return

        # Subsequent strikes
        try: await message.delete()
        except: pass
        
        punishment_msg = ""
        try:
            if count == swear_cfg.get("warn1"):
                punishment_msg = "⚠️ Este é seu **1º aviso**. Mantenha o respeito!"
            elif count == swear_cfg.get("warn2"):
                punishment_msg = "⚠️ Este é seu **2º aviso**. O próximo resultará em castigo!"
            elif count == swear_cfg.get("mute"):
                await message.author.timeout(timedelta(minutes=1), reason="Swear Strike")
                punishment_msg = "🔇 Você foi castigado por **1 minuto**."
            elif count >= swear_cfg.get("quarantine"):
                await apply_quarantine(message.author, "Swear Strikes")
                punishment_msg = "⚖️ Você foi enviado para a **Quarentena** por excesso de avisos."
        except: pass

        warn_msg = f"⚠️ {message.author.mention}, watch your language!"
        if punishment_msg:
            warn_msg += f"\n{punishment_msg}"
        
        await message.channel.send(warn_msg, delete_after=10)

        log_channel_id = cfg.get("LOG_CHANNEL_ID")
        if log_channel_id:
            log_channel = bot.get_channel(int(log_channel_id)) or await bot.fetch_channel(int(log_channel_id))
            if log_channel:
                censored = censor_message(message.content, swear_list)
                log_embed = discord.Embed(title="🚨 Swear Filter Triggered", color=0xE74C3C, timestamp=discord.utils.utcnow())
                log_embed.add_field(name="User", value=message.author.mention, inline=True)
                log_embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                log_embed.add_field(name="Message (censored)", value=censored, inline=False)
                log_embed.set_footer(text="Paradox Bot 💜")
                await log_channel.send(embed=log_embed)

        print(f"  [FILTER] Deleted message from {message.author.name}")
        return  # Stop here if the message was filtered

    # Process commands if no swear words were found
    await bot.process_commands(message)


# ── LOGGING EVENTS ───────────────────────────

@bot.event
async def on_message_delete(message: discord.Message):
    """Log when a message is deleted."""
    if message.author.bot:
        return
    
    cfg = load_config()
    log_whitelisted = cfg.get("LOG_WHITELISTED_USERS", [])
    if message.author.id in log_whitelisted:
        return

    log_channel_id = cfg.get("LOG_CHANNEL_ID")
    if not log_channel_id:
        return
        
    try:
        log_channel = bot.get_channel(int(log_channel_id)) or await bot.fetch_channel(int(log_channel_id))
    except:
        return

    if not log_channel:
        return

    embed = discord.Embed(
        title="🗑️ Message Deleted",
        color=0xE74C3C,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Author", value=message.author.mention, inline=True)
    embed.add_field(name="Channel", value=message.channel.mention, inline=True)
    embed.add_field(name="Content", value=message.content or "*No text content (likely an embed or image)*", inline=False)
    embed.set_footer(text=f"User ID: {message.author.id}")
    
    await log_channel.send(embed=embed)

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):
    """Log when a message is edited."""
    if before.author.bot or before.content == after.content:
        return
        
    cfg = load_config()
    log_whitelisted = cfg.get("LOG_WHITELISTED_USERS", [])
    if before.author.id in log_whitelisted:
        return

    log_channel_id = cfg.get("LOG_CHANNEL_ID")
    if not log_channel_id:
        return
        
    try:
        log_channel = bot.get_channel(int(log_channel_id)) or await bot.fetch_channel(int(log_channel_id))
    except:
        return

    if not log_channel:
        return

    embed = discord.Embed(
        title="📝 Message Edited",
        color=0x3498DB,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="Author", value=before.author.mention, inline=True)
    embed.add_field(name="Channel", value=before.channel.mention, inline=True)
    embed.add_field(name="Before", value=before.content or "*No text content*", inline=False)
    embed.add_field(name="After", value=after.content or "*No text content*", inline=False)
    embed.set_footer(text=f"User ID: {before.author.id}")
    
    await log_channel.send(embed=embed)


# ══════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════

# ── !help ────────────────────────────────────

@bot.command(name="help")
async def help_cmd(ctx: commands.Context, sub: str = None):
    """Custom interactive help command."""
    if sub != "paradox":
        await ctx.send(f"❓ Type `{PREFIX}help paradox` to open my interactive menu!")
        return

    embed = discord.Embed(
        title="🤖 Paradox Bot | Main Menu",
        description=(
            "Welcome to the **Paradox Help Center**!\n\n"
            "Please use the **dropdown menu** below to select a category and view specialized commands and tutorials."
        ),
        color=0x9B59B6,
        timestamp=discord.utils.utcnow()
    )
    embed.add_field(name="🛠️ Setup", value="Basic server configuration", inline=True)
    embed.add_field(name="🎟️ Tickets", value="Support, Macros & Apps", inline=True)
    embed.add_field(name="🛡️ Moderation", value="Tools to keep server safe", inline=True)
    
    embed.set_footer(text="Developed for Paradox 💜")
    embed.set_thumbnail(url=bot.user.display_avatar.url)
    
    await ctx.send(embed=embed, view=HelpView())


# ── !setupticket ─────────────────────────────

@bot.command(name="setupticket")
@commands.has_permissions(administrator=True)
async def setup_ticket_cmd(ctx: commands.Context, mode: str = "support"):
    """Setup the ticket system. Modes: support, macro, helper. Admin only."""
    mode = mode.lower()
    
    if mode == "macro":
        embed = discord.Embed(
            title="⌨️ Macro Tickets",
            description=(
                "Purchase or inquire about Macros! Click the button below.\n"
                "Requests will be sent directly to the team/owner."
            ),
            color=0x2ECC71
        )
        view = MacroTicketView()
    elif mode == "helper":
        embed = discord.Embed(
            title="🎮 PARADOX | Helper Applications",
            description=(
                "**Apply to become a Paradox Helper!**\n"
                "Help our community and earn reputation as a professional booster.\n\n"
                "⭐ **BOOSTER PERKS**\n"
                "Get access to exclusive channels, roles, and community trust.\n\n"
                "⚡ **REQUIREMENTS**\n"
                "You must have meta units and be active daily to apply.\n\n"
                "📋 **HOW IT WORKS**\n"
                "Select your main game below to start your application ticket!"
            ),
            color=0xF1C40F
        )
        embed.set_image(url="https://media.discordapp.net/attachments/1111/banner.png") # Placeholder
        view = HelperTicketView()
    else:  # Default to support
        embed = discord.Embed(
            title="🎟️ Support Tickets",
            description=(
                "Need help? Click the button below to open a support ticket!\n"
                "Our staff team will assist you as soon as possible."
            ),
            color=0x3498DB
        )
        view = SupportTicketView()
        
    embed.set_footer(text=f"Paradox Bot 💜 {mode.capitalize()} Tickets")
    await ctx.send(embed=embed, view=view)
    await ctx.message.delete()

@bot.command(name="sethelpertext")
@commands.has_permissions(administrator=True)
async def set_helper_text(ctx: commands.Context, game_code: str, *, questions: str):
    """Set the application questions for a specific game. Admin only."""
    game_code = game_code.upper()
    cfg = load_config()
    games = cfg.get("HELPER_GAMES", {})
    
    if game_code not in games:
        await ctx.send(f"❌ Game `{game_code}` not found. (Examples: ALS, AV, ASTD)")
        return
    
    games[game_code]["questions"] = questions
    cfg["HELPER_GAMES"] = games
    save_config(cfg)
    await ctx.send(f"✅ Questions updated for **{games[game_code]['name']}**!")


# ── !testjoin ────────────────────────────────

@bot.command(name="testjoin")
@commands.has_permissions(administrator=True)
async def test_join_cmd(ctx: commands.Context):
    """Simulate a member join to test the welcome message. Admin only."""
    member = ctx.author
    cfg = load_config()

    channel_id = cfg.get("WELCOME_CHANNEL_ID")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            welcome_tpl = cfg.get("JOIN_MESSAGE", "Welcome {mention}!")
            color_hex = cfg.get("WELCOME_COLOR", "#9B59B6")
            try:
                color_val = int(color_hex.lstrip('#'), 16)
            except:
                color_val = 0x9B59B6

            embed = discord.Embed(
                title="👋 Welcome!",
                description=format_welcome_message(member, welcome_tpl),
                color=color_val,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            img_url = cfg.get("WELCOME_IMAGE_URL")
            if img_url:
                embed.set_image(url=img_url)

            embed.set_footer(text="Paradox Bot 💜")
            await channel.send(content=f"🎉 Welcome {member.mention}! 🎉", embed=embed)
            if channel != ctx.channel:
                await ctx.send(f"✅ Test welcome sent in {channel.mention}!")
        else:
            await ctx.send("❌ Welcome channel not found!")
    else:
        await ctx.send("❌ No welcome channel set!")

# ── !testleave ───────────────────────────────

@bot.command(name="testleave")
@commands.has_permissions(administrator=True)
async def test_leave_cmd(ctx: commands.Context):
    """Simulate a member leave to test the goodbye message. Admin only."""
    member = ctx.author
    cfg = load_config()

    channel_id = cfg.get("GOODBYE_CHANNEL_ID") or cfg.get("WELCOME_CHANNEL_ID")
    if channel_id:
        channel = bot.get_channel(int(channel_id))
        if channel:
            leave_tpl = cfg.get("LEAVE_MESSAGE", "{member} has left.")
            color_hex = cfg.get("WELCOME_COLOR", "#E74C3C")
            try:
                color_val = int(color_hex.lstrip('#'), 16)
            except:
                color_val = 0xE74C3C

            embed = discord.Embed(
                title="😢 Goodbye!",
                description=format_goodbye_message(member, leave_tpl),
                color=color_val,
                timestamp=discord.utils.utcnow(),
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            
            img_url = cfg.get("GOODBYE_IMAGE_URL")
            if img_url:
                embed.set_image(url=img_url)

            embed.set_footer(text="Paradox Bot 💜")
            await channel.send(embed=embed)
            if channel != ctx.channel:
                await ctx.send(f"✅ Test goodbye sent in {channel.mention}!")
        else:
            await ctx.send("❌ Goodbye channel not found!")
    else:
        await ctx.send("❌ No goodbye channel set!")



# ── !goodbye ─────────────────────────────────

@bot.command(name="goodbye")
async def goodbye_cmd(ctx: commands.Context):
    """Sends the custom goodbye message."""
    cfg = load_config()
    msg = cfg.get("GOODBYE_MESSAGE", "😢 Goodbye! Hope to see you again!")

    embed = discord.Embed(
        title="😢 Goodbye!",
        description=msg,
        color=0xE74C3C,  # Red
    )
    embed.set_footer(text=f"Requested by {ctx.author.name} · Paradox Bot 💜")
    await ctx.send(embed=embed)
# ── !setwelcome ──────────────────────────────

@bot.command(name="setwelcome")
@commands.has_permissions(administrator=True)
async def set_welcome_cmd(ctx: commands.Context, *, message: str):
    """Set a custom automated join message. Admin only.
    Usage: !setwelcome Welcome {mention}! You are member #{count}.
    """
    cfg = load_config()
    cfg["JOIN_MESSAGE"] = message
    save_config(cfg)
    await ctx.send(f"✅ Join message updated! Try `!testjoin` to see it.")


# ── !setgoodbye ──────────────────────────────

@bot.command(name="setgoodbye")
@commands.has_permissions(administrator=True)
async def set_goodbye_cmd(ctx: commands.Context, *, message: str):
    """Set a custom automated leave message. Admin only.
    Usage: !setgoodbye {member} has left the server.
    """
    cfg = load_config()
    cfg["LEAVE_MESSAGE"] = message
    save_config(cfg)
    await ctx.send(f"✅ Leave message updated! Try `!testleave` to see it.")


# ── !setimg ──────────────────────────────────

@bot.command(name="setimg")
@commands.has_permissions(administrator=True)
async def set_img_cmd(ctx: commands.Context, mode: str, url: str = None):
    """Set welcome/goodbye image. Attach an image or provide URL.
    Usage: !setimg welcome [url]
    """
    mode = mode.lower()
    if mode in ["welcome", "join"]:
        mode = "welcome"
    elif mode in ["goodbye", "leave"]:
        mode = "goodbye"
    else:
        await ctx.send("❌ Mode must be `welcome`/`join` or `goodbye`/`leave`.")
        return

    img_url = url
    if not img_url and ctx.message.attachments:
        img_url = ctx.message.attachments[0].url
    
    if not img_url:
        await ctx.send("❌ Please provide a URL or attach an image!")
        return

    cfg = load_config()
    key = "WELCOME_IMAGE_URL" if mode == "welcome" else "GOODBYE_IMAGE_URL"
    cfg[key] = img_url
    save_config(cfg)
    await ctx.send(f"✅ {mode.capitalize()} image updated!")

# ── !logwhitelist ────────────────────────────

@bot.group(name="logwhitelist", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def log_whitelist_grp(ctx: commands.Context):
    """Manage the log whitelist (users who won't be logged). Usage: !logwhitelist <add/remove/list>"""
    await ctx.send(f"❓ Usage: `{PREFIX}logwhitelist <add/remove/list> @user`")

@log_whitelist_grp.command(name="add")
@commands.has_permissions(administrator=True)
async def log_whitelist_add(ctx: commands.Context, member: discord.Member):
    """Add a user to the log whitelist."""
    cfg = load_config()
    whitelist = cfg.get("LOG_WHITELISTED_USERS", [])
    
    if member.id in whitelist:
        await ctx.send(f"⚠️ {member.display_name} is already in the log whitelist.")
        return
        
    whitelist.append(member.id)
    cfg["LOG_WHITELISTED_USERS"] = whitelist
    save_config(cfg)
    await ctx.send(f"✅ {member.mention} foi adicionado à whitelist de logs! Suas mensagens não serão mais registradas.")

@log_whitelist_grp.command(name="remove")
@commands.has_permissions(administrator=True)
async def log_whitelist_remove(ctx: commands.Context, member: discord.Member):
    """Remove a user from the log whitelist."""
    cfg = load_config()
    whitelist = cfg.get("LOG_WHITELISTED_USERS", [])
    
    if member.id not in whitelist:
        await ctx.send(f"⚠️ {member.display_name} não está na whitelist de logs.")
        return
        
    whitelist.remove(member.id)
    cfg["LOG_WHITELISTED_USERS"] = whitelist
    save_config(cfg)
    await ctx.send(f"✅ {member.mention} removido da whitelist de logs. Suas atividades voltarão a ser registradas.")

@log_whitelist_grp.command(name="list")
@commands.has_permissions(administrator=True)
async def log_whitelist_list(ctx: commands.Context):
    """List all log-whitelisted users."""
    cfg = load_config()
    whitelist = cfg.get("LOG_WHITELISTED_USERS", [])
    
    if not whitelist:
        await ctx.send("ℹ️ A whitelist de logs está vazia.")
        return
        
    mentions = [f"<@{uid}>" for uid in whitelist]
    embed = discord.Embed(
        title="👻 Log Whitelist (Invisíveis)",
        description="\n".join(mentions),
        color=0xF1C40F
    )
    await ctx.send(embed=embed)


# ── !setcolor ────────────────────────────────

@bot.command(name="setcolor")
@commands.has_permissions(administrator=True)
async def set_color_cmd(ctx: commands.Context, hex_code: str):
    """Set the embed color (Hex). Usage: !setcolor #FF00FF"""
    if not hex_code.startswith("#") or len(hex_code) != 7:
        await ctx.send("❌ Please provide a valid hex code (e.g., #7289da)")
        return

    cfg = load_config()
    cfg["WELCOME_COLOR"] = hex_code
    save_config(cfg)
    await ctx.send(f"✅ Embed color updated to **{hex_code}**!")

@bot.command(name="setrole")
@commands.has_permissions(administrator=True)
async def set_role_cmd(ctx: commands.Context, *, role_name: str):
    """Set the auto-role name. Admin only.
    Usage: !setrole RoleName
    """
    # Verify the role exists
    role = parse_role_name(ctx.guild, role_name)
    if not role:
        await ctx.send(f"❌ Role `{role_name}` not found! Create it first.")
        return

    cfg = load_config()
    cfg["AUTO_ROLE_NAME"] = role.name
    save_config(cfg)
    await ctx.send(f"✅ Auto-role set to **{role.name}**")


# ── !setwelcomechannel ───────────────────────

@bot.command(name="setwelcomechannel")
@commands.has_permissions(administrator=True)
async def set_welcome_channel_cmd(ctx: commands.Context, channel: discord.TextChannel):
    """Set the welcome/goodbye channel. Admin only.
    Usage: !setwelcomechannel #channel
    """
    cfg = load_config()
    cfg["WELCOME_CHANNEL_ID"] = channel.id
    cfg["GOODBYE_CHANNEL_ID"] = channel.id
    save_config(cfg)
    await ctx.send(f"✅ Welcome & goodbye channel set to {channel.mention}")


# ── !setlogchannel ───────────────────────────

@bot.command(name="setlogchannel")
@commands.has_permissions(administrator=True)
async def set_log_channel_cmd(ctx: commands.Context, channel: discord.TextChannel):
    """Set the channel for logs (moderation, edits, deletes). Admin only.
    Usage: !setlogchannel #channel
    """
    cfg = load_config()
    cfg["LOG_CHANNEL_ID"] = channel.id
    save_config(cfg)
    await ctx.send(f"✅ Log channel set to {channel.mention}")

# ── !whitelist ───────────────────────────────

@bot.group(name="whitelist", invoke_without_command=True)
@commands.has_permissions(administrator=True)
async def whitelist_grp(ctx: commands.Context):
    """Manage the swear filter whitelist. Usage: !whitelist <add/remove/list>"""
    await ctx.send(f"❓ Usage: `{PREFIX}whitelist <add/remove/list> @user`")

@whitelist_grp.command(name="add")
@commands.has_permissions(administrator=True)
async def whitelist_add(ctx: commands.Context, member: discord.Member):
    """Add a user to the swear filter whitelist."""
    cfg = load_config()
    whitelist = cfg.get("WHITELISTED_USERS", [])
    
    if member.id in whitelist:
        await ctx.send(f"⚠️ {member.display_name} is already whitelisted.")
        return
        
    whitelist.append(member.id)
    cfg["WHITELISTED_USERS"] = whitelist
    save_config(cfg)
    await ctx.send(f"✅ {member.mention} has been added to the whitelist! They can now bypass the swear filter.")

@whitelist_grp.command(name="remove")
@commands.has_permissions(administrator=True)
async def whitelist_remove(ctx: commands.Context, member: discord.Member):
    """Remove a user from the swear filter whitelist."""
    cfg = load_config()
    whitelist = cfg.get("WHITELISTED_USERS", [])
    
    if member.id not in whitelist:
        await ctx.send(f"⚠️ {member.display_name} is not in the whitelist.")
        return
        
    whitelist.remove(member.id)
    cfg["WHITELISTED_USERS"] = whitelist
    save_config(cfg)
    await ctx.send(f"✅ {member.mention} has been removed from the whitelist.")

@whitelist_grp.command(name="list")
@commands.has_permissions(administrator=True)
async def whitelist_list(ctx: commands.Context):
    """List all whitelisted users."""
    cfg = load_config()
    whitelist = cfg.get("WHITELISTED_USERS", [])
    
    if not whitelist:
        await ctx.send("ℹ️ The whitelist is currently empty (Administrators bypass it automatically).")
        return
        
    mentions = [f"<@{uid}>" for uid in whitelist]
    embed = discord.Embed(
        title="🛡️ Swear Filter Whitelist",
        description="\n".join(mentions),
        color=0x3498DB
    )
    await ctx.send(embed=embed)

@bot.command(name="addswear")
@commands.has_permissions(administrator=True)
async def add_swear_cmd(ctx: commands.Context, *, word: str):
    """Add a word to the swear filter. Admin only.
    Usage: !addswear badword
    """
    cfg = load_config()
    swear_list = cfg.get("SWEAR_WORDS", [])
    word_lower = word.lower().strip()

    if word_lower in [w.lower() for w in swear_list]:
        await ctx.send(f"⚠️ `{word_lower}` is already in the filter.")
        return

    swear_list.append(word_lower)
    cfg["SWEAR_WORDS"] = swear_list
    save_config(cfg)

    # Delete the command message so the swear word isn't visible
    try:
        await ctx.message.delete()
    except discord.Forbidden:
        pass

    await ctx.send(f"✅ Word added to the swear filter. (Total: {len(swear_list)} words)")


# ── !removeswear ─────────────────────────────

@bot.command(name="removeswear")
@commands.has_permissions(administrator=True)
async def remove_swear_cmd(ctx: commands.Context, *, word: str):
    """Remove a word from the swear filter. Admin only.
    Usage: !removeswear badword
    """
    cfg = load_config()
    swear_list = cfg.get("SWEAR_WORDS", [])
    word_lower = word.lower().strip()

    new_list = [w for w in swear_list if w.lower() != word_lower]
    if len(new_list) == len(swear_list):
        await ctx.send(f"⚠️ `{word_lower}` was not in the filter.")
        return

    cfg["SWEAR_WORDS"] = new_list
    save_config(cfg)
    await ctx.send(f"✅ Word removed from the swear filter. (Total: {len(new_list)} words)")


# ── !togglefilter ────────────────────────────

@bot.command(name="togglefilter")
@commands.has_permissions(administrator=True)
async def toggle_filter_cmd(ctx: commands.Context):
    """Toggle the swear word filter on/off. Admin only."""
    cfg = load_config()
    current = cfg.get("SWEAR_FILTER_ENABLED", True)
    cfg["SWEAR_FILTER_ENABLED"] = not current
    save_config(cfg)

    status = "🟢 **ON**" if not current else "🔴 **OFF**"
    await ctx.send(f"Swear filter is now {status}")


# ── !swearlog ───────────────────────────────

@bot.command(name="swearlog")
@commands.has_permissions(administrator=True)
async def swear_log_cmd(ctx: commands.Context, member: discord.Member = None):
    """View the history of filtered words. Usage: !swearlog [@user]"""
    cfg = load_config()
    infractions = cfg.get("INFRACTIONS", {})
    
    if member:
        # Show log for specific user
        user_id = str(member.id)
        user_data = infractions.get(user_id, [])
        if not user_data:
            await ctx.send(f"✅ **{member.display_name}** tem um histórico limpo!")
            return
            
        embed = discord.Embed(title=f"🚨 Histórico: {member.display_name}", color=0xE74C3C)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        text = ""
        for i, inf in enumerate(user_data[-10:], 1): # Show last 10
            text += f"{i}. `{inf['word']}` em {inf['time']} (#{inf['channel']})\n"
        
        embed.description = text
        embed.set_footer(text=f"Total de infrações: {len(user_data)}")
        await ctx.send(embed=embed)
    else:
        # Show general stats
        if not infractions:
            await ctx.send("ℹ️ Nenhum palavrão registrado ainda.")
            return
            
        embed = discord.Embed(title="📊 Top Infratores", color=0xE74C3C)
        sorted_inf = sorted(infractions.items(), key=lambda x: len(x[1]), reverse=True)
        
        text = ""
        for i, (uid, data) in enumerate(sorted_inf[:10], 1):
            user = bot.get_user(int(uid))
            name = user.name if user else f"ID: {uid}"
            text += f"{i}. **{name}**: {len(data)} infrações\n"
        
        embed.description = text or "Nenhum dado disponível."
        await ctx.send(embed=embed)


# ── !poll ───────────────────────────────────

class PollView(discord.ui.View):
    def __init__(self, timeout=None):
        super().__init__(timeout=timeout)
        self.likes = 0
        self.dislikes = 0
        self.voters = set()

    @discord.ui.button(label="Concordo (0)", style=discord.ButtonStyle.success, emoji="👍", custom_id="poll_like")
    async def like(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voters:
            await interaction.response.send_message("❌ Você já votou nesta enquete!", ephemeral=True)
            return
        self.likes += 1
        self.voters.add(interaction.user.id)
        button.label = f"Concordo ({self.likes})"
        await interaction.response.edit_message(view=self)

    @discord.ui.button(label="Discordo (0)", style=discord.ButtonStyle.danger, emoji="👎", custom_id="poll_dislike")
    async def dislike(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id in self.voters:
            await interaction.response.send_message("❌ Você já votou nesta enquete!", ephemeral=True)
            return
        self.dislikes += 1
        self.voters.add(interaction.user.id)
        button.label = f"Discordo ({self.dislikes})"
        await interaction.response.edit_message(view=self)

@bot.command(name="poll")
async def poll_cmd(ctx: commands.Context, question: str, time: int = 60):
    """Create a poll. Usage: !poll "Sua pergunta" [tempo_segundos]"""
    embed = discord.Embed(
        title="🗳️ Enquete Paradox",
        description=f"**{question}**\n\nVote usando os botões abaixo!",
        color=0x9B59B6,
        timestamp=discord.utils.utcnow()
    )
    embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.display_avatar.url)
    embed.set_footer(text=f"Enquete dura {time}s")
    
    msg = await ctx.send(embed=embed, view=PollView(timeout=time))
    await ctx.message.delete()

# ── SECURITY: QUARANTINE SYSTEM ──

async def get_or_create_quarantine(guild):
    role = discord.utils.get(guild.roles, name=QUARANTINE_ROLE_NAME)
    if not role:
        role = await guild.create_role(name=QUARANTINE_ROLE_NAME, color=0x34495E, reason="Security system setup")
        for channel in guild.channels:
            try:
                await channel.set_permissions(role, view_channel=False, send_messages=False)
            except: pass
            
    channel = discord.utils.get(guild.text_channels, name=QUARANTINE_CHANNEL_NAME)
    if not channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        channel = await guild.create_text_channel(name=QUARANTINE_CHANNEL_NAME, overwrites=overwrites)
        await channel.send("⚠️ **Você foi colocado em quarentena.**\nFale com os moderadores aqui para contestar sua punição.")
    return role, channel

async def apply_quarantine(member: discord.Member, reason: str):
    """Saves roles, removes them, and adds Quarantined role."""
    guild = member.guild
    cfg = load_config()
    
    # Save current roles (excluding @everyone and Quarantined)
    role_ids = [role.id for role in member.roles if not role.is_default() and role.name != QUARANTINE_ROLE_NAME]
    
    quarantine_data = cfg.get("QUARANTINE_ROLES", {})
    quarantine_data[str(member.id)] = role_ids
    cfg["QUARANTINE_ROLES"] = quarantine_data
    save_config(cfg)
    
    role, ch = await get_or_create_quarantine(guild)
    
    # Remove all removable roles and add quarantine
    try:
        # We try to remove all roles at once
        roles_to_remove = [r for r in member.roles if not r.is_default() and r < guild.me.top_role]
        await member.remove_roles(*roles_to_remove, reason=f"Quarantine: {reason}")
        await member.add_roles(role, reason=f"Quarantine: {reason}")
    except:
        # Fallback if bot permissions are tricky
        await member.add_roles(role)

# ── MODERATION COMMANDS ───────────────────────

@bot.command(name="softban")
@commands.has_permissions(ban_members=True)
async def softban_cmd(ctx, member: discord.Member, *, reason="No reason provided"):
    """Ban and immediately unban to clear messages. Admin only."""
    await member.ban(reason=f"Softban: {reason}", delete_message_days=7)
    await ctx.guild.unban(member, reason="Softban completion")
    await ctx.send(f"🧼 **{member.display_name}** was softbanned. (Messages cleared)")

@bot.command(name="mute")
@commands.has_permissions(moderate_members=True)
async def mute_cmd(ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
    """Timeout a member. Usage: !mute @user 10 reason"""
    await member.timeout(timedelta(minutes=minutes), reason=reason)
    await ctx.send(f"🔇 **{member.display_name}** was muted for {minutes} minutes.")

@bot.command(name="quarantine")
@commands.has_permissions(administrator=True)
async def quarantine_cmd(ctx, member: discord.Member):
    """Manually send a member to quarantine. Admin only."""
    await apply_quarantine(member, "Manual Moderator Action")
    ch_name = QUARANTINE_CHANNEL_NAME
    await ctx.send(f"⚖️ **{member.display_name}** foi enviado para a quarentena.")

@bot.command(name="addscam")
@commands.has_permissions(administrator=True)
async def add_scam_cmd(ctx, link: str):
    """Add a new link to the phishing blacklist."""
    global SCAM_LINKS
    if link in SCAM_LINKS:
        await ctx.send("⚠️ Este link já está na blacklist.")
        return
    SCAM_LINKS.append(link)
    await ctx.send(f"✅ Link `{link}` adicionado ao filtro de phishing!")

@bot.command(name="clearscamlog")
@commands.has_permissions(administrator=True)
async def clear_scam_log_cmd(ctx, member: discord.Member):
    """Reset the scam/phishing infraction count for a user."""
    cfg = load_config()
    scam_infractions = cfg.get("SCAM_INFRACTIONS", {})
    if str(member.id) in scam_infractions:
        del scam_infractions[str(member.id)]
        cfg["SCAM_INFRACTIONS"] = scam_infractions
        save_config(cfg)
        await ctx.send(f"✅ Histórico de phishing de {member.display_name} foi limpo.")
    else:
        await ctx.send("ℹ️ Este usuário não possui histórico de phishing.")

@bot.command(name="unquarantine")
@commands.has_permissions(administrator=True)
async def unquarantine_cmd(ctx, member: discord.Member):
    """Manually release a member from quarantine and restore roles."""
    cfg = load_config()
    role = discord.utils.get(ctx.guild.roles, name=QUARANTINE_ROLE_NAME)
    
    if role and role in member.roles:
        await member.remove_roles(role)
        
        # Restore saved roles
        quarantine_data = cfg.get("QUARANTINE_ROLES", {})
        saved_role_ids = quarantine_data.get(str(member.id), [])
        
        roles_to_add = []
        for rid in saved_role_ids:
            r = ctx.guild.get_role(int(rid))
            if r and r < ctx.guild.me.top_role:
                roles_to_add.append(r)
        
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Released from quarantine")
                await ctx.send(f"✅ **{member.display_name}** liberado! {len(roles_to_add)} cargos devolvidos.")
            except:
                await ctx.send(f"✅ **{member.display_name}** liberado, mas houve um erro ao devolver alguns cargos.")
        else:
            await ctx.send(f"✅ **{member.display_name}** liberado da quarentena!")
            
        # Clean up config
        if str(member.id) in quarantine_data:
            del quarantine_data[str(member.id)]
            cfg["QUARANTINE_ROLES"] = quarantine_data
            save_config(cfg)
    else:
        await ctx.send(f"ℹ️ **{member.display_name}** não está na quarentena.")

@bot.command(name="setthreshold")
@commands.has_permissions(administrator=True)
async def set_threshold_cmd(ctx, system: str, key: str, value: int):
    """Set security thresholds. Usage: !setthreshold <swear/scam> <key> <value>"""
    cfg = load_config()
    system = system.lower()
    
    if system == "swear":
        thresholds = cfg.get("SWEAR_THRESHOLDS", {"silent": 1, "warn1": 2, "warn2": 3, "mute": 4, "quarantine": 8})
        thresholds[key] = value
        cfg["SWEAR_THRESHOLDS"] = thresholds
    elif system == "scam":
        thresholds = cfg.get("SCAM_THRESHOLDS", {"warn": 1, "mute1": 2, "mute2": 3, "quarantine": 4, "ban": 5})
        thresholds[key] = value
        cfg["SCAM_THRESHOLDS"] = thresholds
    else:
        await ctx.send("❌ Use `swear` ou `scam` como sistema.")
        return
        
    save_config(cfg)
    await ctx.send(f"✅ Limite de `{system}` para `{key}` atualizado para `{value}`!")

# ── !botinfo ─────────────────────────────────

@bot.command(name="botinfo")
async def bot_info_cmd(ctx: commands.Context):
    """Show information about Paradox Bot."""
    embed = discord.Embed(
        title="🤖 Paradox Bot",
        description="A multi-purpose Discord bot with auto-role, greetings, and moderation!",
        color=0x9B59B6,
    )
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🌐 Servers", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="👥 Users", value=str(sum(g.member_count for g in bot.guilds)), inline=True)
    embed.add_field(
        name="⚙️ Features",
        value=(
            "• Auto-role on join\n"
            "• Welcome & goodbye messages\n"
            "• Custom goodbye command\n"
            "• Swear word auto-filter\n"
            "• Admin configuration commands\n"
            "• Professional Ticket System"
        ),
        inline=False,
    )
    embed.set_footer(text="Paradox Bot 💜 | Made with discord.py")
    await ctx.send(embed=embed)


# ── !serverinfo ──────────────────────────────

@bot.command(name="serverinfo")
async def server_info_cmd(ctx: commands.Context):
    """Show server information."""
    guild = ctx.guild
    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=0x3498DB,
        timestamp=discord.utils.utcnow(),
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="👑 Owner", value=guild.owner.mention if guild.owner else "N/A", inline=True)
    embed.add_field(name="👥 Members", value=str(guild.member_count), inline=True)
    embed.add_field(name="💬 Channels", value=str(len(guild.channels)), inline=True)
    embed.add_field(name="🎭 Roles", value=str(len(guild.roles)), inline=True)
    embed.add_field(name="📅 Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
    embed.set_footer(text="Paradox Bot 💜")
    await ctx.send(embed=embed)


# ── !purge ───────────────────────────────────

@bot.command(name="purge")
@commands.has_permissions(manage_messages=True)
async def purge_cmd(ctx: commands.Context, amount: int = 5):
    """Delete messages in bulk. Mod only.
    Usage: !purge 10
    """
    if amount < 1 or amount > 100:
        await ctx.send("⚠️ Please specify a number between 1 and 100.")
        return

    deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for the command message
    msg = await ctx.send(f"🗑️ Deleted **{len(deleted) - 1}** messages.")
    await msg.delete(delay=3)


# ── !kick ────────────────────────────────────

@bot.command(name="kick")
@commands.has_permissions(kick_members=True)
async def kick_cmd(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Kick a member. Mod only.
    Usage: !kick @user reason
    """
    try:
        await member.kick(reason=reason)
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"**{member.name}** was kicked by {ctx.author.mention}\n**Reason:** {reason}",
            color=0xE67E22,
        )
        embed.set_footer(text="Paradox Bot 💜")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to kick that user.")


# ── !ban ─────────────────────────────────────

@bot.command(name="ban")
@commands.has_permissions(ban_members=True)
async def ban_cmd(ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
    """Ban a member. Admin only.
    Usage: !ban @user reason
    """
    try:
        await member.ban(reason=reason)
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"**{member.name}** was banned by {ctx.author.mention}\n**Reason:** {reason}",
            color=0xE74C3C,
        )
        embed.set_footer(text="Paradox Bot 💜")
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to ban that user.")


# ── !setboostchannel ──────────────────────────

@bot.command(name="setboostchannel")
@commands.has_permissions(administrator=True)
async def set_boost_channel(ctx: commands.Context, channel: discord.TextChannel):
    """Set the channel for boost messages. Admin only."""
    cfg = load_config()
    cfg["BOOST_CHANNEL_ID"] = channel.id
    save_config(cfg)
    await ctx.send(f"✅ Boost messages will now be sent in {channel.mention}.")

# ── !setboostrole ─────────────────────────────

@bot.command(name="setboostrole")
@commands.has_permissions(administrator=True)
async def set_boost_role(ctx: commands.Context, *, role_name: str):
    """Set the custom role given when a user boosts. Admin only."""
    cfg = load_config()
    cfg["BOOST_ROLE_NAME"] = role_name
    save_config(cfg)
    await ctx.send(f"✅ Users who boost will receive the role **{role_name}**.")

# ── !setboostmessage ──────────────────────────

@bot.command(name="setboostmessage")
@commands.has_permissions(administrator=True)
async def set_boost_message(ctx: commands.Context, *, message: str):
    """Set custom boost message. Admin only."""
    cfg = load_config()
    cfg["BOOST_MESSAGE"] = message
    save_config(cfg)
    await ctx.send(f"✅ Boost message updated! Try `!testboost` to see it.")

# ── !testboost ────────────────────────────────

@bot.command(name="testboost")
@commands.has_permissions(administrator=True)
async def test_boost(ctx: commands.Context):
    """Simulate a server boost to test the message and role. Admin only."""
    member = ctx.author
    cfg = load_config()
    
    boost_channel_id = cfg.get("BOOST_CHANNEL_ID")
    channel = bot.get_channel(int(boost_channel_id)) if boost_channel_id else ctx.channel
    
    if channel:
        boost_tpl = cfg.get("BOOST_MESSAGE", "Thank you for boosting the server, {mention}! 💖")
        
        embed = discord.Embed(
            title="✨ Server Boosted! ✨",
            description=boost_tpl.replace("{mention}", member.mention).replace("{member}", member.name).replace("{server}", ctx.guild.name),
            color=0xF47FFF,
            timestamp=discord.utils.utcnow()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text="Paradox Bot 💜")
        
        # Test Role selector if configured
        selectable_names = cfg.get("SELECTABLE_BOOST_ROLES", [])
        if selectable_names:
            roles = []
            for name in selectable_names:
                r = parse_role_name(ctx.guild, name)
                if r: roles.append(r)
            if roles:
                await channel.send(content=f"🎁 {member.mention}, you can pick one special booster role below!", view=BoostRoleView(roles))
        else:
            await channel.send(embed=embed)

        # Test Auto-Role creation/assignment
        role_name = cfg.get("BOOST_ROLE_NAME", "Server Booster")
        role = parse_role_name(ctx.guild, role_name)
        if not role:
            try:
                role = await ctx.guild.create_role(name=role_name, color=0xF47FFF, hoist=True, reason="Test Boost Role Creation")
                await ctx.send(f"🛠️ Created testing role: **{role_name}**")
            except discord.Forbidden:
                await ctx.send(f"❌ Failed to create role **{role_name}** (Permissions)")
        
        if role:
            try:
                await member.add_roles(role)
                await ctx.send(f"✅ Assigned **{role.name}** to you!")
            except discord.Forbidden:
                await ctx.send(f"❌ Failed to assign role (Permissions)")

        if channel != ctx.channel:
            await ctx.send(f"✅ Test boost complete! Check {channel.mention}")
    else:
        await ctx.send("❌ Boost channel not found! Set it with `!setboostchannel #channel`.")

# ── !setticketcategory ───────────────────────

@bot.command(name="setticketcategory")
@commands.has_permissions(administrator=True)
async def set_ticket_category(ctx: commands.Context, category_id: str):
    """Set the category where new tickets are opened. Admin only."""
    cfg = load_config()
    cfg["TICKET_CATEGORY_ID"] = category_id
    save_config(cfg)
    await ctx.send(f"✅ All new tickets will now be created in category ID: `{category_id}`")

# ── !addboostselectrole ───────────────────────

@bot.command(name="addboostselectrole")
@commands.has_permissions(administrator=True)
async def add_boost_select_role(ctx: commands.Context, *, role_name: str):
    """Add a role to the booster selection menu. Admin only."""
    cfg = load_config()
    roles = cfg.get("SELECTABLE_BOOST_ROLES", [])
    if role_name not in roles:
        roles.append(role_name)
        cfg["SELECTABLE_BOOST_ROLES"] = roles
        save_config(cfg)
        await ctx.send(f"✅ Role **{role_name}** added to the booster selector!")
    else:
        await ctx.send("⚠️ That role is already in the list.")

# ── !removeboostselectrole ────────────────────

@bot.command(name="removeboostselectrole")
@commands.has_permissions(administrator=True)
async def remove_boost_select_role(ctx: commands.Context, *, role_name: str):
    """Remove a role from the booster selection menu. Admin only."""
    cfg = load_config()
    roles = cfg.get("SELECTABLE_BOOST_ROLES", [])
    if role_name in roles:
        roles.remove(role_name)
        cfg["SELECTABLE_BOOST_ROLES"] = roles
        save_config(cfg)
        await ctx.send(f"✅ Role **{role_name}** removed from the booster selector.")
    else:
        await ctx.send("⚠️ That role was not in the list.")

# ══════════════════════════════════════════════
#  ERROR HANDLING
# ══════════════════════════════════════════════

@bot.event
async def on_command_error(ctx: commands.Context, error):
    """Global error handler for commands."""
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("🔒 You don't have permission to use that command.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing argument: `{error.param.name}`. Use `{PREFIX}help {ctx.command}` for usage.")
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ Member not found. Make sure to mention them or use their exact name.")
    elif isinstance(error, commands.CommandNotFound):
        pass  # Silently ignore unknown commands
    else:
        print(f"  [ERROR] {type(error).__name__}: {error}")


# ══════════════════════════════════════════════
#  START THE BOT
# ══════════════════════════════════════════════

if __name__ == "__main__":
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("═" * 50)
        print("  ❌  ERROR: No bot token found!")
        print("  📂  Locally: Add it to config.json")
        print("  🚢  Railway: Add DISCORD_TOKEN in variables")
        print("═" * 50)
    else:
        # Run the bot
        bot.run(TOKEN)
