import discord
from discord.ext import commands
from bot_functions import load_config, save_config_sync, parse_role_name
from bot_database import db

class Config(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="autorole")
    @commands.has_permissions(administrator=True)
    async def set_auto_role(self, ctx, *, role_name: str):
        """Set the role given to new members."""
        cfg = load_config()
        cfg["AUTO_ROLE_NAME"] = role_name
        await save_config_sync(cfg)
        await ctx.send(f"✅ New members will now receive the role: **{role_name}**")

    @commands.command(name="setwelcomechannel")
    @commands.has_permissions(administrator=True)
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel for welcome messages."""
        cfg = load_config()
        cfg["WELCOME_CHANNEL_ID"] = channel.id
        await save_config_sync(cfg)
        await ctx.send(f"✅ Welcome messages set to {channel.mention}")

    @commands.command(name="setwelcome")
    @commands.has_permissions(administrator=True)
    async def set_welcome_msg(self, ctx, *, message: str):
        """Set the welcome message. Use {mention}, {member}, {server}."""
        cfg = load_config()
        cfg["WELCOME_MESSAGE"] = message
        await save_config_sync(cfg)
        await ctx.send("✅ Welcome message updated!")

    @commands.command(name="togglewelcome")
    @commands.has_permissions(administrator=True)
    async def toggle_welcome(self, ctx):
        """Enable or disable welcome messages."""
        cfg = load_config()
        cfg["WELCOME_ENABLED"] = not cfg.get("WELCOME_ENABLED", True)
        await save_config_sync(cfg)
        status = "ENABLED" if cfg["WELCOME_ENABLED"] else "DISABLED"
        await ctx.send(f"✅ Welcome messages are now **{status}**.")

    @commands.command(name="testjoin")
    @commands.has_permissions(administrator=True)
    async def test_join(self, ctx):
        """Simulate a join event for yourself."""
        # This will be handled in bot_main.py event listener, but we can call it manually if we expose it
        await ctx.send("⌛ Simulating join... (Make sure you have welcome channel set)")
        # In a real cog, we'd trigger the listener or call a helper

async def setup(bot):
    await bot.add_cog(Config(bot))
