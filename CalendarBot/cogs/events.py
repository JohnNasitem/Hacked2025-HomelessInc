import discord
from discord.ext import commands
from discord import app_commands

import sqlite3
import time
from datetime import datetime

database = sqlite3.connect("database.db")
cursor = database.cursor()
database.execute("DROP TABLE IF EXISTS event")
database.execute("DROP TABLE IF EXISTS rsvp")
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
database.execute("""CREATE TABLE IF NOT EXISTS rsvp(
                 EventID INTEGER,
                 UserID INTEGER,
                 User TEXT,
                 Response TEXT,
                 PRIMARY KEY(EventID, UserID),
                 FOREIGN KEY(EventID) REFERENCES event(ID) ON DELETE CASCADE
                 )""")

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online!")

    @app_commands.command(name="create-event", description="Creates an event")
    async def createevent(self, interaction: discord.Interaction):
        event_id = int(time.time() * 1000)
        creator_id = interaction.user.id
        creator = interaction.user.name

        await interaction.response.send_modal(CreateEventModal(event_id, creator_id, creator))

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
                    f"Event Name: {result[3]}\n"
                    f"Created by: {result[2]}\n"
                    f"Description: {result[4]}\n"
                    f"Start Time: {result[5]}\n"
                    f"End Time: {result[6]}\n"
                    f"Status: {result[7]}"
                    f"```")

            await  interaction.response.send_message("".join(event_list))
        else:
            await interaction.response.send_message("No events found!")
            return

    # edit events has the option to edit the event
    # first takes in the event id and checks if it exists
    # checks current user is creator of that event
    # then provides options to change
    @app_commands.command(name="edit-event", description="Edits an event")
    async def editevent(self, interaction: discord.Interaction, event_id: int):
        result = check_valid_event(event_id)
        if result is None:  # nothing fetched from database
            await interaction.response.send_message("No such event exists!")
            return

        if result[1] != interaction.user.id:
            await interaction.response.send_message("You are not the creator of this event. Cannot edit event.")
            return

        await interaction.response.send_modal(EditEventModal(event_id))

    # user can rsvp to a specific event (or update their response)
    @app_commands.command(name="rsvp", description="Say yes/no to an event")
    async def rsvp(self, interaction: discord.Interaction, event_id: int, response: str):
        result = check_valid_event(event_id)
        if result is None:  # nothing fetched from database
            await interaction.response.send_message("No such event exists or invalid event id provided!")
            return

        if response.lower() != "yes" and response.lower() != "no":
            await interaction.response.send_message("Invalid response. Please enter yes or no only.")
            return
        else:
            response = response.lower()

        fetched = find_rsvp_response(event_id, interaction.user.id)
        if fetched:
            update_rsvp(event_id, interaction.user.id, response)
            await interaction.response.send_message(f"Updated response as **'{response}'** to event **{result[3]}**")
        else:
            rsvp(event_id, interaction.user.id, interaction.user.name, response)
            await interaction.response.send_message(f"Responded **'{response}'** to event **{result[3]}**")

    # check_rsvp provides information about a single event and rsvp responses from people
    @app_commands.command(name='check-event-details', description='Check rsvp responses and details for an event')
    async def checkeventdetails(self, interaction: discord.Interaction, event_id: int):
        result = check_valid_event(event_id)
        if result is None:  # nothing fetched from database
            await interaction.response.send_message("No such event exists or invalid event id provided!")
            return

        yes_count, yes_users = fetch_rsvp_response(event_id, 'yes')
        no_count, no_users = fetch_rsvp_response(event_id, 'no')
        yes_user_name = ', '.join(f"{user_id}" for user_id in yes_users) if yes_users else "No users yet."
        no_user_name = ', '.join(f"{user_id}" for user_id in no_users) if no_users else "No users yet."

        event_details = (f"```"
                 f"ID: {result[0]}\n"
                 f"Event Name: {result[3]}\n"
                 f"Created by: {result[2]}\n"
                 f"Description: {result[4]}\n"
                 f"Start Time: {result[5]}\n"
                 f"End Time: {result[6]}\n"
                 f"Status: {result[7]}\n"
                 f"Yes count: {yes_count}\n"
                 f"No count: {no_count}\n"
                 f"Users who RSVP'd Yes: {yes_user_name}\n"
                 f"Users who RSVP'd No: {no_user_name}"        
                 f"```"
        )

        await interaction.response.send_message(event_details)

    # cancelevent command cancels an event; needs event id and requires the user who created the event
    @app_commands.command(name="delete-event", description="Deletes an event")
    async def deleteevent(self, interaction: discord.Interaction, event_id: int):
        # fetch the event from the database, if possible
        result = check_valid_event(event_id)
        if result is None: # nothing fetched from database
            await interaction.response.send_message("No such event exists or invalid event id provided!")
            return

        # check if current user is the user that created the event
        if result[1] != interaction.user.id:
            await interaction.response.send_message("You are not the creator of this event. Cannot delete event.")
            return

        delete_event(event_id)
        await interaction.response.send_message(f"Event **{result[3]}** has been **deleted**.") # result[3] is event name



async def setup(bot):
    await bot.add_cog(Events(bot))

# helper functions for commands
# get_events gets all items from event table in database
def get_events():
    print("In events function") # testing
    query = "SELECT * FROM event ORDER BY StartTime ASC" # earliest event first
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
    query = "UPDATE event SET Status = ? WHERE StartTime < ? AND EndTime > ? AND STATUS = 'Confirmed'" # FIXME only when status is confirmed
    cursor.execute(query, ("Ongoing", current_datetime, current_datetime))
    database.commit()

# TODO add more changing status logic

# cancel_event cancels the event with the provided id
def cancel_event(event_id):
    query = "UPDATE event SET Status = ? WHERE ID = ?"
    cursor.execute(query, ("Cancelled", event_id))
    database.commit()

def find_rsvp_response(event_id, user_id):
    query = "SELECT Response FROM rsvp WHERE EventID = ? AND UserID = ?"
    cursor.execute(query, (event_id, user_id))
    result = cursor.fetchone()
    return result

def rsvp(event_id, user_id, user_name, response):
    query = "INSERT INTO rsvp VALUES (?, ?, ?, ?)"
    cursor.execute(query, (event_id, user_id, user_name, response))
    database.commit()

def update_rsvp(event_id, user_id, response):
    query = "UPDATE rsvp SET Response = ? WHERE EventID = ? AND UserID = ?"
    cursor.execute(query, (response, event_id, user_id))
    database.commit()

def fetch_rsvp_response(event_id, response):
    query = "SELECT User FROM rsvp WHERE Response = ? AND EventID = ?"
    cursor.execute(query, (response, event_id))
    result = cursor.fetchall()
    user_ids = [row[0] for row in result]
    count = len(user_ids)
    return count, user_ids

# def rsvp_no(event_id):
#     query = "SELECT COUNT(*) FROM rsvp WHERE Response = 'no' AND EventID = ?"
#     cursor.execute(query, (event_id,))
#     result = cursor.fetchone()
#     return result[0]

# modal to create event
class CreateEventModal(discord.ui.Modal, title="Create Event"):
    def __init__(self, event_id: int, creator_id: int, creator: str):
        super().__init__()
        self.event_id = event_id
        self.creator_id = creator_id
        self.creator = creator
        self.status = "Not set"

        self.name = discord.ui.TextInput(label="Event Name", style=discord.TextStyle.short, required=True)
        self.description = discord.ui.TextInput(label="Event Description", style=discord.TextStyle.paragraph,
                                                required=False)
        self.start_time = discord.ui.TextInput(label="Start Time (YYYY-MM-DD HH:MM)", style=discord.TextStyle.short,
                                               required=True)
        self.end_time = discord.ui.TextInput(label="End Time (YYYY-MM-DD HH:MM)", style=discord.TextStyle.short,
                                             required=True)

        # Add components to the modal
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.start_time)
        self.add_item(self.end_time)

    async def on_submit(self, interaction: discord.Interaction):
        # check if datetime was inserted properly
        datetime_format = "%Y-%m-%d %H:%M"  # no seconds
        try:
            # check start_time and end_time are in correct date_time format
            start_time = datetime.strptime(self.start_time.value, datetime_format)
            end_time = datetime.strptime(self.end_time.value, datetime_format)
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

        status_options = ["Pending", "Ongoing"]
        current_datetime = datetime.now()
        if current_datetime < start_time:
            self.status = status_options[0]
        elif current_datetime < end_time:
            self.status = status_options[1]
        else:
            await interaction.response.send_message("Invalid event time! Cannot create event in the past.")
            return

        try:
            query = "INSERT INTO event VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
            cursor.execute(query, (self.event_id, self.creator_id, self.creator, self.name.value, self.description.value, self.start_time.value, self.end_time.value, self.status))
            database.commit()
            await interaction.response.send_message(f"Event `{self.event_id}` created successfully!")
        except Exception as e:
            await interaction.response.send_message(f"Error updating event: {str(e)}", ephemeral=True)

# modal to edit event
class EditEventModal(discord.ui.Modal, title="Edit Event"):
    def __init__(self, event_id: int):
        super().__init__()
        self.event_id = event_id

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
        # check if datetime was inserted properly
        datetime_format = "%Y-%m-%d %H:%M"  # no seconds
        try:
            # check start_time and end_time are in correct date_time format
            start_time = datetime.strptime(self.start_time.value, datetime_format)
            end_time = datetime.strptime(self.end_time.value, datetime_format)
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

        # check if status was entered properly
        status = self.status.value.strip().lower()  # Get the status value and make it lowercase
        if status == "cancelled":
            self.status = "Cancelled"
        elif status == "confirmed":
            self.status = "Confirmed"
        elif status == "pending":
            self.status = "Pending"
        else:
            await interaction.response.send_message(
                f"Invalid status. Please enter one of the following: Pending, Confirmed, Cancelled")
            return

        try:
            query = "UPDATE event SET Name = ?, Description = ?, StartTime = ?, EndTime = ?, Status = ? WHERE ID = ?"
            cursor.execute(query, (self.name.value, self.description.value, self.start_time.value, self.end_time.value, self.status, self.event_id))
            database.commit()
            await interaction.response.send_message(f"Event `{self.event_id}` updated successfully!")
        except Exception as e:
            await interaction.response.send_message(f"Error updating event: {str(e)}", ephemeral=True)


