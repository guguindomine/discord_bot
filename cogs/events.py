import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime
from bot_functions import load_config, get_greeting, get_random_response, get_level_from_xp, handle_level_up
from bot_database import db
from bot_economy_data import MAX_EVERYONE_MENTIONS, SCAM_LINKS

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = load_config()
        if not cfg.get("WELCOME_ENABLED", True): return
        
        channel_id = cfg.get("WELCOME_CHANNEL_ID")
        if not channel_id: return
        
        channel = member.guild.get_channel(int(channel_id))
        if not channel: return

        greeting = get_greeting()
        msg = cfg.get("WELCOME_MESSAGE", "Welcome to the server, {mention}!")
        msg = msg.replace("{mention}", member.mention).replace("{member}", member.name).replace("{server}", member.guild.name)
        
        embed = discord.Embed(title=f"{greeting}!", description=msg, color=0x9B59B6)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        
        await channel.send(embed=embed)
        
        # Auto-role
        role_name = cfg.get("AUTO_ROLE_NAME")
        if role_name:
            role = discord.utils.get(member.guild.roles, name=role_name)
            if role:
                try: await member.add_roles(role)
                except: pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot: return
        
        # ── XP System ──
        # Give 5-15 XP per message (cooldown 30s)
        uid = str(message.author.id)
        last_xp = await db.get_cooldown(uid, "xp_gain")
        if not last_xp or (datetime.now() - last_xp).total_seconds() > 30:
            xp_gain = random.randint(5, 15)
            await db.update_xp(uid, xp_gain)
            await db.set_cooldown(uid, "xp_gain", datetime.now())
            
            # Level up check
            user_data = await db.get_user(uid)
            old_lvl = user_data.get("level", 0)
            new_lvl = get_level_from_xp(user_data.get("xp", 0))
            if new_lvl > old_lvl:
                await db.set_level(uid, new_lvl)
                await handle_level_up(message.author, new_lvl, message.channel)

        # ── Phishing Filter ──
        for link in SCAM_LINKS:
            if link in message.content.lower():
                await message.delete()
                await message.channel.send(f"⚠️ {message.author.mention}, that link is blacklisted for security reasons.")
                # Increment strikes
                strikes = await db.get_scam_strikes(uid) + 1
                await db.set_scam_strikes(uid, strikes)
                # Punishment logic here if needed
                return

        # ── Everyone Mention Filter ──
        if "@everyone" in message.content or "@here" in message.content:
            if not message.author.guild_permissions.mention_everyone:
                # Basic check, can be more complex
                pass

async def setup(bot):
    await bot.add_cog(Events(bot))
