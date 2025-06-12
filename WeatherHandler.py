import requests
import pandas as pd
from datetime import datetime, timedelta
import helper_funcs
import os

class WeatherHandler:
    """
    Encapsulates weather data fetching, initialization of the data store,
    and logging of user-reported pain levels alongside the weather data.
    """

    def __init__(self, csv_path='data.csv'):
        self.csv_path = csv_path
        if os.path.isfile(csv_path) == False:
            self.init_data()

    def get_weather(self):
        """Fetches hourly weather data from the Open-Meteo API."""
        config = helper_funcs.get_config()
        if config is None:
            return

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": config['lat'],
            "longitude": config['log'],
            "hourly": ",".join([
                "temperature_2m", "relative_humidity_2m", "dew_point_2m",
                "apparent_temperature", "precipitation_probability", "precipitation",
                "rain", "showers", "snowfall", "snow_depth", "weather_code",
                "pressure_msl", "surface_pressure", "cloud_cover", "cloud_cover_low",
                "cloud_cover_mid", "cloud_cover_high", "visibility",
                "evapotranspiration", "et0_fao_evapotranspiration",
                "vapour_pressure_deficit"
            ]),
            "timezone": config['timezone'],
            "start_date": "2025-05-21",
            "end_date": "2025-05-25"
        }

        response = requests.get(url, params=params)
        return response.json()

    def init_data(self):
        """Initializes the CSV file with weather data and a placeholder pain_level column."""
        data = self.get_weather()
        cols = list(data['hourly'].keys())
        cols.insert(1, "pain_level")

        df = pd.DataFrame(columns=cols)
        for category, values in data['hourly'].items():
            df[category] = values
        df['pain_level'] = 0.0

        df.set_index('time').to_csv(self.csv_path)
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

    def update_pain(self, timestamp: str, pain_level: float, prev_timestamp: str = None):
        """
        Updates the CSV:
        - If prev_timestamp exists, fills in the pain_level from prev_timestamp to timestamp,
          handling day boundaries.
        - Otherwise, simply logs the pain_level at timestamp.
        """
        df = pd.read_csv(self.csv_path, index_col='time', parse_dates=['time'])
        end_idx = df.index.get_loc(timestamp)

        if prev_timestamp:
            start_idx = df.index.get_loc(prev_timestamp)
            d1 = datetime.fromisoformat(prev_timestamp)
            d2 = datetime.fromisoformat(str(timestamp))
            delta = d2 - d1

            prev_pain = df.iloc[start_idx]['pain_level']

            if delta.days > 0:
                # Fill prev_timestamp's day for same pain_level
                eod = prev_timestamp[:-5] + "23:00"
                eod_idx = df.index.get_loc(eod) + 1
                df.iloc[start_idx:eod_idx, df.columns.get_loc('pain_level')] = prev_pain
                # Log new pain_level
                df.iloc[end_idx, df.columns.get_loc('pain_level')] = pain_level
                print(f"Pain backfilled for [{eod} at {float(prev_pain)}]")
            else:
                # Interpolate linearly between prev and current
                step = self._normalize_pain(prev_pain, pain_level, start_idx, end_idx)
                for i in range(start_idx, end_idx + 1):
                    df.iloc[i, df.columns.get_loc('pain_level')] = round(
                        prev_pain - (step * (i - start_idx)), 1
                    )
                print(f"Pain logged from [{prev_timestamp} @ {prev_pain}] to [{timestamp} at {float(pain_level)}]")
            helper_funcs.append_config('previous_time', str(timestamp))
        else:
            # First-ever log entry
            df.iloc[end_idx, df.columns.get_loc('pain_level')] = pain_level
            helper_funcs.append_config('previous_time', str(timestamp))
            print(f"FIRST - Pain logged at [{timestamp} at {float(pain_level)}]")

        df.to_csv(self.csv_path)

    def _normalize_pain(self, prev_pain: float, curr_pain: float, start_idx: int, end_idx: int) -> float:
        """
        Calculates the per-hour decrement between prev_pain and curr_pain
        over the interval [start_idx, end_idx].
        """
        hours = end_idx - start_idx
        return 0 if hours == 0 else (prev_pain - curr_pain) / hours

handler = WeatherHandler()
handler.log_pain('2025-05-24T12:00', 7)

