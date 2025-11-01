#here we have our prediciton functions so we can updat them easily
import pandas as pd
import os
import math
from datetime import datetime, timezone 
import pytz
import numpy
import numpy as np

def wave_summary(df, bouy_name, timezone):
    # Ensure necessary columns are present
    required = ['WVHT', 'DPD','MWD','datetime']
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
    df = df.dropna(subset=['WVHT','MWD','DPD'])

    if df.empty:
        print("No usable data available after cleaning.")
        return

    # Calculate wave length and energy
    df['wave_length'] = 9.81 * (df['DPD'] ** 2) / (2 * math.pi)
    df['wave_energy'] = 1.025 * 9.81 * ((df['WVHT']) ** 2) * df['wave_length'] / 8
    df['wave_bearing'] = np.where(
        df['MWD'] > 180,
        df['MWD'] - 180,
        df['MWD'] + 180
    )
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    # Get the most recent row
    latest = df.iloc[-1]
    local_time = latest['datetime'].astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

    print(f"\n🌊 Summary for {bouy_name} Buoy at {local_time} ")
    print(f"  - Wave Height: {latest['WVHT']} m")
    print(f"  - Dominant Period: {latest['DPD']} s")
    print(f"  - Estimated Wave Energy: {latest['wave_energy']:.2f} kJ/m²")
    print(f"  - Wave Bearing: {latest['wave_bearing']:.2f} deg")
    return latest

def tide_report(df, time, timezone): #is fed the dataframe of tides and looks for the one at the time of the most recent wave data, and returns the tide status (high/low/rising/falling) at that time.
    required = ['v','datetime']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Missing required wave data columns: {missing}")
        return
        # Convert columns to numeric (in case of strings) and drop fully NaN rows
    for col in required:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['datetime'])

    if df.empty:
        print("No usable data available after cleaning.")
        return
    
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True) 
    # Get the row closest to the specified time
    df['time_diff'] = abs(df['datetime'] - time) #convert to UTC for comparison
    closest_row = df.loc[df['time_diff'].idxmin()]
    idx = df['time_diff'].idxmin()
    row_after = df.loc[idx +1 ] if idx +1 < len(df) else None
    tide_change = row_after["v"]-closest_row["v"]
    if tide_change >.2:
        tide_status = "Rising"
    elif tide_change <-.2:
        tide_status = "Falling"
    else:
        tide_status = "Slack"
    local_time = closest_row['datetime'].astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

    print(f"\n🐟 Tide Summary {local_time} ")
    print(f"  - Tide Height: {closest_row['v']:.2f} m")
    print(f"  - Tide Status: {tide_status} by {tide_change:.2f}m in the next hour")
    return closest_row 

def current_report(df, time, timezone): #is fed the dataframe of currents and looks for the one at the time of the most rectnt wave data, and returns the current speed and direction at that time.
    required = [' Velocity_Major', ' meanFloodDir',' meanEbbDir','datetime']
    missing = [col for col in required if col not in df.columns]
    if missing:
        print(f"Missing required wave data columns: {missing}")
        return
        # Convert columns to numeric (in case of strings) and drop fully NaN rows
    for col in required:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(subset=['datetime'])

    if df.empty:
        print("No usable data available after cleaning.")
        return
    
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True) #labeling the datetime at UTC
    # Get the row closest to the specified time
    df['time_diff'] = abs(df['datetime'] - time) 
    closest_row = df.loc[df['time_diff'].idxmin()]
    idx = df['time_diff'].idxmin()
    row_after = df.loc[idx +1 ] if idx +1 < len(df) else None
    current_change = row_after[" Velocity_Major"]-closest_row[" Velocity_Major"]
    if closest_row[" Velocity_Major"]> 10:
        current_status = "Flooding"
    elif closest_row[" Velocity_Major"]< 10:
        current_status = "Ebbing"
    else:
        current_status = "Slack"

    local_time = closest_row['datetime'].astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
    print(f"\n🌊 Summary for Current at {local_time}")
    print(f"  - Current Status: {current_status} at {closest_row[' Velocity_Major']:.2f} cm/s")
    print(f"  - Current Speed will accelerate by {current_change:.2f} cm/s in the next hour")
    print(f"  - Mean Flood Bearing: {closest_row[' meanFloodDir']:.2f} deg East of North")
    return closest_row 

def wind_report(df, bouy_name, timezone):
    # Ensure necessary columns are present
    required = ['WDIR','WSPD','GST','datetime']
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
    df = df.dropna(subset=['WDIR','WSPD','GST'])

    if df.empty:
        print("No usable data available after cleaning.")
        return

    # Get the most recent row
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    latest = df.iloc[-1]
    local_time = latest['datetime'].astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

    print(f"\n🌬️ Summary for {bouy_name} Buoy at {local_time}")
    print(f"  - Average wind Speed (WSPD): {latest['WSPD']} m/s")
    print(f"  - Wind Direction: {latest['WDIR']} deg from N")
    print(f"  - Wind Gust {latest['GST']:.2f} m/s")
    return latest

def setstatus(wave, buoy_id): 
    # Create folder if it doesn’t exist
    os.makedirs("data/status", exist_ok=True)
    file_path = f"data/status/{buoy_id}.csv"

    # Read file if it exists
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
    else:
        df = pd.DataFrame(columns=["datetime", "status"])

    # Convert datetime column if it exists
    if not df.empty:
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")

    # Handle case where there’s no record yet
    if df.empty:
        print(f"No record of {buoy_id} status found, creating new record")
        df.loc[0] = [wave["datetime"], wave["status"]]  # first row
        df.loc[1] = [wave["datetime"], wave["status"]]  # second row
    else:
        # Check if the last data point is more than 6 hours old
        latest_time = df["datetime"].max()
        if pd.to_datetime(wave["datetime"]) - latest_time > pd.Timedelta(hours=6):
            print(f"Data old for {buoy_id}. Last data at {latest_time} UTC")
    
        df.loc[0] = df.loc[1] # overwright
        df.loc[1] = [wave["datetime"], wave["status"]] #1 is the most recent
    # Save updated file
    df.to_csv(file_path, index=False)
    print(f"Status updated for {buoy_id}")
    return df
