import discord
from discord.ext import commands

class Availability(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print("Bot is online!")

    #replace with availability commands
    @commands.command()
    async def cmd2(self, ctx):
        await ctx.send("Pong!!")

async def setup(bot):
    await bot.add_cog(Availability(bot))