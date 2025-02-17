import discord
from discord.ext import commands
from discord import app_commands

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Ping is online!")

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction):
        latency = self.bot.latency * 1000  # Convert latency to milliseconds
        await interaction.response.send_message(f"Pong! Latency: {latency:.2f} ms")

async def setup(bot):
    await bot.add_cog(Ping(bot))