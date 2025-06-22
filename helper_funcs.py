import datetime
import pytz
from dotenv import load_dotenv, set_key
import os
import requests
import json

def get_time(timezone) : 
    tz = pytz.timezone(timezone)
    return tz.localize(datetime.datetime.now())

def load_env():
    #reads .env file
    load_dotenv()
    #grabs env variables
    token = os.getenv('DISCORD_TOKEN')
    guild = os.getenv('GUILD_ID')

    return token, guild

def country_check(country) :
    VALID = ['US', 'JP', 'CN', 'CA', 'MX'] #United States, Japan, China, Canada, Mexico
    if country in VALID :
        return True
    else :
        return False

#API call to get location information
def get_location(zipOrCity, country) : 
    check = country_check(country)

    response = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={zipOrCity}&count=1&language=en&format=json&countryCode={country}")
    data = response.json()

    if 'results' not in data or check is False :
        return None
    else :
        info = data['results'][0]
        lat = info['latitude']
        log = info['longitude']
        timezone = info['timezone'] 
        
        output = {
            "zipOrCity" : zipOrCity,
            "country" : country,
            "timezone" : timezone,
            "lat" : lat,
            "log" : log
        }
        
        return output

def add_config(info) :
    json_object = json.dumps(info, indent=4)
    with open("config.json", "w") as f :
        f.write(json_object)

def append_config(key,value) :
    with open("config.json", "r") as f:
        data = json.load(f)
        data[key] = value
    with open("config.json", "w") as ff :
        json.dump(data, ff, indent=4)

def get_config() :
    try: 
        with open("config.json", "r") as f :
            json_object = json.load(f)
            return json_object
    except json.JSONDecodeError:
        return None