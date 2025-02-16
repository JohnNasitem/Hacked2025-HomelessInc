import discord
from discord.ext import commands
from discord import app_commands
import os
from dotenv import load_dotenv
import asyncio

#stuff to initialize in main ig 
load_dotenv()


class Client(commands.Bot):
    async def on_ready(self):
        print(f'Logged on as {self.user}!')

        #try loop syncs the bot and commands
        try:
            guild = discord.Object(1340369941001539636)
            synced = await self.tree.sync(guild=guild)
            print(f'synced {len(synced)} commands to guild {guild.id}')
        except Exception as e:
            print(f'Error syncing commands:{e}')

    # extra stuff can test around with i think idfk
    async def on_message(self,message):
        if message.author == self.user:
            return

        if message.content.startswith('hello'):
            await message.channel.send(f'hi there {message.author}')
        
    async def on_reaction_add(self,reaction,user):
        await reaction.message.channel.send('you reacted')

TOKEN = os.getenv("BOT_TOKEN")
intents = discord.Intents.default()
intents.message_content = True
client = Client(command_prefix="!", intents=intents)

#grab server id, dont make /commands global cause it will take a long time to update every server 
# it is in when running the code, prob doesnt matter cause its only in 1 server
#1340369941001539636 -> hackathon serverid
Guild_ID = discord.Object(id=1340369941001539636)

#how to create a slash command, specify name and description, and guild (pretty much server specific obj)

@client.tree.command(name="hello", description = "say hello", guild=Guild_ID)
async def sayHello(interaction: discord.Interaction):
    #respond to where-ever the slash prompt was sent
    await interaction.response.send_message("hello")



# example of slash command where you have the user passing info into command
@client.tree.command(name="printer", description = "prints whatever you give it", guild=Guild_ID)
async def sayHello(interaction: discord.Interaction, printer: str, num: int):
    #respond to where-ever the slash prompt was sent
    await interaction.response.send_message(printer, num)



client.run(TOKEN)