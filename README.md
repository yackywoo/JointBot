# JointBot
A personalized machine learning system that forecasts joint pain using user feedback and weather data via Discord.

---

### Features

- **Pain logging**: `/pain <level>` records your pain (0–10) with timestamp and interpolates values between entries.
- **Weather enrichment**: Automatically fetches hourly weather (temperature, pressure, humidity, etc.) from Open‑Meteo.
- **Machine learning**: Trains a Random Forest regressor to learn how weather patterns affect your pain.
- **Pain forecasting**: `/forecast` returns the maximum predicted pain per day for the next 7 days.
- **Location settings**: `/local <zip_or_city> <country>` updates your forecast location.

---

### Tech Stack

- **Language & Framework**: Python 3.12, discord.py  
- **Data & ML**: pandas, scikit‑learn, joblib  
- **Geocoding & Weather API**: Open‑Meteo  

---

### How-To

1. **Clone the repo** (excluding `data.csv` and `pain_model.pkl`)
```bash
git clone https://github.com/yourusername/jointbot.git
cd jointbot
```

2. **Create a virtual environment**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. **Configure environment**
   - Create your own `.env` file
   - Enter and save your `DISCORD_TOKEN` and `GUILD_ID`

4. **Start the Bot!**
```bash
python3 main.py
```

5. **Forecasting Prerequisites**
   - Within your Discord server, set your location using `/local <zip_or_city> <country>`
   - Once enough pain data is gathered use `/updatemodel` to generate a model
   - You can also use `/stats` beforehand to check the R^2 and MSE
   - Use `/forecast` to view the forecasted pain for the next week with the generated model