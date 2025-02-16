import discord
from discord.ext import commands

import sqlite3
from datetime import datetime

database = sqlite3.connect("database.db")
cursor = database.cursor()
database.execute("DROP TABLE IF EXISTS event")
database.execute("DROP TABLE IF EXISTS messages")
# create event table
database.execute("""CREATE TABLE IF NOT EXISTS event(
                 ID INTEGER PRIMARY KEY, 
                 Name TEXT NOT NULL,
                 Description TEXT,
                 StartTime DATETIME,
                 EndTime DATETIME,
                 STATUS TEXT
                 )""")

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online!")

    @commands.command()
    async def event(self, ctx, *, message: str):
        parts = message.strip().split(", ") # FIXME: need a more robust way to split parts properly

        if len(parts) != 4:
            await ctx.send("Incorrect number of arguments, should be 4 ")
            return

        name, description, start_time, end_time = parts
        print(start_time)
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

        await ctx.send(f"User ID: {ctx.message.author.id}") # test line

        # set status based on current datetime compared to event datetimes
        status_options = ["Pending", "Ongoing", "Completed"]
        current_datetime = datetime.now()
        if current_datetime < start_time:
            status = status_options[0]
        elif current_datetime < end_time:
            status = status_options[1]
        else:
            status = status_options[2]

        # insert values into query
        query = "INSERT INTO event VALUES (?, ?, ?, ?, ?, ?)"
        cursor.execute(query, (ctx.message.id, name, description, start_time, end_time, status))
        database.commit()

        # for debugging purposes
        await ctx.send(f"Message saved! We have stored: {ctx.message.id}, {name}, {description}, {start_time}, {end_time}, {status}")

async def setup(bot):
    await bot.add_cog(Events(bot))




