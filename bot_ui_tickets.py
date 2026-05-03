import discord
import asyncio
from bot_database import db
from bot_functions import load_config

# ──────────────────────────────────────────────
#  TICKET SYSTEM UI
# ──────────────────────────────────────────────

class TicketControlView(discord.ui.View):
    """View inside a created ticket for claiming, closing, and vouching."""
    def __init__(self, vouch_enabled: bool = False, claimer_id: int = None, vouched: bool = False):
        super().__init__(timeout=None)
        self.vouch_enabled = vouch_enabled
        self.claimer_id = claimer_id
        self.vouched = vouched

        if not claimer_id:
            # Unclaimed
            btn_claim = discord.ui.Button(label="Claim Ticket", style=discord.ButtonStyle.primary, custom_id="claim_ticket", emoji="🙋")
            btn_claim.callback = self.claim_ticket
            self.add_item(btn_claim)
        elif vouch_enabled and not vouched:
            # Claimed, Vouch enabled, not vouched
            btn_vouch = discord.ui.Button(label="Vouch Staff", style=discord.ButtonStyle.success, custom_id="vouch_ticket", emoji="⭐")
            btn_vouch.callback = self.vouch_ticket
            self.add_item(btn_vouch)
            
        # Always have Close button
        btn_close = discord.ui.Button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket", emoji="🔒")
        btn_close.callback = self.close_ticket
        self.add_item(btn_close)

    async def claim_ticket(self, interaction: discord.Interaction):
        # Only users with manage_channels (mods) can claim
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Only staff can claim tickets!", ephemeral=True)
            return
            
        self.claimer_id = interaction.user.id
        
        # We can update the message
        await interaction.response.send_message(f"✅ Ticket claimed by {interaction.user.mention}!")
        
        # Update view
        new_view = TicketControlView(vouch_enabled=self.vouch_enabled, claimer_id=self.claimer_id, vouched=False)
        await interaction.message.edit(view=new_view)

    async def vouch_ticket(self, interaction: discord.Interaction):
        # Vouch the claimer
        if not self.claimer_id:
            await interaction.response.send_message("⚠️ This ticket hasn't been claimed yet!", ephemeral=True)
            return
            
        if interaction.user.id == self.claimer_id:
            await interaction.response.send_message("❌ You cannot vouch yourself!", ephemeral=True)
            return

        cfg = load_config()
        p_id = str(self.claimer_id)
        
        # Database Update
        count = await db.get_vouches(p_id) + 1
        await db.set_vouches(p_id, count)
        
        level = (count // 5) + 1
        vouch_channel_id = cfg.get("VOUCH_CHANNEL_ID")
        
        member = interaction.guild.get_member(self.claimer_id)
        member_name = member.name if member else f"ID: {self.claimer_id}"
        member_mention = member.mention if member else f"<@{self.claimer_id}>"
        
        if vouch_channel_id:
            try:
                vouch_channel = interaction.guild.get_channel(int(vouch_channel_id))
                if vouch_channel:
                    embed = discord.Embed(
                        title="🌟 New Vouch!",
                        description=f"**{interaction.user.mention}** vouched for **{member_mention}** in {interaction.channel.mention}!",
                        color=0xF1C40F,
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(name="Staff Member", value=member_name, inline=True)
                    embed.add_field(name="Total Vouches", value=str(count), inline=True)
                    embed.add_field(name="Vouch Level", value=str(level), inline=True)
                    embed.set_footer(text="Paradox Bot 💜 | Helper Reputation")
                    await vouch_channel.send(embed=embed)
            except: pass

        await interaction.response.send_message(f"✅ You vouched for **{member_name}**! They now have **{count}** vouches.", ephemeral=True)
        
        # Update view to disable vouching
        new_view = TicketControlView(vouch_enabled=self.vouch_enabled, claimer_id=self.claimer_id, vouched=True)
        try:
            await interaction.message.edit(view=new_view)
        except: pass

    async def close_ticket(self, interaction: discord.Interaction):
        await interaction.response.send_message("🚨 **Closing ticket thread in 5 seconds...**")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception as e:
            print(f"Failed to delete ticket: {e}")

class SupportTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_support_ticket", emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_logic(interaction, "support", "Customer Support")

class HelperTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_helper_ticket", emoji="🛠️")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_logic(interaction, "helper", "Helper Inquiry")

class MacroTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Open Ticket", style=discord.ButtonStyle.primary, custom_id="open_macro_ticket", emoji="🤖")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket_logic(interaction, "macro", "Macro Inquiry")

async def create_ticket_logic(interaction: discord.Interaction, ticket_type: str, title_name: str):
    cfg = load_config()
    cat_id = cfg.get("TICKET_CATEGORY_ID")
    
    if not cat_id:
        return await interaction.response.send_message("❌ Ticket system is not fully configured (missing category).", ephemeral=True)
        
    category = interaction.guild.get_channel(int(cat_id))
    if not category:
        return await interaction.response.send_message("❌ Ticket category not found.", ephemeral=True)

    # Create thread/channel
    # Use private thread for now if it's a TextChannel, or just a channel in category
    channel_name = f"{ticket_type}-{interaction.user.name}"
    
    try:
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        ticket_channel = await interaction.guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Ticket created by {interaction.user}"
        )
        
        embed = discord.Embed(
            title=f"🎫 {title_name}",
            description=(
                f"Hello {interaction.user.mention}! Staff will be with you shortly.\n\n"
                "While you wait, please explain your inquiry in detail."
            ),
            color=0x3498DB
        )
        embed.set_footer(text="Paradox Bot 💜 | Support System")
        
        vouch_enabled = (ticket_type == "helper") # Example logic
        view = TicketControlView(vouch_enabled=vouch_enabled)
        
        await ticket_channel.send(content=f"{interaction.user.mention} | <@&{cfg.get('STAFF_ROLE_ID', '')}>", embed=embed, view=view)
        await interaction.response.send_message(f"✅ Ticket created! {ticket_channel.mention}", ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to create ticket: {e}", ephemeral=True)
