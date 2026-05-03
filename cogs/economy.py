import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import random
from bot_functions import load_config, save_config_sync
from bot_database import db
from bot_economy_data import CURRENCY_NAME, SHOP_ITEMS, COMMAND_COOLDOWNS

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.apply_interest_task.start()
        self.check_loans_task.start()
        self.check_debt_selling_task.start()

    def cog_unload(self):
        self.apply_interest_task.cancel()
        self.check_loans_task.cancel()
        self.check_debt_selling_task.cancel()

    # ── TASKS ───────────────────────────────────

    @tasks.loop(hours=1)
    async def apply_interest_task(self):
        """Apply dynamic variable interest to all bank balances every hour."""
        roll = random.random()
        if roll < 0.2:
            rate = random.uniform(-1.0, 0.0)
            tier = "📉 Negative"
        else:
            rate = random.uniform(0.1, 1.3)
            tier = "📊 Normal"
        multiplier = 1 + rate / 100
        await db.apply_bank_interest(multiplier)
        print(f"  [ECONOMY] Hourly bank interest applied: {rate:.2f}% ({tier})")

    @tasks.loop(minutes=10)
    async def check_loans_task(self):
        """Check for overdue loans every 10 minutes."""
        now = datetime.now()
        cursor = db.db.users.find({"loan": {"$exists": True}})
        async for user in cursor:
            loan_data = user.get("loan", {})
            due_date = loan_data.get("due_date")
            if due_date and now > due_date:
                user_id = user["_id"]
                await self.handle_overdue_loan(None, user_id, loan_data)

    @tasks.loop(hours=1)
    async def check_debt_selling_task(self):
        """Check for users in debt for > 48 hours and sell their items for 50% price."""
        users = await db.get_all_users()
        now = datetime.now()
        for user_doc in users:
            user_id = user_doc["_id"]
            wallet = user_doc.get("balance", 0)
            bank = user_doc.get("bank", 0)
            total_wealth = wallet + bank
            debt_since = user_doc.get("debt_since")
            
            if total_wealth < 0:
                if not debt_since:
                    await db.set_debt_since(user_id, now)
                elif now > debt_since + timedelta(hours=48):
                    inventory = user_doc.get("inventory", [])
                    if inventory:
                        total_sell_value = 0
                        items_sold = []
                        for item_name in inventory[:]:
                            item_data = SHOP_ITEMS.get(item_name)
                            if item_data:
                                sell_price = int(item_data["price"] * 0.5)
                                total_sell_value += sell_price
                                items_sold.append(item_name)
                                await db.remove_item(user_id, item_name)
                        
                        if total_sell_value > 0:
                            await db.update_balance(user_id, total_sell_value)
                            user = self.bot.get_user(int(user_id))
                            if user:
                                try:
                                    embed = discord.Embed(
                                        title="⚖️ Bank Foreclosure",
                                        description=(
                                            f"You have been in debt for over 48 hours. "
                                            f"The bank has sold your items to recover funds at **50% market value**.\n\n"
                                            f"**Items Sold:** {', '.join(items_sold)}\n"
                                            f"**Recovered:** {total_sell_value:,} {CURRENCY_NAME}"
                                        ),
                                        color=0xE74C3C,
                                        timestamp=discord.utils.utcnow()
                                    )
                                    await user.send(embed=embed)
                                except: pass
                    await db.set_debt_since(user_id, None) 
            else:
                if debt_since:
                    await db.set_debt_since(user_id, None)

    # ── HELPERS ──────────────────────────────────

    async def handle_overdue_loan(self, ctx_or_user, user_id, loan_data):
        """Handle overdue loan with fines and jail."""
        warnings = loan_data.get("warnings", 0)
        amount = loan_data["amount"]
        if warnings == 0:
            fine = int(amount * 0.05)
            jail_time = 2
            warnings = 1
        elif warnings == 1:
            fine = int(amount * 0.12)
            jail_time = 4
            warnings = 2
        else:
            inventory = await db.get_inventory(user_id)
            if inventory:
                item = inventory[0]
                price = int(SHOP_ITEMS.get(item, {"price": 0})["price"] * 0.8)
                await db.update_balance(user_id, price)
                await db.remove_item(user_id, item)
                if ctx_or_user: await ctx_or_user.send(f"⚠️ Your loan is overdue. Sold **{item}** for **{price:,}** {CURRENCY_NAME}.")
                return
            else:
                fine = int(amount * 0.2)
                await db.update_balance(user_id, -fine)
                if ctx_or_user: await ctx_or_user.send(f"⚠️ Your loan is overdue. Fined **{fine:,}** {CURRENCY_NAME}.")
                return

        await db.update_balance(user_id, -fine)
        await db.set_cooldown(user_id, "jail", datetime.now() + timedelta(hours=jail_time))
        loan_data["fines"] = loan_data.get("fines", 0) + fine
        loan_data["warnings"] = warnings
        await db.set_loan(user_id, loan_data)

        msg = f"🚨 Loan overdue! Fined **{fine:,}** {CURRENCY_NAME} and jailed for **{jail_time}** hours."
        if ctx_or_user:
            await ctx_or_user.send(msg)
        else:
            user = self.bot.get_user(int(user_id))
            if user:
                try: await user.send(msg)
                except: pass

    # ── COMMANDS ─────────────────────────────────

    @commands.command(name="balance", aliases=["bal", "money"])
    async def balance_cmd(self, ctx, member: discord.Member = None):
        """Check your Paradoxal balance and bank storage."""
        member = member or ctx.author
        wallet = await db.get_balance(str(member.id))
        bank = await db.get_bank(str(member.id))
        inventory = await db.get_inventory(str(member.id))
        
        embed = discord.Embed(title=f"💰 Economy: {member.display_name}", color=0xF1C40F)
        embed.add_field(name="Wallet", value=f"**{wallet:,}** {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Bank", value=f"**{bank:,}** {CURRENCY_NAME}", inline=True)
        embed.add_field(name="Total", value=f"**{wallet + bank:,}** {CURRENCY_NAME}", inline=False)
        
        if inventory:
            effects = []
            if "Lucky Coin" in inventory: effects.append("🍀 Luck +5%")
            if "Golden Clover" in inventory: effects.append("🍀 Luck +15%")
            if "Thief Kit" in inventory: effects.append("🧤 Steal +12%")
            if "Crime Mask" in inventory: effects.append("👺 Crime +15%")
            if "Shield" in inventory: effects.append("🛡️ Shielded (40%)")
            if "VIP Pass" in inventory: effects.append("💎 VIP (+75% Daily, +25% Work)")
            if effects:
                embed.add_field(name="Active Effects", value=", ".join(effects), inline=False)

        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Paradox Bot 💜 | Bank earns variable interest (-1% to 1.3% hourly)")
        await ctx.send(embed=embed)

    @commands.group(name="bank", invoke_without_command=True)
    async def bank_group(self, ctx):
        """Manage your bank. Usage: !bank deposit <amount> or !bank withdraw <amount>"""
        await ctx.send("❓ Usage: `!bank deposit <amount>` or `!bank withdraw <amount>`")

    @bank_group.command(name="info", aliases=["growth", "increase"])
    async def bank_info(self, ctx):
        """Show your bank amount and how much interest it may earn."""
        user_id = str(ctx.author.id)
        bank = await db.get_bank(user_id)
        if bank <= 0:
            return await ctx.send("💤 Your bank is empty. Deposit some paradoxals first to start earning interest.")

        projected_low = int(bank * -1.0 / 100)
        projected_high = int(bank * 1.3 / 100)

        embed = discord.Embed(
            title="📈 Bank Interest Forecast",
            description=(
                f"Your current bank balance is **{bank:,}** {CURRENCY_NAME}.\n\n"
                f"Estimated hourly change: **{projected_low:,}** - **{projected_high:,}** {CURRENCY_NAME}.\n"
                "Interest varies from -1% to 1.3% each hour (20% chance negative)."
            ),
            color=0x2ECC71
        )
        embed.set_footer(text="Keep money in the bank to earn variable hourly interest.")
        await ctx.send(embed=embed)

    @bank_group.command(name="deposit", aliases=["dep"])
    async def bank_deposit(self, ctx, amount: str):
        user_id = str(ctx.author.id)
        wallet = await db.get_balance(user_id)
        if amount.lower() == "all": amount = wallet
        else:
            try: amount = int(amount)
            except: return await ctx.send("❌ Please provide a valid number.")
        if amount <= 0 or amount > wallet: return await ctx.send("❌ Invalid amount.")
        await db.update_balance(user_id, -amount)
        await db.update_bank(user_id, amount)
        await ctx.send(f"🏦 Deposited **{amount:,}** {CURRENCY_NAME} into your bank!")

    @bank_group.command(name="withdraw", aliases=["with"])
    async def bank_withdraw(self, ctx, amount: str):
        user_id = str(ctx.author.id)
        bank = await db.get_bank(user_id)
        if amount.lower() == "all": amount = bank
        else:
            try: amount = int(amount)
            except: return await ctx.send("❌ Please provide a valid number.")
        if amount <= 0 or amount > bank: return await ctx.send("❌ Invalid amount.")
        await db.update_bank(user_id, -amount)
        await db.update_balance(user_id, amount)
        await ctx.send(f"🏦 Withdrew **{amount:,}** {CURRENCY_NAME} from your bank!")

    @commands.command(name="loan")
    async def loan_cmd(self, ctx, amount: str):
        """Take a loan from the bank. Max 300k."""
        user_id = str(ctx.author.id)
        loan_data = await db.get_loan(user_id)
        if loan_data:
            due_date = loan_data.get("due_date")
            if due_date and datetime.now() < due_date:
                return await ctx.send("❌ You already have an active loan. Pay it back first.")
            else:
                await self.handle_overdue_loan(ctx, user_id, loan_data)
                return

        try: amount = int(amount)
        except ValueError: return await ctx.send("❌ Please enter a valid loan amount.")
        if amount <= 0 or amount > 300000: return await ctx.send("❌ Loan amount must be between 1 and 300,000.")

        await db.update_balance(user_id, amount)
        await db.update_bank(user_id, -amount)
        due_date = datetime.now() + timedelta(hours=24)
        loan_data = {"amount": amount, "due_date": due_date, "fines": 0, "warnings": 0}
        await db.set_loan(user_id, loan_data)
        await ctx.send(f"✅ You took a loan of **{amount:,}** {CURRENCY_NAME}. Pay it back within 24 hours.")

    @commands.command(name="payloan")
    async def pay_loan_cmd(self, ctx):
        """Pay off your loan by covering the negative bank balance."""
        user_id = str(ctx.author.id)
        loan_data = await db.get_loan(user_id)
        if not loan_data: return await ctx.send("❌ You have no active loan.")
        bank = await db.get_bank(user_id)
        if bank >= 0:
            await db.clear_loan(user_id)
            await ctx.send("✅ Your loan is paid off!")
        else:
            await ctx.send(f"❌ You need to deposit **{-bank:,}** more {CURRENCY_NAME} to pay off your loan.")

    @commands.command(name="daily")
    async def daily_cmd(self, ctx):
        """Claim your daily paradoxals."""
        user_id = str(ctx.author.id)
        last_claim = await db.get_cooldown(user_id, "daily")
        cd_seconds = COMMAND_COOLDOWNS["daily"]
        if last_claim and datetime.now() < last_claim + timedelta(seconds=cd_seconds):
            rem = (last_claim + timedelta(seconds=cd_seconds)) - datetime.now()
            return await ctx.send(f"❌ You already claimed your daily! Try again in **{int(rem.total_seconds()//3600)}h {int((rem.total_seconds()%3600)//60)}m**.")

        amount = random.randint(15000, 35000)
        inventory = await db.get_inventory(user_id)
        if "VIP Pass" in inventory: amount = int(amount * 1.75)
        await db.update_balance(user_id, amount)
        await db.set_cooldown(user_id, "daily", datetime.now())
        await db.update_quest_progress(user_id, "daily")
        await ctx.send(f"🎁 You claimed your daily reward of **{amount:,}** {CURRENCY_NAME}!")

    @commands.command(name="work")
    async def work_cmd(self, ctx):
        """Work to earn some paradoxals safely."""
        user_id = str(ctx.author.id)
        last_work = await db.get_cooldown(user_id, "work")
        cd = COMMAND_COOLDOWNS["work"]
        if last_work and datetime.now() < last_work + timedelta(seconds=cd):
            rem = (last_work + timedelta(seconds=cd)) - datetime.now()
            return await ctx.send(f"⏳ You are tired! Rest for **{int(rem.total_seconds())}s**.")

        amount = random.randint(1000, 5000)
        inventory = await db.get_inventory(user_id)
        if "VIP Pass" in inventory: amount = int(amount * 1.25)
        jobs = ["Quantum Developer", "Void Designer", "Reality Scripter", "Timeline Moderator", "Paradox Artist"]
        job = random.choice(jobs)
        await db.update_balance(user_id, amount)
        await db.set_cooldown(user_id, "work", datetime.now())
        await db.update_quest_progress(user_id, "work")
        await ctx.send(f"💼 You worked as a **{job}** and earned **{amount:,}** {CURRENCY_NAME}!")

    @commands.command(name="give", aliases=["pay", "transfer"])
    async def give_cmd(self, ctx, member: discord.Member, amount: str):
        """Transfer paradoxy to another user."""
        if member.id == ctx.author.id or member.bot: return await ctx.send("❌ Invalid recipient.")
        user_id = str(ctx.author.id)
        wallet = await db.get_balance(user_id)
        if amount.lower() == "all": amount = wallet
        else:
            try: amount = int(amount)
            except: return await ctx.send("❌ Please provide a valid number.")
        if amount <= 0 or amount > wallet: return await ctx.send("❌ Invalid amount.")
        await db.update_balance(user_id, -amount)
        await db.update_balance(str(member.id), amount)
        await ctx.send(f"💸 {ctx.author.mention} transferred **{amount:,}** {CURRENCY_NAME} to {member.mention}!")

    @commands.command(name="shop")
    async def shop_cmd(self, ctx):
        """Browse shop items."""
        embed = discord.Embed(title="🛒 Paradox Shop", color=0x2ECC71)
        for name, data in SHOP_ITEMS.items():
            embed.add_field(name=f"{name} — {data['price']:,} {CURRENCY_NAME}", value=data["desc"], inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="buy")
    async def buy_cmd(self, ctx, *, item_name: str):
        """Purchase a shop item."""
        search = next((name for name in SHOP_ITEMS if name.lower() == item_name.strip().lower()), None)
        if not search: return await ctx.send("❌ Item not found.")
        user_id = str(ctx.author.id)
        inventory = await db.get_inventory(user_id)
        if search in inventory: return await ctx.send(f"❌ You already own **{search}**.")
        price = SHOP_ITEMS[search]["price"]
        wallet = await db.get_balance(user_id)
        if wallet < price: return await ctx.send(f"❌ Not enough funds.")
        await db.update_balance(user_id, -price)
        await db.add_item(user_id, search)
        await ctx.send(f"✅ You purchased **{search}** for **{price:,}** {CURRENCY_NAME}!")

    @commands.command(name="inventory", aliases=["inv"])
    async def inventory_cmd(self, ctx, member: discord.Member = None):
        """View owned items."""
        member = member or ctx.author
        inventory = await db.get_inventory(str(member.id))
        if not inventory: return await ctx.send(f"{member.display_name} has no items.")
        item_counts = {}
        for item in inventory: item_counts[item] = item_counts.get(item, 0) + 1
        embed = discord.Embed(title=f"🧾 {member.display_name}'s Inventory", color=0x9B59B6)
        for item, count in item_counts.items():
            embed.add_field(name=item, value=f"Quantity: {count}" if count > 1 else "Owned", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="leaderboard", aliases=["lb", "rich", "top"])
    async def leaderboard_cmd(self, ctx):
        """View the richest users."""
        lb_data = await db.get_leaderboard(10)
        if not lb_data: return await ctx.send("ℹ️ No data available.")
        embed = discord.Embed(title=f"🏆 Wealth Leaderboard", color=0xF1C40F)
        desc = ""
        for i, user_doc in enumerate(lb_data, 1):
            uid = int(user_doc["_id"])
            user = self.bot.get_user(uid) or await self.bot.fetch_user(uid)
            desc += f"{i}. **{user.name if user else uid}** — {user_doc['total']:,} {CURRENCY_NAME}\n"
        embed.description = desc
        await ctx.send(embed=embed)

    @commands.command(name="resetcd")
    @commands.is_owner()
    async def reset_cooldowns(self, ctx, member: discord.Member = None):
        """Reset command cooldowns for a user. Owner only."""
        target = member or ctx.author
        await db.reset_cooldowns(str(target.id))
        await ctx.send(f"✅ Cooldowns reset for **{target.display_name}**.")

    @commands.command(name="reseteco")
    @commands.is_owner()
    async def reset_economy(self, ctx, member: discord.Member = None):
        """Reset economy data for a user. Owner only."""
        if not member:
            return await ctx.send("⚠️ Specify a member to reset.")
        await db.reset_user_economy(str(member.id))
        await ctx.send(f"💥 Economy data for **{member.display_name}** has been wiped!")

async def setup(bot):
    await bot.add_cog(Economy(bot))
