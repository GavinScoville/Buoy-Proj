import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import math
from io import StringIO

def fetch_and_clean_buoy_data(buoy_id):
    """
    Fetches and cleans NOAA buoy data for the given buoy ID.
    Saves both raw and processed CSVs in data/raw/ and data/processed/.
    """
    url = f"https://www.ndbc.noaa.gov/data/realtime2/{buoy_id}.txt"
    response = requests.get(url)

    if response.status_code != 200:
        print(f" Failed to fetch data. Status code: {response.status_code}")
        return None

    lines = response.text.splitlines()
    headers = lines[0].split()
    data = [line.split() for line in lines[2:]]  # Skip units line

    df = pd.DataFrame(data, columns=headers)

    # Create folders
    os.makedirs("data/raw", exist_ok=True)
    os.makedirs("data/processed", exist_ok=True)
    os.makedirs("data/historic", exist_ok=True)

    # Save raw
    raw_path = f"data/raw/buoy_{buoy_id}_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"Raw data saved to {raw_path}")

    # Clean
    date_cols = ['#YY', 'MM', 'DD', 'hh', 'mm']
    try:
        df['datetime'] = pd.to_datetime(
            df[date_cols].astype(str).agg('-'.join, axis=1),
            format="%Y-%m-%d-%H-%M"
        )
    except Exception as e:
        print(f" Could not convert datetime: {e}")

    for col in df.columns:
        if col not in date_cols + ['datetime']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    df_clean = df.drop(columns=date_cols)
#Handel NAs

    # Ensure necessary columns are present
    required = ['WVHT', 'DPD', 'MWD', 'datetime']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Missing required wave data columns: {missing}")
        return

    # Convert columns to numeric (in case of strings) and drop fully NaN rows
    for col in required:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['datetime'])

    # Forward-fill all columns to deal with random gaps

    if df.empty:
        print("No usable data available after cleaning.")
        return

    # Save cleaned
    clean_path = f"data/processed/buoy_{buoy_id}_processed.csv"
    df_clean.to_csv(clean_path, index=False)
    print(f"Cleaned data saved to {clean_path}")

    # Merge with old data to create longer and longer df: 
    historic_path = f"data/historic/buoy_{buoy_id}_historic.csv"
     # Save raw
    try:
        df_historic = pd.read_csv(historic_path, parse_dates=["datetime"])
    except FileNotFoundError:
        df_historic = pd.DataFrame()

        # Combine old + new data
    df_combined = pd.concat([df_historic, df_clean], ignore_index=True)
    # Remove duplicates (e.g., based on timestamp or ID)
    df_combined = df_combined.drop_duplicates(subset=["datetime"])
    # Sort if needed
    df_combined = df_combined.sort_values("datetime")
    # Save historic
    df_combined.to_csv(historic_path, index=False)
    print(f"Historic data updated to {historic_path}")
    
    return df_clean


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
        "time_zone": "gmt",
        "units": "metric",
        "interval": interval,
        "format": "json"
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    df = pd.DataFrame(data["predictions"])
    df["datetime"] = pd.to_datetime(df["t"])     # convert time column to datetime
    df["v"] = df["v"].astype(float)       # convert tide height to float


    # Merge with old data to create longer and longer df: 
    historic_path = f"data/historic/tide_{station}_historic.csv"
     # Save raw
    try:
        df_historic = pd.read_csv(historic_path, parse_dates=["datetime"])
    except FileNotFoundError:
        df_historic = pd.DataFrame()

    # Combine old + new data
    df_combined = pd.concat([df_historic, df], ignore_index=True)
    # Remove duplicates (e.g., based on timestamp or ID)
    df_combined = df_combined.drop_duplicates(subset=["datetime"])
    # Sort if needed
    df_combined = df_combined.sort_values("datetime")
    # Save historic
    df_combined.to_csv(historic_path, index=False)
    print(f"Historic Tides updated to {historic_path}")

    return df


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
        "time_zone": "gmt",
        "units": "metric",
        "interval": interval,
        "format": "csv"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()

    # Load CSV into pandas directly
    text = response.text
    # Some CSVs from the API include leading metadata lines; let pandas infer header
    try:
        df = pd.read_csv(StringIO(text))
    except Exception:
        # fallback: try reading without header and infer
        df = pd.read_csv(StringIO(text), header=0, error_bad_lines=False)

    # Many CSVs use 'Time' or 'time' for timestamp column
    time_cols = [c for c in df.columns if c.lower() in ('time', 't', 'datetime')]
    if time_cols:
        df['datetime'] = pd.to_datetime(df[time_cols[0]])

    # Coerce numeric columns to numbers where possible
    for col in df.columns:
        if col == 'datetime':
            continue
        # Remove commas/units if present then coerce
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '').str.strip()
        df[col] = pd.to_numeric(df[col], errors='coerce')



    historic_path = f"data/historic/current_{station}_historic.csv"
     # get old data
    try:
        df_historic = pd.read_csv(historic_path, parse_dates=["datetime"])
    except FileNotFoundError:
        df_historic = pd.DataFrame()

    # Combine that old n new data
    df_combined = pd.concat([df_historic, df], ignore_index=True)
    # Remove duplicates 
    df_combined = df_combined.drop_duplicates(subset=["datetime"])
    # Sort if needed
    df_combined = df_combined.sort_values("datetime")
    # Save historic
    df_combined.to_csv(historic_path, index=False)
    print(f"Historic Currents updated to {historic_path}")

    return df

