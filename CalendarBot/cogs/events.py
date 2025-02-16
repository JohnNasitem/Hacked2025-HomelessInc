import discord
from discord.ext import commands
from discord import app_commands

import sqlite3
import time
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



    @app_commands.command(name="create-event", description="Creates an event")
    async def createevent(self, interaction: discord.Interaction, name: str, description: str, start_time: str, end_time: str):
        creator_id = interaction.user.id
        creator = interaction.user.name
        event_id = int(time.time() * 1000)

        datetime_format = "%Y-%m-%d %H:%M"  # no seconds
        try:
            # check start_time and end_time are in correct date_time format
            start_time = datetime.strptime(start_time, datetime_format)
            end_time = datetime.strptime(end_time, datetime_format)
            if start_time > end_time:
                await interaction.response.send_message("Start time must be before end time!")
                return
            elif start_time == end_time:
                await interaction.response.send_message("Start time and end time cannot be the same!")
                return
        except ValueError:
            await interaction.response.send_message(
                f"Incorrect datetime format, should be {datetime_format}, like 2025-02-14 15:30, or incorrect datetime values inputted")
            return

        # set status based on current datetime compared to event datetimes
        status_options = ["Pending", "Ongoing", "Cancelled"]
        current_datetime = datetime.now()
        if current_datetime < start_time:
            status = status_options[0]
        elif current_datetime < end_time:
            status = status_options[1]
        else:
            await interaction.response.send_message("Invalid event time! Cannot create event in the past.")
            return

        # insert values into query
        try:
            query = "INSERT INTO event VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(query, (event_id, creator_id, creator, name, description, start_time, end_time, status))
            database.commit()

            # confirmation message
            await interaction.response.send_message(
                f"Event has been saved! Event ID: {event_id} <@{creator_id}> has created event **{name}** ({status}) starting from **{start_time} to {end_time}**.")
        except Exception as e:
            await interaction.response.send_message(f"Database error: {str(e)}")

            # for debugging purposes
        # await interaction.response.send_message(
            # f"Message saved! We have stored: {event_id}, {creator_id}, {creator}, {name}, {description}, {start_time}, {end_time}, {status}")


    @app_commands.command(name="view-events", description="Displays all events created")
    async def viewevents(self, interaction: discord.Interaction):  # TODO: can add pagination
        # update events appropriately
        delete_past_events()
        change_to_ongoing()
        results = get_events() # fetch query results

        if results:
            event_list = ["Here are the created events: "]
            for idx, result in enumerate(results, 1):  # parse through each row of the result and display it
                event_list.append( # backticks
                    f"```"
                    f"{idx}. ID: {result[0]}\n"
                    f"   Name: {result[3]} by {result[2]}\n"
                    f"   Description: {result[4]}\n"
                    f"   Start Time: {result[5]}\n"
                    f"   End Time: {result[6]}\n"
                    f"   Status: {result[7]}"
                    f"```"
                )
            await  interaction.response.send_message("".join(event_list))
        else:
            await interaction.response.send_message("No events found!")
            return

    # edit events has the option to edit the event
    # first takes in the event id and checks if it exists
    # checks current user is creator of that event
    # then provides options to change
    @app_commands.command(name="edit-events", description="Edits an event")
    async def editevent(self, interaction: discord.Interaction, event_id: int):
        result = check_valid_event(event_id)
        if result is None:  # nothing fetched from database
            await interaction.response.send_message("No such event exists!")
            return

        if result[1] != interaction.user.id:
            await interaction.response.send_message("You are not the creator of this event. Cannot edit event.")
            return

        # await interaction.response.send_message({result})
        print("before")
        await interaction.response.send_modal(EditEventModal(event_id))
        print("yay")
    # @commands.command() # test command for followup messages
    # async def followup(self, ctx):
    #     await ctx.send("plz say something")
    #     def check(message):
    #         return message.author == ctx.author and message.channel == ctx.channel
    #     msg = await self.bot.wait_for('message', check=check)
    #     await ctx.send(f"hey {msg.author}, you said {msg.content}")


    # cancelevent command cancels an event; needs event id and requires the user who created the event
    @commands.command()
    async def cancelevent(self, ctx, *, message: str):
        await ctx.send(f"Message received: {message}. In cancelevent command") # testing

        # update events appropriately
        delete_past_events()
        change_to_ongoing()

        try:
            event_id = int(message.strip()) # convert string input into int
        except ValueError:
            await ctx.send("Invalid event ID! Please provide a valid numeric ID.")
            return

        # fetch the event from the database, if possible
        result = check_valid_event(event_id)
        if result is None: # nothing fetched from database
            await ctx.send("No such event exists!")
            return

        # check if current user is the user that created the event
        if result[1] != ctx.message.author.id:
            await ctx.send("You are not the creator of this event. Cannot cancel event.")
            return

        cancel_event(event_id)
        await ctx.send(f"Event {result[3]} has been cancelled.") # result[3] is event name


async def setup(bot):
    await bot.add_cog(Events(bot))

# helper functions for commands
# get_events gets all items from event table in database
def get_events():
    print("In events function") # testing
    query = "SELECT * FROM event"
    cursor.execute(query)
    result = cursor.fetchall()
    return result

# check_valid_event fetches event for given id
def check_valid_event(event_id):
    query = "SELECT * FROM event WHERE ID = ?"
    cursor.execute(query, (event_id,))
    result = cursor.fetchone()
    return result

# delete_event deletes the event with the provided id
def delete_event(event_id):
    query = "DELETE FROM event WHERE ID = ?"
    cursor.execute(query, (event_id,))
    database.commit()

# called in certain commands to delete any events that have past
def delete_past_events():
    current_datetime = datetime.now()
    query = "DELETE FROM event WHERE EndTime < ?"
    cursor.execute(query, (current_datetime,))
    database.commit()

# called in certain commands to update any events who should be ongoing
def change_to_ongoing():
    current_datetime = datetime.now()
    query = "UPDATE event SET Status = ? WHERE StartTime < ? AND EndTime > ?" # FIXME only when status is confirmed
    cursor.execute(query, ("Ongoing", current_datetime, current_datetime))
    database.commit()

# cancel_event cancels the event with the provided id
def cancel_event(event_id):
    query = "UPDATE event SET Status = ? WHERE ID = ?"
    cursor.execute(query, ("Cancelled", event_id))
    database.commit()

class EditEventModal(discord.ui.Modal, title="Edit Event"):
    def __init__(self, event_id: int):
        super().__init__()
        self.event_id = event_id

        # name = discord.ui.TextInput(label="Event Name", style=discord.TextStyle.short)
        # description = discord.ui.TextInput(label="Event Description", style=discord.TextStyle.paragraph)
        # start_time = discord.ui.TextInput(label="Start Time", style=discord.TextStyle.short)
        # end_time = discord.ui.TextInput(label="End Time", style=discord.TextStyle.short)
        # status = discord.ui.Select(
        #     placeholder="Select event status",
        #     options=[
        #         discord.SelectOption(label="Pending", value="Pending"),
        #         discord.SelectOption(label="Confirmed", value="Confirmed"),
        #         discord.SelectOption(label="Cancelled", value="Cancelled"),
        #     ],
        # )

        self.name = discord.ui.TextInput(label="Event Name", style=discord.TextStyle.short, required=True)
        self.description = discord.ui.TextInput(label="Event Description", style=discord.TextStyle.paragraph,
                                                required=False)
        self.start_time = discord.ui.TextInput(label="Start Time (YYYY-MM-DD HH:MM)", style=discord.TextStyle.short,
                                               required=True)
        self.end_time = discord.ui.TextInput(label="End Time (YYYY-MM-DD HH:MM)", style=discord.TextStyle.short,
                                             required=True)
        self.status = discord.ui.TextInput(label="Status (Pending, Confirmed, Cancelled)",
                                           style=discord.TextStyle.short, required=True)


        # Add components to the modal
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.start_time)
        self.add_item(self.end_time)
        self.add_item(self.status)


    async def on_submit(self, interaction: discord.Interaction):
        status = self.status.value.strip().lower()  # Get the status value and make it lowercase

        if status == "cancelled":
            status = "Cancelled"
        elif status == "confirmed":
            status = "Confirmed"
        elif status == "pending":
            status = "Pending"
        else:
            await interaction.response.send_message(
                f"Invalid status. Please enter one of the following: Pending, Confirmed, Cancelled"
            )
            return

        try:
            query = "UPDATE event SET Name = ?, Description = ?, StartTime = ?, EndTime = ?, Status = ? WHERE ID = ?"
            cursor.execute(query, (self.name.value, self.description.value, self.start_time.value, self.end_time.value, self.status.value, self.event_id))
            database.commit()
            await interaction.response.send_message(f"Event `{self.event_id}` updated successfully!")
        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating event: {str(e)}", ephemeral=True)


