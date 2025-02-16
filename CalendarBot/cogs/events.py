import discord
from discord.ext import commands

import sqlite3
from datetime import datetime

database = sqlite3.connect("database.db")
cursor = database.cursor()
database.execute("DROP TABLE IF EXISTS event")
# create event table
database.execute("""CREATE TABLE IF NOT EXISTS event(
                 ID INTEGER PRIMARY KEY, 
                 CreatorID INTEGER,
                 Creator TEXT,
                 Name TEXT NOT NULL,
                 Description TEXT,
                 StartTime DATETIME,
                 EndTime DATETIME,
                 Status TEXT
                 )""")

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online!")

    # command to create an event
    @commands.command()
    async def createevent(self, ctx, *, message: str):
        parts = message.strip().split(", ") # FIXME: need a more robust way to split parts properly

        if len(parts) != 4:
            await ctx.send("Incorrect number of arguments, should be 4 ")
            return

        name, description, start_time, end_time = parts
        creator_id = ctx.message.author.id
        creator = ctx.message.author.name

        datetime_format = "%Y-%m-%d %H:%M" # no seconds
        try:
            # check start_time and end_time are in correct date_time format
            start_time = datetime.strptime(start_time, datetime_format)
            end_time = datetime.strptime(end_time, datetime_format)
            if start_time > end_time:
                await ctx.send("Start time must be before end time!")
                return
        except ValueError:
            await ctx.send(f"Incorrect datetime format, should be {datetime_format}, like 2025-02-14 15:30, or incorrect datetime values inputted")
            return

        await ctx.send(f"User: {ctx.message.author} is cool") # test line

        # set status based on current datetime compared to event datetimes
        status_options = ["Pending", "Ongoing", "Completed"] # FIXME Completed events should be deleted; add cancelled events
        current_datetime = datetime.now()
        if current_datetime < start_time:
            status = status_options[0]
        elif current_datetime < end_time:
            status = status_options[1]
        else:
            status = status_options[2]

        # insert values into query
        query = "INSERT INTO event VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
        cursor.execute(query, (ctx.message.id, creator_id, creator, name, description, start_time, end_time, status))
        database.commit()

        # for debugging purposes
        await ctx.send(f"Message saved! We have stored: {ctx.message.id}, {creator_id}, {creator}, {name}, {description}, {start_time}, {end_time}, {status}")

        # confirmation message
        await ctx.send(f"Event has been saved! {creator} has created event {name} ({status}) starting from {start_time} to {end_time}.")

    @commands.command()
    async def viewevents(self, ctx):
        results = get_events() # fetch query results

        if results:
            await ctx.send("Here are the created events: ")
            for idx, result in enumerate(results, 1): # parse through each row of the result and output it
                await ctx.send(f"{idx}. ID: {result[0]}, Creator: {result[2]}, Name: {result[3]}, Description: {result[4]}, Start Time: {result[5]}, End Time: {result[6]}, Status: {result[7]}")
        else:
            await ctx.send("No events found!")
            return


async def setup(bot):
    await bot.add_cog(Events(bot))


# get_events is a helper function for the command viewevents
def get_events():
    print("In events function") # testing
    query = "SELECT * FROM event"
    cursor.execute(query)
    result = cursor.fetchall()
    return result





