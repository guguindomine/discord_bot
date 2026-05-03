import discord
from bot_functions import load_config

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
