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
    
    @commands.command()
    async def sync(self, ctx):
        """
        Sync slash commands for the guild
        """
        try:
            synced_commands = await ctx.bot.tree.sync(guild=ctx.guild)
            await ctx.sendd(f"Synced {len(synced_commands)} commands")
            print(f"Synced {len(synced_commands)} commands")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

async def setup(bot):
    await bot.add_cog(Ping(bot))