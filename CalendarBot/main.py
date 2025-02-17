import asyncio
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands
from cogs.availabilities import db_clean_up_old

load_dotenv()

class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print(f'Logged in as {self.user}')

        # sync slash commands
        try:
            synced_commands = await self.tree.sync()
            print(f"Synced {len(synced_commands)} commands")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

        self.loop.create_task(self.hourly_task())

    async def hourly_task(self):
        """
        Runs every hour
        :return: None
        """
        await self.wait_until_ready()
        while not self.is_closed():
            print("Running hourly task")
            # Clean the old expired schedules
            db_clean_up_old()
            print("Cleaned up old availabilities")
            # Wait for an hour (3600 seconds) before running again
            await asyncio.sleep(3600)

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

