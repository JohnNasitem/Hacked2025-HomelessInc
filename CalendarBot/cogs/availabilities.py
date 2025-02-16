import datetime
import discord
import re
import random
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import os
import sqlite3
from datetime import datetime

database = sqlite3.connect("database.db")
cursor = database.cursor()
database.execute("DROP TABLE IF EXISTS availability")
database.execute("""CREATE TABLE IF NOT EXISTS availability(
                 USERID INTEGER, 
                 StartTime DATETIME,
                 EndTime DATETIME,
                 RECURRING TEXT
                 )""")


col_header_font = ImageFont.truetype("arial.ttf", 50)
row_header_font = ImageFont.truetype("arial.ttf", 30)
days_of_week = [ "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
time_regex_string = r"(\d\d?):(\d\d) (am|pm)"


class Day:
    """
    Holds an availability slot on the selected day for a specific user
    """
    def __init__(self, user_id, weekday, start_time, end_time):
        self.user_id = user_id
        self.weekday = weekday
        self.start_time = start_time
        self.end_time = end_time

#harded coded text values
week = [
    # ID 1 (Person 1)
    Day(357657793215332357, "Monday", "8:00 am", "12:00 pm"),
    Day(357657793215332357, "Monday", "1:00 pm", "4:00 pm"),
    Day(357657793215332357, "Tuesday", "9:00 am", "12:00 pm"),
    Day(357657793215332357, "Wednesday", "7:30 am", "11:30 am"),
    Day(357657793215332357, "Thursday", "10:00 am", "2:00 pm"),
    Day(357657793215332357, "Friday", "8:30 am", "12:30 pm"),
    Day(357657793215332357, "Saturday", "9:00 am", "11:30 am"),
    Day(357657793215332357, "Sunday", "10:00 am", "12:30 pm"),

    # ID 2 (Person 2)
    Day(799817805099827200, "Monday", "7:00 am", "11:00 am"),
    Day(799817805099827200, "Monday", "12:00 pm", "4:00 pm"),
    Day(799817805099827200, "Tuesday", "8:00 am", "12:00 pm"),
    Day(799817805099827200, "Wednesday", "6:30 am", "10:30 am"),
    Day(799817805099827200, "Thursday", "9:00 am", "1:00 pm"),
    Day(799817805099827200, "Friday", "8:00 am", "12:00 pm"),
    Day(799817805099827200, "Saturday", "7:30 am", "11:30 am"),
    Day(799817805099827200, "Sunday", "9:00 am", "12:00 pm"),

    # ID 3 (Person 3)
    Day(183651970526085120, "Monday", "8:00 am", "12:00 pm"),
    Day(183651970526085120, "Wednesday", "9:00 am", "1:00 pm"),
    Day(183651970526085120, "Thursday", "2:00 pm", "5:00 pm"),
    Day(183651970526085120, "Friday", "10:00 am", "1:00 pm"),
    Day(183651970526085120, "Saturday", "2:30 pm", "5:30 pm"),
    Day(183651970526085120, "Sunday", "12:00 pm", "4:00 pm"),

    # ID 4 (Person 4)
    Day(401501356327698434, "Tuesday", "10:00 am", "1:00 pm"),
    Day(401501356327698434, "Thursday", "11:00 am", "2:00 pm"),
    Day(401501356327698434, "Friday", "9:30 am", "12:30 pm"),
    Day(401501356327698434, "Saturday", "3:00 pm", "6:00 pm"),
    Day(401501356327698434, "Sunday", "10:00 am", "12:30 pm"),

    # ID 5 (Person 5)
    Day(381874990783528960, "Monday", "9:00 am", "1:00 pm"),
    Day(381874990783528960, "Wednesday", "2:00 pm", "5:00 pm"),
    Day(381874990783528960, "Thursday", "8:00 am", "12:00 pm"),
    Day(381874990783528960, "Friday", "11:30 am", "2:30 pm"),
    Day(381874990783528960, "Saturday", "1:00 pm", "4:00 pm"),
    Day(381874990783528960, "Sunday", "8:00 am", "11:00 am"),
]

class Availability(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Availability is ready!")

    def _correctFormat(self, date_time):
        """
        Check if date_time is in the following formats:
        YYYY-MM-DD HH:MM

        Returns:
            True if data_time is in the correct format
            False otherwise
        """
        date_time_format = "%Y-%m-%d %H:%M"
        try:
            datetime.strptime(date_time, date_time_format)
            return True
        except ValueError:
            return False

    @staticmethod
    def convert_row_to_day(row):
        """
        Convert a row from the availability table to a day instance
        :param row:
        :return:
        """
        dt_start = datetime.strptime(row[1], '%Y-%m-%d %H:%M')
        dt_end = datetime.strptime(row[2], '%Y-%m-%d %H:%M')
        new_day_user_id = row[0]
        new_day_day_of_week = dt_start.strftime('%A')  # '%A' gives the full weekday name
        new_day_start_time = dt_start.strftime("%I:%M %p")
        new_day_end_time = dt_end.strftime("%I:%M %p")
        return Day(new_day_user_id, new_day_day_of_week, new_day_start_time, new_day_end_time)

    @app_commands.command(name="set-availability", description="Set your availability for a specific time period")
    @app_commands.describe(repeating="Choose how often this availability repeats")
    @app_commands.choices(repeating=[
        discord.app_commands.Choice(name="Does not repeat", value="false"),
        discord.app_commands.Choice(name="Daily", value="daily"),
        discord.app_commands.Choice(name="Weekly", value="weekly"),
        discord.app_commands.Choice(name="Monthly", value="monthly"),
        discord.app_commands.Choice(name="Yearly", value="yearly")
    ])
    async def setAvailability(self, interaction: discord.Interaction, start: str, end: str, repeating: str):
        """
        Set the availability for a specific time period

        Returns:
            (userID, start date_time, end date_time, repeating) if the message is in the correct format
            None otherwise

        shouts out to chris for getting slash commands to work
        """
        try:
            if not self._correctFormat(start) or not self._correctFormat(end):  # verify if start and end correctly formatted
                raise Exception("Invalid date_time format.")
            
            await interaction.response.send_message(f"Set availability for <@{interaction.user.id}> from {start} to {end} repeating: {repeating}")

            #return interaction.user.id, start, end, repeating
            add_availability(interaction.user.id, start, end, repeating)
            add_availability(interaction.user.id, start, end, "false")
        
        except Exception as exception:
            await interaction.response.send_message(f"{exception} Please provide the date_time in the following format: YYYY-MM-DD HH:MM")
            return None

    @app_commands.command(name="get-availability", description="Get availability for a specific user(s)")
    async def getAvailability(self, interaction: discord.Interaction, user: discord.User):
        try:
            week_test = []
            for result in get_availability(user.id):
                week_test.append(Availability.convert_row_to_day(result))
            #await interaction.response.send_message(f"Availability for <@{user.id}>\n{output}")
            await create_image(self.bot, week_test)
            with open('generated_images/schedule.png', 'rb') as f:
                await interaction.response.send_message("Here is your image!", file=discord.File(f))
        except Exception as ex:
            await interaction.response.send_message(f"Something went wrong:\n{ex}")
        
    @commands.command()
    async def image(self, ctx):
        try:
            await create_image(self.bot, week)
            with open('generated_images/schedule.png', 'rb') as f:
                await ctx.send("Here is your image!", file=discord.File(f))
        except Exception as e:
            await ctx.send(f"Couldn't Generate Image\n{e}")

    @app_commands.command(name="embed", description="Send an embed message")
    async def app_embed(self, interaction: discord.Interaction):
        embed = discord.Embed(
            colour=discord.Colour.dark_teal(),
            description="this is the description",
            title="this is the title"
        )

        embed.set_footer(text="this is the footer")
        embed.set_author(name="this is the author")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Availability(bot))

async def create_image(bot, week_data, show_overlap_count = True):
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

        # def generate_light_color():
        #     """
        #     Generate light colours
        #     :return: r, g, b values
        #     """
        #     r_int = random.randint(180, 255)
        #     g_int = random.randint(180, 255)
        #     b_int = random.randint(180, 255)
        #     return r_int, g_int, b_int

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
        draw.text((350 + (colIndex * 300), 60), day, font=col_header_font, fill=(0, 0, 0), anchor="ms")

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
        draw.rectangle([(200 + (days_of_week.index(day.weekday) * 300), y_indices[0]),
                        (500 + (days_of_week.index(day.weekday) * 300), y_indices[1])],
                       fill=colour_table[day.user_id])

        # Composite this overlay onto the background
        background = Image.alpha_composite(background, overlay)

    # Display the number of overlaps in each cell
    if show_overlap_count and unique_id_count > 1:
        draw = ImageDraw.Draw(background)
        # Nested loop to iterate through each cell
        for colIndex, day_in_week in enumerate(days_of_week):
            for time_index in range(48):
                count = len([time_slot for time_slot in week if get_time_index(time_slot.start_time) <= time_index < get_time_index(time_slot.end_time) and time_slot.weekday == day_in_week])
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

def add_availability(user_id, start_date_time, end_date_time, recurring):
    """
    Add availability to database
    :param user_id: user id of the availability
    :param start_date_time: start time
    :param end_date_time: end time
    :param recurring: false, daily, weekly, monthly, yearly
    :return: none
    """
    query = "INSERT INTO availability VALUES (?, ?, ?, ?)"
    cursor.execute(query, (user_id, start_date_time, end_date_time, recurring))
    database.commit()

def get_availability(user_id):
    """
    Get all the availabilities set for that user id.
    :param user_id: user id to get availabilities for
    :return: all the related availabilities
    """
    query = "SELECT * FROM availability WHERE USERID = ?"
    cursor.execute(query, (user_id,))
    return cursor.fetchall()