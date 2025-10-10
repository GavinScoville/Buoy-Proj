import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
import math

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
    print(f"💾 Raw data saved to {raw_path}")

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
    df = df.sort_values('datetime').bfill()

    # Drop rows that still have missing required values after filling
    df = df.dropna(subset=['WVHT', 'DPD', 'MWD'])

    if df.empty:
        print("No usable data available after cleaning.")
        return

    # Save cleaned
    clean_path = f"data/processed/buoy_{buoy_id}_processed.csv"
    df_clean.to_csv(clean_path, index=False)
    print(f" 💾 Cleaned data saved to {clean_path}")

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
    print(f" 💾  Historic data updated to {historic_path}")
    
    return df_combined



def wave_summary(df, buoy_id):
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
    df = df.sort_values('datetime').bfill()

    # Drop rows that still have missing required values after filling
    df = df.dropna(subset=['WVHT', 'DPD', 'MWD'])

    if df.empty:
        print("No usable data available after cleaning.")
        return

    # Calculate wave length and energy
    df['wave_length'] = 9.81 * (df['DPD'] ** 2) / (2 * math.pi)
    df['wave_energy'] = 1.025 * 9.81 * ((df['WVHT']) ** 2) * df['wave_length'] / 8

    # Get the most recent row
    latest = df.iloc[-1]

    print(f"\n🌊 Summary for Buoy {buoy_id} (most recent):")
    print(f"  - Wave Height (WVHT): {latest['WVHT']} m")
    print(f"  - Dominant Period (DPD): {latest['DPD']} s")
    print(f"  - Estimated Wavelength: {latest['wave_length']:.2f} m")
    print(f"  - Estimated Wave Energy: {latest['wave_energy']:.2f} kJ/m²")
    print(f"  - Wave Direction : {latest['MWD']:.2f} deg")



def plot_wave_height(df1, buoy_id1, df2, buoy_id2):
    # Check if required columns are present
    if 'WVHT' not in df1.columns or 'WVHT' not in df2.columns:
        print("Wave height (WVHT) column not found in one of the DataFrames.")
        return

    # Drop rows with missing values
    df1 = df1.dropna(subset=['datetime', 'WVHT'])
    df2 = df2.dropna(subset=['datetime', 'WVHT'])

    # Plot
    plt.figure(figsize=(10, 5))
    plt.plot(df1['datetime'], df1['WVHT'], label=f"Buoy {buoy_id1}", color='red')
    plt.plot(df2['datetime'], df2['WVHT'], label=f"Buoy {buoy_id2}", color='blue')
    
    plt.title(f"Wave Height: Buoys {buoy_id1} and {buoy_id2}")
    plt.xlabel("Date")
    plt.ylabel("Wave Height (m)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()


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

    # The API returns a structure like:
    # { 'current_predictions': { 'units': '...', 'cp': [ {..}, {..}, ... ] } }
    # Extract the list of current-prediction dicts (cp) and normalize into a DataFrame.
    cp_list = None
    if isinstance(data, dict):
        cp_list = data.get('current_predictions', {})
        if isinstance(cp_list, dict):
            cp_list = cp_list.get('cp')
    # Fallback if structure differs
    if cp_list is None:
        # try other common keys
        cp_list = data.get('cp') or data.get('current_predictions') or []

    # If cp_list is already a DataFrame-like structure, turn into DataFrame
    df = pd.DataFrame(cp_list)

    # Common JSON field is 'Time' for the timestamp; convert it to datetime if present
    if 'Time' in df.columns:
        df['datetime'] = pd.to_datetime(df['Time'])
        # Optionally drop the original 'Time' column
        # df = df.drop(columns=['Time'])

    # Coerce numeric columns to numbers where possible
    for col in df.columns:
        if col == 'datetime':
            continue
        # Remove commas/units if present then coerce
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(',', '').str.strip()
        df[col] = pd.to_numeric(df[col], errors='coerce')

    return df

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