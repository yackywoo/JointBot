import requests
import pandas as pd
import csv
from datetime import datetime
import helper_funcs



def get_weather():
    info = helper_funcs.get_config()
    if info is None :
        return
    
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude" : info['lat'],
        "longitude" : info['log'],
        "hourly" : ",".join([
            "temperature_2m", "relative_humidity_2m", "dew_point_2m",
            "apparent_temperature", "precipitation_probability", "precipitation",
            "rain", "showers", "snowfall", "snow_depth", "weather_code",
            "pressure_msl", "surface_pressure", "cloud_cover", "cloud_cover_low",
            "cloud_cover_mid", "cloud_cover_high", "visibility",
            "evapotranspiration", "et0_fao_evapotranspiration",
            "vapour_pressure_deficit"
        ]),
        "timezone": info['timezone'],
        "start_date" : "2025-05-21",
        "end_date" : "2025-05-25"
    } 

    response = requests.get(url, params=params)
    data = response.json()
    #no date range means give next WEEKS worth of forecast, hourly
    return data

def init_data() :
    data = get_weather()
    cols_keys = data['hourly'].keys()
    cols = list(cols_keys)
    cols.insert(1,"pain_level")

    df = pd.DataFrame(columns=cols)
    for category in data['hourly'] :
        df[category] = data['hourly'][category]
    df['pain_level'] = float(0.0)
    
    df.set_index('time').to_csv('data.csv')

def log_pain(logged_time, painlevel) : 
    prev_time = get_prev_info(logged_time)
    update_pain(logged_time, painlevel, prev_time)


def get_prev_info(current_time) : 
    config = helper_funcs.get_config() 

    if 'previous_time' not in config :
        return None
    else :
        return config['previous_time']

def update_pain(curr_time, painlevel, prev_time=None) : 
    #read csv
    df = pd.read_csv('data.csv', index_col='time', parse_dates=['time'])
    end = df.index.get_loc(curr_time)
    
    #if continuing 1 pain recording
    if prev_time is not None :
        print("HELO")
        start = df.index.get_loc(prev_time)

        date1 = datetime.fromisoformat(prev_time)
        date2 = datetime.fromisoformat(curr_time)
        diff = date2-date1
        
        prev_pain = df.iloc[start]['pain_level']
        #if more than a day elapsed since last pain, cut off prev pain at EOD
        if diff.days > 0 :
            EOD_prev_time = prev_time[:-5:] + "23:00"
            EOD_index = df.index.get_loc(EOD_prev_time) + 1

            #finish recording prev day's pain
            df.iloc[start:EOD_index, df.columns.get_loc('pain_level')] = prev_pain
            #record curr pain
            df.iloc[end, df.columns.get_loc('pain_level')] = painlevel
        else : 
            #else fill in gaps with prev pain if less than a day has passed            
            delta_pain = normalize_pain(prev_pain, painlevel, start, end)
            for i in range(start,end+1) :
                df.iloc[i, df.columns.get_loc('pain_level')] = round(float(prev_pain) - (delta_pain * (i - start)), 1)
        
        helper_funcs.append_config('previous_time', curr_time)
    else : #edge case for first recording trip
        df.iloc[end, df.columns.get_loc('pain_level')] = painlevel
        helper_funcs.append_config('previous_time', curr_time)
    
    df.to_csv("data.csv")

def normalize_pain(prev_pain, curr_pain, start_index, end_index) :
    inbetween_hours = end_index - start_index 
    if inbetween_hours == 0 : 
        return 0
    return (prev_pain-curr_pain) / inbetween_hours

# init_data()
log_pain('2025-05-25T10:00', 10)

class WeatherHandler : 
    def __init__(self, feed_url):
        self