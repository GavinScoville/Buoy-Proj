# here I am going to plot conditions for entering the bay. 

import pandas as pd
import numpy as np
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import math
import os
import cartopy.crs as ccrs
import cartopy.feature as cfeature

import matplotlib.pyplot as plt


from _fetch_buoy_functions import fetch_and_clean_buoy_data,  predict_currents, predict_tides
from _report_funcitons import  wave_summary
from _geodesy import azimuth

PacificTime = ZoneInfo("America/Los_Angeles")

Neah_Bay_Tide = "9443090"
Neah_Bay_Current = "PUG1642"
Neah_Bay = '46087' #Neah Bay bouy 
waves124 = fetch_and_clean_buoy_data(Neah_Bay) 
wave124 = wave_summary(waves124, "Neah Bay", PacificTime) 
# today
today = date.today()
today_str = today.strftime("%Y%m%d")
# tomorrow
tomorrow = today + timedelta(days=1)
tomorrow_str = tomorrow.strftime("%Y%m%d")
#GMT to PT conversion:
timezone = ZoneInfo("America/Los_Angeles")

local_time = wave124['datetime'].astimezone(PacificTime).strftime("%Y-%m-%d %H:%M:%S %Z")



# line plot https://matplotlib.org/stable/gallery/lines_bars_and_markers/simple_plot.html#sphx-glr-gallery-lines-bars-and-markers-simple-plot-py

# fill in area between two lines https://matplotlib.org/stable/gallery/lines_bars_and_markers/fill_betweenx_demo.html#sphx-glr-gallery-lines-bars-and-markers-fill-betweenx-demo-py

# energy going into the strait https://matplotlib.org/stable/gallery/lines_bars_and_markers/multicolored_line.html#sphx-glr-gallery-lines-bars-and-markers-multicolored-line-py 

def plot_tide_currents(tides, currents, local_time, timezone, station_name):

# Convert both datetime columns to Los Angeles time zone
    currents['datetime'] = pd.to_datetime(currents['datetime'], utc=True).dt.tz_convert(timezone)
    tides['datetime'] = pd.to_datetime(tides['datetime'], utc = True).dt.tz_convert(timezone)
    local_time = pd.to_datetime(local_time)

# Create the figure
    fig, ax1 = plt.subplots(figsize=(10,5))

# Plot currents on the left y-axis
    ax1.plot(currents['datetime'], currents[' Velocity_Major']/100, color='tab:blue', label='Current Velocity (m/s)')
    ax1.set_xlabel("Time (Local)")
    ax1.set_ylabel("Current Velocity (m/s)", color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

# Create a twin axis for tides
    ax2 = ax1.twinx()
    ax2.plot(tides['datetime'], tides['v'], color='tab:green', label='Tide Height (m)')
    ax2.set_ylabel("Tide Height (m)", color='tab:green')
    ax2.tick_params(axis='y', labelcolor='tab:green')

# Add vertical line for current local time
    ax1.axvline(local_time, color='red', linestyle='--', linewidth=1.5, label='Now')

# Improve appearance
    fig.autofmt_xdate()
    plt.title(f"{station_name} Currents and Tides (NOAA predicted)")
    fig.tight_layout()

# Combine legends from both axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left')

    plt.show()
    os.makedirs("plots/tidecurrent", exist_ok=True)
    fig.savefig(f"plots/tidecurrent/{station_name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


waves = waves124

def plot_waves(waves, station_name, timezone="America/Los_Angeles"):
    # Check for column existence
    if 'WVHT' not in waves.columns:
        print("Wave height (WVHT) column not found in DataFrame.")
        return
    
    # Convert datetime column (appears to be int64 → likely UNIX timestamp)
    waves['datetime'] = pd.to_datetime(waves['datetime'], utc=True).dt.tz_convert(timezone)
    
    df = waves.sort_values('datetime').bfill()

     #make bearing 
    df['wave_bearing'] = np.where(
        df['MWD'] > 180,
        df['MWD'] - 180,
        df['MWD'] + 180
    )
    
    # Filter only the last two days
    local_time = df.iloc[-1]["datetime"]
    two_days_ago = local_time - timedelta(days=2)
    df_recent = df[df['datetime'] >= two_days_ago]

    
 #Create figure
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot wave height
    ax1.plot(df_recent['datetime'], df_recent['WVHT'], color='tab:blue', label='Wave Height (m)')
    ax1.set_xlabel("Date (Local Time)")
    ax1.set_ylabel("Wave Height (m)", color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # Add second y-axis for DPD
    ax2 = ax1.twinx()
    ax2.plot(df_recent['datetime'], df_recent['DPD'], color='tab:green', linestyle='--', label='Dominant Period (s)')
    ax2.set_ylabel("Dominant Wave Period (s)", color='tab:green')
    ax2.tick_params(axis='y', labelcolor='tab:green')

    # Add a third y-axis for wave bearing (degrees)
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("outward", 60))  # shift third axis outward
    ax3.plot(df_recent['datetime'], df_recent['wave_bearing'], color='tab:orange', linestyle=':', label='Wave Bearing (°)')
    ax3.set_ylabel("Wave Bearing (°)", color='tab:orange')
    ax3.tick_params(axis='y', labelcolor='tab:orange')

    # Title and layout
    plt.title(f"Wave Conditions — Last 2 Days at {station_name}")
    fig.autofmt_xdate()
    fig.tight_layout()
    plt.grid(True)

    # Combine legends from all axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(lines + lines2 + lines3, labels + labels2 + labels3, loc='upper left')

    plt.show()
    os.makedirs("plots/waves", exist_ok=True)
    fig.savefig(f"plots/waves/{station_name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)

#neah waves will eb different becasue it is going to plot amount of KJ entering the staight pr. m2
def plot_neah_waves(waves, timezone="America/Los_Angeles"):
    # Check for column existence
    if 'WVHT' not in waves.columns:
        print("Wave height (WVHT) column not found in DataFrame.")
        return
    
    # Convert datetime column (appears to be int64 → likely UNIX timestamp)
    waves['datetime'] = pd.to_datetime(waves['datetime'], utc=True).dt.tz_convert(timezone)
    
    df = waves.sort_values('datetime').bfill()

     #make bearing 
    df['wave_bearing'] = np.where(
        df['MWD'] > 180,
        df['MWD'] - 180,
        df['MWD'] + 180
    )


#I want to see how much wave energy is entering the straight: 
    df["wave_normal"]= np.cos(np.radians(abs(df["wave_bearing"] - azimuth(48.493, 124.727,48.2248207, 122.7701732))))
    # Filter only the last two days
    local_time = df.iloc[-1]["datetime"]
    two_days_ago = local_time - timedelta(days=2)
    df['wave_length'] = 9.81 * (df['DPD'] ** 2) / (2 * math.pi)
    df['wave_energy'] = 1.025 * 9.81 * ((df['WVHT']) ** 2) * df['wave_length'] / 8 #this is pr m of crest in jouls
    df["wave_power_flux"]=df["wave_normal"]*df['wave_energy']/df['DPD']# this is watts pr m going into the stait 
    
    df_recent = df[df['datetime'] >= two_days_ago]
 #Create figure
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot wave height
    ax1.plot(df_recent['datetime'], df_recent['WVHT'], color='tab:blue', label='Wave Height (m)')
    ax1.set_xlabel("Date (Local Time)")
    ax1.set_ylabel("Wave Height (m)", color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # Add second y-axis for DPD
    ax2 = ax1.twinx()
    ax2.plot(df_recent['datetime'], df_recent['DPD'], color='tab:green', linestyle='--', label='Dominant Period (s)')
    ax2.set_ylabel("Dominant Wave Period (s)", color='tab:green')
    ax2.tick_params(axis='y', labelcolor='tab:green')

    # Add a third y-axis for wave bearing (degrees)
    ax3 = ax1.twinx()
    ax3.spines["right"].set_position(("outward", 60))  # shift third axis outward
    ax3.plot(df_recent['datetime'], df_recent["wave_power_flux"], color='tab:orange', linestyle=':', label='Watt/m')
    ax3.set_ylabel("Wave Power Flux (Watt/m)", color='tab:orange')
    ax3.tick_params(axis='y', labelcolor='tab:orange')

    # Title and layout
    plt.title(f"Wave Conditions — Last 2 Days at the entrance to the Strait")
    fig.autofmt_xdate()
    fig.tight_layout()
    plt.grid(True)

    # Combine legends from all axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    lines3, labels3 = ax3.get_legend_handles_labels()
    ax1.legend(lines + lines2 + lines3, labels + labels2 + labels3, loc='upper left')

    plt.show()
    os.makedirs("plots/waves", exist_ok=True)
    fig.savefig(f"plots/waves/Neah_Bay.png", bbox_inches="tight", dpi=150)
    plt.close(fig)


def plot_wind(waves, station_name="Neah Bay", timezone="America/Los_Angeles"):
    # Check for column existence
    if 'WSPD' not in waves.columns:
        print("Wind Speed (WSPD) column not found in DataFrame.")
        return
    
    # Convert datetime column (appears to be int64 → likely UNIX timestamp)
    waves['datetime'] = pd.to_datetime(waves['datetime'], utc=True).dt.tz_convert(timezone)
    
    df = waves.sort_values('datetime').bfill()

     #make bearing 
    df['wind_bearing'] = np.where(
        df['WDIR'] > 180,
        df['WDIR'] - 180,
        df['WDIR'] + 180
    )
    
    # Filter only the last two days
    local_time = df.iloc[-1]["datetime"]
    two_days_ago = local_time - timedelta(days=2)
    df_recent = df[df['datetime'] >= two_days_ago]
    
    #Create figure
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Plot wave height
    ax1.plot(df_recent['datetime'], df_recent['WSPD'], color='tab:blue', label='Wind Speed (m/s)')
    ax1.set_xlabel("Date (Local Time)")
    ax1.set_ylabel("Wind Speed (m/s) at 3.8m above water", color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # Add a third y-axis for wave bearing (degrees)
    ax2 = ax1.twinx()
    ax2.spines["right"] # shift third axis outward
    ax2.plot(df_recent['datetime'], df_recent['PRES'], color='tab:orange', linestyle=':', label='Air Pressure hPa')
    ax2.set_ylabel("Air Pressure hPa", color='tab:orange')
    ax2.tick_params(axis='y', labelcolor='tab:orange')

    # Title and layout
    plt.suptitle(f"Wind Conditions — Last 2 Days at {station_name}")
    ax1.set_title(f"Wind currently blowing from {df_recent["WDIR"].iloc[-1]}°", fontsize=12) 
    fig.autofmt_xdate()
    fig.tight_layout()
    plt.grid(True)

    # Combine legends from all axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left')

    plt.show()
    os.makedirs("plots/wind", exist_ok=True)
    fig.savefig(f"plots/wind/{station_name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
