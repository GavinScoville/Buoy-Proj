import os
import glob
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

    # Append to monthly-partitioned historic store (for model training later)
    _write_historic_partitions(df_clean, f"buoy_{buoy_id}")

    return df_clean

def init_from_buoy(buoy_id="46087"):
    """Fetch wave parameters from NOAA buoy, fallback to defaults."""
    try:
        df = fetch_and_clean_buoy_data(buoy_id)
        if df is None or df.empty:
            raise ValueError("Empty dataframe")
        for idx in range(len(df) - 1, -1, -1):
            row = df.iloc[idx]
            h = row.get('WVHT') if 'WVHT' in row.index else None
            T = row.get('DPD') if 'DPD' in row.index else None
            direction = row.get('MWD') if 'MWD' in row.index else None
            if pd.notna(h) and pd.notna(T) and pd.notna(direction):
                h, T, direction = float(h), float(T), float(direction)
                print(f"✓ Loaded from buoy {buoy_id}: h={h:.2f}m, T={T}s, dir={direction}°")
                return {'h': h, 'T': T, 'direction': direction}
        raise ValueError("No valid wave data in dataframe")
    except Exception as e:
        print(f"⚠ Failed to fetch buoy data ({e}), using defaults")
        return {'h': 2.0, 'T': 12.0, 'direction': 60.0}

def _write_historic_partitions(df, key):
    """
    Append df to monthly Parquet partitions under data/historic/{key}/YYYY-MM.parquet.
    Only the month(s) present in df are read/rewritten, so months that are done
    accumulating data stay untouched and git doesn't have to re-store the whole
    history on every run.
    """
    if df is None or df.empty or "datetime" not in df:
        return
    base_dir = f"data/historic/{key}"
    os.makedirs(base_dir, exist_ok=True)
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"])
    for month, month_df in df.groupby(df["datetime"].dt.to_period("M")):
        path = f"{base_dir}/{month}.parquet"
        if os.path.exists(path):
            combined = pd.concat([pd.read_parquet(path), month_df], ignore_index=True)
        else:
            combined = month_df
        combined = combined.drop_duplicates(subset=["datetime"]).sort_values("datetime")
        combined.to_parquet(path, index=False)
    print(f"Historic data updated under {base_dir}/")

def read_recent_historic(key, months_back=1):
    """
    Load the most recent monthly historic partitions written by
    _write_historic_partitions, for use as a fallback when the live NOAA
    API is unavailable. Returns an empty DataFrame if nothing is stored yet.
    """
    base_dir = f"data/historic/{key}"
    paths = sorted(glob.glob(f"{base_dir}/*.parquet"))[-(months_back + 1):]
    if not paths:
        return pd.DataFrame()
    return pd.concat([pd.read_parquet(p) for p in paths], ignore_index=True).sort_values("datetime")

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


    # Append to monthly-partitioned historic store
    _write_historic_partitions(df, f"tide_{station}")

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



    # Append to monthly-partitioned historic store
    _write_historic_partitions(df, f"current_{station}")

    return df

