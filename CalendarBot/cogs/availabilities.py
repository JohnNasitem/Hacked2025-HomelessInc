import datetime
import discord
import re
import random
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select
from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3
import datetime as dt
from datetime import datetime

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

def discordTime(date_time):
    """
    Convert date_time to a discord timestamp
    """
    return f"<t:{int(datetime.timestamp(date_time))}>" 


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

    # depracated function do not use
    # @staticmethod
    # def _verifyFormat(date, time):
    #     """
    #     Check if date and time is in the following formats respectivel:
    #     YYYY-MM-DD 
    #     HH:MM

    #     Returns:
    #         True if both are in the correct format
    #         False otherwise
    #     """
    #     try:
    #         datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")
    #         return True
    #     except ValueError:
    #         return False
    
    # depracated function do not use
    # @staticmethod
    # def _convertToUnix(date, time):
    #     """
    #     Convert date and time to a Unix timestamp
    #     """
    #     date_time = datetime.strptime(f"{date} {time}", "%Y-%m-%d %I:%M %p")
    #     return int(datetime.timestamp(date_time))

    @staticmethod
    def convert_row_to_day(row):
        result_user_id, availability_date, start_time, end_time, recurring = row
        dt_date = datetime.strptime(availability_date, '%Y-%m-%d')
        return Day(result_user_id, dt_date.strftime('%Y-%m-%d'), start_time, end_time)

    @app_commands.command(name="set-availability", description="Set your availability for a specific time period")
    @app_commands.describe(day="Choose the day you are available (YYYY-MM-DD)",
                           start_time="Choose the time you are available to start (HH:MM AM/PM)",
                           end_time="Choose the time you are available to end (HH:MM AM/PM)",
                           repeating="Choose how often this availability repeats (Default: no repeat)",)
    @app_commands.choices(repeating=[
        discord.app_commands.Choice(name="Does not repeat", value="false"),
        discord.app_commands.Choice(name="Daily", value="daily"),
        discord.app_commands.Choice(name="Weekly", value="weekly"),
        discord.app_commands.Choice(name="Monthly", value="monthly"),
        discord.app_commands.Choice(name="Yearly", value="yearly")
    ])
    async def set_availability(self, interaction: discord.Interaction, start_time: str, end_time: str, day: str=None, repeating: str = "false"):
        """
        Set the availability for a specific time period

        Returns:
            (userID, day, start_time, end_time) if the message is in the correct format
            None otherwise

        shouts out to chris for getting slash commands to work
        """
        try:
            if day is None:
                day = datetime.today().strftime("%Y-%m-%d") 
            # create datetime objects for start and end to simplify
            start_date = datetime.strptime(f"{day} {start_time}", "%Y-%m-%d %I:%M %p")
            end_date = datetime.strptime(f"{day} {end_time}", "%Y-%m-%d %I:%M %p")

            if start_date.timestamp() > end_date.timestamp():  # Check if start time is before end time
                raise Exception("Start time cannot be after end time.")
            
            await interaction.response.send_message(f"Set availability for {interaction.user.mention} from {discordTime(start_date)} to {discordTime(end_date)} repeating: {repeating}")

            db_add_availability(interaction.user.id, day, start_time, end_time, repeating)
        
        except ValueError:
            await interaction.response.send_message("Improperly formatted date or time. Please provide the times in the following format: YYYY-MM-DD HH:MM AM/PM")
        except Exception as exception:
            await interaction.response.send_message(f"{exception} Please provide the times in the following format: YYYY-MM-DD HH:MM AM/PM")
            return None


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

        edit_embed = discord.Embed(
            title = "Edit Availabilities",
            description = "Please select an availability to edit",
            color = interaction.user.colour
        )

        for index,result in enumerate(db_get_availability(interaction.user.id)):
            user_id, date, start_time, end_time, recurring = result  # unpack the tuple

            # create datetime objects for start and end to simplify
            start = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %I:%M %p")
            end = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %I:%M %p")

            edit_embed.add_field(
                name = f"{index + 1} <t:{int(start.timestamp())}:D>",
                value = f"<t:{int(start.timestamp())}:t> to <t:{int(end.timestamp())}:t>",    
                inline=False
            )

        await interaction.response.send_message(embed=edit_embed)

async def setup(bot):
    await bot.add_cog(Availability(bot))

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
                    unfiltered_availabilities_list.append(Availability.convert_row_to_day(result))
        # If users is empty then that means everyone should be considered
        else:
            for result in db_get_all_availabilities():
                unfiltered_availabilities_list.append(Availability.convert_row_to_day(result))

        # Filter out any availabilities not happening this week
        filtered_availabilities_list = []
        for availability in unfiltered_availabilities_list:
            if week_dates[0].strftime('%Y-%m-%d') <= availability.date <= week_dates[6].strftime('%Y-%m-%d'):
                filtered_availabilities_list.append(availability)

        await create_image(bot, filtered_availabilities_list, week_dates)
        with open('generated_images/schedule.png', 'rb') as f:
            await interaction.response.send_message(f"Availabilities>", file=discord.File(f))
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