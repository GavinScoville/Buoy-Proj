import requests
import pandas as pd
import json

def predict_currents(station, begin_date, end_date, interval):
    """
    Fetch tidal predictions from NOAA CO-OPS API and return a DataFrame.
    """
    url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    params = {
        "product": "currents_predictions",
        "application": "NOS.COOPS.TAC.WL",
        "begin_date": begin_date,
        "end_date": end_date,
        "datum": "MLLW",
        "station": station,
        "time_zone": "lst_ldt",
        "units": "metric",
        "interval": interval,
        "format": "json"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data["current_predictions"])
    return df
    

# ok this is wokring great so now we are ready to plot: 

import matplotlib.pyplot as plt

def plot_currents(tide_df, station_name="Tide Station"):
    plt.figure(figsize=(10,5))
    plt.plot(tide_df["t"], tide_df["v"], marker="o", linestyle="-")
    plt.title(f"Tidal Predictions - {station_name}")
    plt.xlabel("Time")
    plt.ylabel("Water Level (m)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

from datetime import date, timedelta
# today
today = date.today()
today_str = today.strftime("%Y%m%d")

# tomorrow
tomorrow = today + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y%m%d")


Neah_Bay_Current = "PUG1642" #PUG1642
New_Dungeness_Current = "PUG1635"

currents = predict_currents(Neah_Bay_Current, today_str, tomorrow_str, interval="h")

print(currents)


