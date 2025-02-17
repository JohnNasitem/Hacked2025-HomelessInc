import asyncio
import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
from discord import app_commands
from math import ceil

load_dotenv()

class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged in as {self.user}')

        # sync slash commands
        try:
            guildID = discord.Object(id=1340369941001539636)
            synced_commands = await bot.tree.sync()
            print(f"Synced {len(synced_commands)} commands")
        except Exception as e:
            print(f"Failed to sync commands: {e}")


TOKEN = os.getenv("BOT_TOKEN")
intents = discord.Intents.all()
intents.message_content = True  # Enable message content intent
bot = Client(command_prefix="!", intents=intents)

async def load():
    cogs_dir = os.path.join(os.path.dirname(__file__), 'cogs')
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py"):
            await bot.load_extension(f'cogs.{filename[:-3]}')

class PaginationView(discord.ui.View):
    current_page: int = 1  # default current page starts at 1
    separator: int = 5  # how many items are shown per page by default

    async def send(self, ctx):
        self.message = await ctx.send(view=self)  # send our view, the reference itself
        await self.update_message(self.data[:self.separator])
    
    def create_embed(self, data):
        embed = discord.Embed(title="Example")
        for item in data:
            embed.add_field(name=item, value=item, inline=False)
        return embed

    async def update_message(self, data):
        self.update_buttons()
        await self.message.edit(embed=self.create_embed(data), view=self)

    def update_buttons(self):
        if self.current_page == 1:
            self.first_page_button.disable = True
            self.prev_button.disabled = True
        else:
            self.first_page_button.disabled = False
            self.prev_page_button.disabled = False
        
        if self.current_page == ceil(len(self.data) / self.separator):
            self.next_button.disabled = True
            self.last_page_button.disabled = True
        else:
            self.next_button.disabled = False
            self.last_page_button.disabled = False


    # create four buttons |< < > >|
    @discord.ui.button(label="|<",
                       style=discord.ButtonStyle.primary)
    async def first_page_button(self, interaction: discord.Interaction, buton: discord.ui.Button):
        await interaction.response.defer()  # disc always expects ar esponse so delay response
        self.current_page = 1
        until_item = self.currentpage * self.separator
        from_item = until_item - self.separator
        await self.update_message(self.data[:until_item])

    @discord.ui.button(label="<",
                       style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, buton: discord.ui.Button):
        await interaction.response.defer()  # disc always expects ar esponse so delay response
        self.current_page -= 1
        until_item = self.currentpage * self.separator
        from_item = until_item - self.separator
        await self.update_message(self.data[from_item:until_item])

    @discord.ui.button(label=">",
                       style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, buton: discord.ui.Button):
        await interaction.response.defer()  # disc always expects ar esponse so delay response
        self.current_page += 1
        until_item = self.currentpage * self.separator
        from_item = until_item - self.separator
        await self.update_message(self.data[from_item:until_item])
    
    @discord.ui.button(label=">|",
                       style=discord.ButtonStyle.primary)
    async def last_page_button(self, interaction: discord.Interaction, buton: discord.ui.Button):
        await interaction.response.defer()  # disc always expects ar esponse so delay response
        self.current_page = ceil(len(self.data) / self.separator)
        until_item = self.currentpage * self.separator
        from_item = until_item - self.separator
        await self.update_message(self.data[from_item:])
    


@bot.command()
async def paginate(ctx):
    data = range(1, 15)
    pagination_view = PaginationView()  # custom class for pagination
    pagination_view.data = data  # set the data
    await pagination_view.send(ctx)  # custom context send

async def main():
    await load()
    await bot.start(TOKEN)

asyncio.run(main())

