import discord
from discord.ext import commands
from bot_functions import get_level_from_xp, get_xp_progress, load_config
from bot_database import db
from bot_economy_data import LEVEL_ROLES

import random
from discord.ext import tasks

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_xp_task.start()

    def cog_unload(self):
        self.voice_xp_task.cancel()

    @tasks.loop(minutes=1)
    async def voice_xp_task(self):
        """Give XP to members in voice channels."""
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                if len(vc.members) >= 2:
                    for member in vc.members:
                        if not member.bot and not member.voice.self_deaf and not member.voice.deaf:
                            xp = random.randint(15, 30)
                            await db.update_xp(str(member.id), xp)

    @commands.command(name="rank", aliases=["level", "xp"])
    async def rank_cmd(self, ctx, member: discord.Member = None):
        """Check your level and XP progress."""
        member = member or ctx.author
        user_data = await db.get_user(str(member.id))
        xp = user_data.get("xp", 0)
        level = get_level_from_xp(xp)
        progress = get_xp_progress(xp)
        
        embed = discord.Embed(title=f"🏆 {member.display_name}'s Level", color=0x9B59B6)
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="Total XP", value=f"**{xp:,}**", inline=True)
        embed.add_field(name="Next Level", value=progress, inline=False)
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Find next role reward
        next_role = None
        for req_level in sorted(LEVEL_ROLES.keys()):
            if req_level > level:
                next_role = f"Level {req_level}: {LEVEL_ROLES[req_level]['name']}"
                break
        if next_role:
            embed.add_field(name="Next Role Reward", value=f"🛡️ {next_role}", inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="topxp", aliases=["xplb"])
    async def topxp_cmd(self, ctx):
        """View the highest level users."""
        users = await db.get_all_users()
        sorted_users = sorted(users, key=lambda x: x.get("xp", 0), reverse=True)[:10]
        
        embed = discord.Embed(title="🏆 XP Leaderboard", color=0x9B59B6)
        desc = ""
        for i, u in enumerate(sorted_users, 1):
            uid = int(u["_id"])
            user = self.bot.get_user(uid) or await self.bot.fetch_user(uid)
            xp = u.get("xp", 0)
            level = get_level_from_xp(xp)
            desc += f"{i}. **{user.name if user else uid}** — Lvl {level} ({xp:,} XP)\n"
        embed.description = desc
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))
