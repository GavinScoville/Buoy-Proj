import os
import requests
import pandas as pd

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
