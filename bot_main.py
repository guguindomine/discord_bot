import discord
from discord.ext import commands
import os
import asyncio
from dotenv import load_dotenv
from bot_functions import load_config
from bot_database import db

# Load environment variables
load_dotenv()

# ──────────────────────────────────────────────
#  BOT INITIALIZATION
# ──────────────────────────────────────────────

# Setup configuration and credentials
config = load_config()
TOKEN = os.getenv("DISCORD_TOKEN")
PREFIX = os.environ.get("PREFIX") or config.get("PREFIX", "!")

# Set intents (Member and Message Content are essential)
intents = discord.Intents.all() 
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

@bot.event
async def on_ready():
    """Triggered when the bot is fully connected and ready."""
    print(f"✅ Logged in as: {bot.user.name} (ID: {bot.user.id})")
    print(f"📡 Guilds: {len(bot.guilds)}")
    print(f"🛠️ Prefix: {PREFIX}")
    print("🚀 All systems online and cogs initialized!")
    
    # Optional: Set bot presence
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{PREFIX}help paradox")
    await bot.change_presence(activity=activity)

async def main():
    """Main entry point for the bot."""
    # Initialize Database
    mongo_uri = os.getenv("MONGO_URI")
    if mongo_uri:
        db.setup(mongo_uri)
    else:
        print("⚠️ Warning: MONGO_URI not found. Database features will be disabled.")

    async with bot:
        # Load all extensions from the cogs directory
        cogs_dir = './cogs'
        if not os.path.exists(cogs_dir):
            os.makedirs(cogs_dir)
            
        print("📂 Loading Cogs...")
        for filename in os.listdir(cogs_dir):
            if filename.endswith('.py'):
                try:
                    await bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f"  └─ 📦 {filename} loaded successfully.")
                except Exception as e:
                    print(f"  └─ ❌ Failed to load {filename}: {e}")
        
        # Start the bot
        if TOKEN:
            await bot.start(TOKEN)
        else:
            print("❌ Error: DISCORD_TOKEN not found in environment variables.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot process interrupted. Shutting down gracefully...")
    except Exception as e:
        print(f"💥 Critical Error: {e}")
