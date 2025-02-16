import datetime
import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont

class Availability(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _correctFormat(self, date_time):
        """
        Check if date_time is in the following format:
        YYYY-MM-DD HH:MM

        Returns:
            True if data_time is in the correct format
            False otherwise
        """
        format = "%Y-%m-%d %H:%M"
        try:
            datetime.datetime.strptime(date_time, format)
            return True
        except ValueError:
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online!")

    @commands.command(name="sa")
    async def specificAvailability(self, ctx):
        """
        Parse the message to ge the userID, start date_time and end date_time
        
        Returns:
            (userID, start date_time, end date_time) if the message is in the correct format
            -1 otherwise
        """
        try:
            # tidying up the content before passing it to the logic
            content = ctx.message.content
            no_command = content.replace(f"!{ctx.command.name}", "").strip()  # remove the command part from the content (command removed)
            start_end = no_command.split(",")  # list with start and end datetimes

            if len(start_end) != 2:  # if there are not exactly two date_times
                raise Exception("Invalid number of arguments.")
            
            # remove the extra spaces around start and end date_times
            start = start_end[0].strip()
            end = start_end[1].strip()

            if not self._correctFormat(start) or not self._correctFormat(end):  # verify if start and end correctly formatted
                raise Exception("Invalid date_time format.")
            
            await ctx.send(f"userID: {ctx.author.id} Start: {start}, End: {end}")  # test command remove later
            return (ctx.author.id, start, end)
        
        except Exception as exception:
            await ctx.send(f"{exception} Please provide the date_time in the following format: YYYY-MM-DD HH:MM")
            return -1
        
    @app_commands.command(name="set-availability", description="Set your availability for a specific time period")
    async def setAvailability(self, interaction: discord.Interaction, start: str, end: str):
        """
            
        """
        await interaction.response.send_message("Test")


async def setup(bot):
    await bot.add_cog(Availability(bot))


