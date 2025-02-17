import datetime
import discord
import re
import random
from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import View, Select, Button
from PIL import Image, ImageDraw, ImageFont # pip install Pillow
from dateutil.relativedelta import relativedelta # pip install python-dateutil
import os
import sqlite3
import datetime as dt
from datetime import datetime

# TODO: move to own cog file, one command to load both databases
database = sqlite3.connect("database.db")
cursor = database.cursor()
database.execute("DROP TABLE IF EXISTS availability")
database.execute("""CREATE TABLE IF NOT EXISTS availability(
                 USERID INTEGER,
                 AVAILABILITYDATE TEXT,
                 StartTime TEXT,
                 EndTime TEXT,
                 RECURRING TEXT
                 )""")

col_header_font = ImageFont.truetype("arial.ttf", 45)
row_header_font = ImageFont.truetype("arial.ttf", 30)
days_of_week = [ "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
time_regex_string = r"(\d\d?):(\d\d) (am|pm)"

def discordTime(date_time, format=None):
    """
    Convert date_time to a discord timestamp
    """
    if format is None:
        return f"<t:{int(datetime.timestamp(date_time))}>" 
    if format == "t":
        return f"<t:{int(datetime.timestamp(date_time))}:t>"
    if format == "D":
        return f"<t:{int(datetime.timestamp(date_time))}:D>"

class CreateAvailabilityModal(discord.ui.Modal, title="Create Availability"):
    def __init__(self):
        super().__init__()
        # Inputs
        self.date = discord.ui.TextInput(label="Date (YYYY-MM-DD)", style=discord.TextStyle.short, required=True, default=datetime.today().strftime("%Y-%m-%d"))
        self.start_time = discord.ui.TextInput(label="Start Time (HH:MM AM/PM)", style=discord.TextStyle.short,required=True)
        self.end_time = discord.ui.TextInput(label="End Time (HH:MM AM/PM)", style=discord.TextStyle.short,required=True)
        self.recurring = discord.ui.TextInput(label="Recurring (false, d, w, m, y)", style=discord.TextStyle.short,required=True, default="false")

        # Add components to the modal
        self.add_item(self.date)
        self.add_item(self.start_time)
        self.add_item(self.end_time)
        self.add_item(self.recurring)

    async def on_submit(self, modal_interaction: discord.Interaction):
        recurring_dict = {
            'false': 'false',  # No recurrence
            'd': 'daily',  # Daily recurrence
            'w': 'weekly',  # Weekly recurrence
            'm': 'monthly',  # Monthly recurrence
            'y': 'yearly'  # Yearly recurrence
        }

        try:
            # Extract data from input fields
            day = self.date.value.lower()
            start_time = self.start_time.value.lower()
            end_time = self.end_time.value.lower()
            recurring = recurring_dict[self.recurring.value.lower()]
            # create datetime objects for start and end to simplify
            start_date = datetime.strptime(f"{day} {start_time}", "%Y-%m-%d %I:%M %p")
            end_date = datetime.strptime(f"{day} {end_time}", "%Y-%m-%d %I:%M %p")

            if start_date.timestamp() > end_date.timestamp():  # Check if start time is before end time
                raise Exception("Start time cannot be after end time.")

            db_add_availability(modal_interaction.user.id, day, start_time, end_time, recurring)

            await modal_interaction.response.send_message(embed=discord.Embed(
                title="Successfully set availability!",
                description=f"Date: {discordTime(start_date, 'D')}\nTime: {discordTime(start_date, 't')} - {discordTime(end_date, 't')}\nRecurring: {recurring}",
                color=modal_interaction.user.colour
            ), ephemeral=True)
        except KeyError:
            await modal_interaction.response.send_message(
                content="Invalid recurring option. Options: false, d, w, m, y",
                ephemeral=True)
        except ValueError:
            await modal_interaction.response.send_message(
                content="Improperly formatted date or time. Please provide the times in the following format: YYYY-MM-DD HH:MM AM/PM",
                ephemeral=True)
        except Exception as exception:
            await modal_interaction.response.send_message(
                content=f"{exception} Please provide the times in the following format: YYYY-MM-DD HH:MM AM/PM",
                ephemeral=True)
            return None

class EditAvailabilityModal(discord.ui.Modal, title="Edit Availability"):
    def __init__(self, old_row):
        self.old_row = old_row
        user_id, date, start_time, end_time, recurring = old_row  # unpack the tuple
        super().__init__()
        # Inputs
        self.date = discord.ui.TextInput(label="Date (YYYY-MM-DD)", style=discord.TextStyle.short, required=True, default=date)
        self.start_time = discord.ui.TextInput(label="Start Time (HH:MM AM/PM)", style=discord.TextStyle.short,required=True, default=start_time)
        self.end_time = discord.ui.TextInput(label="End Time (HH:MM AM/PM)", style=discord.TextStyle.short,required=True, default=end_time)
        self.recurring = discord.ui.TextInput(label="Recurring (d, w, m, y)", style=discord.TextStyle.short,required=True, default=recurring)

        # Add components to the modal
        self.add_item(self.date)
        self.add_item(self.start_time)
        self.add_item(self.end_time)
        self.add_item(self.recurring)

    async def on_submit(self, modal_interaction: discord.Interaction):
        recurring_dict = {
            'false': 'false',  # No recurrence
            'd': 'daily',  # Daily recurrence
            'w': 'weekly',  # Weekly recurrence
            'm': 'monthly',  # Monthly recurrence
            'y': 'yearly'  # Yearly recurrence
        }
        user_id, old_date, old_start_time, old_end_time, old_recurring = self.old_row  # unpack the tuple

        try:
            # Extract data from input fields
            day = self.date.value.lower()
            start_time = self.start_time.value.lower()
            end_time = self.end_time.value.lower()
            recurring = recurring_dict[self.recurring.value.lower()]
            # create datetime objects for start and end to simplify
            start_date = datetime.strptime(f"{day} {start_time}", "%Y-%m-%d %I:%M %p")
            end_date = datetime.strptime(f"{day} {end_time}", "%Y-%m-%d %I:%M %p")
            old_start_date = datetime.strptime(f"{old_date} {old_start_time}", "%Y-%m-%d %I:%M %p")
            old_end_date = datetime.strptime(f"{old_date} {old_end_time}", "%Y-%m-%d %I:%M %p")

            if start_date.timestamp() > end_date.timestamp():  # Check if start time is before end time
                raise Exception("Start time cannot be after end time.")

            db_edit_availability(self.old_row, (modal_interaction.user.id, day, start_time, end_time, recurring))

            await modal_interaction.response.send_message(embed=discord.Embed(
                title="Successfully edited availability!",
                description=f"Date: {discordTime(old_start_date, 'D')} -> {discordTime(start_date, 'D')}\nTime: {discordTime(old_start_date, 't')} - {discordTime(old_end_date, 't')} -> {discordTime(start_date, 't')} - {discordTime(end_date, 't')}\nRecurring: {old_recurring} -> {recurring}",
                color=modal_interaction.user.colour
            ), ephemeral=True)
        except KeyError:
            await modal_interaction.response.send_message(
                content="Invalid recurring option. Options: false, d, w, m, y",
                ephemeral=True)
        except ValueError:
            await modal_interaction.response.send_message(
                content="Improperly formatted date or time. Please provide the times in the following format: YYYY-MM-DD HH:MM AM/PM",
                ephemeral=True)
        except Exception as exception:
            await modal_interaction.response.send_message(
                content=f"{exception} Please provide the times in the following format: YYYY-MM-DD HH:MM AM/PM",
                ephemeral=True)
            return None

class EditAvailabilityView(View):
    def __init__(self, raw_availabilities, amount, offset):
        super().__init__()
        self.raw_availabilities = raw_availabilities
        self.amount = amount
        self.offset = offset

class NextButton(Button):
    def __init__(self, view: View):
        super().__init__(label="Next")
        self.parent_view = view

        if len(view.raw_availabilities) <= view.amount:
            self.disabled = True

    async def callback(self, interaction: discord.Interaction):
        print("Button pressed")
        await interaction.response.defer()
        # Enable previous button
        self.parent_view.children[0].disabled = False

        # Increment offset
        self.parent_view.offset += self.parent_view.amount

        print(f'offset: {self.parent_view.offset} - amount: {self.parent_view.amount}')

        # Disable next button if it reached the end
        if len(self.parent_view.raw_availabilities) < self.parent_view.offset + self.parent_view.amount:
            self.disabled = True

        #update options
        self.parent_view.children[1].options = get_edit_availabilities_options(self.parent_view.raw_availabilities, self.parent_view.amount, self.parent_view.offset)

        await interaction.edit_original_response(embed=gen_edit_availabilities_embed(self.parent_view.raw_availabilities, self.parent_view.amount, self.parent_view.offset), view=self.parent_view)


class PreviousButton(Button):
    def __init__(self, view: View):
        super().__init__(label="Previous", disabled=True)
        self.parent_view = view

    async def callback(self, interaction: discord.Interaction):
        print("Button pressed")

        await interaction.response.defer()
        # Enable next button
        self.parent_view.children[2].disabled = False

        # Increment offset
        self.parent_view.offset -= self.parent_view.amount

        print(f'offset: {self.parent_view.offset} - amount: {self.parent_view.amount}')

        # Disable next button if it reached the end
        if self.parent_view.offset == 0:
            self.disabled = True

        # update options
        self.parent_view.children[1].options = get_edit_availabilities_options(self.parent_view.raw_availabilities, self.parent_view.amount, self.parent_view.offset)

        await interaction.edit_original_response(embed=gen_edit_availabilities_embed(self.parent_view.raw_availabilities, self.parent_view.amount, self.parent_view.offset), view=self.parent_view)





class Day:
    """
    Holds an availability slot on the selected day for a specific user
    """
    def __init__(self, user_id, date, start_time, end_time):
        self.user_id = user_id
        self.date = date
        self.start_time = start_time
        self.end_time = end_time

class Availability(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Availability is ready!")

    @staticmethod
    def convert_row_to_day(row):
        result_user_id, availability_date, start_time, end_time, recurring = row
        dt_date = datetime.strptime(availability_date, '%Y-%m-%d')
        return Day(result_user_id, dt_date.strftime('%Y-%m-%d'), start_time, end_time)

    @app_commands.command(name="set-availability", description="Set your availability for a specific time period")
    async def set_availability(self, interaction: discord.Interaction):
        """
        Set the availability for a specific time period

        Returns:
            (userID, day, start_time, end_time) if the message is in the correct format
            None otherwise

        shouts out to chris for getting slash commands to work
        """
        await interaction.response.send_modal(CreateAvailabilityModal())

    @app_commands.command(name="get-availability", description="Get availability for a specific user(s)")
    async def get_availability(self, interaction: discord.Interaction, user_str: str = "", week_num: int = -1):
        """
        get availability slash command
        :param interaction: interaction
        :param user_str: users to get availabilities from
        :param week_num: specified week num
        :return: None
        """
        today_date = datetime.today()

        if week_num < 0:
            week_num = int(today_date.strftime("%U"))
        await display_availabilities(self.bot, interaction, user_str, week_num, today_date.year)

    @app_commands.command(name="edit-availability", description="Edit your availabilities")
    async def edit_availability(self, interaction: discord.Interaction):
        """
        edit availability slash command
        :param interaction: interaction
        :return: None
        """
        await edit_availabilities(interaction, 2, 0)


async def setup(bot):
    await bot.add_cog(Availability(bot))

def gen_edit_availabilities_embed(raw_availabilities, amount, offset):
    """
    Generate an embed from the provided data within the provided range
    :param raw_availabilities: data
    :param amount: how many to display
    :param offset: starting offset
    :return: Embed
    """

    if amount > 25:
        raise Exception("Amount cannot be larger than 25")

    edit_embed_menu = discord.Embed(
        title="Edit Availabilities",
        description="Please select an availability to edit",
    )

    for index, result in enumerate(raw_availabilities):
        if index < offset:
            continue
        if index == offset + amount:
            break

        user_id, date, start_time, end_time, recurring = result  # unpack the tuple

        # create datetime objects for start and end to simplify
        start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %I:%M %p")
        end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %I:%M %p")

        edit_embed_menu.add_field(
            name=f"{index + 1} {discordTime(start, 'D')}",
            value=f"{discordTime(start, 't')} to {discordTime(end, 't')}",
            inline=False
        )

    return edit_embed_menu

def get_edit_availabilities_options(raw_availabilities, amount, offset):
    options = []
    for index, result in enumerate(raw_availabilities):
        if index < offset:
            continue
        if index == offset + amount:
            break

        user_id, date, start_time, end_time, recurring = result  # unpack the tuple

        # create datetime objects for start and end to simplify
        start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %I:%M %p")
        end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %I:%M %p")

        options.append(discord.SelectOption(label=f"{index + 1}. {start.strftime("%b %d %Y")}",
                                            description=f"{start.strftime("%I:%M %p")} to {end.strftime("%I:%M %p")}",
                                            value=str(index)))
    return options

async def edit_availabilities(interaction: discord.Interaction, amount: int, offset: int):
    try:
        raw_availabilities = db_get_availability(interaction.user.id)
        dropdown = Select(
            placeholder="Choose an option...",  # Placeholder text when no selection is made
            min_values=1,  # Minimum number of selections
            max_values=1,  # Maximum number of selections
            options=get_edit_availabilities_options(raw_availabilities, amount, offset)
        )

        async def dropdown_callback(interaction_callback: discord.Interaction):
            await interaction_callback.response.send_modal(EditAvailabilityModal(raw_availabilities[int(dropdown.values[0])]))

        # Assign the callback to the dropdown
        dropdown.callback = dropdown_callback

        view = EditAvailabilityView(raw_availabilities, amount, offset)
        if len(dropdown.options) > 0:
            view.add_item(PreviousButton(view))
            view.add_item(dropdown)
            view.add_item(NextButton(view))

        await interaction.response.send_message(embed=gen_edit_availabilities_embed(raw_availabilities, amount, offset), view=view, ephemeral=True)
    except Exception as ex:
        print(ex)

async def display_availabilities(bot, interaction: discord.Interaction, user_str: str, week_num, year_num):
    """
    Display the availability for the specified week
    :param bot: Bot
    :param interaction: interaction
    :param user_str: user ids
    :param week_num: week number
    :param year_num: year number
    :return: None
    """
    try:
        users = []
        # Jan 1 of whatever year is supplied
        first_day_of_year = dt.date(year_num, 1, 1)
        # Get the sunday in this week specified by the week number
        first_day_of_week = first_day_of_year + dt.timedelta(
            days=(6 - first_day_of_year.weekday()) % 7) + dt.timedelta(weeks=week_num - 1)
        week_dates = []
        # Get the dates within this week
        for i in range(7):
            day = first_day_of_week + dt.timedelta(days=i)
            week_dates.append(day)

        # If argument is left empty then default ot calling user
        if user_str == "":
            users.append(interaction.user)
        else:
            # Find all numbers in argument
            user_id_match = re.findall(r'\d+', user_str)

            # Check each id if it is a user id and add it if it is
            for possible_id in user_id_match:
                try:
                    found_user = await bot.fetch_user(possible_id)
                    users.append(found_user)
                except discord.NotFound:
                    print(f'{possible_id} is an invalid user id')

        unfiltered_availabilities_list = []
        if users:
            for t_user in users:
                for result in db_get_availability(t_user.id):
                    unfiltered_availabilities_list.append(result)
        # If users is empty then that means everyone should be considered
        else:
            for result in db_get_all_availabilities():
                unfiltered_availabilities_list.append(result)

        # Filter out any availabilities not happening this week
        filtered_availabilities_list = []
        for raw_availability in unfiltered_availabilities_list:
            # Convert to Day
            converted_availability = Availability.convert_row_to_day(raw_availability)
            # Un-package the raw data
            result_user_id, availability_date, start_time, end_time, recurring = raw_availability
            #start and end strings
            start_str, end_str = week_dates[0].strftime('%Y-%m-%d'), week_dates[6].strftime('%Y-%m-%d')

            # Check if the exact date is within the range
            if start_str <= converted_availability.date <= end_str:
                filtered_availabilities_list.append(converted_availability)

            if recurring == "daily":
                for i in range(7):
                    new_date = datetime.strptime(converted_availability.date if start_str <= converted_availability.date <= end_str else start_str, "%Y-%m-%d") + dt.timedelta(days=i)
                    if new_date.strftime("%Y-%m-%d") == converted_availability.date:
                        continue
                    if new_date.strftime("%Y-%m-%d") > end_str:
                        break
                    filtered_availabilities_list.append(Day(converted_availability.user_id, new_date.strftime("%Y-%m-%d"), converted_availability.start_time, converted_availability.end_time))
            elif recurring == "weekly":
                if not start_str <= converted_availability.date <= end_str:
                    new_date = [date.strftime("%Y-%m-%d") for date in week_dates if (date - datetime.strptime(converted_availability.date, "%Y-%m-%d").date()).days % 7 == 0][0]
                    filtered_availabilities_list.append(Day(converted_availability.user_id, new_date, converted_availability.start_time, converted_availability.end_time))
            elif recurring == "monthly":
                if not start_str <= converted_availability.date <= end_str:
                    new_date = [date.strftime("%Y-%m-%d") for date in week_dates
                                if relativedelta(date, datetime.strptime(converted_availability.date, "%Y-%m-%d").date()).days == 0
                                and relativedelta(date, datetime.strptime(converted_availability.date, "%Y-%m-%d").date()).months >= 1]
                    if len(new_date) > 0:
                        filtered_availabilities_list.append(Day(converted_availability.user_id, new_date[0], converted_availability.start_time, converted_availability.end_time))
            elif recurring == "yearly":
                if not start_str <= converted_availability.date <= end_str:
                    new_date = [date.strftime("%Y-%m-%d") for date in week_dates
                                if relativedelta(date, datetime.strptime(converted_availability.date, "%Y-%m-%d").date()).days == 0
                                and relativedelta(date, datetime.strptime(converted_availability.date, "%Y-%m-%d").date()).months == 0
                                and relativedelta(date, datetime.strptime(converted_availability.date, "%Y-%m-%d").date()).years >= 1]
                    if len(new_date) > 0:
                        filtered_availabilities_list.append(Day(converted_availability.user_id, new_date[0], converted_availability.start_time, converted_availability.end_time))



        await create_image(bot, filtered_availabilities_list, week_dates)
        with open('generated_images/schedule.png', 'rb') as f:
            await interaction.response.send_message(f"Availabilities:", file=discord.File(f))
    except Exception as ex:
        await interaction.response.send_message(f"Something went wrong:\n{ex}")

async def create_image(bot, week_data, week_dates, show_overlap_count = True):
    """
    Create an image using a list of days, legend will be included if more than one user id exists in the list.
    :param week_data: list holding instances of Day
    """
    def generate_colour_table(user_ids):
        """
        Populate a colour dictionary with random colours
        :param user_ids:
        :return: Color Dictionary (user_id: color)
        """
        def generate_light_color():
            """
            Generate a light color, avoiding brown or gray shades.
            :return: r, g, b values
            """
            while True:
                r_int = random.randint(180, 255)
                g_int = random.randint(180, 255)
                b_int = random.randint(180, 255)

                # Avoid colors with too similar RGB values (to skip gray-like tones)
                # Avoid brownish hues by ensuring no dominant mix of red and green
                if abs(r_int - g_int) > 30 or abs(r_int - b_int) > 30 or abs(g_int - b_int) > 30 and not (r_int > 200 and 210 < g_int > 150 and b_int < 100):
                    return r_int, g_int, b_int

        colour_dict = {}
        incr = 0
        while len(colour_dict) != len(user_ids):
            r, g, b = generate_light_color()
            color = (r, g, b, 128)

            if color in colour_dict:
                continue

            colour_dict[user_ids[incr]] = color
            incr += 1

        return colour_dict

    def get_unique_ids():
        """
        Makes a unique list of user ids from the week_data
        :return: list of unique ids
        """
        unique_ids = []
        for week_data_item in week_data:
            if week_data_item.user_id not in unique_ids:
                unique_ids.append(week_data_item.user_id)
        return unique_ids

    def get_time_index(time_string):
        """
        Get time index of the time string.
        :param time_string: time string in the format of 8:30 am
        :return: index of that string
        """
        time_string = time_string.lower()
        time_match = re.match(time_regex_string, time_string)
        time_i = 0 if time_match.group(3) == "am" else 24
        time_i += (int(time_match.group(1)) % 12) * 2
        time_i += 0 if time_match.group(2) == "00" else 1
        return time_i

    week_data = sorted(week_data, key = lambda wd: wd.date)

    background_width = 2300

    # Get unique ids and count
    unique_ids = get_unique_ids()
    unique_id_count = len(unique_ids)

    # Get colour table
    colour_table = generate_colour_table(unique_ids)
    image_size = background_width if len(colour_table) < 2 else background_width + 400, 2500
    # Generates the white background
    background = Image.new('RGBA', image_size, color=(255, 255, 255, 255))
    # Sets drawing canvas to the background
    draw = ImageDraw.Draw(background)
    # Load pixels for line drawing
    pixels = background.load()

    # Populate row headers and draw horizontal lines
    for rowIndex in range(48):
        # Add row header
        text = str(rowIndex % 24 // 2)
        if text == "0":
            text = "12"
        text += ":00" if rowIndex % 2 == 0 else ":30"
        text += " am" if rowIndex < 24 else " pm"
        draw.text((100, 135 + (rowIndex * 50)), text, font=row_header_font, fill=(0, 0, 0), anchor="ms")

        # Add horizontal line
        for x in range(background_width):
            pixels[x, 100 + (rowIndex * 50)] = (0, 0, 0)

    # Populate column headers and draw vertical lines
    for colIndex, day in enumerate(days_of_week):
        #add column header
        draw.text((350 + (colIndex * 300), 45), f"{week_dates[colIndex].strftime('%b %d')}\n{day}", font=col_header_font, fill=(0, 0, 0), anchor="ms")

        # Add vertical lines
        for y in range(background.height):
            pixels[200 + (colIndex * 300), y] = (0, 0, 0)

    # Save empty schedule if no week data exists
    if not week_data:
        # Ensure folder exists
        os.makedirs('generated_images', exist_ok=True)
        # Save and show the result
        background.save('generated_images/schedule.png')
        return

    # Add a rectangle for each slot
    for day in week_data:
        # Create a new overlay for the rectangle
        overlay = Image.new('RGBA', image_size, color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)

        # Convert start and end times to y positions
        y_indices = []
        for day_time in [day.start_time, day.end_time]:
            y_indices.append(100 + (get_time_index(day_time) * 50))

        # Draw rectangle on the overlay
        date_obj = datetime.strptime(day.date, '%Y-%m-%d')
        day_of_week = date_obj.strftime('%A')
        draw.rectangle([(200 + (days_of_week.index(day_of_week) * 300), y_indices[0]),
                        (500 + (days_of_week.index(day_of_week) * 300), y_indices[1])],
                       fill=colour_table[day.user_id])

        # Composite this overlay onto the background
        background = Image.alpha_composite(background, overlay)

    # Display the number of overlaps in each cell
    if show_overlap_count and unique_id_count > 1:
        draw = ImageDraw.Draw(background)
        # Nested loop to iterate through each cell
        for colIndex, day_in_week in enumerate(days_of_week):
            for time_index in range(48):
                count = len([time_slot for time_slot in week_data if get_time_index(time_slot.start_time) <= time_index < get_time_index(time_slot.end_time) and datetime.strptime(time_slot.date, '%Y-%m-%d').strftime('%A') == day_in_week])
                if count != 0:
                    draw.text((350 + (colIndex * 300), 135 + (time_index * 50)), str(count), font=row_header_font, fill=(0, 0, 0), anchor="ms")

    # Show legend if more than 1 person is being displayed
    if unique_id_count > 1:
        # Add another vertical line separating the legend
        pixels = background.load()
        for y in range(background.height):
            pixels[200 + (len(days_of_week * 300)), y] = (0, 0, 0)

        #Add legend
        overlay = Image.new('RGBA', image_size, color=(255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        for user_id_index, user_id in enumerate(unique_ids):
            user = await bot.fetch_user(user_id)
            # Back color
            draw.rectangle([(background_width, user_id_index * 50), (background_width + 400, 50 + (user_id_index * 50))], fill=colour_table[user_id])
            draw.text((background_width + 200, 35 + (user_id_index * 50)), user.display_name, font=row_header_font, fill=(0,0,0), anchor="ms")

        # Composite this overlay onto the background
        background = Image.alpha_composite(background, overlay)

    # Ensure folder exists
    os.makedirs('generated_images', exist_ok=True)
    # Save and show the result
    background.save('generated_images/schedule.png')

def db_add_availability(user_id, date, start_date_time, end_date_time, recurring):
    """
    Add availability to database
    :param user_id: user id of the availability
    :param start_date_time: start time
    :param end_date_time: end time
    :param recurring: false, daily, weekly, monthly, yearly
    :return: none
    """
    try:
        query = "INSERT INTO availability VALUES (?, ?, ?, ?, ?)"
        cursor.execute(query, (user_id, date, start_date_time, end_date_time, recurring))
        database.commit()
    except Exception as ex:
        print(f"problem\n{ex}")

def db_get_availability(user_id):
    """
    Get all the availabilities set for that user id.
    :param user_id: user id to get availabilities for
    :return: all the related availabilities
    """
    query = "SELECT * FROM availability WHERE USERID = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()

def db_get_all_availabilities():
    """
    Get all the availabilities
    :return: list of tuples
    """
    query = "SELECT * FROM availability"
    cursor.execute(query)
    return cursor.fetchall()

def db_edit_availability(old_row, new_row):
    """
    Make edits to a row
    :param old_row:
    :param new_row:
    :return:
    """
    new_user_id, new_date, new_start_time, new_end_time, new_recurring = new_row

    try:
        query = """UPDATE availability 
                   SET AVAILABILITYDATE = ?, StartTime = ?, EndTime = ?,  RECURRING = ?
                   WHERE USERID = ? and AVAILABILITYDATE = ? and StartTime = ? and EndTime = ? and RECURRING = ?"""
        cursor.execute(query, (new_date, new_start_time, new_end_time, new_recurring, *old_row))
        database.commit()
    except Exception as ex:
        print(f"Problem with updating database\n{ex}")