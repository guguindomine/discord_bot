import discord
from discord.ext import commands
import asyncio
from bot_functions import load_config
from bot_ui_help import HelpView

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_cmd(self, ctx, category: str = None):
        """Show the help menu."""
        if category and category.lower() == "paradox":
            embed = discord.Embed(
                title="💜 Paradox Bot Help",
                description="Select a category from the dropdown menu to see all available commands!",
                color=0x9B59B6
            )
            embed.set_footer(text="Paradox Bot | Modern & Modular")
            await ctx.send(embed=embed, view=HelpView())
        else:
            prefix = load_config().get("PREFIX", "!")
            await ctx.send(f"❓ Use `{prefix}help paradox` to open the interactive help menu!")

    @commands.command(name="poll")
    async def poll_cmd(self, ctx, question: str, time_limit: int = 60):
        """Create a simple poll. Usage: !poll \"Question?\" 60"""
        embed = discord.Embed(title="📊 New Poll", description=question, color=0x3498DB)
        embed.set_footer(text=f"Time limit: {time_limit}s")
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")
        
        await asyncio.sleep(time_limit)
        
        msg = await ctx.channel.fetch_message(msg.id)
        yes = 0
        no = 0
        for reaction in msg.reactions:
            if str(reaction.emoji) == "✅": yes = reaction.count - 1
            if str(reaction.emoji) == "❌": no = reaction.count - 1
        
        results = discord.Embed(title="📊 Poll Results", description=f"**{question}**\n\n✅: {yes}\n❌: {no}", color=0x3498DB)
        await ctx.send(embed=results)

    @commands.command(name="saycolor")
    @commands.has_permissions(administrator=True)
    async def say_color_cmd(self, ctx, color: str, *, message: str):
        """Send a colored message in an embed. Admin only."""
        try:
            clr = int(color.replace("#", ""), 16)
        except:
            clr = 0x9B59B6
        
        embed = discord.Embed(description=message, color=clr)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Utility(bot))
