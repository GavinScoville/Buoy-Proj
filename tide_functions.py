import requests
import pandas as pd
import json

def predict_tides(station, begin_date, end_date, interval):
    """
    Fetch tidal predictions from NOAA CO-OPS API and return a DataFrame.
    """
    url = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
    params = {
        "product": "predictions",
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
    df = pd.DataFrame(data["predictions"])
    df["t"] = pd.to_datetime(df["t"])     # convert time column to datetime
    df["v"] = df["v"].astype(float)       # convert tide height to float

    return df

# ok this is wokring great so now we are ready to plot: 

import matplotlib.pyplot as plt

def plot_tides(tide_df, station_name="Tide Station"):
    plt.figure(figsize=(10,5))
    plt.plot(tide_df["t"], tide_df["v"], marker="o", linestyle="-")
    plt.title(f"Tidal Predictions - {station_name}")
    plt.xlabel("Time")
    plt.ylabel("Water Level (m)")
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()