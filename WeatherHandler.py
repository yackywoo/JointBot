import requests
import pandas as pd
from datetime import datetime, timedelta
import os
import joblib

import helper_funcs
import ml

conditions = [
                "temperature_2m", "relative_humidity_2m", "dew_point_2m",
                "apparent_temperature", "precipitation_probability", "precipitation",
                "rain", "showers", "snowfall", "snow_depth", "weather_code",
                "pressure_msl", "surface_pressure", "cloud_cover", "cloud_cover_low",
                "cloud_cover_mid", "cloud_cover_high", "visibility",
                "evapotranspiration", "et0_fao_evapotranspiration",
                "vapour_pressure_deficit"
            ]

class WeatherHandler:
    """
    Encapsulates weather data fetching, initialization of the data store,
    and logging of user-reported pain levels alongside the weather data.
    """

    def __init__(self, csv_path='data.csv', pain_model='pain_model.pkl'):
        self.csv_path = csv_path
        self.pain_model = pain_model
        if os.path.isfile(csv_path) == False:
            self.init_data()

    def get_weather(self, past:str, future:str):
        """Fetches hourly weather data from the Open-Meteo API."""
        config = helper_funcs.get_config()
        if config is None:
            return

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": config['lat'],
            "longitude": config['log'],
            "hourly": ",".join(conditions),
            "timezone": config['timezone'],
            "start_date": f"{past}",
            "end_date": f"{future}"
        }

        response = requests.get(url, params=params)
        return response.json()

    def init_data(self):
        """Initializes the CSV file with weather data and a placeholder pain_level column."""
        today = datetime.now()
        today_date = today.date()
        next_week = today_date + timedelta(days=7)

        data = self.get_weather(str(today_date),str(next_week))
        custom_data = self.add_columns(data)
        custom_data.to_csv(self.csv_path, index_label='time')

        #adds to config.json, previous_time = today at current time
        today_str = self._clean_timestamp(str(today))
        helper_funcs.append_config('previous_time',str(today_str)) #correct
        self.routine()

        print(f"{self.csv_path} initalized")

    def _clean_timestamp(self, timestamp: str) :
        """
        Rounds timestamp to the nearest hour where cutoff is 30 minutes.
        """
        ts = datetime.fromisoformat(timestamp)
        if int(ts.minute) >= 30 : 
            one_hour = timedelta(hours=1)
            ts = ts + one_hour
        
        clean_ts = ts.replace(minute=0,second=0,microsecond=0)
        return clean_ts

    def log_pain(self, timestamp: str, pain_level: float):
        """
        Records a new pain_level entry at `timestamp`, interpolating or
        filling previous entries as needed.
        """
        prev_ts = self._get_previous_timestamp()
        clean_ts = self._clean_timestamp(timestamp)
        self.update_pain(clean_ts, pain_level, prev_ts)

    def _get_previous_timestamp(self):
        """Retrieves the last-logged timestamp from the config."""
        config = helper_funcs.get_config()
        return config.get('previous_time') if config and 'previous_time' in config else None

    def update_pain(self, timestamp: str, pain_level: float, prev_timestamp: str):
        """
        Updates the CSV:
        - If prev_timestamp exists, fills in the pain_level from prev_timestamp to timestamp,
          handling day boundaries.
        - Otherwise, simply logs the pain_level at timestamp.
        """
        df = pd.read_csv(self.csv_path, index_col='time', parse_dates=['time'])
        
        start_idx = df.index.get_loc(prev_timestamp)
        end_idx = df.index.get_loc(timestamp)

        d1 = datetime.fromisoformat(prev_timestamp)
        d2 = datetime.fromisoformat(str(timestamp))
        delta = d2 - d1
        
        #only needed when backfilling / interpolating
        prev_pain = df.iloc[start_idx]['pain_level']

        if start_idx == end_idx : 
            df.iloc[start_idx, df.columns.get_loc('pain_level')] = pain_level
            print(f"Pain logged for [{timestamp} @ {float(pain_level)}]")
        elif delta.days > 0:
            # Fill prev_timestamp's day for same pain_level (end abruptly prev time at EOD)
            eod = prev_timestamp[:-8] + "23:00:00"
            eod_idx = df.index.get_loc(eod) 
            df.iloc[start_idx:(eod_idx+1), df.columns.get_loc('pain_level')] = prev_pain
            # Log new pain_level
            df.iloc[end_idx, df.columns.get_loc('pain_level')] = pain_level
            print(f"Pain backfilled for [{eod} @ {float(prev_pain)}] AND logged for [{timestamp} @ {float(pain_level)}]")

        else:
            # Interpolate linearly between prev and current
            step = self._normalize_pain(prev_pain, pain_level, start_idx, end_idx)
            for i in range(start_idx, end_idx + 1):
                df.iloc[i, df.columns.get_loc('pain_level')] = round(
                    prev_pain - (step * (i - start_idx)), 1
                )
            print(f"Pain logged from [{prev_timestamp} @ {prev_pain}] to [{timestamp} @ {float(pain_level)}]")
     
        helper_funcs.append_config('previous_time', str(timestamp))
        df.to_csv(self.csv_path)

    def _normalize_pain(self, prev_pain: float, curr_pain: float, start_idx: int, end_idx: int) -> float:
        """
        Calculates the per-hour decrement between prev_pain and curr_pain
        over the interval [start_idx, end_idx].
        """
        hours = end_idx - start_idx
        return 0 if hours == 0 else (prev_pain - curr_pain) / hours

    def add_columns(self, data) : 
        cols = list(data['hourly'].keys())
        cols.insert(1, "pain_level")
        cols.insert(2, "predicted_pain")
        cols.insert(3, "is_actual")

        df = pd.DataFrame(columns=cols)
        for category, values in data['hourly'].items():
            df[category] = values

        df['pain_level'] = 0.0
        df['predicted_pain'] = 0.0
        df['is_actual'] = False
        df['time'] = pd.to_datetime(df['time'])

        return df.set_index('time')
    
    def _update_features(self, new_features, time) :
        #new_features = raw weather data, json object
        #time = index to stop at
        new_forecast = self.add_columns(new_features)
        current_data = pd.read_csv(self.csv_path, index_col='time', parse_dates=['time'])
        
        '''
        get overlapping indices of current_data (from data.csv) 
        and new_forceast (API call for next week's data)

        then overwrite current_data's conditions (default columns, excludes my additional cols)
        with new_forecast's updated weather conditions
        '''
        overlap = current_data.index.intersection(new_forecast.index)
        current_data.loc[overlap, conditions] = new_forecast.loc[overlap, conditions]
       
        '''
        update values for 'is_actual' column from [prev_update_day @ 12AM, todays_date @ AM/PM] to be TRUE
        '''
        start = current_data.index[0]
        end = time
        current_data.loc[start:end, 'is_actual'] = True

        '''
        this is all new, relative to [current_data]

        get disjoint set of indices from new_forecast (=new_indices)
        then use those new_indices to copy new_forecast's values (=new_rows)
        finally append those new_rows onto our current_data (=updated_data)
        '''
        #there shouldn't be new rows, but if there are, its handled gracefully
        new_indices = new_forecast.index.difference(current_data.index) #bunch of timedate objects
        new_rows = new_forecast.loc[new_indices] 
        
        updated_data = pd.concat([current_data, new_rows])
        updated_data = updated_data.sort_index()
        updated_data.to_csv(self.csv_path)

        print(f'Actuals updated from [{start}] to [{end}]')


    #updates and adds weather data from range[start_date,end_date] into data.csv
    def _update_forecast_range(self, start_date ,end_date) :
        data = self.get_weather(str(start_date.date()), str(end_date.date()))

        new_forecast = self.add_columns(data)
        current_data = pd.read_csv(self.csv_path, index_col='time', parse_dates=['time'])
        
        '''
        get overlapping indices of current_data (from data.csv) 
        and new_forceast (API call for next week's data)

        then overwrite current_data's conditions (default columns, excludes my additional cols)
        with new_forecast's updated weather conditions
        '''
        overlap = current_data.index.intersection(new_forecast.index)
        current_data.loc[overlap, conditions] = new_forecast.loc[overlap, conditions]

        #update 'is_actual' to be true up until NOW 
        now = self._clean_timestamp(str(datetime.now()))
        start = current_data.index[0]
        current_data.loc[start:now, 'is_actual'] = True

        '''
        this is all new, relative to [current_data]

        get disjoint set of indices from new_forecast (=new_indices)
        then use those new_indices to copy new_forecast's values (=new_rows)
        finally append those new_rows onto our current_data
        '''
        new_indices = new_forecast.index.difference(current_data.index) #bunch of timedate objects
        new_rows = new_forecast.loc[new_indices] 

        updated_data = pd.concat([current_data, new_rows])
        updated_data = updated_data.sort_index()
        updated_data.to_csv(self.csv_path)

        print(f'Actuals updated from [{str(start_date.date())}] to [{end_date.date()}]')

    #updates range[previous_time (in config.json) : ceiling(current_day_time)] weather data
    #difference is this one stops at a specific hour ? redundant?
    def _update_forecast_hour(self, current_time) : 
        prev_update_time = helper_funcs.get_config()['previous_time']
                
        prev_date = prev_update_time[0:10]
        curr_date = str(current_time.date())

        data = self.get_weather(prev_date, curr_date)
        self._update_features(data, current_time)

    def routine(self) :
        now_ts = self._clean_timestamp(str(datetime.now()))
        hour = int(now_ts.hour)
        
        # this runs when actuals for for current hour matter like pain log / forecasting 
        if hour == hour :
            self.intraday_routine(now_ts)
        # # day just ended - update actuals for prev day & get forecast for next week
        if hour == hour :
            yesterday = now_ts - timedelta(days=1)
            next_week = now_ts + timedelta(days=7)
            self.forecast_routine(yesterday, now_ts, next_week)
    
    def intraday_routine(self, time) : 
        self._update_forecast_hour(time)
        print(f'Intraday update finished at [{datetime.now()}]')

    def forecast_routine(self, past, now, future) : 
        # update yesterdays actuals (weather)
        self._update_forecast_range(past, past) 
        # update next weeks forecast (weather)
        self._update_forecast_range(now, future) 
        # update next weeks forecast (pain) if painmodel exists
        if os.path.isfile(self.pain_model) == True:
            self.model_pain(False)
        print(f'Forecast update finished at [{datetime.now()}]')

    def model_pain(self, is_actual:bool) : 
        try :
            model = joblib.load(self.pain_model)
            print(f"Loaded model : {self.pain_model}")  
        except Exception as e: 
            print(f"Model load error : {e}")
            return
        
        try : 
            forecast = ml.preprocess(self.csv_path, is_actual)
            print(f"Preprocessed CSV : {self.csv_path}")
        except Exception as e: 
            print(f"Preprocess error : {e}")
            return
        
        try :
            features = forecast[model.feature_names_in_]
        except Exception as e: 
            print(f"Missing feature(s) : {e}")
            return


        forecast['predicted_pain'] = model.predict(features)
        forecast['predicted_pain'] = forecast['predicted_pain'].round(1).round()

        df = pd.read_csv(self.csv_path, index_col='time', parse_dates=['time'])
        indicies = df[df['is_actual']== is_actual].index
        df.loc[indicies,'predicted_pain'] = forecast['predicted_pain'].values
        df = df.sort_index()
        df.to_csv(self.csv_path)

    def get_forecast(self) : 
        self.routine()
        df = pd.read_csv(self.csv_path, index_col='time', parse_dates=['time'])

        df = df[df['is_actual']==False]
        df['date'] = df.index.normalize()
        dates = df.index.normalize().unique()
    
        pain_forecast = {}

        for date in dates : 
            date = str(date)[0:10]
            filtered = df[df['date']==date]
            max_pain = filtered['predicted_pain'].max()
            pain_forecast[date] = pain_forecast.get(date,int(max_pain))

        return pain_forecast
    
    def see_stats(self) : 
        return ml.get_stats(self.csv_path)
    
    def update_model(self) :
        ml.update_model(self.csv_path, self.pain_model)    