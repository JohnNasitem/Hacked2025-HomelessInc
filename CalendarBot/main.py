import asyncio
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from cogs.availabilities import db_clean_up_old
from cogs.database import create_missing_tables
from cogs.events import send_reminders

load_dotenv()

class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        print("")
        super().__init__(*args, **kwargs)

    async def on_ready(self):
        print(f'Logged in as {self.user}')

        # Sync slash commands
        try:
            synced_commands = await self.tree.sync()
            print(f"Synced {len(synced_commands)} commands")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

        # Create any missing database tables
        try:
            create_missing_tables()
        except Exception as ex:
            print(f"Couldn't create missing tables: {ex}")

        # Start hourly task
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
            try:
                db_clean_up_old()
                print("Cleaned up old availabilities")
            except Exception as ex:
                print(f"Couldn't clean up availabilities\n{ex}")

            try:
                await send_reminders(self)
            except Exception as ex:
                print(f"Couldn't send reminders: {ex}")

            # Delay an hour
            await asyncio.sleep(3600)

TOKEN = os.getenv("BOT_TOKEN")
intents = discord.Intents.all()
intents.message_content = True
bot = Client(command_prefix="!", intents=intents)

async def load():
    """
    Load cogs
    """
    cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            await bot.load_extension(f'cogs.{filename[:-3]}')

async def main():
    """
    Main
    """
    print("Loading cogs...")
    await load()
    print("Cogs loaded!")
    await bot.start(TOKEN)

asyncio.run(main())
