import discord
from discord.ext import commands
import sqlite3

database = sqlite3.connect("database.db")
cursor = database.cursor()

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Databases is ready!")

    @commands.command()
    async def reset_database(self, ctx):
        # Setting it to only work for Eatdatpizza for now
        print(ctx.author)
        if ctx.author.id != 357657793215332357:
            return

        database.execute("DROP TABLE IF EXISTS availability")
        database.execute("""CREATE TABLE IF NOT EXISTS availability(
                         USERID INTEGER,
                         AVAILABILITYDATE TEXT,
                         StartTime TEXT,
                         EndTime TEXT,
                         RECURRING TEXT
                         )""")

        await ctx.send("Reset the availability table")

async def setup(bot):
    await bot.add_cog(Database(bot))