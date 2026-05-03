import discord
from discord.ext import commands
import random
import asyncio
from bot_functions import load_config
from bot_database import db
from bot_economy_data import CURRENCY_NAME, RiggedOdds
from bot_ui_games import BlackjackView, PokerGame

class Casino(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="poker")
    async def poker_cmd(self, ctx, buyin: int = 5000):
        """Start a poker table and keep the game board at the bottom of the chat."""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        if balance < buyin:
            return await ctx.send(f"❌ You need at least **{buyin:,}** {CURRENCY_NAME} to start a table.")
        
        await db.update_balance(user_id, -buyin)
        game = PokerGame(ctx, buyin, buyin * 10)
        game.add_player(user_id, buyin)
        
        # This will send the first message
        await game.update_embed()

    @commands.command(name="bj", aliases=["blackjack"])
    async def bj_cmd(self, ctx, amount: str):
        """Start a round of blackjack."""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        if amount.lower() == "all": bet = balance
        else:
            try: bet = int(amount)
            except: return await ctx.send("❌ Valid bet required.")
        if bet <= 0 or bet > balance: return await ctx.send("❌ Invalid bet.")

        inventory = await db.get_inventory(user_id)
        win_chance = await RiggedOdds.calculate_win_chance("bj", inventory)
        
        await db.update_balance(user_id, -bet)
        view = BlackjackView(ctx, ctx.author.id, bet)
        view.win_chance = win_chance
        await ctx.send(embed=view.create_embed(), view=view)

    @commands.command(name="cf", aliases=["coinflip", "flip"])
    async def coinflip_cmd(self, ctx, bet: str, choice: str = "heads"):
        """Flip a coin. Usage: !cf <bet> [heads/tails]"""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        if bet.lower() == "all": bet_amount = balance
        else:
            try: bet_amount = int(bet)
            except: return await ctx.send("❌ Valid bet required.")
        if bet_amount <= 0 or bet_amount > balance: return await ctx.send("❌ Invalid bet.")

        choice = choice.lower()
        if choice not in ["heads", "tails", "h", "t"]: return await ctx.send("❌ Heads or tails?")
        
        msg = await ctx.send("🪙 **Flipping...**")
        await asyncio.sleep(2)

        inventory = await db.get_inventory(user_id)
        win_chance = await RiggedOdds.calculate_win_chance("cf", inventory)
        win = random.random() < win_chance
        result = choice if win else ("tails" if choice in ["heads", "h"] else "heads")
        
        await db.update_quest_progress(user_id, "gamble")
        if win:
            await db.update_balance(user_id, bet_amount)
            await msg.edit(content=None, embed=discord.Embed(title="🪙 Coinflip WIN", description=f"Won **{bet_amount:,}** {CURRENCY_NAME}!", color=0x2ECC71))
        else:
            await db.update_balance(user_id, -bet_amount)
            await msg.edit(content=None, embed=discord.Embed(title="🪙 Coinflip LOSE", description=f"Lost **{bet_amount:,}** {CURRENCY_NAME}.", color=0xE74C3C))

    @commands.command(name="slots")
    async def slots_cmd(self, ctx, bet: int):
        """Spin the slots."""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        if bet <= 0 or bet > balance: return await ctx.send("❌ Invalid bet.")
        
        symbols = ["🍒", "🍋", "🍇", "💎", "⭐", "🔔"]
        msg = await ctx.send("🎰 **Spinning...**")
        await asyncio.sleep(1.5)
        
        inventory = await db.get_inventory(user_id)
        win_chance = await RiggedOdds.calculate_win_chance("slots_normal", inventory)
        win = random.random() < win_chance
        
        if win:
            res = [random.choice(symbols)] * 3
            payout = bet * 5
            await db.update_balance(user_id, payout)
            emb = discord.Embed(title="🎰 Slots WIN", description=f"**[ {' | '.join(res)} ]**\nWon **{payout:,}** {CURRENCY_NAME}!", color=0x2ECC71)
        else:
            res = [random.choice(symbols) for _ in range(3)]
            while res[0] == res[1] == res[2]: res = [random.choice(symbols) for _ in range(3)]
            await db.update_balance(user_id, -bet)
            emb = discord.Embed(title="🎰 Slots LOSE", description=f"**[ {' | '.join(res)} ]**\nLost **{bet:,}** {CURRENCY_NAME}.", color=0xE74C3C)
        
        await db.update_quest_progress(user_id, "gamble")
        await msg.edit(content=None, embed=emb)

    @commands.command(name="roulette")
    async def roulette_cmd(self, ctx, bet: int, choice: str):
        """Roulette: red, black, green, or a number 0-36."""
        user_id = str(ctx.author.id)
        balance = await db.get_balance(user_id)
        if bet <= 0 or bet > balance: return await ctx.send("❌ Invalid bet.")
        
        colors = {"red": [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36], "black": [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35], "green": [0]}
        result_num = random.randint(0, 36)
        result_color = "green" if result_num == 0 else ("red" if result_num in colors["red"] else "black")
        
        win = False
        payout = 0
        if choice.isdigit():
            if int(choice) == result_num: win = True; payout = bet * 35
        elif choice.lower() in colors:
            if choice.lower() == result_color: win = True; payout = bet if choice.lower() != "green" else bet * 17
        else: return await ctx.send("❌ Invalid choice.")
        
        await db.update_quest_progress(user_id, "gamble")
        if win:
            await db.update_balance(user_id, payout)
            await ctx.send(f"🎰 Roulette: **{result_num} ({result_color})**. You won **{payout:,}** {CURRENCY_NAME}!")
        else:
            await db.update_balance(user_id, -bet)
            await ctx.send(f"🎰 Roulette: **{result_num} ({result_color})**. You lost **{bet:,}** {CURRENCY_NAME}.")

async def setup(bot):
    await bot.add_cog(Casino(bot))
