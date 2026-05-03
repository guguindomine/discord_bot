import discord
import random
import asyncio
from datetime import datetime, timedelta
from bot_database import db
from bot_functions import load_config, humanize_number
from bot_economy_data import CURRENCY_NAME, HEIST_TARGETS

# ──────────────────────────────────────────────
#  BLACKJACK SYSTEM
# ──────────────────────────────────────────────

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, user_id, bet):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user_id = user_id
        self.initial_bet = bet
        self.deck = self.create_deck()
        self.hands = [[self.deck.pop(), self.deck.pop()]]
        self.current_hand_index = 0
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.bets = [bet]
        self.is_over = False
        self.win_chance = 0.48 

    async def on_timeout(self):
        if not self.is_over:
            self.is_over = True
            for item in self.children:
                item.disabled = True
            try:
                embed = self.create_embed()
                embed.title = "⏰ Blackjack Timeout"
                embed.description = "You took too long! Hand forfeited."
                await self.ctx.send(content=f"<@{self.user_id}>", embed=embed)
            except: pass

    def create_deck(self):
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        deck = [f"{r}{s}" for s in suits for r in ranks]
        random.shuffle(deck)
        return deck

    def get_score(self, hand):
        score = 0
        aces = 0
        for card in hand:
            rank = card[:-1]
            if rank in ["J", "Q", "K"]: score += 10
            elif rank == "A": aces += 1; score += 11
            else: score += int(rank)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def can_split(self):
        if len(self.hands) >= 2: return False
        hand = self.hands[self.current_hand_index]
        if len(hand) != 2: return False
        return self.get_card_value(hand[0]) == self.get_card_value(hand[1])

    def get_card_value(self, card):
        rank = card[:-1]
        if rank in ["J", "Q", "K"]: return 10
        if rank == "A": return 11
        return int(rank)

    def create_embed(self, revealed=False):
        embed = discord.Embed(title="🃏 Paradox Blackjack", color=0x34495E)
        d_cards = " ".join(self.dealer_hand) if revealed else f"{self.dealer_hand[0]} ❓"
        d_score = self.get_score(self.dealer_hand) if revealed else "?"
        embed.add_field(name=f"Dealer: {d_score}", value=f"`{d_cards}`", inline=False)
        for i, hand in enumerate(self.hands):
            prefix = "▶️ " if i == self.current_hand_index and not revealed else ""
            status = f" (Hand {i+1})" if len(self.hands) > 1 else ""
            embed.add_field(name=f"{prefix}You{status}: {self.get_score(hand)}", value=f"`{' '.join(hand)}`", inline=True)
        embed.set_footer(text=f"Total Bet: {sum(self.bets):,} {CURRENCY_NAME}")
        return embed

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.primary)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        self.hands[self.current_hand_index].append(self.deck.pop())
        if self.get_score(self.hands[self.current_hand_index]) > 21:
            await self.next_hand_or_finish(interaction)
        else:
            await interaction.response.edit_message(embed=self.create_embed())

    @discord.ui.button(label="Double", style=discord.ButtonStyle.success)
    async def double(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        bet = self.bets[self.current_hand_index]
        bal = await db.get_balance(str(self.user_id))
        if bal < bet: return await interaction.response.send_message("Not enough funds!", ephemeral=True)
        await db.update_balance(str(self.user_id), -bet)
        self.bets[self.current_hand_index] *= 2
        self.hands[self.current_hand_index].append(self.deck.pop())
        await self.next_hand_or_finish(interaction)

    @discord.ui.button(label="Split", style=discord.ButtonStyle.secondary, emoji="✂️")
    async def split(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id or not self.can_split(): return
        bal = await db.get_balance(str(self.user_id))
        if bal < self.initial_bet: return await interaction.response.send_message("Not enough funds!", ephemeral=True)
        await db.update_balance(str(self.user_id), -self.initial_bet)
        card = self.hands[self.current_hand_index].pop()
        self.hands[self.current_hand_index].append(self.deck.pop())
        self.hands.append([card, self.deck.pop()])
        self.bets.append(self.initial_bet)
        await interaction.response.edit_message(embed=self.create_embed(), view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.danger)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id: return
        await self.next_hand_or_finish(interaction)

    async def next_hand_or_finish(self, interaction: discord.Interaction):
        self.current_hand_index += 1
        if self.current_hand_index < len(self.hands):
            await interaction.response.edit_message(embed=self.create_embed())
        else:
            await self.finish_game(interaction)

    async def finish_game(self, interaction: discord.Interaction):
        self.is_over = True
        self.stop()
        while self.get_score(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
        
        d_score = self.get_score(self.dealer_hand)
        results = []
        for i, hand in enumerate(self.hands):
            bet = self.bets[i]
            p_score = self.get_score(hand)
            if p_score > 21: results.append(f"Hand {i+1}: Bust! Lost {bet:,}")
            elif d_score > 21 or p_score > d_score:
                await db.update_balance(str(self.user_id), bet * 2)
                results.append(f"Hand {i+1}: Win! Gained {bet:,}")
            elif p_score == d_score:
                await db.update_balance(str(self.user_id), bet)
                results.append(f"Hand {i+1}: Push!")
            else: results.append(f"Hand {i+1}: Lose! Lost {bet:,}")
        
        embed = self.create_embed(revealed=True)
        embed.description = "\n".join(results)
        await interaction.response.edit_message(embed=embed, view=None)

# ── POKER SYSTEM ──

class PokerGame:
    def __init__(self, ctx, min_buyin, max_buyin):
        self.ctx = ctx
        self.min_buyin = min_buyin
        self.max_buyin = max_buyin
        self.players = {}
        self.pot = 0
        self.community_cards = []
        self.deck = self.create_deck()
        self.phase = "waiting" 
        self.current_bet = 0
        self.message = None
        self.active_player_index = 0
        self.player_order = []

    def create_deck(self):
        suits = ["♠", "♥", "♦", "♣"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        deck = [f"{r}{s}" for s in suits for r in ranks]
        random.shuffle(deck)
        return deck

    def add_player(self, user_id, amount):
        if user_id in self.players: return False
        self.players[user_id] = {"chips": amount, "bet": 0, "folded": False, "cards": []}
        return True

    def start_game(self):
        if len(self.players) < 2: return False
        self.phase = "pre-flop"
        self.player_order = list(self.players.keys())
        for uid in self.player_order:
            self.players[uid]["cards"] = [self.deck.pop(), self.deck.pop()]
        return True

    async def update_embed(self, delete_old=False):
        embed = discord.Embed(title="🃏 Paradox Poker", color=0x34495E)
        desc = f"**Pot:** {self.pot:,} {CURRENCY_NAME}\n**Community:** {' '.join(self.community_cards) or 'None'}\n\n"
        for uid in self.player_order:
            p = self.players[uid]
            status = "🔴 FOLDED" if p["folded"] else ("🟢 TURN" if self.player_order[self.active_player_index] == uid else "⚪ WAITING")
            desc += f"<@{uid}>: {p['chips']:,} {CURRENCY_NAME} | {status}\n"
        embed.description = desc
        
        # Always re-send to keep it at the bottom if requested
        if delete_old and self.message:
            try: await self.message.delete()
            except: pass
            self.message = await self.ctx.send(embed=embed, view=PokerView(self))
        else:
            if self.message:
                await self.message.edit(embed=embed, view=PokerView(self))
            else:
                self.message = await self.ctx.send(embed=embed, view=PokerView(self))

class PokerView(discord.ui.View):
    def __init__(self, game):
        super().__init__(timeout=60)
        self.game = game

    @discord.ui.button(label="Fold", style=discord.ButtonStyle.red)
    async def fold(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid != self.game.player_order[self.game.active_player_index]: 
            return await interaction.response.send_message("Not your turn!", ephemeral=True)
        self.game.players[uid]["folded"] = True
        # Move to next turn and refresh message at bottom
        self.game.active_player_index = (self.game.active_player_index + 1) % len(self.game.player_order)
        await interaction.response.defer()
        await self.game.update_embed(delete_old=True)

    @discord.ui.button(label="Call/Check", style=discord.ButtonStyle.primary)
    async def call(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        if uid != self.game.player_order[self.game.active_player_index]: 
            return await interaction.response.send_message("Not your turn!", ephemeral=True)
        # Next turn and refresh at bottom
        self.game.active_player_index = (self.game.active_player_index + 1) % len(self.game.player_order)
        await interaction.response.defer()
        await self.game.update_embed(delete_old=True)

# ── HEIST SYSTEM ──

class HeistTargetView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user_id = ctx.author.id

    @discord.ui.button(label="Jewelry Store", style=discord.ButtonStyle.primary)
    async def jewelry(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start(interaction, "jewelry")

    @discord.ui.button(label="Main Bank", style=discord.ButtonStyle.primary)
    async def bank(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start(interaction, "bank")

    @discord.ui.button(label="Armored Truck", style=discord.ButtonStyle.primary)
    async def truck(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start(interaction, "truck")

    async def start(self, interaction, target):
        if interaction.user.id != self.user_id: return
        view = CrimeDifficultyView(self.ctx, target)
        embed = discord.Embed(title="🏦 Strategic Heist", description=f"Target: **{target.title()}**. Choose difficulty:", color=0x34495E)
        await interaction.response.edit_message(embed=embed, view=view)

class CrimeDifficultyView(discord.ui.View):
    def __init__(self, ctx, target: str):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.user_id = ctx.author.id
        self.target = target
        self.selection_made = False

    @discord.ui.button(label="Easy", style=discord.ButtonStyle.success)
    async def easy(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_minigame(interaction, "easy")

    @discord.ui.button(label="Normal", style=discord.ButtonStyle.primary)
    async def normal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_minigame(interaction, "normal")

    @discord.ui.button(label="Hard", style=discord.ButtonStyle.danger)
    async def hard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.start_minigame(interaction, "hard")

    async def start_minigame(self, interaction: discord.Interaction, difficulty: str):
        if interaction.user.id != self.user_id or self.selection_made: return
        self.selection_made = True
        
        game_type = random.choice(["lockpick", "circuit", "safe"])
        if game_type == "lockpick":
            await self.lockpick_game(interaction, difficulty)
        elif game_type == "circuit":
            await self.circuit_game(interaction, difficulty)
        else:
            await self.safe_game(interaction, difficulty)

    async def lockpick_game(self, interaction: discord.Interaction, diff: str):
        zone_count = 3 if diff == "easy" else 4 if diff == "normal" else 5
        correct = random.randint(1, zone_count)
        attempts = 3 if diff == "easy" else 2 if diff == "normal" else 1
        
        view = LockpickMinigameView(self.ctx, self.user_id, self.target, diff, correct, attempts, zone_count)
        embed = discord.Embed(title="🔓 Lockpicking", description=f"Find the correct zone (1-{zone_count}). Attempts: {attempts}", color=0xF1C40F)
        await interaction.response.edit_message(embed=embed, view=view)

    async def circuit_game(self, interaction: discord.Interaction, diff: str):
        num_colors = 3 if diff == "easy" else 4 if diff == "normal" else 5
        all_colors = ["Red", "Blue", "Green", "Yellow", "Purple"][:4]
        target_seq = [random.choice(all_colors) for _ in range(num_colors)]
        
        embed = discord.Embed(title="⚡ Memorize the Sequence!", description="**" + " → ".join(target_seq) + "**", color=0x3498DB)
        await interaction.response.edit_message(embed=embed, view=None)
        await asyncio.sleep(4 if diff == "easy" else 3)
        
        view = CircuitMinigameView(self.ctx, self.user_id, self.target, diff, target_seq)
        embed = discord.Embed(title="⚡ Cut the Wires!", description=f"Repeat the sequence! Progress: {'⬜' * num_colors}", color=0x3498DB)
        await interaction.edit_original_response(embed=embed, view=view)

    async def safe_game(self, interaction: discord.Interaction, diff: str):
        limit = 5 if diff == "easy" else 10 if diff == "normal" else 15
        correct = random.randint(1, limit)
        attempts = 3 if diff == "easy" else 2 if diff == "normal" else 1
        
        view = SafeMinigameView(self.ctx, self.user_id, self.target, diff, correct, attempts, limit)
        embed = discord.Embed(title="🔐 Safe Cracking", description=f"Guess the number (1-{limit}). Attempts: {attempts}", color=0xE74C3C)
        await interaction.response.edit_message(embed=embed, view=view)

# ── MINIGAME VIEWS ──

class LockpickMinigameView(discord.ui.View):
    def __init__(self, ctx, user_id, target, diff, correct, attempts, zones):
        super().__init__(timeout=60)
        self.ctx, self.user_id, self.target, self.diff = ctx, user_id, target, diff
        self.correct, self.attempts = correct, attempts
        for i in range(1, zones + 1):
            btn = discord.ui.Button(label=f"Zone {i}", style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_callback(self, num):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id: return
            if num == self.correct:
                await finish_heist(interaction, self.target, self.diff, True)
            else:
                self.attempts -= 1
                if self.attempts <= 0:
                    await finish_heist(interaction, self.target, self.diff, False)
                else:
                    embed = interaction.message.embeds[0]
                    embed.description = f"❌ Wrong zone! Try again. Attempts left: {self.attempts}"
                    await interaction.response.edit_message(embed=embed)
        return callback

class CircuitMinigameView(discord.ui.View):
    def __init__(self, ctx, user_id, target, diff, target_seq):
        super().__init__(timeout=60)
        self.ctx, self.user_id, self.target, self.diff = ctx, user_id, target, diff
        self.target_seq = target_seq
        self.user_seq = []
        for color in ["Red", "Blue", "Green", "Yellow"]:
            btn = discord.ui.Button(label=color, style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(color)
            self.add_item(btn)

    def make_callback(self, color):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id: return
            self.user_seq.append(color)
            idx = len(self.user_seq) - 1
            if self.user_seq[idx] != self.target_seq[idx]:
                await finish_heist(interaction, self.target, self.diff, False)
            elif len(self.user_seq) == len(self.target_seq):
                await finish_heist(interaction, self.target, self.diff, True)
            else:
                embed = interaction.message.embeds[0]
                progress = "🟩" * len(self.user_seq) + "⬜" * (len(self.target_seq) - len(self.user_seq))
                embed.description = f"✅ Correct wire! Keep going...\nProgress: {progress}"
                await interaction.response.edit_message(embed=embed)
        return callback

class SafeMinigameView(discord.ui.View):
    def __init__(self, ctx, user_id, target, diff, correct, attempts, limit):
        super().__init__(timeout=60)
        self.ctx, self.user_id, self.target, self.diff = ctx, user_id, target, diff
        self.correct, self.attempts = correct, attempts
        for i in range(1, limit + 1):
            btn = discord.ui.Button(label=str(i), style=discord.ButtonStyle.secondary)
            btn.callback = self.make_callback(i)
            self.add_item(btn)

    def make_callback(self, num):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id: return
            if num == self.correct:
                await finish_heist(interaction, self.target, self.diff, True)
            else:
                self.attempts -= 1
                if self.attempts <= 0:
                    await finish_heist(interaction, self.target, self.diff, False)
                else:
                    embed = interaction.message.embeds[0]
                    hint = "Higher ⬆️" if self.correct > num else "Lower ⬇️"
                    embed.description = f"❌ WRONG! Hint: {hint}. Attempts left: {self.attempts}"
                    await interaction.response.edit_message(embed=embed)
        return callback

async def finish_heist(interaction, target, diff, success):
    data = HEIST_TARGETS[target][diff]
    if success:
        amt = random.randint(data[0], data[1])
        await db.update_balance(str(interaction.user.id), amt)
        embed = discord.Embed(title="💰 Heist Successful!", description=f"You escaped with **{amt:,}** {CURRENCY_NAME}!", color=0x2ECC71)
    else:
        fine = 5000 if diff == "easy" else 15000
        await db.update_balance(str(interaction.user.id), -fine)
        await db.set_cooldown(str(interaction.user.id), "jail", datetime.now() + timedelta(minutes=20))
        embed = discord.Embed(title="🚨 Heist Failed!", description=f"Busted! Fined **{fine:,}** and jailed for 20m.", color=0xE74C3C)
    await interaction.response.edit_message(embed=embed, view=None)
