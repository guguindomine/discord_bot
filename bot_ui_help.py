import discord
from bot_functions import load_config

class HelpView(discord.ui.View):
    """View for the interactive help command."""
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(HelpSelect())

class HelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Setup & Config", description="Greetings, Roles, Logs & Channels", emoji="⚙️", value="setup"),
            discord.SelectOption(label="Tickets & Apps", description="Support, Macros & Application setup", emoji="🎟️", value="tickets"),
            discord.SelectOption(label="Server Boost", description="Rewards, Logs & Special Roles", emoji="💎", value="boost"),
            discord.SelectOption(label="Moderation", description="Kick, Ban, Mute & Cleanup", emoji="🔨", value="mod"),
            discord.SelectOption(label="Security & Filter", description="Anti-Scam, Quarantine & Swear Filter", emoji="🛡️", value="security"),
            discord.SelectOption(label="General & Stats", description="Polls, Info & Server data", emoji="📊", value="general"),
            discord.SelectOption(label="Economy & Casino", description="Gambling, Bank & Paradoxals", emoji="🪙", value="economy"),
            discord.SelectOption(label="Leveling & Ranks", description="XP, Levels & Kingdom Roles", emoji="🏆", value="leveling"),
            discord.SelectOption(label="Social & Marriage", description="Marry, Hug, Kiss & Interactions", emoji="💖", value="social")
        ]
        super().__init__(placeholder="Select a category to view commands...", options=options)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        prefix = load_config().get("PREFIX", "!")
        
        embed = discord.Embed(color=0x9B59B6, timestamp=discord.utils.utcnow())
        
        if cat == "setup":
            embed.title = "⚙️ Setup & Configuration"
            embed.description = (
                f"`{prefix}autorole <role>` - Set the auto-join role\n"
                f"`{prefix}setwelcomechannel <#ch>` - Set where greetings go\n"
                f"`{prefix}setlogchannel <#ch>` - Set where logs go\n"
                f"`{prefix}setwelcome <msg>` - Set the join message\n"
                f"`{prefix}setgoodbye <msg/channel>` - Set leave message or channel\n"
                f"`{prefix}setimg <welcome/goodbye> <url>` - Set banners\n"
                f"`{prefix}togglewelcome` - Enable/Disable greetings\n"
                f"`{prefix}testjoin` / `{prefix}testleave` - Test greeting embeds"
            )
        elif cat == "tickets":
            embed.title = "🎟️ Tickets & Helper Applications"
            embed.description = (
                f"`{prefix}setupticket <support/helper/macro>` - Setup buttons\n"
                f"`{prefix}setticketcategory <id>` - Set category for new tickets\n"
                f"`{prefix}setvouchchannel <#ch>` - Set where vouches go"
            )
        elif cat == "boost":
            embed.title = "💎 Server Boosting System"
            embed.description = (
                f"`{prefix}testboost` - Simulate a boost event\n"
                f"`{prefix}setboostchannel <#ch>` - Set where boost messages go\n"
                f"`{prefix}setboostrole <role>` - Set auto-assigned boost role\n"
                f"`{prefix}setboostmessage <msg>` - Set custom boost message"
            )
        elif cat == "mod":
            embed.title = "🔨 Advanced Moderation"
            embed.description = (
                f"`{prefix}purge <num>` - Delete bulk messages\n"
                f"`{prefix}mute <@user> <min>` - Timeout a member\n"
                f"`{prefix}softban <@user>` - Kick & clear messages\n"
                f"`{prefix}kick <@user> [reason]` - Kick a member\n"
                f"`{prefix}ban <@user> [reason]` - Ban a member\n"
                f"`{prefix}quarantine <@user>` - Send to quarantine manually\n"
                f"`{prefix}unquarantine <@user>` - Release user from quarantine"
            )
        elif cat == "security":
            embed.title = "🛡️ Security & Filter System"
            embed.description = (
                f"`{prefix}togglefilter` - Toggle swear detection\n"
                f"`{prefix}setthreshold <sys> <key> <val>` - Config punishment levels\n"
                f"`{prefix}addscam <link>` - Add to phishing blacklist\n"
                f"`{prefix}clearscamlog <@user>` - Reset scam strikes"
            )
        elif cat == "general":
            embed.title = "📊 General & Stats"
            embed.description = (
                f"`{prefix}poll \"Question\" <time>` - Create interactive poll\n"
                f"`{prefix}saycolor <color> <text>` - Send a colored message\n"
                f"`{prefix}botinfo` - See bot stats & features\n"
                f"`{prefix}serverinfo` - See detailed server stats\n"
                f"`{prefix}help paradox` - Open this menu"
            )
        elif cat == "economy":
            embed.title = "🪙 Paradoxy Economy"
            embed.description = (
                f"`{prefix}balance [@user]` - Wallet, bank & effects\n"
                f"`{prefix}daily` - Claim daily reward\n"
                f"`{prefix}work` - Safe earnings\n"
                f"`{prefix}give <@user> <amount>` - Transfer paradoxy\n"
                f"`{prefix}shop` - Browse items\n"
                f"`{prefix}buy <item>` - Purchase an item\n"
                f"`{prefix}inventory` - View items\n\n"
                f"**Casino:**\n"
                f"`{prefix}cf <bet>` - Coinflip\n"
                f"`{prefix}slots <bet>` - Slot machine\n"
                f"`{prefix}bj <bet>` - Blackjack\n"
                f"`{prefix}roulette <bet> <choice>` - Roulette"
            )
        elif cat == "leveling":
            embed.title = "🏆 Leveling & Ranks"
            embed.description = (
                f"`{prefix}rank [@user]` - Check level and XP progress\n"
                f"`{prefix}topxp` - XP Leaderboard"
            )
        elif cat == "social":
            embed.title = "💖 Social & Marriage"
            embed.description = (
                f"`{prefix}marry <@user>` - Propose to someone\n"
                f"`{prefix}divorce` - End your marriage\n"
                f"`{prefix}hug <@user>` / `{prefix}kiss <@user>` - Social actions"
            )
            
        embed.set_footer(text="Paradox Bot 💜 | Interactive Help")
        await interaction.response.edit_message(embed=embed)
