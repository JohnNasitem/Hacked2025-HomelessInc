from discord.ext import commands
import sqlite3

# Database connection
database = sqlite3.connect("database.db", 10)

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Databases is ready!")

    @commands.command()
    async def reset_database(self, ctx):
        """
        Reset all database tables
        :param ctx: context
        :return: None
        """
        # Setting it to only work for Eatdatpizza for now
        if ctx.author.id != 357657793215332357:
            return

        status = "Attempting to reset tables..."

        try:
            reset_availability()

            status += "\nReset the availability table"

            reset_events()

            status += "\nReset the event table"

            reset_rsvp()

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

def reset_events():
    """
    Reset event table
    :return: None
    """
    database.execute("DROP TABLE IF EXISTS event")
    database.execute("""CREATE TABLE IF NOT EXISTS event(
                                 ID INTEGER PRIMARY KEY AUTOINCREMENT, 
                                 CreatorID INTEGER,
                                 Creator TEXT,
                                 Name TEXT NOT NULL,
                                 Description TEXT,
                                 StartTime DATETIME,
                                 EndTime DATETIME,
                                 Status TEXT,
                                 ChannelID INTEGER,
                                 AlreadyRemindedOwner INTEGER,
                                 AlreadyRemindedParticipants INTEGER,
                                 AlreadyAnnounced INTEGER,
                                 GUILDID INTEGER
                                 )""")

def reset_rsvp():
    """
    Reset rsvp table
    :return: None
    """
    database.execute("DROP TABLE IF EXISTS rsvp")
    database.execute("""CREATE TABLE IF NOT EXISTS rsvp(
                                 EventID INTEGER,
                                 UserID INTEGER,
                                 User TEXT,
                                 Response TEXT,
                                 PRIMARY KEY(EventID, UserID),
                                 FOREIGN KEY(EventID) REFERENCES event(ID) ON DELETE CASCADE
                                 )""")

def create_missing_tables():
    """
    Create any missing tables
    :return:
    """
    cursor = database.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name= ?", ("availability",))

    if not cursor.fetchone():
        print("availability was missing. Created a new one")
        reset_availability()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name= ?", ("event",))

    if not cursor.fetchone():
        print("event was missing. Created a new one")
        reset_events()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name= ?", ("rsvp",))

    if not cursor.fetchone():
        print("rsvp was missing. Created a new one")
        reset_rsvp()
    cursor.close()