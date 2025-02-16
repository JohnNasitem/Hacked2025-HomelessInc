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

TOKEN = os.getenv("BOT_TOKEN")
intents = discord.Intents.default()
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

