import discord
from discord.ext import commands
import random
from bot_functions import get_greeting, get_random_response
from bot_database import db

class Social(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="marry")
    async def marry_cmd(self, ctx, member: discord.Member):
        """Propose to another user."""
        if member.id == ctx.author.id: return await ctx.send("❌ Self-marriage is not supported yet.")
        if member.bot: return await ctx.send("❌ You can't marry a bot!")
        
        # Check if already married
        partner = await db.get_marriage(str(ctx.author.id))
        if partner: return await ctx.send(f"❌ You are already married to <@{partner}>!")
        
        partner2 = await db.get_marriage(str(member.id))
        if partner2: return await ctx.send(f"❌ {member.display_name} is already married!")

        await ctx.send(f"💍 {member.mention}, {ctx.author.mention} has proposed to you! Type `yes` to accept.")
        
        def check(m):
            return m.author.id == member.id and m.channel.id == ctx.channel.id and m.content.lower() == "yes"

        try:
            await self.bot.wait_for("message", check=check, timeout=60)
            await db.set_marriage(str(ctx.author.id), str(member.id))
            await db.set_marriage(str(member.id), str(ctx.author.id))
            await ctx.send(f"🎊 {ctx.author.mention} and {member.mention} are now married! ❤️")
        except:
            await ctx.send(f"💔 {member.display_name} didn't respond in time...")

    @commands.command(name="divorce")
    async def divorce_cmd(self, ctx):
        """End your marriage."""
        partner = await db.get_marriage(str(ctx.author.id))
        if not partner: return await ctx.send("❌ You aren't married.")
        
        await db.set_marriage(str(ctx.author.id), None)
        await db.set_marriage(partner, None)
        await ctx.send(f"💔 You are now divorced from <@{partner}>.")

    @commands.command(name="hug")
    async def hug_cmd(self, ctx, member: discord.Member):
        """Give someone a warm hug."""
        embed = discord.Embed(description=f"🤗 {ctx.author.mention} gave {member.mention} a big hug!", color=0xFF69B4)
        await ctx.send(embed=embed)

    @commands.command(name="kiss")
    async def kiss_cmd(self, ctx, member: discord.Member):
        """Give someone a sweet kiss."""
        embed = discord.Embed(description=f"💋 {ctx.author.mention} kissed {member.mention}!", color=0xFF0000)
        await ctx.send(embed=embed)

    @commands.command(name="slap")
    async def slap_cmd(self, ctx, member: discord.Member):
        """Slap someone!"""
        embed = discord.Embed(description=f"🖐️ {ctx.author.mention} slapped {member.mention}! Ouch.", color=0x000000)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Social(bot))
