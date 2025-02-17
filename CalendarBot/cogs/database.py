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
        #if ctx.author.id != 357657793215332357:
        #    return

        status = "Attempting to reset tables..."

        try:
            reset_availability()

            status += "\nReset the availability table"

            database.execute("DROP TABLE IF EXISTS event")
            database.execute("""CREATE TABLE IF NOT EXISTS event(
                             ID INTEGER PRIMARY KEY, 
                             CreatorID INTEGER,
                             Creator TEXT,
                             Name TEXT NOT NULL,
                             Description TEXT,
                             StartTime DATETIME,
                             EndTime DATETIME,
                             Status TEXT,
                             ChannelID INTEGER
                             )""")

            status += "\nReset the event table"

            database.execute("DROP TABLE IF EXISTS rsvp")
            database.execute("""CREATE TABLE IF NOT EXISTS rsvp(
                             EventID INTEGER,
                             UserID INTEGER,
                             User TEXT,
                             Response TEXT,
                             PRIMARY KEY(EventID, UserID),
                             FOREIGN KEY(EventID) REFERENCES event(ID) ON DELETE CASCADE
                             )""")
            status += "\nReset the rsvp table"

            status += "\nReset was a success"
        except Exception as ex:
            status += f"\nProblem occurred: {ex}"

        await ctx.send(status)

async def setup(bot):
    await bot.add_cog(Database(bot))

def reset_availability():
    """
    Reset availability table
    """
    database.execute("DROP TABLE IF EXISTS availability")
    database.execute("""CREATE TABLE IF NOT EXISTS availability(
                                 USERID INTEGER,
                                 AVAILABILITYDATE TEXT,
                                 StartTime TEXT,
                                 EndTime TEXT,
                                 RECURRING TEXT
                                 )""")