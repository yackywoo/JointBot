import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio

import helper_funcs
import WeatherHandler

#init objects + grab .env variables
token, guild = helper_funcs.load_env()
guild_id=discord.Object(id=guild)
weatherBot=WeatherHandler.WeatherHandler()

#set logging and intents (permissions)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
intents = discord.Intents.default()
intents.message_content=True
intents.members=True

bot = commands.Bot(command_prefix='!', intents=intents)
followup_task: asyncio.Task | None = None
emojis = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]


class PainLevelSelect(discord.ui.Select):
    def __init__(self): 
        options = [
            discord.SelectOption(label=str(i), value=i, emoji=emojis[int(i)])
            for i in range(len(emojis))
        ]
        super().__init__(placeholder="Updated Pain (0-10)", min_values=1, max_values=1, options=options, custom_id="string_select")

    async def callback(self, interaction: discord.Interaction) :
        updated_pain = self.values[0]
        await handle_pain(interaction, int(updated_pain))
        await interaction.message.delete()

class PainLevelView(discord.ui.View) :
    def __init__(self,timeout=1) : 
        super().__init__()
        self.add_item(PainLevelSelect())

@bot.event
async def on_ready(): 
    await bot.tree.sync(guild=guild_id)
    print(f"{bot.user.name} LOADED")

@bot.tree.command(name="local", description="Set location parameters", guild=guild_id)
@app_commands.describe(zip_or_city="Zipcode / City to use for joint and weather forecasts", country = "Country to use for joint and weather forecasts")
async def local (interaction: discord.Interaction, zip_or_city: str, country: str) :
    if len(country) != 2 :
        await interaction.response.send_message("❌ - Invalid country code, provide 2 letter country code")
        return
    
    check = helper_funcs.get_location(zip_or_city.upper(), country.upper()) 

    if check is None :
        await interaction.response.send_message("❌ - Invalid zipcode or city provided, try again")
    elif check != None :
        for key,value in check.items() :
            helper_funcs.append_config(key,value)
        local_zipOrCity = check['zipOrCity']
        local_country = check['country']
        await interaction.response.send_message(f"✅ - Zipcode / City has changed to {local_zipOrCity}, {local_country} by {interaction.user.mention}")
    else :
        await interaction.response.send_message(f"❌ - Zipcode / City error, try again")

    
@bot.tree.command(name="location", guild=guild_id) 
async def location (interaction: discord.Interaction) :
    info = helper_funcs.get_config()
    if info is None :
        await interaction.response.send_message("Use '/local' to set location information first")
    else :
        zipOrCity = info['zipOrCity']
        country = info['country']
        timezone = info['timezone']
        lat = info['lat']
        log = info['log']
        await interaction.response.send_message(f"Zip / City={zipOrCity}\nCountry={country}\nTimezone={timezone}\nCoords=({lat},{log})") 

async def send_followup(interaction, painlevel) :
    high = 7
    medium = 4
    
    wait_hours = {
        high:10,
        medium:20
    }
    
    if painlevel >= high : 
        hours = wait_hours[high]
    elif painlevel >= medium :
        hours = wait_hours[medium]
    else : #painlevel == low -> no followup
        return

    await interaction.followup.send(f"✅ - Follow up will be sent in {hours} hours", ephemeral=True)
    await asyncio.sleep(hours * 60 * 60) #actual wait time

    await interaction.followup.send(f"👩🏻‍⚕️ - How are you feeling now? 🤒 {interaction.user.mention}", view=PainLevelView()) 


@bot.tree.command(name="pain", description="Level of joint pain", guild=guild_id)
@app_commands.describe(pain_level="Rate pain level from 1-10")
async def pain (interaction: discord.Interaction, pain_level: int) : 
    await handle_pain(interaction, pain_level)


@bot.tree.command(name="updatemodel", description="Update model - consider doing when R2 and MSE look good.", guild=guild_id)
async def update_model(interaction: discord.Interaction) :
    before = get_forecast()
    weatherBot.update_model()
    after = get_forecast()
    await interaction.response.send_message(f"\n**__BEFORE__** :{before}**__AFTER__** :{after}")


@bot.tree.command(name="stats", description="Testing stats for current actuals", guild=guild_id)
async def stats (interaction: discord.Interaction) :
    stats = weatherBot.see_stats()
    msg = "\n```\n"
    for key,value in stats.items() : 
        msg += f"{key} : {value}\n"
    msg += "```"
    await interaction.response.send_message(msg)

def get_forecast() : 
    forecast = weatherBot.get_forecast()
    msg = "\n**Pain Forecast - Next Week:**\n```"    
    for date, maxpain in forecast.items() :
        msg += f"{date} : {emojis[maxpain]}\n"
    msg += "```"
    return msg

@bot.tree.command(name="forecast", description="Displays next week's max forecasted pain level", guild=guild_id)
async def forecast (interaction: discord.Interaction) : 
    msg = str(get_forecast())
    await interaction.response.send_message(msg)

async def handle_pain(interaction: discord.Interaction, pain_level: int) : 
    info = helper_funcs.get_config()
    if info is None :
        await interaction.response.send_message("Use '/local' to set location information first")
    else :
        if pain_level < 0 or pain_level > 10 :
            await interaction.response.send_message("❌ - Invalid pain level, try again.")
        else :
            global followup_task
            if followup_task and not followup_task.done() : 
                followup_task.cancel()
                
            
            timezone = helper_funcs.get_config()['timezone']
            now = helper_funcs.get_time(timezone)
            date = now.date()
            hour = now.hour
            minute = now.minute
            pain_log = str(date)+"T"+str(hour)+":"+str(minute)+":00"
            await interaction.response.send_message(f"🤕 - Pain level of {emojis[pain_level]} recorded at {str(date)} {str(hour)}:{str(minute)} by {interaction.user.mention}")
            
            weatherBot.log_pain(pain_log, pain_level)
            followup_task = asyncio.create_task(send_followup(interaction, pain_level))


bot.run(token,log_handler=handler, log_level=logging.DEBUG)