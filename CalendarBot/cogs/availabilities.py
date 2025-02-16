import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont

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

    # replace with availability commands
    @commands.command()
    async def image(self, ctx):
        img = Image.new('RGB', (200, 100), color = (255, 0, 0))
        draw = ImageDraw.Draw(img)
        img.save('generated_images/test.png')

        with open('generated_images/test.png', 'rb') as f:
            await ctx.send("Here is your image!",file=discord.File(f))

async def setup(bot):
    await bot.add_cog(Availability(bot))


