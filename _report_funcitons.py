#here we have our prediciton functions so we can updat them easily
import pandas as pd
import os
import math
from datetime import datetime, timezone 
import pytz



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
    df['wave_bearing'] = df['MWD']-180 
    df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
    # Get the most recent row
    latest = df.iloc[-1]
    local_time = latest['datetime'].astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

    print(f"\n🌊 Summary for {bouy_name} Buoy at {local_time} ")
    print(f"  - Wave Height (WVHT): {latest['WVHT']} m")
    print(f"  - Dominant Period (DPD): {latest['DPD']} s")
    print(f"  - Estimated Wave Energy: {latest['wave_energy']:.2f} kJ/m²")
    print(f"  - Wave Direction: {latest['MWD']:.2f} deg")
    return latest



def tide_report(df, time, timezone): #is fed the dataframe of tides and looks for the one at the time of the most rectnt wave data, and returns the tide status (high/low/rising/falling) at that time.
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

    print(f"\n🐟 Summary for Current at {local_time} ")
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
    required = [+'datetime']
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
    latest = df.iloc[-1]
    local_time = latest['datetime'].astimezone(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")

    print(f"\n🌬️ Summary for {bouy_name} Buoy at {local_time}")
    print(f"  - Average wind Speed (WSPD): {latest['WSPD']} m/s")
    print(f"  - Wind Direction: {latest['WDIR']} deg from N")
    print(f"  - Wind Gust {latest['GST']:.2f} m/s")
    return latest

def setstatus(status, buoy_id): 
       # Create folder if it doesnt exist
    os.makedirs("data/status", exist_ok=True)
    df = pd.read_csv(f"data/raw/buoy_{buoy_id}_raw.csv")
    if df.empty or df['datetime'].max() - pd.to_datetime(latest['datetime']) > pd.Timedelta(hours=6):
        print(f"Data missing for {buoy_id}. Last data at {df['datetime'].max()}")
        df[1] = pd.DataFrame([status])
        df[2] = pd.DataFrame([status])
    else:
        print(f"Data current for {buoy_id}. Last data at {df['datetime'].max()}")
        df[2] = df[1]
        df[1] = pd.DataFrame([status])
    # Save raw
    df.to_csv(f"data/raw/buoy_{buoy_id}_raw.csv", index=False)
    print(f"Status updated")

