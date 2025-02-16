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
        
    @app_commands.command(name="set-availability", description="Set your availability for a specific time period")
    async def setAvailability(self, interaction: discord.Interaction, start: str, end: str, repeating: bool):
        """
        Set the availability for a specific time period

        Returns:
            (userID, start date_time, end date_time, repeating) if the message is in the correct format
            -1 otherwise
        """
        try:
            if not self._correctFormat(start) or not self._correctFormat(end):  # verify if start and end correctly formatted
                raise Exception("Invalid date_time format.")
            
            await interaction.response.send_message(f"userID: {interaction.user.id} Start: {start}, End: {end}, Repeating: {repeating}")  # test command remove later
            return (interaction.user.id, start, end, repeating)
        
        except Exception as exception:
            await interaction.response.send_message(f"{exception} Please provide the date_time in the following format: YYYY-MM-DD HH:MM")
            return -1


async def setup(bot):
    await bot.add_cog(Availability(bot))


