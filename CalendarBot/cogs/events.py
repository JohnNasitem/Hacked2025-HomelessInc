import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button
import sqlite3
from datetime import datetime, timedelta
from helper import discord_time

database = sqlite3.connect("database.db", 10)

# TODO: add try catch to all user commands
# TODO: Tighten the margins for reminders and make hourly task run every 30 mins instead
# TODO: use regex instead of "%Y-%m-%d %I:%M %p", to allow users to flexible time inputs like 3am

# region Classes
class EditEventView(View):
    def __init__(self, event_list, amount, offset):
        super().__init__()
        # Handle what data is being shown
        self.event_list = event_list
        self.amount = amount
        self.offset = offset

class NextButton(Button):
    def __init__(self, view: View):
        super().__init__(label="Next")
        self.parent_view = view

        # Disable of the amount of availabilities is less than the display amount
        if len(view.event_list) <= view.amount:
            self.disabled = True

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Enable previous button
        self.parent_view.children[0].disabled = False
        # Increment offset
        self.parent_view.offset += self.parent_view.amount
        # Disable next button if it reached the end
        if len(self.parent_view.event_list) < self.parent_view.offset + self.parent_view.amount:
            self.disabled = True

        #update options
        self.parent_view.children[1].options = get_edit_events_options(self.parent_view.event_list, self.parent_view.amount, self.parent_view.offset)

        # Update menu
        await interaction.edit_original_response(embed=gen_view_events_embed(self.parent_view.event_list, self.parent_view.amount, self.parent_view.offset), view=self.parent_view)

class PreviousButton(Button):
    def __init__(self, view: View):
        super().__init__(label="Previous", disabled=True)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()

        # Enable next button
        self.parent_view.children[2].disabled = False
        # Increment offset
        self.parent_view.offset -= self.parent_view.amount
        # Disable next button if it reached the end
        if self.parent_view.offset == 0:
            self.disabled = True

        # Update options
        self.parent_view.children[1].options = get_edit_events_options(self.parent_view.event_list, self.parent_view.amount, self.parent_view.offset)

        # Update menu
        await interaction.edit_original_response(embed=gen_view_events_embed(self.parent_view.event_list, self.parent_view.amount, self.parent_view.offset), view=self.parent_view)

class Events(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Events is ready!")

    # TODO: Take in an optional arg, channel to output the event to
    @app_commands.command(name="create-event", description="Creates an event")
    async def create_event(self, interaction: discord.Interaction):
        # Open create event modal
        try:
            await interaction.response.send_modal(CreateEventModal(interaction.user.id, interaction.user.name, interaction.channel.id))
        except Exception as ex:
            print(f"Problem occurred: {ex}")

    @app_commands.command(name="view-events", description="Displays all events created")
    async def view_events(self, interaction: discord.Interaction):  # TODO: can add pagination
        await display_events(interaction, 2, 0)


    # edit events has the option to edit the event
    # first takes in the event id and checks if it exists
    # checks current user is creator of that event
    # then provides options to change
    @app_commands.command(name="edit-event", description="Edits an event")
    async def edit_event(self, interaction: discord.Interaction, event_id: int):
        result = check_valid_event(event_id)
        # nothing fetched from database
        if result is None:
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
# endregion

# TODO: edit to only show 1 page, and use buttons to vote, to go other pages, and add a button if that user is the owner
async def display_events(interaction: discord.Interaction, amount: int, offset: int):
    """
    Display event embed menu
    :param interaction: interation
    :param amount: amount of events to display in 1 page
    :param offset: index offset
    :return:
    """
    # update events appropriately
    delete_past_events()
    change_to_ongoing()
    # fetch query results
    results = get_events()

    if not results:
        await interaction.response.send_message("No events found!", ephemeral=True)
        return

    dropdown = Select(
        placeholder="Choose an event to edit...",
        min_values=1,
        max_values=1,
        options=get_edit_events_options(results, amount, offset)
    )

    async def dropdown_callback(interaction_callback: discord.Interaction):
        """
        Open a modal dialog when user selects an availability
        :param interaction_callback: interaction
        :return: None
        """
        await interaction_callback.response.send_message(f"Selected {dropdown.values[0]}", ephemeral=True)
        # TODO: change to modal
        #await interaction_callback.response.send_modal(
        #    EditEventModal(raw_availabilities[int(dropdown.values[0])]))

    # Assign the callback to the dropdown
    dropdown.callback = dropdown_callback

    view = EditEventView(results, amount, offset)
    if len(dropdown.options) > 0:
        view.add_item(PreviousButton(view))
        view.add_item(dropdown)
        view.add_item(NextButton(view))

    await interaction.response.send_message(embed=gen_view_events_embed(results, 2, 0), view=view, ephemeral=True)

def gen_view_events_embed(event_list, amount, offset):
    """
    Generate an embed from the provided data within the provided range
    :param event_list: list of events
    :param amount: how many to display
    :param offset: starting offset
    :return: Embed
    """

    if amount > 25:
        raise Exception("Amount cannot be larger than 25")

    # parse through each row of the result and display it
    view_event_embed_menu = discord.Embed(
        title="All Scheduled Events",
    )
    for idx, result in enumerate(event_list, 1):
        # Ignore any not being displayed
        if idx < offset + 1:
            continue
        if idx == offset + amount + 1:
            break

        # Add event as embed field
        datetime_format = "%Y-%m-%d %I:%M %p"
        start_date = datetime.strptime(result[5], datetime_format)
        end_date = datetime.strptime(result[6], datetime_format)
        view_event_embed_menu.add_field(
            # Name
            name=f"{idx} - {result[3]}",
            # Created By: creator \n StartTime - EndTime \n Description \n Status: status
            value=f"Created by: {result[2]} \n {discord_time(start_date, 'f')} - {discord_time(end_date, 'f')}\nDescription: {result[4]}\nStatus: {result[7]}",
            inline=False
        )

    return view_event_embed_menu

def get_edit_events_options(event_list, amount, offset):
    """
    Get select options in range from event_list
    :param event_list: list of events to display
    :param amount: amount to display
    :param offset: index offset
    :return: list of SelectOptions
    """

    if amount > 25:
        raise Exception("Amount cannot be larger than 25")

    options = []
    for idx, result in enumerate(event_list, 1):
        # Ignore any not being displayed
        if idx < offset + 1:
            continue
        if idx == offset + amount + 1:
            break
                                            # Event name
        options.append(discord.SelectOption(label=f"{idx} - {result[3]}",
                                            # Creator
                                            description=f"Created by: {result[2]}",
                                            value=str(idx)))

    return options

async def send_reminders(bot):
    """
    Send reminders
    """
    await send_early_reminder(bot)
    await send_starting_reminder(bot)
    await remind_creator(bot)
    print("Sent reminders.")

async def send_early_reminder(bot):
    """
    Send a reminder to event participants 24 hours before event starts
    :param bot: bot
    :return: None
    """
    current_datetime = datetime.now()
    twenty_four_hours_later = current_datetime + timedelta(hours=24)
    margin = timedelta(hours=2)

    # find events to that start in about 24 hours that are confirmed to happen
    cursor = database.cursor()
    query = "SELECT * FROM event WHERE StartTime BETWEEN ? AND ? AND Status = 'Confirmed' AND AlreadyRemindedParticipants = '0'"
    cursor.execute(query, (twenty_four_hours_later - margin, twenty_four_hours_later + margin))
    result = cursor.fetchall()
    cursor.close()
    if result:
        for event in result:
            guild = bot.get_guild(int(event[13]))
            if guild:
                channel_id = event[8]
                # find the channel where the user originally created the event
                channel = guild.get_channel(channel_id)
                if channel:
                    # TODO: should this ping everyone? a role? or only the people who voted yes?
                    await channel.send(f"Hey @everyone! The event, **{event[3]}**, will occur in 24 hours!")
                    print(f"Reminder for {event[3]} sent.")

                    # set AlreadyRemindedParticipants flag for event
                    cursor = database.cursor()
                    cursor.execute("UPDATE event SET AlreadyRemindedParticipants = '1' WHERE ID = ?", (event[0],))
                    database.commit()
                    cursor.close()
                else:
                    print("Channel not found.")
            else:
                print("Guild not found.")

async def send_starting_reminder(bot):
    """
    Send an announcement when the event does start
    :param bot:
    :return:
    """
    current_datetime = datetime.now()
    margin = timedelta(hours=2)

    # find events to that start in about 24 hours that are confirmed to happen
    query = "SELECT * FROM event WHERE StartTime BETWEEN ? AND ? AND Status = 'Confirmed' AND AlreadyAnnounced = '0'"
    cursor = database.cursor()
    cursor.execute(query, (current_datetime - margin, current_datetime + margin))
    result = cursor.fetchall()
    cursor.close()
    if result:
        for event in result:
            guild = bot.get_guild(int(event[13]))  # Replace with your guild ID
            if guild:
                channel_id = event[8]
                # find the channel where the user originally created the event
                channel = guild.get_channel(channel_id)
                if channel:
                    # TODO: should this ping everyone? a role? or only the people who voted yes?
                    await channel.send(f"Hey @everyone! The event, **{event[3]}**, is occurring!")
                    print(f"Announcement for {event[3]} sent.")

                    # set AlreadyAnnounced flag for event
                    cursor = database.cursor()
                    cursor.execute("UPDATE event SET AlreadyAnnounced = '1' WHERE ID = ?", (event[0],))
                    database.commit()
                    cursor.close()
                else:
                    print("Channel not found.")
            else:
                print("Guild not found.")
    cursor.close()
async def remind_creator(bot):
    """
    Remind the creator 48 hours a head of time to confirm the event if it is still pending
    :param bot: Bot
    :return: None
    """
    current_datetime = datetime.now()
    forty_eight_hours_later = current_datetime + timedelta(hours=48)
    margin = timedelta(hours=2)

    query = "SELECT * FROM event WHERE StartTime BETWEEN ? AND ? AND Status = 'Pending' AND AlreadyRemindedOwner= '0'"
    cursor = database.cursor()
    cursor.execute(query, (forty_eight_hours_later - margin, forty_eight_hours_later + margin))
    result = cursor.fetchall()
    cursor.close()
    if result:
        for event in result:
            guild = bot.get_guild(int(event[13]))  # Replace with your guild ID
            if guild:
                user_id = event[1]
                user = bot.get_user(user_id)
                if user:
                    await user.send(f"Hey {user.mention}! The event, **{event[3]}** in **{guild.name}** has not been confirmed yet. Please confirm it (via `/edit-event`) so that server members can be notified 24 hours before!")
                    print(f"Reminder for {event[3]} sent to creator.")

                    # set AlreadyRemindedOwner flag for event
                    sub_query = "UPDATE event SET AlreadyRemindedOwner = '1' WHERE ID = ?"
                    cursor = database.cursor()
                    cursor.execute(sub_query, (event[0],))
                    database.commit()
                    cursor.close()
                else:
                    print("User not found.")
            else:
                print("Guild not found.")
    cursor.close()

async def setup(bot):
    await bot.add_cog(Events(bot))

# region database functions
def get_events():
    """
    Get all events ordered by start time ascending
    :return: all event rows
    """
    cursor = database.cursor()
    cursor.execute("SELECT * FROM event ORDER BY StartTime ASC" )# earliest event first
    result = cursor.fetchall()
    cursor.close()
    return result

def check_valid_event(event_id):
    """
    fetches event for given id.
    :param event_id: event id
    :return: event row
    """
    cursor = database.cursor()
    cursor.execute("SELECT * FROM event WHERE ID = ?", (event_id,))
    result = cursor.fetchone()
    cursor.close()
    return result

def delete_event(event_id):
    """
    Deletes the event with the provided id.
    :param event_id: id of event to delete
    :return: None
    """
    cursor = database.cursor()
    cursor.execute("DELETE FROM event WHERE ID = ?", (event_id,))
    database.commit()
    cursor.close()

def delete_past_events():
    """
    Delete any events that have past
    :return: None
    """
    cursor = database.cursor()
    cursor.execute("DELETE FROM event WHERE EndTime < ?", (datetime.now(),))
    database.commit()
    cursor.close()

def change_to_ongoing():
    """
    Update any events who should be ongoing
    :return: None
    """
    cursor = database.cursor()
    cursor.execute("UPDATE event SET Status = ? WHERE StartTime < ? AND EndTime > ? AND STATUS = 'Confirmed'", ("Ongoing", datetime.now(), datetime.now()))
    database.commit()
    cursor.close()

def cancel_event(event_id):
    """
    Cancels the event with the provided id.
    :param event_id: id of event to cancel
    :return: None
    """
    cursor = database.cursor()
    cursor.execute("UPDATE event SET Status = ? WHERE ID = ?", ("Cancelled", event_id))
    database.commit()
    cursor.close()

def find_rsvp_response(event_id, user_id):
    """
    Get rsvp response from a user for an event
    :param event_id: id of event
    :param user_id: id of user
    :return: Response row
    """
    cursor = database.cursor()
    cursor.execute("SELECT Response FROM rsvp WHERE EventID = ? AND UserID = ?", (event_id, user_id))
    result = cursor.fetchone()
    cursor.close()
    return result

def rsvp(event_id, user_id, user_name, response):
    """
    Rsvp a user to an event
    :param event_id: id of event
    :param user_id: id of user
    :param user_name: username of user
    :param response: users response
    :return: None
    """
    cursor = database.cursor()
    cursor.execute("INSERT INTO rsvp VALUES (?, ?, ?, ?)", (event_id, user_id, user_name, response))
    database.commit()
    cursor.close()

def update_rsvp(event_id, user_id, response):
    """
    Update a users rsvp to an event
    :param event_id: id of event
    :param user_id: id of user
    :param response: new response
    :return: None
    """
    cursor = database.cursor()
    cursor.execute("UPDATE rsvp SET Response = ? WHERE EventID = ? AND UserID = ?", (response, event_id, user_id))
    database.commit()
    cursor.close()

def fetch_rsvp_response(event_id, response):
    """
    Get all users who rsvped for the event
    :param event_id: id of event
    :param response: what response to filter for
    :return: count, list of user ids
    """
    cursor = database.cursor()
    cursor.execute("SELECT User FROM rsvp WHERE Response = ? AND EventID = ?", (response, event_id))
    result = cursor.fetchall()
    user_ids = list([row[0] for row in result])
    cursor.close()
    return len(user_ids), user_ids
# endregion

class CreateEventModal(discord.ui.Modal, title="Create Event"):
    def __init__(self, creator_id: int, creator: str, channel_id: int):
        super().__init__()
        self.creator_id = creator_id
        self.creator = creator
        self.status = "Not set"
        self.channel_id = channel_id


        self.name = discord.ui.TextInput(label="Event Name", style=discord.TextStyle.short, required=True)
        self.description = discord.ui.TextInput(label="Event Description", style=discord.TextStyle.paragraph,
                                                required=False)
        self.start_time = discord.ui.TextInput(label="Start Time (YYYY-MM-DD HH:MM AM/PM)", style=discord.TextStyle.short,
                                               required=True)
        self.end_time = discord.ui.TextInput(label="End Time (YYYY-MM-DD HH:MM AM/PM)", style=discord.TextStyle.short,
                                             required=True)

        # Add components to the modal
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.start_time)
        self.add_item(self.end_time)

    async def on_submit(self, interaction: discord.Interaction):
        # check if datetime was inserted properly
        datetime_format = "%Y-%m-%d %I:%M %p"
        try:
            # check start_time and end_time are in correct date_time format
            start_time = datetime.strptime(self.start_time.value, datetime_format)
            end_time = datetime.strptime(self.end_time.value, datetime_format)
            if start_time > end_time:
                await interaction.response.send_message("Start time must be before end time!", ephemeral=True)
                return
            elif start_time == end_time:
                await interaction.response.send_message("Start time and end time cannot be the same!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message( f"Incorrect datetime format, should be {datetime_format}, like 2025-02-14 15:30, or incorrect datetime values inputted" , ephemeral=True)
            return

        status_options = ["Pending", "Ongoing"]
        current_datetime = datetime.now()
        if current_datetime < start_time:
            self.status = status_options[0]
        elif current_datetime < end_time:
            self.status = status_options[1]
        else:
            await interaction.response.send_message("Invalid event time! Cannot create event in the past.", ephemeral=True)
            return

        try:
            query = """
            INSERT INTO event (CreatorID, Creator, Name, Description, StartTime, EndTime, Status, ChannelID, AlreadyRemindedOwner, AlreadyRemindedParticipants, AlreadyAnnounced, GUILDID)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor = database.cursor()
            cursor.execute(query, (self.creator_id, self.creator, self.name.value, self.description.value, self.start_time.value, self.end_time.value, self.status, self.channel_id, "0", "0", "0", interaction.guild.id))
            database.commit()
            cursor.close()
            start_date = datetime.strptime(self.start_time.value, datetime_format)
            end_date = datetime.strptime(self.end_time.value, datetime_format)
            await interaction.response.send_message(embed=discord.Embed(
                title="Sucessfully created event!",
                description=f"Event Name: **{self.name.value}**\nCreated by: {self.creator} \n {discord_time(start_date, 'f')} - {discord_time(end_date, 'f')}\nDescription: {self.description.value}\nStatus: {self.status}",
            ), ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Error updating event: {str(e)}", ephemeral=True)

# modal to edit event
class EditEventModal(discord.ui.Modal, title="Edit Event"):
    def __init__(self, event_id: int):
        super().__init__()
        self.event_id = event_id

        event = self.get_event_details()

        self.name = discord.ui.TextInput(label="Event Name", style=discord.TextStyle.short, required=True, default=event['name'])
        self.description = discord.ui.TextInput(label="Event Description", style=discord.TextStyle.paragraph,
                                                required=False, default=event['description'])
        self.start_time = discord.ui.TextInput(label="Start Time (YYYY-MM-DD HH:MM)", style=discord.TextStyle.short,
                                               required=True, default=event['start_time'])
        self.end_time = discord.ui.TextInput(label="End Time (YYYY-MM-DD HH:MM)", style=discord.TextStyle.short,
                                             required=True, default=event['end_time'])
        self.status = discord.ui.TextInput(label="Status (Pending, Confirmed, Cancelled)",
                                           style=discord.TextStyle.short, required=True, default=event['status'])

        # Add components to the modal
        self.add_item(self.name)
        self.add_item(self.description)
        self.add_item(self.start_time)
        self.add_item(self.end_time)
        self.add_item(self.status)

    def get_event_details(self):
        """
        Get event details
        :return: Event entry related to this event id
        """
        cursor = database.cursor()
        cursor.execute("SELECT * FROM event WHERE ID = ?", (self.event_id,))
        result = cursor.fetchone()
        cursor.close()

        if result:
            return {
                'name': result[3],
                'description': result[4],
                'start_time': result[5],
                'end_time': result[6],
                'status': result[7]
            }
        else:
            return None

    async def on_submit(self, interaction: discord.Interaction):
        # check if datetime was inserted properly
        datetime_format = "%Y-%m-%d %H:%M"  # no seconds
        try:
            # check start_time and end_time are in correct date_time format
            start_time = datetime.strptime(self.start_time.value, datetime_format)
            end_time = datetime.strptime(self.end_time.value, datetime_format)
            if start_time > end_time:
                await interaction.response.send_message("Start time must be before end time!", ephemeral=True)
                return
            elif start_time == end_time:
                await interaction.response.send_message("Start time and end time cannot be the same!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message(
                f"Incorrect datetime format, should be {datetime_format}, like 2025-02-14 15:30, or incorrect datetime values inputted", ephemeral=True)
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
            await interaction.response.send_message(f"Invalid status. Please enter one of the following: Pending, Confirmed, Cancelled", ephemeral=True)
            return

        try:
            cursor = database.cursor()
            query = "UPDATE event SET Name = ?, Description = ?, StartTime = ?, EndTime = ?, Status = ? WHERE ID = ?"
            cursor.execute(query, (self.name.value, self.description.value, self.start_time.value, self.end_time.value, self.status, self.event_id))
            database.commit()
            cursor.close()
            await interaction.response.send_message(f"Event `{self.event_id}` updated successfully!", ephemeral=True)
            # TODO: Make edits to original message with new changes
        except Exception as e:
            await interaction.response.send_message(f"Error updating event: {str(e)}", ephemeral=True)

