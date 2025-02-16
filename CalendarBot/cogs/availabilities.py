import datetime
import discord
import re
import random
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont

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
    Day(1, "Monday", "8:00 am", "12:00 pm"),
    Day(1, "Monday", "1:00 pm", "4:00 pm"),
    Day(1, "Tuesday", "9:00 am", "12:00 pm"),
    Day(1, "Wednesday", "7:30 am", "11:30 am"),
    Day(1, "Thursday", "10:00 am", "2:00 pm"),
    Day(1, "Friday", "8:30 am", "12:30 pm"),
    Day(1, "Saturday", "9:00 am", "11:30 am"),
    Day(1, "Sunday", "10:00 am", "12:30 pm"),

    # ID 2 (Person 2)
    Day(2, "Monday", "7:00 am", "11:00 am"),
    Day(2, "Monday", "12:00 pm", "4:00 pm"),
    Day(2, "Tuesday", "8:00 am", "12:00 pm"),
    Day(2, "Wednesday", "6:30 am", "10:30 am"),
    Day(2, "Thursday", "9:00 am", "1:00 pm"),
    Day(2, "Friday", "8:00 am", "12:00 pm"),
    Day(2, "Saturday", "7:30 am", "11:30 am"),
    Day(2, "Sunday", "9:00 am", "12:00 pm"),

    # ID 3 (Person 3)
    Day(3, "Monday", "8:00 am", "12:00 pm"),
    Day(3, "Wednesday", "9:00 am", "1:00 pm"),
    Day(3, "Thursday", "2:00 pm", "5:00 pm"),
    Day(3, "Friday", "10:00 am", "1:00 pm"),
    Day(3, "Saturday", "2:30 pm", "5:30 pm"),
    Day(3, "Sunday", "12:00 pm", "4:00 pm"),

    # ID 4 (Person 4)
    Day(4, "Tuesday", "10:00 am", "1:00 pm"),
    Day(4, "Thursday", "11:00 am", "2:00 pm"),
    Day(4, "Friday", "9:30 am", "12:30 pm"),
    Day(4, "Saturday", "3:00 pm", "6:00 pm"),
    Day(4, "Sunday", "10:00 am", "12:30 pm"),

    # ID 5 (Person 5)
    Day(5, "Monday", "9:00 am", "1:00 pm"),
    Day(5, "Wednesday", "2:00 pm", "5:00 pm"),
    Day(5, "Thursday", "8:00 am", "12:00 pm"),
    Day(5, "Friday", "11:30 am", "2:30 pm"),
    Day(5, "Saturday", "1:00 pm", "4:00 pm"),
    Day(5, "Sunday", "8:00 am", "11:00 am"),
]

class Availability(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online!")

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
            datetime.datetime.strptime(date_time, date_time_format)
            return True
        except ValueError:
            return False
        
    @app_commands.command(name="set-availability", description="Set your availability for a specific time period")
    @app_commands.describe(repeating="Choose how often this availability repeats")
    @app_commands.choices(repeating=[
        discord.app_commands.Choice(name="Daily", value="daily"),
        discord.app_commands.Choice(name="Weekly", value="weekly"),
        discord.app_commands.Choice(name="Monthly", value="monthly")
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
            
            print(f"Repeating: \"{repeating}\"")
            
            await interaction.response.send_message(f"Set availability for <@{interaction.user.id}> from {start} to {end} repeating: {repeating}" + 
                                                    f"\nuserID: {interaction.user.id} Start: {start}, End: {end}, Repeating: {repeating}")
            return interaction.user.id, start, end, repeating
        
        except Exception as exception:
            await interaction.response.send_message(f"{exception} Please provide the date_time in the following format: YYYY-MM-DD HH:MM")
            return None

    @commands.command()
    async def image(self, ctx):
        try:
            create_image(week, True)
            with open('generated_images/schedule.png', 'rb') as f:
                await ctx.send("Here is your image!", file=discord.File(f))
        except Exception as e:
            await ctx.send(f"Couldn't Generate Image\n{e}")

async def setup(bot):
    await bot.add_cog(Availability(bot))

# TODO: Add legend for each color in the color table, dont show if only 1 person is being viewed (or not :shrug:)
def create_image(week_data, show_overlap_count):
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
            Generate light colours
            :return: r, g, b values
            """
            r = random.randint(180, 255)
            g = random.randint(180, 255)
            b = random.randint(180, 255)
            return r, g, b

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
        time_match = re.match(time_regex_string, time_string)
        time_i = 0 if time_match.group(3) == "am" else 24
        time_i += (int(time_match.group(1)) % 12) * 2
        time_i += 0 if time_match.group(2) == "00" else 1
        return time_i

    # Get colour table
    colour_table = generate_colour_table(get_unique_ids())
    # Generates the white background
    background = Image.new('RGBA', (2300, 2500), color=(255, 255, 255, 255))
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
        for x in range(background.width):
            pixels[x, 100 + (rowIndex * 50)] = (0, 0, 0)

    # Populate column headers and draw vertical lines
    for colIndex, day in enumerate(days_of_week):
        #add column header
        draw.text((350 + (colIndex * 300), 60), day, font=col_header_font, fill=(0, 0, 0), anchor="ms")

        # Add vertical lines
        for y in range(background.height):
            pixels[200 + (colIndex * 300), y] = (0, 0, 0)

    # Add a rectangle for each slot
    for day in week:
        # Create a new overlay for the rectangle
        overlay = Image.new('RGBA', (2300, 2500), color=(255, 255, 255, 0))
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
    if show_overlap_count:
        draw = ImageDraw.Draw(background)
        for colIndex, day_in_week in enumerate(days_of_week):
            for time_index in range(48):
                count = len([time_slot for time_slot in week if get_time_index(time_slot.start_time) <= time_index < get_time_index(time_slot.end_time) and time_slot.weekday == day_in_week])
                if count != 0:
                    draw.text((350 + (colIndex * 300), 135 + (time_index * 50)), str(count), font=row_header_font, fill=(0, 0, 0), anchor="ms")

    # Save and show the result
    background.save('generated_images/schedule.png')
