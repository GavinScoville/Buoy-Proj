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
import matplotlib.cm as cm
import matplotlib.colors as mcolors

from matplotlib.collections import LineCollection
from datetime import timedelta

from _geodesy import azimuth

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

    os.makedirs("plots/tidecurrent", exist_ok=True)
    fig.savefig(f"plots/tidecurrent/{station_name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)

def plot_waves(waves, station_name, timezone="America/Los_Angeles", lat=49.903, lon=-145.246):
    # Check for necessary columns
    if 'WVHT' not in waves.columns or 'DPD' not in waves.columns or 'MWD' not in waves.columns:
        print("Missing required columns (WVHT, DPD, or MWD) in DataFrame.")
        return

    # Convert datetime column
    waves['datetime'] = pd.to_datetime(waves['datetime'], utc=True).dt.tz_convert(timezone)
    df = waves.sort_values('datetime').bfill()

    # Compute wave bearing (convert from direction *from* → direction *to*)
    df['wave_bearing'] = np.where(df['MWD'] > 180, df['MWD'] - 180, df['MWD'] + 180)

    # Filter last 2 days
    local_time = df.iloc[-1]["datetime"]
    two_days_ago = local_time - timedelta(days=2)
    df_recent = df[df['datetime'] >= two_days_ago].reset_index(drop=True)

    # Compute deviation ("miss") from Fort Ebey direction
    azy = azimuth(lat, lon, 48.2248207, 122.7701732)
    df_recent["miss"] = (df_recent['wave_bearing'] - azy + 180) % 360 - 180  # range [-180, 180]

    # Setup colormap
    cmap = cm.viridis
    vmin, vmax = -90, 90
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

    # Convert datetimes to numeric for plotting
    times = df_recent["datetime"].map(pd.Timestamp.timestamp).to_numpy()

    # --- Create figure and main axis
    fig, ax1 = plt.subplots(figsize=(10, 6))

    # Function to create color-mapped line segments
    def make_colored_line(x, y, c):
        points = np.array([x, y]).T.reshape(-1, 1, 2)
        segments = np.concatenate([points[:-1], points[1:]], axis=1)
        lc = LineCollection(segments, cmap=cmap, norm=norm)
        lc.set_array(c[:-1])
        lc.set_linewidth(2.5)
        return lc

    # --- Plot Wave Height (WVHT)
    lc1 = make_colored_line(times, df_recent["WVHT"].to_numpy(), df_recent["miss"].to_numpy())
    ax1.add_collection(lc1)
    ax1.set_xlim(times.min(), times.max())
    ax1.set_ylim(df_recent["WVHT"].min(), df_recent["WVHT"].max())
    ax1.set_ylabel("Wave Height (m)", color='black')

    # Format datetime x-axis
    import matplotlib.dates as mdates
    ax1.xaxis_date()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))

    # --- Second y-axis for DPD
    ax2 = ax1.twinx()
    lc2 = make_colored_line(times, df_recent["DPD"].to_numpy(), df_recent["miss"].to_numpy())
    lc2.set_linestyle("--")
    ax2.add_collection(lc2)
    ax2.set_xlim(times.min(), times.max())
    ax2.set_ylim(df_recent["DPD"].min(), df_recent["DPD"].max())
    ax2.set_ylabel("Dominant Wave Period (s)", color='black')

    # --- Add horizontal colorbar for wave direction miss
    sm = cm.ScalarMappable(norm=norm, cmap=cmap)
    cbar = fig.colorbar(sm, ax=[ax1, ax2], orientation="horizontal", pad=0.12, fraction=0.04, aspect=40)
    cbar.set_label("Wave Bearing Miss (° from Fort Ebey)", fontsize=11)

    # --- Title and layout
    plt.title(f"Wave Conditions — Last 2 Days at {station_name}", fontsize=14, fontweight='bold')
    fig.autofmt_xdate()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    # Save figure
    os.makedirs("plots/waves", exist_ok=True)
    fig.savefig(f"plots/waves/{station_name}.png", bbox_inches="tight", dpi=180)
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
    ax1.set_title(f"Wind currently blowing from {df_recent['WDIR'].iloc[-1]}°", fontsize=12) 
    fig.autofmt_xdate()
    fig.tight_layout()
    plt.grid(True)

    # Combine legends from all axes
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left')

    
    os.makedirs("plots/wind", exist_ok=True)
    fig.savefig(f"plots/wind/{station_name}.png", bbox_inches="tight", dpi=150)
    plt.close(fig)
