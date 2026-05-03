import discord
from discord.ext import commands
import random
import asyncio
from datetime import datetime, timedelta
from bot_functions import load_config
from bot_database import db
from bot_economy_data import CURRENCY_NAME, HEIST_TARGETS, COMMAND_COOLDOWNS
from bot_ui_games import HeistTargetView

class Crimes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="heist")
    async def heist_cmd(self, ctx):
        """Start a strategic heist."""
        user_id = str(ctx.author.id)
        jail_end = await db.get_cooldown(user_id, "jail")
        if jail_end and datetime.now() < jail_end:
            rem = jail_end - datetime.now()
            return await ctx.send(f"🔒 You are in **Jail**! Release in **{int(rem.total_seconds()//60)}m**.")

        last_heist = await db.get_cooldown(user_id, "heist")
        cd = COMMAND_COOLDOWNS["heist"]
        if last_heist and datetime.now() < last_heist + timedelta(seconds=cd):
            rem = (last_heist + timedelta(seconds=cd)) - datetime.now()
            return await ctx.send(f"⏳ Wait **{int(rem.total_seconds()//60)}m**.")

        view = HeistTargetView(ctx)
        embed = discord.Embed(title="🏦 Strategic Heist", description="Select a target to begin planning.", color=0x34495E)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="crime")
    async def crime_cmd(self, ctx):
        """Commit a random crime."""
        user_id = str(ctx.author.id)
        jail_end = await db.get_cooldown(user_id, "jail")
        if jail_end and datetime.now() < jail_end:
            rem = jail_end - datetime.now()
            return await ctx.send(f"🔒 In jail for **{int(rem.total_seconds()//60)}m**.")

        last_crime = await db.get_cooldown(user_id, "crime")
        cd = COMMAND_COOLDOWNS["crime"]
        if last_crime and datetime.now() < last_crime + timedelta(seconds=cd):
            return await ctx.send("⏳ Too soon!")

        scenarios = [
            {"name": "Pickpocketing", "chance": 0.65, "win": (2000, 5000), "fine": (1000, 3000)},
            {"name": "Hacking", "chance": 0.45, "win": (8000, 15000), "fine": (4000, 8000)}
        ]
        crime = random.choice(scenarios)
        success = random.random() < crime["chance"]
        await db.set_cooldown(user_id, "crime", datetime.now())
        await db.update_quest_progress(user_id, "crime")

        if success:
            amt = random.randint(*crime["win"])
            await db.update_balance(user_id, amt)
            await ctx.send(f"✅ Success! Earned **{amt:,}** {CURRENCY_NAME} via {crime['name']}.")
        else:
            amt = random.randint(*crime["fine"])
            await db.update_balance(user_id, -amt)
            await ctx.send(f"🚨 Busted! Fined **{amt:,}** {CURRENCY_NAME} for {crime['name']}.")

    @commands.command(name="steal")
    async def steal_cmd(self, ctx, target: discord.Member):
        """Rob another user."""
        if target.id == ctx.author.id: return await ctx.send("❌ No self-robbing.")
        t_id = str(target.id)
        a_id = str(ctx.author.id)
        t_bal = await db.get_balance(t_id)
        if t_bal < 5000: return await ctx.send("❌ Target is too poor.")

        last_steal = await db.get_cooldown(a_id, "steal")
        if last_steal and datetime.now() < last_steal + timedelta(seconds=COMMAND_COOLDOWNS["steal"]):
            return await ctx.send("⏳ Wait!")

        success = random.random() < 0.4
        await db.set_cooldown(a_id, "steal", datetime.now())
        if success:
            amt = int(t_bal * random.uniform(0.1, 0.25))
            await db.update_balance(a_id, amt)
            await db.update_balance(t_id, -amt)
            await ctx.send(f"🧤 Stole **{amt:,}** from {target.mention}!")
        else:
            fine = 5000
            await db.update_balance(a_id, -fine)
            await ctx.send(f"🚨 Failed! Fined **{fine:,}**.")

    @commands.command(name="bail")
    async def bail_cmd(self, ctx):
        """Pay to get out of jail."""
        user_id = str(ctx.author.id)
        jail_end = await db.get_cooldown(user_id, "jail")
        if not jail_end or datetime.now() >= jail_end:
            return await ctx.send("ℹ️ You aren't in jail.")
        
        rem_min = int((jail_end - datetime.now()).total_seconds() // 60)
        cost = rem_min * 500
        bal = await db.get_balance(user_id)
        if bal < cost: return await ctx.send(f"❌ Bail costs **{cost:,}**. You need more money.")
        
        await db.update_balance(user_id, -cost)
        await db.set_cooldown(user_id, "jail", datetime.now())
        await ctx.send(f"🔓 Paid **{cost:,}** bail. You are free!")

async def setup(bot):
    await bot.add_cog(Crimes(bot))
