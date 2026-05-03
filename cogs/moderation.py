import discord
from discord.ext import commands
from datetime import datetime, timedelta
from bot_functions import load_config, save_config_sync, parse_role_name
from bot_database import db
from bot_economy_data import MAX_EVERYONE_MENTIONS, QUARANTINE_ROLE_NAME, QUARANTINE_CHANNEL_NAME, SCAM_LINKS
from bot_ui_roles import BoostRoleView

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_or_create_quarantine(self, guild):
        role = discord.utils.get(guild.roles, name=QUARANTINE_ROLE_NAME)
        if not role:
            try:
                role = await guild.create_role(name=QUARANTINE_ROLE_NAME, color=0x34495E, reason="Paradox Security Setup")
            except:
                return None, None
        
        channel = discord.utils.get(guild.text_channels, name=QUARANTINE_CHANNEL_NAME)
        if not channel:
            try:
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    role: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                channel = await guild.create_text_channel(QUARANTINE_CHANNEL_NAME, overwrites=overwrites)
            except:
                return role, None
        return role, channel

    async def apply_quarantine(self, member: discord.Member, reason: str):
        guild = member.guild
        role_ids = [role.id for role in member.roles if not role.is_default() and role.name != QUARANTINE_ROLE_NAME]
        await db.save_quarantine_roles(str(member.id), role_ids)
        role, ch = await self.get_or_create_quarantine(guild)
        if not role: return

        try:
            roles_to_remove = [r for r in member.roles if not r.is_default() and r < guild.me.top_role]
            await member.remove_roles(*roles_to_remove, reason=f"Quarantine: {reason}")
            await member.add_roles(role, reason=f"Quarantine: {reason}")
        except:
            try:
                await member.add_roles(role)
            except: pass

    @commands.command(name="softban")
    @commands.has_permissions(ban_members=True)
    async def softban_cmd(self, ctx, member: discord.Member, *, reason="No reason provided"):
        """Ban and immediately unban to clear messages. Admin only."""
        await member.ban(reason=f"Softban: {reason}", delete_message_days=7)
        await ctx.guild.unban(member, reason="Softban completion")
        await ctx.send(f"🧼 **{member.display_name}** was softbanned. (Messages cleared)")

    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute_cmd(self, ctx, member: discord.Member, minutes: int = 10, *, reason="No reason provided"):
        """Timeout a member. Usage: !mute @user 10 reason"""
        await member.timeout(timedelta(minutes=minutes), reason=reason)
        await ctx.send(f"🔇 **{member.display_name}** was muted for {minutes} minutes.")

    @commands.command(name="quarantine")
    @commands.has_permissions(administrator=True)
    async def quarantine_cmd(self, ctx, member: discord.Member):
        """Manually send a member to quarantine. Admin only."""
        await self.apply_quarantine(member, "Manual Moderator Action")
        await ctx.send(f"⚖️ **{member.display_name}** has been sent to quarantine.")

    @commands.command(name="addscam")
    @commands.has_permissions(administrator=True)
    async def add_scam_cmd(self, ctx, link: str):
        """Add a new link to the phishing blacklist."""
        # Using a local copy since SCAM_LINKS is a list and we want to update config
        cfg = load_config()
        links = cfg.get("SCAM_LINKS", SCAM_LINKS)
        if link in links:
            await ctx.send("⚠️ This link is already in the blacklist.")
            return
        links.append(link)
        cfg["SCAM_LINKS"] = links
        await save_config_sync(cfg)
        await ctx.send(f"✅ Link `{link}` added to phishing filter!")

    @commands.command(name="clearscamlog")
    @commands.has_permissions(administrator=True)
    async def clear_scam_log_cmd(self, ctx, member: discord.Member):
        """Reset the scam/phishing infraction count for a user."""
        strikes = await db.get_scam_strikes(str(member.id))
        if strikes > 0:
            await db.clear_scam_strikes(str(member.id))
            await ctx.send(f"✅ Phishing history for {member.display_name} has been cleared.")
        else:
            await ctx.send("ℹ️ This user has no phishing history.")

    @commands.command(name="unquarantine")
    @commands.has_permissions(administrator=True)
    async def unquarantine_cmd(self, ctx, member: discord.Member):
        """Manually release a member from quarantine and restore roles."""
        role = discord.utils.get(ctx.guild.roles, name=QUARANTINE_ROLE_NAME)
        if role and role in member.roles:
            await member.remove_roles(role)
            saved_role_ids = await db.get_quarantine_roles(str(member.id))
            roles_to_add = []
            for rid in saved_role_ids:
                r = ctx.guild.get_role(int(rid))
                if r and r < ctx.guild.me.top_role:
                    roles_to_add.append(r)
            
            if roles_to_add:
                try:
                    await member.add_roles(*roles_to_add, reason="Released from quarantine")
                    await ctx.send(f"✅ **{member.display_name}** released! {len(roles_to_add)} roles returned.")
                except:
                    await ctx.send(f"✅ **{member.display_name}** released, but there was an error returning some roles.")
            else:
                await ctx.send(f"✅ **{member.display_name}** released from quarantine!")
            await db.clear_quarantine_roles(str(member.id))
        else:
            await ctx.send(f"ℹ️ **{member.display_name}** is not in quarantine.")

    @commands.command(name="setthreshold")
    @commands.has_permissions(administrator=True)
    async def set_threshold_cmd(self, ctx, system: str, key: str, value: int):
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
            await ctx.send("❌ Use `swear` or `scam` as the system.")
            return
        await save_config_sync(cfg)
        await ctx.send(f"✅ Threshold for `{system}` ({key}) updated to `{value}`!")

    @commands.command(name="botinfo")
    async def bot_info_cmd(self, ctx: commands.Context):
        """Show information about Paradox Bot."""
        embed = discord.Embed(
            title="🤖 Paradox Bot",
            description="A multi-purpose Discord bot with auto-role, greetings, and moderation!",
            color=0x9B59B6,
        )
        embed.add_field(name="📡 Ping", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="🌐 Servers", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="👥 Users", value=str(sum(g.member_count for g in self.bot.guilds)), inline=True)
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

    @commands.command(name="serverinfo")
    async def server_info_cmd(self, ctx: commands.Context):
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

    @commands.command(name="purge")
    @commands.has_permissions(manage_messages=True)
    async def purge_cmd(self, ctx: commands.Context, amount: int = 5):
        """Delete messages in bulk. Mod only. Usage: !purge 10"""
        if amount < 1 or amount > 100:
            await ctx.send("⚠️ Please specify a number between 1 and 100.")
            return
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"🗑️ Deleted **{len(deleted) - 1}** messages.")
        await msg.delete(delay=3)

    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member. Mod only. Usage: !kick @user reason"""
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

    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member. Admin only. Usage: !ban @user reason"""
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

    @commands.command(name="setboostchannel")
    @commands.has_permissions(administrator=True)
    async def set_boost_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        """Set the channel for boost messages. Admin only."""
        cfg = load_config()
        cfg["BOOST_CHANNEL_ID"] = channel.id
        await save_config_sync(cfg)
        await ctx.send(f"✅ Boost messages will now be sent in {channel.mention}.")

    @commands.command(name="setboostrole")
    @commands.has_permissions(administrator=True)
    async def set_boost_role(self, ctx: commands.Context, *, role_name: str):
        """Set the custom role given when a user boosts. Admin only."""
        cfg = load_config()
        cfg["BOOST_ROLE_NAME"] = role_name
        await save_config_sync(cfg)
        await ctx.send(f"✅ Users who boost will receive the role **{role_name}**.")

    @commands.command(name="setboostmessage")
    @commands.has_permissions(administrator=True)
    async def set_boost_message(self, ctx: commands.Context, *, message: str):
        """Set custom boost message. Use {mention}, {member}, {server}."""
        cfg = load_config()
        cfg["BOOST_MESSAGE"] = message
        await save_config_sync(cfg)
        await ctx.send(f"✅ Boost message updated! Try `!testboost` to see it.")

    @commands.command(name="testboost", aliases=["setboost"])
    @commands.has_permissions(administrator=True)
    async def test_boost(self, ctx: commands.Context, member: discord.Member = None):
        """Simulate a server boost for yourself or another member. Admin only."""
        member = member or ctx.author
        cfg = load_config()
        boost_channel_id = cfg.get("BOOST_CHANNEL_ID")
        channel = self.bot.get_channel(int(boost_channel_id)) if boost_channel_id else ctx.channel
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
            role_name = cfg.get("BOOST_ROLE_NAME", "Server Booster")
            role = parse_role_name(ctx.guild, role_name)
            if not role:
                try:
                    role = await ctx.guild.create_role(name=role_name, color=0xF47FFF, hoist=True, reason="Test Boost Role Creation")
                except: pass
            if role:
                try:
                    await member.add_roles(role)
                except: pass
            if channel != ctx.channel:
                await ctx.send(f"✅ Test boost for {member.display_name} complete! Check {channel.mention}")
        else:
            await ctx.send("❌ Boost channel not found! Set it with `!setboostchannel #channel`.")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
