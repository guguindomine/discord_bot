import discord
from discord.ext import commands
from bot_functions import load_config, save_config_sync
from bot_database import db
from bot_ui_tickets import SupportTicketView, HelperTicketView, MacroTicketView

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setupticket")
    @commands.has_permissions(administrator=True)
    async def setup_ticket(self, ctx, ticket_type: str = "support"):
        """Setup a ticket button in the current channel. Admin only."""
        ticket_type = ticket_type.lower()
        if ticket_type == "support":
            view = SupportTicketView()
            title = "🎟️ Paradox Support"
            desc = "Click the button below to open a support ticket."
        elif ticket_type == "helper":
            view = HelperTicketView()
            title = "🛠️ Helper Application"
            desc = "Interested in joining our staff? Open a ticket to apply!"
        elif ticket_type == "macro":
            view = MacroTicketView()
            title = "🤖 Macro/Bot Help"
            desc = "Need help with macros or our bots? Open a ticket here."
        else:
            return await ctx.send("❌ Invalid ticket type. Use `support`, `helper`, or `macro`.")

        embed = discord.Embed(title=title, description=desc, color=0x3498DB)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="setticketcategory")
    @commands.has_permissions(administrator=True)
    async def set_ticket_category(self, ctx, category: discord.CategoryChannel):
        """Set the category where new tickets will be created. Admin only."""
        cfg = load_config()
        cfg["TICKET_CATEGORY_ID"] = category.id
        await save_config_sync(cfg)
        await ctx.send(f"✅ Ticket category set to **{category.name}**.")

    @commands.command(name="setvouchchannel")
    @commands.has_permissions(administrator=True)
    async def set_vouch_channel(self, ctx, channel: discord.TextChannel):
        """Set the channel where staff vouches are logged. Admin only."""
        cfg = load_config()
        cfg["VOUCH_CHANNEL_ID"] = channel.id
        await save_config_sync(cfg)
        await ctx.send(f"✅ Vouch logs will now be sent in {channel.mention}.")

    @commands.command(name="vouches")
    async def vouches_cmd(self, ctx, member: discord.Member = None):
        """Check how many vouches you or another staff member has."""
        member = member or ctx.author
        count = await db.get_vouches(str(member.id))
        level = (count // 5) + 1
        
        embed = discord.Embed(title=f"⭐ Vouch Info: {member.display_name}", color=0xF1C40F)
        embed.add_field(name="Total Vouches", value=str(count), inline=True)
        embed.add_field(name="Staff Reputation Level", value=str(level), inline=True)
        embed.set_footer(text="Vouches are earned through helping users in tickets.")
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Tickets(bot))
