import discord
from discord.ext import commands

class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online!")

    #replace with events commands
    @commands.command()
    async def cmd(self, ctx):
        await ctx.send("Pong!!")

async def setup(bot):
    await bot.add_cog(Event(bot))