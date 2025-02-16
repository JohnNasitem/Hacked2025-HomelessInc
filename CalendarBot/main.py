import asyncio
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands

load_dotenv()

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

        # sync slash commands
        try:
            guildID = discord.Object(id=1340369941001539636)
            synced_commands = await bot.tree.sync()
            print(f"Synced {len(synced_commands)} commands")
        except Exception as e:
            print(f"Failed to sync commands: {e}")


TOKEN = os.getenv("BOT_TOKEN")
intents = discord.Intents.all()
intents.message_content = True  # Enable message content intent
bot = Client(command_prefix="!", intents=intents)

async def load():
    cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            await bot.load_extension(f'cogs.{filename[:-3]}')

async def main():
    await load()
    await bot.start(TOKEN)

asyncio.run(main())